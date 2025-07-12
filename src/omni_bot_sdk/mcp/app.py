#!/usr/bin/env python
# -*- coding: utf-8 -*-

import functools
import hashlib
import json
import logging
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import asdict, dataclass
from typing import Any, Callable, List, Literal, Optional, Tuple

from mcp.server.fastmcp import Context, FastMCP
from omni_bot_sdk.clients.mqtt_client import MQTTClient
from omni_bot_sdk.mcp.dispatchers import MqttCommandDispatcher
from omni_bot_sdk.mcp.protocols import CommandDispatcher
from omni_bot_sdk.models import Contact, UserInfo
from omni_bot_sdk.rpa.action_handlers import RPAActionType
from omni_bot_sdk.services.core.database_service import DatabaseService
from omni_bot_sdk.weixin.message_classes import MessageType

# 配置日志记录
logger = logging.getLogger(__name__)


@dataclass
class AppContext:
    """
    应用上下文，包含所有共享资源。
    用于在FastMCP生命周期内传递数据库、用户信息、命令分发器等。
    """

    db: DatabaseService
    userinfo: UserInfo
    command_dispatcher: CommandDispatcher


def init_mqtt_client(config: dict) -> MQTTClient:
    """
    初始化并连接MQTT客户端。
    支持异常捕获和日志记录。
    """
    client_id = f"mcp-client"
    client = MQTTClient(
        host=config.get("host", "127.0.0.1"),
        port=config.get("port", 1883),
        client_id=client_id,
        username=config.get("username", "weixin"),
        password=config.get("password", "123456"),
    )
    try:
        client.connect()
        logger.info("MQTT客户端连接成功。")
    except Exception as e:
        logger.error(f"MQTT初始连接失败: {e}")
    return client


@asynccontextmanager
async def app_lifespan(
    app: FastMCP, db: DatabaseService, user_info: UserInfo, mqtt_config: dict
) -> AsyncIterator[AppContext]:
    """
    管理应用生命周期，创建上下文并将其yield给FastMCP框架。
    负责MQTT连接、命令分发器初始化及资源释放。
    """
    logger.info("应用生命周期开始，正在初始化上下文...")

    mqtt_client = init_mqtt_client(mqtt_config)
    dispatcher = MqttCommandDispatcher(mqtt_client, user_info)

    app_context = AppContext(
        db=db,
        userinfo=user_info,
        command_dispatcher=dispatcher,
    )

    try:
        yield app_context
    finally:
        logger.warning("应用关闭，正在释放资源...")
        if hasattr(app_context.command_dispatcher, "mqtt"):
            app_context.command_dispatcher.mqtt.disconnect()
        logger.info("资源释放完成。")


def handle_tool_exceptions(func: Callable) -> Callable:
    """
    工具函数异常处理装饰器。
    捕获并返回清晰的错误信息，便于前端/调用方处理。
    """

    @functools.wraps(func)
    def wrapper(*args, **kwargs) -> Any:
        try:
            return func(*args, **kwargs)
        except Exception as e:
            error_msg = f"工具调用出错: {type(e).__name__}: {str(e)}"
            logger.error(f"错误详情: {error_msg}", exc_info=True)
            return error_msg

    return wrapper


def _get_app_context_from_request(ctx: Context) -> AppContext:
    """
    从请求上下文中安全地获取应用上下文。
    FastMCP 预期路径: ctx.request_context.lifespan_context
    """
    if not hasattr(ctx.request_context, "lifespan_context"):
        raise RuntimeError("严重错误：应用上下文未在lifespan中正确初始化或传递。")
    return ctx.request_context.lifespan_context


def _find_contact_by_identifier(
    db: DatabaseService,
    identifier: str,
    contact_type: Literal["user", "group", "any"] = "any",
) -> Tuple[Optional[Contact], Optional[str]]:
    """
    通过标识符查找联系人或群组。
    支持用户名、昵称、备注等多种方式。
    contact_type: 限定查找类型（user/group/any）。
    """
    contact = db.get_contact_by_username(identifier)
    if contact:
        is_group = contact.username.endswith("@chatroom")
        if contact_type == "group" and not is_group:
            return None, f"错误：'{identifier}' 是一个用户，但此处需要一个群组。"
        if contact_type == "user" and is_group:
            return None, f"错误：'{identifier}' 是一个群组，但此处需要一个用户。"
        return contact, None

    contacts = db.get_contact_by_display_name(identifier)
    if not contacts:
        return None, f"错误：找不到名为 '{identifier}' 的联系人或群组。"

    if contact_type == "group":
        contacts = [c for c in contacts if c.username.endswith("@chatroom")]
    elif contact_type == "user":
        contacts = [c for c in contacts if not c.username.endswith("@chatroom")]

    if not contacts:
        return (
            None,
            f"错误：找不到类型为 '{contact_type}' 且名为 '{identifier}' 的对象。",
        )

    if len(contacts) > 1:
        options = [c.to_json() for c in contacts]
        return (
            None,
            f"歧义：找到多个名为 '{identifier}' 的对象，请使用更精确的名称或ID。选项: {json.dumps(options, ensure_ascii=False, indent=2)}",
        )

    return contacts[0], None


def _resolve_recipient(
    ctx: Context, identifier: str
) -> Tuple[Optional[Contact], Optional[str]]:
    """
    解析收信人（用户或群组）。
    """
    app_context = _get_app_context_from_request(ctx)
    return _find_contact_by_identifier(app_context.db, identifier, contact_type="any")


def _resolve_room(
    ctx: Context, identifier: str
) -> Tuple[Optional[Contact], Optional[str]]:
    """
    解析群聊。
    """
    app_context = _get_app_context_from_request(ctx)
    return _find_contact_by_identifier(app_context.db, identifier, contact_type="group")


def _resolve_user(
    ctx: Context, identifier: str
) -> Tuple[Optional[Contact], Optional[str]]:
    """
    解析单个用户。
    """
    app_context = _get_app_context_from_request(ctx)
    return _find_contact_by_identifier(app_context.db, identifier, contact_type="user")


def _resolve_room_member(
    ctx: Context, room: Contact, identifier: str
) -> Tuple[Optional[Contact], Optional[str]]:
    """
    在指定群聊中查找成员。
    支持昵称、用户名、群备注等多种方式。
    """
    app_context = _get_app_context_from_request(ctx)
    room_member_list = app_context.db.get_room_member_list(room.username)
    for member in room_member_list:
        if (
            member.display_name == identifier
            or member.username == identifier
            or member.nick_name == identifier
            or member.room_remark == identifier
        ):
            return member, None
    return None, f"错误：在群'{room.display_name}'中找不到名为 '{identifier}' 的成员。"


def create_app(db: DatabaseService, user_info: UserInfo, config: dict) -> FastMCP:
    """
    创建并配置MCP应用实例，采用依赖注入。
    注册所有MCP工具函数，支持微信消息、群管理、朋友圈等操作。
    """
    lifespan_handler = functools.partial(
        app_lifespan, db=db, user_info=user_info, mqtt_config=config.get("mqtt", {})
    )
    mcp_config = config.get("mcp", {})
    mcp = FastMCP(
        name="WeiXinMCP",
        instructions="""
        你是一个微信助手，可以分析数据和执行操作。
        - 查询指定联系人或群组的聊天记录。
        - 发送文本、文件或“拍一拍”消息。
        - 管理群聊：查看/邀请/移除成员，修改群名，发布公告等。
        - 发布朋友圈。
        在调用工具时，请使用用户的确切昵称、备注或微信ID。如果存在多个同名用户，我会提示你进行选择。
        """,
        lifespan=lifespan_handler,
        json_response=True,
        host=mcp_config.get("host", "127.0.0.1"),
        port=mcp_config.get("port", 8000),
    )

    # --- 工具函数定义 ---

    @mcp.tool()
    @handle_tool_exceptions
    def get_timestamp(ctx: Context) -> int:
        """
        获取当前时间的Unix时间戳（毫秒）。
        """
        return int(time.time() * 1000)

    @mcp.tool()
    @handle_tool_exceptions
    def get_wechat_user_info(ctx: Context) -> str:
        """
        获取当前登录的微信用户信息（敏感信息已脱敏）。
        """
        app_context = _get_app_context_from_request(ctx)
        user_info_dict = asdict(app_context.userinfo)
        for key in ["alias", "account", "phone", "data_dir", "key"]:
            if user_info_dict.get(key) and len(str(user_info_dict[key])) > 1:
                user_info_dict[key] = str(user_info_dict[key])[0] + "*" * (
                    len(str(user_info_dict[key])) - 1
                )
        user_info_dict["db_keys"] = {}
        return json.dumps(user_info_dict, ensure_ascii=False, indent=4)

    @mcp.tool()
    @handle_tool_exceptions
    def query_wechat_msg(
        ctx: Context,
        contact_name: str,
        query: Optional[str] = None,
        start_timestamp: Optional[int] = None,
        end_timestamp: Optional[int] = None,
        limit: Optional[int] = 500,
    ) -> str:
        """
        查询指定用户或群组的微信消息记录。
        支持内容关键字、时间范围、数量限制等参数。
        """
        app_context = _get_app_context_from_request(ctx)
        contact, error = _resolve_recipient(ctx, contact_name)
        if error:
            return error
        db = app_context.db
        db_path = db.get_db_path_by_username(contact.username)
        if not db_path:
            return f"找不到 '{contact.display_name}' 的数据库文件。"
        username_md5 = hashlib.md5(contact.username.encode()).hexdigest()
        start = int((start_timestamp or 0) / 1000)
        end = int((end_timestamp or int(time.time() * 1000)) / 1000)
        sql = f"""SELECT a.message_content, b.user_name FROM Msg_{username_md5} a 
                   LEFT JOIN (SELECT ROW_NUMBER() OVER () AS id, user_name FROM Name2Id) b ON a.real_sender_id=b.id  
                   WHERE a.local_type=1 AND a.create_time BETWEEN {start} AND {end}"""
        if query:
            sql += f" AND a.message_content LIKE '%{query}%'"
        sql += f" ORDER BY a.sort_seq DESC LIMIT {limit}"
        msg_list = db.execute_query(db_path, sql)
        processed_msg_list = [
            {
                "from": (
                    db.get_contact_by_username(msg[1]).display_name
                    if db.get_contact_by_username(msg[1])
                    else "未知发件人"
                ),
                "text": msg[0],
            }
            for msg in msg_list
            if isinstance(msg[0], str)
        ]
        logger.info(
            f"为 '{contact.display_name}' 查询到 {len(processed_msg_list)} 条消息。"
        )
        return json.dumps(processed_msg_list, ensure_ascii=False, indent=None)

    @mcp.tool()
    @handle_tool_exceptions
    def send_text_msg(
        ctx: Context,
        recipient_name: str,
        message: str,
        at_user_name: Optional[str] = None,
    ) -> str:
        """
        向用户或群组发送文本消息。
        支持@群成员。
        """
        app_context = _get_app_context_from_request(ctx)
        recipient, error = _resolve_recipient(ctx, recipient_name)
        if error:
            return error

        at_list = []
        is_chatroom = recipient.username.endswith("@chatroom")
        if at_user_name:
            if not is_chatroom:
                return "错误：只能在群聊中@成员。"
            at_user, error = _resolve_room_member(ctx, recipient, at_user_name)
            if error:
                return f"错误：在群'{recipient.display_name}'中找不到要@的用户 '{at_user_name}'。"
            at_list.append(at_user.display_name)

        topic = f"msg/{app_context.userinfo.account}/rpa_action"
        payload = {
            "local_type": MessageType.Text,
            "message_content": message,
            "username": recipient.username,
            "nickname": recipient.display_name,
            "at_list": at_list,
            "is_chatroom": is_chatroom,
            "create_time": int(time.time()),
        }
        app_context.command_dispatcher.dispatch(topic, payload)
        return f"消息已成功提交至 '{recipient.display_name}'。"

    @mcp.tool()
    @handle_tool_exceptions
    def send_pat_msg(
        ctx: Context, user_name: str, room_name: Optional[str] = None
    ) -> str:
        """
        发送“拍一拍”消息。
        支持群聊和单聊。
        """
        app_context = _get_app_context_from_request(ctx)

        target_user = None
        patted_user_display_name = ""

        if room_name:
            room, error = _resolve_room(ctx, room_name)
            if error:
                return error
            patted_user, error = _resolve_room_member(ctx, room, user_name)
            if error:
                return error
            target_user = room
            patted_user_display_name = patted_user.display_name
        else:
            user, error = _resolve_user(ctx, user_name)
            if error:
                return error
            target_user = user
            patted_user_display_name = user.display_name

        topic = f"msg/{app_context.userinfo.account}/rpa_action"
        payload = {
            "local_type": MessageType.Pat,
            "message_content": "",
            "username": target_user.username,
            "nickname": target_user.display_name,
            "at_list": [patted_user_display_name],
            "is_chatroom": target_user.username.endswith("@chatroom"),
            "create_time": int(time.time()),
        }
        app_context.command_dispatcher.dispatch(topic, payload)
        return f"已成功提交向 '{patted_user_display_name}' 发送“拍一拍”的任务。"

    @mcp.tool()
    @handle_tool_exceptions
    def send_file_msg(ctx: Context, recipient_name: str, file_path: str) -> str:
        """
        向用户或群组发送文件（如图片、视频）。
        """
        app_context = _get_app_context_from_request(ctx)
        recipient, error = _resolve_recipient(ctx, recipient_name)
        if error:
            return error

        topic = f"msg/{app_context.userinfo.account}/rpa_action"
        payload = {
            "local_type": MessageType.File,
            "message_content": "",
            "username": recipient.username,
            "nickname": recipient.display_name,
            "file": file_path,
            "is_chatroom": recipient.username.endswith("@chatroom"),
            "create_time": int(time.time()),
        }
        app_context.command_dispatcher.dispatch(topic, payload)
        return f"向 '{recipient.display_name}' 发送文件的任务已提交。"

    @mcp.tool()
    @handle_tool_exceptions
    def send_pyq(
        ctx: Context, content: str = "", images: Optional[List[str]] = None
    ) -> str:
        """
        发布一条朋友圈。
        """
        app_context = _get_app_context_from_request(ctx)
        return app_context.command_dispatcher.dispatch_rpa(
            RPAActionType.SEND_PYQ.value, {"content": content, "images": images or []}
        )

    @mcp.tool()
    @handle_tool_exceptions
    def query_room_member_list(ctx: Context, room_name: str) -> str:
        """
        查询指定群聊的成员列表。
        返回成员的JSON信息。
        """
        app_context = _get_app_context_from_request(ctx)
        room, error = _resolve_room(ctx, room_name)
        if error:
            return error
        members = app_context.db.get_room_member_list(room.username)
        return json.dumps([m.to_json() for m in members], ensure_ascii=False, indent=2)

    @mcp.tool()
    @handle_tool_exceptions
    def remove_room_member(ctx: Context, room_name: str, member_name: str) -> str:
        """
        从群聊中移除一个成员。
        """
        app_context = _get_app_context_from_request(ctx)
        room, error = _resolve_room(ctx, room_name)
        if error:
            return error
        member, error = _resolve_room_member(ctx, room, member_name)
        if error:
            return f"无法在群'{room.display_name}'中找到要移除的成员 '{member_name}'。"
        return app_context.command_dispatcher.dispatch_rpa(
            RPAActionType.REMOVE_ROOM_MEMBER.value,
            {"target": room.display_name, "user_name": member.display_name},
        )

    @mcp.tool()
    @handle_tool_exceptions
    def invite_room_member(ctx: Context, room_name: str, user_name: str) -> str:
        """
        邀请一个用户加入群聊。
        """
        app_context = _get_app_context_from_request(ctx)
        room, error = _resolve_room(ctx, room_name)
        if error:
            return error
        user_to_invite, error = _resolve_user(ctx, user_name)
        if error:
            return error
        return app_context.command_dispatcher.dispatch_rpa(
            RPAActionType.INVITE_2_ROOM.value,
            {"target": room.display_name, "user_name": user_to_invite.display_name},
        )

    @mcp.tool()
    @handle_tool_exceptions
    def public_room_announcement(
        ctx: Context, room_name: str, content: str, force_edit: bool = False
    ) -> str:
        """
        发布或编辑群公告。
        """
        app_context = _get_app_context_from_request(ctx)
        room, error = _resolve_room(ctx, room_name)
        if error:
            return error
        return app_context.command_dispatcher.dispatch_rpa(
            RPAActionType.PUBLIC_ROOM_ANNOUNCEMENT.value,
            {"target": room.display_name, "content": content, "force_edit": force_edit},
        )

    @mcp.tool()
    @handle_tool_exceptions
    def rename_room_name(ctx: Context, room_name: str, new_name: str) -> str:
        """
        重命名一个群聊。
        """
        app_context = _get_app_context_from_request(ctx)
        room, error = _resolve_room(ctx, room_name)
        if error:
            return error
        return app_context.command_dispatcher.dispatch_rpa(
            RPAActionType.RENAME_ROOM_NAME.value,
            {"target": room.display_name, "name": new_name},
        )

    @mcp.tool()
    @handle_tool_exceptions
    def rename_room_remark(ctx: Context, room_name: str, new_remark: str) -> str:
        """
        为群聊设置或修改备注。
        """
        app_context = _get_app_context_from_request(ctx)
        room, error = _resolve_room(ctx, room_name)
        if error:
            return error
        return app_context.command_dispatcher.dispatch_rpa(
            RPAActionType.RENAME_ROOM_REMARK.value,
            {"target": room.display_name, "remark": new_remark},
        )

    @mcp.tool()
    @handle_tool_exceptions
    def rename_name_in_room(ctx: Context, room_name: str, new_name_in_room: str) -> str:
        """
        修改“我”在某个群聊中的昵称。
        """
        app_context = _get_app_context_from_request(ctx)
        room, error = _resolve_room(ctx, room_name)
        if error:
            return error
        return app_context.command_dispatcher.dispatch_rpa(
            RPAActionType.RENAME_NAME_IN_ROOM.value,
            {"target": room.display_name, "name": new_name_in_room},
        )

    @mcp.tool()
    @handle_tool_exceptions
    def leave_room(ctx: Context, room_name: str) -> str:
        """
        退出一个群聊。
        """
        app_context = _get_app_context_from_request(ctx)
        room, error = _resolve_room(ctx, room_name)
        if error:
            return error
        return app_context.command_dispatcher.dispatch_rpa(
            RPAActionType.LEAVE_ROOM.value, {"target": room.display_name}
        )

    return mcp


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    class MockDb:
        def get_contact_by_username(self, uname):
            return None

        def get_contact_by_display_name(self, dname):
            return []

        def get_db_path_by_username(self, uname):
            return "mock_db_path"

        def execute_query(self, *args, **kwargs):
            return []

        def get_room_member_list(self, uname):
            return []

    mock_user_info = UserInfo(
        account="test_user",
        name="测试用户",
        data_dir="/tmp",
        mobile="13800138000",
        db_keys={},
        key="mock_key",
        small_head_url="",
        big_head_url="",
        alias="",
        city="",
        province="",
        country="",
    )

    mcp_app = create_app(db=MockDb(), user_info=mock_user_info)
    mcp_app.run(transport="streamable-http")

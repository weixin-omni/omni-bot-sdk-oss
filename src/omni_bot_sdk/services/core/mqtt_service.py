"""
MQTT 服务模块。
提供 MQTT 消息发布、订阅等相关服务。
"""

import logging
import time
from queue import Queue
from typing import Any, Dict

from omni_bot_sdk.clients.mqtt_client import MQTTClient
from omni_bot_sdk.models import UserInfo
from omni_bot_sdk.rpa.action_handlers import (
    Invite2RoomAction,
    LeaveRoomAction,
    PatAction,
    RemoveRoomMemberAction,
    RenameNameInRoomAction,
    RenameRoomNameAction,
    RenameRoomRemarkAction,
    SendFileAction,
    SendPyqAction,
    SendTextMessageAction,
    PublicRoomAnnouncementAction,
)
from omni_bot_sdk.rpa.action_handlers import RPAActionType
from omni_bot_sdk.services.core.database_service import DatabaseService
from omni_bot_sdk.utils.helpers import download_file_if_url
from omni_bot_sdk.weixin.message_classes import MessageType


class MQTTService:
    def __init__(
        self,
        user_info: UserInfo,
        db: DatabaseService,
        rpa_task_queue: Queue,
        mqtt_config: dict,
    ):
        self.host = mqtt_config.get("host")
        self.port = mqtt_config.get("port")
        self.client_id = mqtt_config.get("client_id")
        self.username = mqtt_config.get("username")
        self.password = mqtt_config.get("password")
        self.db = db
        self.mqtt_client = None
        self.rpa_task_queue = rpa_task_queue
        self.logger = logging.getLogger(__name__)
        self.max_retries = 3
        self.retry_delay = 5  # 重试间隔（秒）
        self.userinfo = user_info

    def setup(self):
        self.mqtt_client = MQTTClient(
            self.host, self.port, self.client_id, self.username, self.password
        )

    def start(self):
        """启动MQTT服务"""
        self.mqtt_client.set_message_callback(self._handle_message)
        retry_count = 0

        while retry_count < self.max_retries:
            try:
                self.mqtt_client.connect()
                self._subscribe_topics()
                self.logger.info(f"MQTT服务已启动")
                return
            except Exception as e:
                retry_count += 1
                if retry_count < self.max_retries:
                    self.logger.warning(
                        f"MQTT连接失败，{self.retry_delay}秒后重试 ({retry_count}/{self.max_retries}): {str(e)}"
                    )
                    time.sleep(self.retry_delay)
                else:
                    self.logger.error(f"MQTT连接失败，已达到最大重试次数: {str(e)}")
                    raise

    def _subscribe_topics(self):
        # 这里订阅的内容，和用户是强相关的，只订阅用户自己的频道比较合理
        account = self.userinfo.account
        self.mqtt_client.subscribe(f"msg/{account}/rpa_action")
        self.mqtt_client.subscribe(f"msg/{account}/other_rpa_action")

    def _handle_message(self, msg: Dict[str, Any]):
        """同步回调，调度异步消息处理，不阻塞MQTT主线程"""
        try:
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(self._handle_message_async(msg))
                else:
                    asyncio.run(self._handle_message_async(msg))
            except RuntimeError:
                # 没有事件循环
                asyncio.run(self._handle_message_async(msg))
        except Exception as e:
            self.logger.error(f"处理消息时出错: {e}")

    async def _handle_message_async(self, msg: Dict[str, Any]):
        """异步处理接收到的MQTT消息

        根据消息主题进行分发处理，目前支持:
        1. RPA动作消息(msg/{account}/rpa_action):
           - 文本消息(local_type=MessageType.Text): 构造发送文本动作
           - 文件消息(local_type=MessageType.File): 下载文件后构造发送文件动作
        将有效动作放入RPA任务队列等待执行

        Args:
            msg (Dict[str, Any]): MQTT消息字典，包含topic和payload等字段

        Raises:
            Exception: 记录处理过程中出现的任何错误到日志
        """
        try:
            topic = msg.get("topic")
            if topic == f"msg/{self.userinfo.account}/rpa_action":
                payload = msg.get("payload")
                local_type = payload.get("local_type")
                action = None
                if local_type == MessageType.Text:
                    at_list = payload.get("at_list")
                    if len(at_list) == 0:
                        action = SendTextMessageAction(
                            content=payload.get("message_content"),
                            target=payload.get("nickname"),
                        )
                    else:
                        action = SendTextMessageAction(
                            content=payload.get("message_content"),
                            target=payload.get("nickname"),
                            at_user_name=at_list[0],
                        )
                elif local_type == MessageType.File:
                    file_path = payload.get("file")
                    file_path = await download_file_if_url(file_path)
                    self.logger.info(f"下载文件：{file_path}")
                    action = SendFileAction(
                        file_path=file_path,
                        target=payload.get("nickname"),
                        is_chatroom=payload.get("is_chatroom"),
                    )
                elif local_type == MessageType.Pat:
                    action = PatAction(
                        target=payload.get("nickname"),
                        user_name=payload.get("at_list")[0],
                        is_chatroom=payload.get("is_chatroom"),
                    )
                if action:
                    self.rpa_task_queue.put(action)
            elif topic == f"msg/{self.userinfo.account}/other_rpa_action":
                payload = msg.get("payload")
                action_type = payload.get("action_type")
                action_data = payload.get("action_data")
                if action_type == RPAActionType.SEND_PYQ.value:
                    # 这里收到的图片可能是网络地址，因此要循环遍历，全部下载到本地
                    images = []
                    for image in action_data.get("images"):
                        image_path = await download_file_if_url(image)
                        images.append(image_path)
                    action = SendPyqAction(
                        content=action_data.get("content"),
                        images=images,
                    )
                    self.rpa_task_queue.put(action)
                elif action_type == RPAActionType.REMOVE_ROOM_MEMBER.value:
                    action = RemoveRoomMemberAction(
                        user_name=action_data.get("user_name"),
                        target=action_data.get("target"),
                    )
                    self.rpa_task_queue.put(action)
                elif action_type == RPAActionType.INVITE_2_ROOM.value:
                    action = Invite2RoomAction(
                        user_name=action_data.get("user_name"),
                        target=action_data.get("target"),
                    )
                    self.rpa_task_queue.put(action)
                elif action_type == RPAActionType.PUBLIC_ROOM_ANNOUNCEMENT.value:
                    action = PublicRoomAnnouncementAction(
                        content=action_data.get("content"),
                        target=action_data.get("target"),
                        force_edit=action_data.get("force_edit", True),
                    )
                    self.rpa_task_queue.put(action)
                elif action_type == RPAActionType.RENAME_ROOM_NAME.value:
                    action = RenameRoomNameAction(
                        target=action_data.get("target"),
                        name=action_data.get("name"),
                    )
                    self.rpa_task_queue.put(action)
                elif action_type == RPAActionType.RENAME_ROOM_REMARK.value:
                    action = RenameRoomRemarkAction(
                        target=action_data.get("target"),
                        remark=action_data.get("remark"),
                    )
                    self.rpa_task_queue.put(action)
                elif action_type == RPAActionType.RENAME_NAME_IN_ROOM.value:
                    action = RenameNameInRoomAction(
                        target=action_data.get("target"),
                        name=action_data.get("name"),
                    )
                    self.rpa_task_queue.put(action)
                elif action_type == RPAActionType.LEAVE_ROOM.value:
                    action = LeaveRoomAction(
                        target=action_data.get("target"),
                    )
                    self.rpa_task_queue.put(action)
            else:
                self.logger.warning(f"收到未知主题的消息: {topic}")
                return
        except Exception as e:
            self.logger.error(f"处理消息时出错: {e}")

    def stop(self):
        """停止MQTT服务"""
        self.mqtt_client.disconnect()
        self.logger.info("MQTT服务已停止")

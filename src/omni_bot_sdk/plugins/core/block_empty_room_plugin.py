"""
群聊重命名插件

该插件负责处理群聊名称相关的功能。
主要功能：
- 检测群聊名称是否为空
- 处理群聊重命名相关的操作
- 提供群聊名称管理的响应

注意事项：
- 该插件配置为高优先级(999)，确保群聊名称能够被及时处理
- 需要确保群聊名称的合法性
- 需要处理群聊重命名失败的情况
"""

from omni_bot_sdk.plugins.interface import Bot, Plugin, PluginExcuteContext
from pydantic import BaseModel


class BlockEmptyRoomPluginConfig(BaseModel):
    """
    群聊重命名插件配置
    enabled: 是否启用该插件
    priority: 插件优先级，数值越大优先级越高
    """

    enabled: bool = False
    priority: int = 998


class BlockEmptyRoomPlugin(Plugin):
    """
    群聊重命名插件实现类
    """

    priority = 998
    name = "block-empty-room-plugin"

    def __init__(self, bot: "Bot" = None):
        # 设置视频文件保存路径
        super().__init__(bot)
        # 动态优先级支持
        self.priority = getattr(self.plugin_config, "priority", self.__class__.priority)

    def get_priority(self) -> int:
        return self.priority

    async def handle_message(self, context: PluginExcuteContext) -> None:
        """
        处理接收到的消息

        参数：
            context (PluginExcuteContext): 消息处理上下文信息

        返回：
            None: 处理结果通过context.add_response()方法返回
        """
        message = context.get_message()

        if message.is_chatroom and (
            message.room.nick_name is None or message.room.nick_name == ""
        ):
            self.logger.warn("当前群没有备注或名称，无法定位，请手动设置群名称")
            self.logger.warn(message)
            # TODO 可以发送修改请求，较复杂，后续开发
            context.should_stop = True

    def get_plugin_name(self) -> str:
        return self.name

    def get_plugin_description(self) -> str:
        return "这是一个用于给新创建的群修改备注的插件"

    @classmethod
    def get_plugin_config_schema(cls):
        """
        返回插件配置的pydantic schema类。
        """
        return BlockEmptyRoomPluginConfig

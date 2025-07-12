import asyncio
from typing import TYPE_CHECKING
from pydantic import BaseModel

from omni_bot_sdk.plugins.interface import Plugin, PluginExcuteContext

if TYPE_CHECKING:
    from omni_bot_sdk.bot import Bot


class SelfMsgPluginConfig(BaseModel):
    """
    自我消息插件配置
    enabled: 是否启用该插件
    priority: 插件优先级，数值越大优先级越高
    """

    enabled: bool = False
    priority: int = 1000


class SelfMsgPlugin(Plugin):
    """
    自我消息处理插件实现类

    继承自Plugin基类，用于处理用户自己发送的消息。
    作为消息处理链中的第一个插件，用于拦截用户自己发送的消息，防止这些消息进入后续处理流程。

    属性：
        priority (int): 插件优先级，设置为1000确保最先执行
        name (str): 插件名称标识符
    """

    priority = 1000
    name = "self-msg-plugin"

    def __init__(self, bot: "Bot" = None):
        super().__init__(bot)
        # 动态优先级支持
        self.priority = getattr(self.plugin_config, "priority", self.__class__.priority)

    def get_priority(self) -> int:
        return self.priority

    async def handle_message(self, plusginExcuteContext: PluginExcuteContext) -> None:
        message = plusginExcuteContext.get_message()
        context = plusginExcuteContext.get_context()
        if message.is_self:
            self.logger.info("检测到是自己的消息，直接拦截，不再让后续的处理")
            plusginExcuteContext.should_stop = True
        else:
            plusginExcuteContext.should_stop = False

    def get_plugin_name(self) -> str:
        return self.name

    def get_plugin_description(self) -> str:
        return "这是一个用于处理用户自己发送消息的插件，用于拦截自己发送的消息"

    @classmethod
    def get_plugin_config_schema(cls):
        """
        返回插件配置的pydantic schema类。
        """
        return SelfMsgPluginConfig

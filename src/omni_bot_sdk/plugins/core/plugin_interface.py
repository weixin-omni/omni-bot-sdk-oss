import logging
from abc import ABC, abstractmethod
from queue import Queue
from typing import TYPE_CHECKING, Any, Dict, List, Type
import json

from omni_bot_sdk.rpa.action_handlers import RPAAction
from omni_bot_sdk.weixin.message_classes import Message
from pydantic import BaseModel, ValidationError

if TYPE_CHECKING:
    from omni_bot_sdk.bot import Bot


class PluginExcuteResponse:
    """
    插件处理结果对象。
    用于收集插件处理消息后的响应、动作、状态等。
    """

    plugin_name: str
    handled: bool
    should_stop: bool
    response: Dict[str, Any]
    actions: List[RPAAction]
    message: Message

    def __init__(
        self,
        plugin_name: str,
        handled: bool = False,
        should_stop: bool = False,
        response: Dict[str, Any] = None,
        actions: List[RPAAction] = None,
        message: Message = None,
    ):
        self.plugin_name = plugin_name
        self.handled = handled
        self.should_stop = should_stop
        self.response = response or {}
        self.actions = actions or []
        self.message = message

    def add_action(self, action: RPAAction):
        """
        添加一个RPA动作到响应。
        """
        self.actions.append(action)

    def get_actions(self) -> List[RPAAction]:
        """
        获取所有RPA动作。
        """
        return self.actions or []


class PluginExcuteContext:
    """
    插件执行上下文。
    封装消息、上下文、响应、错误、should_stop等。
    """

    message: Message
    context: dict
    responses: List[PluginExcuteResponse]
    errors: List[Exception]
    should_stop: bool

    def __init__(self, message: Message, context: dict):
        self.message = message
        self.context = context
        self.errors = []
        self.responses = []
        self.should_stop = False

    def get_message(self) -> Message:
        """
        获取当前消息对象。
        """
        return self.message

    def get_context(self) -> dict:
        """
        获取当前上下文。
        """
        return self.context

    def add_error(self, plugin_name: str, error_message: str):
        """
        添加插件处理错误。
        """
        self.errors.append(f"Error in {plugin_name}: {error_message}")
        # 可选：可在此处设置 should_stop = True

    def add_response(self, value: PluginExcuteResponse):
        """
        添加插件处理响应。
        """
        self.responses.append(value)

    def get_responses(self) -> List[PluginExcuteResponse]:
        """
        获取所有插件响应。
        """
        return self.responses

    def should_stop(self) -> bool:
        """
        是否中断后续插件处理。
        """
        return self.should_stop


class Plugin(ABC):
    """
    异步插件抽象基类。
    所有插件必须继承自此类，实现核心接口。
    """

    priority: int = 0  # 插件执行优先级，数字越大越先执行

    def __init__(self, bot: "Bot"):
        self.bot = bot
        self.logger = bot.logger
        self.config = bot.config
        self.rpa_queue = bot.rpa_task_queue
        self.plugin_config = None
        self.reload_plugin_config()

    def _load_plugin_config(self):
        """
        加载插件特定配置。
        """
        plugin_name = self.get_plugin_name()
        plugins_config = self.config.get("plugins", {})
        return plugins_config.get(plugin_name, {})

    def reload_plugin_config(self):
        """
        重新加载并校验插件配置，支持热重载。
        """
        raw_config = self._load_plugin_config()
        schema = self.get_plugin_config_schema()
        try:
            validated_config = schema(**raw_config)
        except ValidationError as e:
            self.logger.error(f"插件 {self.get_plugin_name()} 配置校验失败: {e}")
            raise
        self.plugin_config = validated_config
        return self.plugin_config

    def get_plugin_config(self, key, default=None):
        """
        获取插件配置项（已校验后的pydantic对象）。
        支持点号和dict访问。
        """
        if self.plugin_config is None:
            self.reload_plugin_config()
        if hasattr(self.plugin_config, key):
            return getattr(self.plugin_config, key, default)
        return getattr(self.plugin_config, "__dict__", {}).get(key, default)

    def add_rpa_action(self, action: RPAAction):
        """
        添加单个RPA动作到队列。
        Args:
            action: RPA动作对象
        """
        self.add_rpa_actions([action])

    def add_rpa_actions(self, actions: List[RPAAction]):
        """
        批量添加RPA动作到队列。
        线程安全由ProcessorService保证。
        """
        if not actions:
            return
        self.bot.processor_service.add_rpa_actions(actions)

    @classmethod
    @abstractmethod
    def get_plugin_config_schema(cls) -> Type[BaseModel]:
        """
        返回插件配置的pydantic schema类。
        """
        raise NotImplementedError

    def get_validated_plugin_config(self) -> BaseModel:
        """
        获取并校验当前插件配置，返回pydantic模型对象。
        """
        if self.plugin_config is None:
            self.reload_plugin_config()
        return self.plugin_config

    def get_plugin_config_info(self) -> Dict[str, Any]:
        """
        获取插件配置schema和当前配置。
        Returns:
            dict: { 'schema': schema_json, 'config': current_config }
        """
        schema = self.get_plugin_config_schema()
        config_dict = self.plugin_config.model_dump() if self.plugin_config else {}
        return {
            "schema": json.dumps(schema.model_json_schema(), ensure_ascii=False),
            "config": config_dict,
        }

    @abstractmethod
    def get_priority(self) -> int:
        """
        获取插件优先级。
        """
        return 0

    @abstractmethod
    async def handle_message(self, context: PluginExcuteContext):
        """
        处理消息的异步方法。
        插件的核心逻辑在这里实现。
        """
        raise NotImplementedError

    @abstractmethod
    def get_plugin_name(self) -> str:
        """
        返回插件的唯一名称。
        """
        raise NotImplementedError

    @abstractmethod
    def get_plugin_description(self) -> str:
        """
        获取插件描述
        """
        raise NotImplementedError

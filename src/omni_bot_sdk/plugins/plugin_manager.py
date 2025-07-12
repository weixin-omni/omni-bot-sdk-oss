import importlib.metadata
import logging
from queue import Queue
from typing import TYPE_CHECKING, Dict, List

# TYPE_CHECKING块仅用于类型提示，避免运行时循环依赖。
if TYPE_CHECKING:
    from omni_bot_sdk.bot import Bot
    from omni_bot_sdk.weixin.message_classes import Message

from omni_bot_sdk.plugins.core.plugin_interface import (
    Plugin,
    PluginExcuteContext,
    PluginExcuteResponse,
)

# 插件入口点组名，所有插件需注册到该组。
PLUGIN_ENTRY_POINT_GROUP = "omni_bot.plugins"


class PluginManager:
    """
    插件管理器。
    负责插件的自动发现、加载、优先级排序、消息分发与热重载。
    """

    def __init__(self, bot: "Bot"):
        """
        初始化插件管理器。
        Args:
            bot (Bot): 主Bot实例，将注入到每个插件。
        """
        self.logger = logging.getLogger(__name__)
        self.bot = bot
        self.plugins: List[Plugin] = []

    def setup(self):
        """
        初始化并加载所有插件。
        """
        self.load_plugins()

    def load_plugins(self):
        """
        发现并加载所有已安装插件。
        支持插件启用/禁用配置，自动注入Bot实例。
        加载后按优先级排序。
        """
        self.logger.info(f"开始通过入口点组 '{PLUGIN_ENTRY_POINT_GROUP}' 加载插件...")

        plugins_config = self.bot.config.get("plugins", {})

        try:
            discovered_plugins = importlib.metadata.entry_points(
                group=PLUGIN_ENTRY_POINT_GROUP
            )
        except AttributeError:
            discovered_plugins = importlib.metadata.entry_points().get(
                PLUGIN_ENTRY_POINT_GROUP, []
            )

        if not discovered_plugins:
            self.logger.warning("未发现任何已安装的插件。请确保插件包已正确安装。")

        for entry_point in discovered_plugins:
            plugin_id = entry_point.name
            try:
                plugin_conf = plugins_config.get(plugin_id, {})
                if (
                    isinstance(plugin_conf, dict)
                    and plugin_conf.get("enabled", False) is False
                ):
                    self.logger.info(f"插件 '{plugin_id}' 在配置中被禁用，跳过加载。")
                    continue

                self.logger.debug(
                    f"正在加载插件 '{plugin_id}' from '{entry_point.value}'..."
                )

                plugin_class = entry_point.load()

                if not (
                    isinstance(plugin_class, type) and issubclass(plugin_class, Plugin)
                ):
                    self.logger.warning(
                        f"入口点 '{plugin_id}' 指向的对象不是有效的 Plugin 子类，已跳过。"
                    )
                    continue

                plugin_instance = plugin_class(self.bot)
                self.plugins.append(plugin_instance)
                self.logger.info(
                    f"成功加载并实例化插件: {plugin_instance.get_plugin_name()} (ID: {plugin_id})"
                )

            except Exception as e:
                self.logger.error(
                    f"加载插件 '{plugin_id}' 时发生错误: {e}", exc_info=True
                )

        # 按插件优先级降序排序
        self.plugins.sort(key=lambda p: getattr(p, "priority", 0), reverse=True)

        if self.plugins:
            plugin_order = " -> ".join([p.get_plugin_name() for p in self.plugins])
            self.logger.info(f"插件加载完成，执行顺序: {plugin_order}")
        else:
            self.logger.info("插件加载完成，但没有活动的插件。")

    async def process_message(
        self, message: "Message", context: Dict
    ) -> List[PluginExcuteResponse]:
        """
        异步处理消息，依次调用每个插件的 async handle_message 方法。
        支持should_stop机制，遇到插件中断链路时提前终止。
        """
        excute_context = PluginExcuteContext(message, context)
        for plugin in self.plugins:
            try:
                await plugin.handle_message(excute_context)
                self.logger.debug(f"插件 '{plugin.get_plugin_name()}' 处理完成。")
                if excute_context.should_stop:
                    self.logger.info(
                        f"插件 '{plugin.get_plugin_name()}' 停止了消息链的后续处理。"
                    )
                    break
            except Exception as e:
                self.logger.error(
                    f"插件 '{plugin.get_plugin_name()}' 处理消息时出错: {e}",
                    exc_info=True,
                )
                excute_context.add_error(plugin.get_plugin_name(), str(e))
        self.logger.info(f"插件处理消息完成")
        return excute_context.get_responses()

    def reload_all_plugins(self):
        """
        重新加载所有插件。
        清空当前插件实例列表并重新发现、加载。
        """
        self.logger.info("开始重新加载所有插件...")
        self.plugins.clear()
        self.load_plugins()
        self.logger.info("插件热重载完成。")

"""
异步插件运行器模块。
提供插件异步执行相关服务。
"""

import asyncio
import logging
import threading
from queue import Queue

from omni_bot_sdk.plugins.interface import ProcessorService
from omni_bot_sdk.plugins.plugin_manager import PluginManager


class AsyncPluginRunner:
    """
    一个在独立线程中运行 asyncio 事件循环的执行器，
    用于从同步代码中调用异步插件。
    """

    def __init__(
        self, plugin_manager: PluginManager, processor_service: "ProcessorService"
    ):
        self.logger = logging.getLogger(__name__)
        self.plugin_manager = plugin_manager
        self.processor_service = processor_service
        self.loop: asyncio.AbstractEventLoop = None
        self.thread: threading.Thread = None
        self.is_running = False

    def _run_loop(self):
        self.logger.info("异步执行器线程启动...")
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()
        self.logger.info("异步事件循环已停止。")

    def start(self):
        if self.is_running:
            return
        self.is_running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        while self.loop is None or not self.loop.is_running():
            pass  # 等待事件循环真正启动
        self.logger.info("异步执行器已启动。")

    def stop(self):
        if not self.is_running:
            return
        self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join()
        self.is_running = False
        self.logger.info("异步执行器已停止。")

    def submit_task(self, message, context: dict):
        """从任何线程安全地提交一个异步任务到事件循环。"""
        if not self.is_running:
            self.logger.warning("异步执行器未运行，任务无法提交。")
            return
        asyncio.run_coroutine_threadsafe(
            self._process_and_handle_result(message, context), self.loop
        )

    async def _process_and_handle_result(self, message, context: dict):
        """在事件循环线程中实际执行插件处理的协程。"""
        try:
            responses = await self.plugin_manager.process_message(message, context)
            if responses:
                for response in responses:
                    self.logger.info(
                        f"插件 {response.plugin_name} (async) 处理结束，移交RPA，指令数量：{len(response.actions)}"
                    )
                    if response.actions:
                        self.processor_service.add_rpa_actions(response.actions)
        except Exception as e:
            self.logger.error(f"在异步插件处理中发生错误: {e}", exc_info=True)

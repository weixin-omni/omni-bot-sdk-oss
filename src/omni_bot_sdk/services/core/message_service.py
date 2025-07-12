"""
消息服务模块。
提供消息的存储、检索、分发等服务。
"""

import logging
import threading
import time
from queue import Empty, Queue
from typing import Callable, Optional

from omni_bot_sdk.services.core.database_service import DatabaseService


class MessageService:
    def __init__(self, message_queue: Queue, db: DatabaseService):
        self.logger = logging.getLogger(__name__)
        self.message_queue = message_queue
        self.db = db
        self.is_running = False
        self.is_paused = False  # 新增：用于标记是否暂停
        self.thread: Optional[threading.Thread] = None
        self.callback: Optional[Callable] = None

    def start(self):
        """启动监听器"""
        if self.is_running:
            self.logger.warning("监听器已经在运行中")
            return False

        self.is_running = True
        self.thread = threading.Thread(target=self._message_loop)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("监听器已启动")
        return True

    def stop(self):
        """停止监听器"""
        if not self.is_running:
            self.logger.warning("监听器未在运行")
            return False

        self.is_running = False
        if self.thread:
            self.thread.join()
        self.logger.info("监听器已停止")
        return True

    def set_callback(self, callback: Callable):
        """设置消息回调函数"""
        self.callback = callback

    def pause(self):
        """
        暂停消息获取
        """
        if not self.is_running or self.is_paused:
            self.logger.info("消息监听器已暂停或未运行，无需重复暂停。")
            return
        self.is_paused = True
        self.logger.info("消息监听器已暂停。")

    def resume(self):
        """
        恢复消息获取
        """
        if not self.is_running or not self.is_paused:
            self.logger.info("消息监听器未暂停或未运行，无需恢复。")
            return
        self.is_paused = False
        self.logger.info("消息监听器已恢复。")

    def _message_loop(self):
        """监听循环"""
        while self.is_running:
            if self.is_paused:
                time.sleep(1)
                continue
            try:
                message = self.db.check_new_messages()
                if message:
                    for msg in message:
                        self.logger.info(f"新消息插入队列")
                        self.message_queue.put(msg)
                    self.logger.info(f"消息队列大小: {self.message_queue.qsize()}")
                    # 保存消息到数据库
                    if self.callback:
                        self.callback(message)
                time.sleep(0.75)
            except Empty:
                # 队列为空，继续下一次循环
                time.sleep(1)  #
                continue
            except Exception as e:
                if self.is_running:  # 忽略超时异常
                    self.logger.error(f"处理消息时出错: {e}")
                    time.sleep(1)  #

    def get_status(self) -> dict:
        """获取监听器状态"""
        return {"is_running": self.is_running, "queue_size": self.message_queue.qsize()}

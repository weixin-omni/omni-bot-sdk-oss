"""
处理器服务模块。
提供消息、任务等处理相关的服务。
"""

import logging
import multiprocessing
import threading
from concurrent.futures import ThreadPoolExecutor
from queue import Empty, Queue
from typing import Dict, Optional

from omni_bot_sdk.models import Contact, UserInfo
from omni_bot_sdk.plugins.plugin_manager import PluginManager
from omni_bot_sdk.services.core.database_service import DatabaseService
from omni_bot_sdk.services.core.message_factory_service import MessageFactoryService

from .async_plugin_runner import AsyncPluginRunner


class ProcessorService:
    def __init__(
        self,
        user_info: UserInfo,
        message_queue: Queue,
        rpa_task_queue: Queue,
        db: DatabaseService,
        message_factory_service: MessageFactoryService,
        plugin_manager: PluginManager,
    ):
        self.logger = logging.getLogger(__name__)
        self.user_info = user_info
        self.db = db
        self.message_factory_service = message_factory_service
        self.message_queue = message_queue
        self.rpa_task_queue = rpa_task_queue
        self.is_running = False
        self.thread: Optional[threading.Thread] = None
        self.message_event = threading.Event()

        # 初始化配置
        thread_pool_size = multiprocessing.cpu_count() - 1
        self.logger.info(f"CPU线程数量: {thread_pool_size}")
        # 初始化消息处理线程池
        self.thread_pool = ThreadPoolExecutor(max_workers=thread_pool_size)
        self.logger.info(f"初始化消息处理器线程池，大小: {thread_pool_size}")

        # 用于同步RPA队列的锁
        self.rpa_queue_lock = threading.Lock()

        self.plugin_manager = plugin_manager

        self.room_cache = {}
        self.contact_cache = {}

        # 会话队列管理
        self.session_queues: Dict[str, Queue] = {}
        self.session_threads: Dict[str, threading.Thread] = {}
        self.session_queue_lock = threading.Lock()
        self.active_sessions: Dict[str, bool] = {}
        self.active_sessions_lock = threading.Lock()

        # 新增：初始化并持有异步执行器
        self.async_runner = AsyncPluginRunner(plugin_manager, self)

    def setup(self):
        # self.plugin_manager.setup()
        self.logger.info(f"已加载 {len(self.plugin_manager.plugins)} 个插件")

    def start(self):
        """启动发布器"""
        if self.is_running:
            self.logger.warning("发布器已经在运行中")
            return False

        self.is_running = True
        # 新增：启动异步执行器
        self.async_runner.start()
        self.thread = threading.Thread(target=self._process_loop)
        self.thread.daemon = True
        self.thread.start()
        self.logger.info("发布器已启动")
        return True

    def stop(self):
        """停止发布器"""
        if not self.is_running:
            self.logger.warning("发布器未在运行")
            return False

        self.is_running = False
        # 新增：停止异步执行器
        self.async_runner.stop()
        if self.thread:
            self.thread.join()

        # 关闭线程池
        self.thread_pool.shutdown(wait=True)
        self.logger.info("发布器已停止")
        return True

    def _process_message(self, message: tuple):
        """
        处理单条消息的方法。
        核心改动：不再直接处理，而是提交给异步执行器。
        """
        try:
            message_obj = self.message_factory_service.create_message(message)
            if message_obj:
                context = {
                    "message": message_obj,
                    "db": self.db,
                    "room": message_obj.room,
                    "contact": message_obj.contact,
                    "user": self.user_info,
                }
                # 将任务交给异步执行器，立即返回，不阻塞
                self.async_runner.submit_task(message_obj, context)
        except Exception as e:
            self.logger.error(f"准备消息并提交给异步执行器时出错: {e}", exc_info=True)

    def _get_session_id(self, message: tuple) -> str:
        """获取会话ID"""
        table_name, msg_with_db = message
        # 如果是群消息，使用群ID作为会话ID
        if table_name.startswith("Msg_"):
            return table_name.replace("Msg_", "")
        # 如果是私聊消息，使用发送者ID作为会话ID
        return f"private_{msg_with_db[4]}"

    def _ensure_session_queue(self, session_id: str) -> Queue:
        """确保会话队列存在并返回"""
        with self.session_queue_lock:
            if session_id not in self.session_queues:
                self.session_queues[session_id] = Queue()
            return self.session_queues[session_id]

    def _process_session_messages(self, session_id: str):
        """处理特定会话的消息"""
        queue = self.session_queues[session_id]
        while self.is_running:
            try:
                message = queue.get(timeout=1)
                if message:
                    self._process_message(message)
                queue.task_done()
            except Empty:
                # 如果队列为空，标记会话为非活动状态
                with self.active_sessions_lock:
                    self.active_sessions[session_id] = False
                break
            except Exception as e:
                self.logger.error(f"处理会话 {session_id} 消息时出错: {e}")
                with self.active_sessions_lock:
                    self.active_sessions[session_id] = False
                break

    def _schedule_session_processing(self, session_id: str):
        """调度会话处理"""
        with self.active_sessions_lock:
            if not self.active_sessions.get(session_id, False):
                self.active_sessions[session_id] = True
                self.thread_pool.submit(self._process_session_messages, session_id)

    def _process_loop(self):
        """处理循环"""
        while self.is_running:
            try:
                message = self.message_queue.get(timeout=1)
                if message:
                    # 获取会话ID并将消息放入对应的会话队列
                    session_id = self._get_session_id(message)
                    session_queue = self._ensure_session_queue(session_id)
                    session_queue.put(message)
                    # 调度会话处理
                    self._schedule_session_processing(session_id)
                self.message_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                self.logger.error(f"处理消息时出错: {e}")
                continue

    def get_status(self) -> dict:
        """获取发布器状态"""
        return {"is_running": self.is_running, "queue_size": self.message_queue.qsize()}

    def _get_room_from_cache(self, username_md5: str) -> Optional[Contact]:
        """
        从缓存中获取群聊信息

        Args:
            username_md5: 群聊username的MD5值

        Returns:
            Optional[Contact]: 群聊对象，如果未找到则返回None
        """
        return self.room_cache.get(username_md5)

    def _get_contact_from_cache(
        self, message_db_path: str, sender_id: int
    ) -> Optional[Contact]:
        """
        从缓存中获取联系人信息

        Args:
            message_db_path: 消息数据库路径
            sender_id: 发送者ID

        Returns:
            Optional[Contact]: 联系人对象，如果未找到则返回None
        """
        cache_key = f"{message_db_path}_{sender_id}"
        return self.contact_cache.get(cache_key)

    def _cache_room(self, md5: str, room: Contact):
        """
        缓存群聊信息

        Args:
            md5: 群聊username的MD5值
            room: 群聊对象
        """
        self.room_cache[md5] = room

    def _cache_contact(self, message_db_path: str, sender_id: int, contact: Contact):
        """
        缓存联系人信息

        Args:
            message_db_path: 消息数据库路径
            sender_id: 发送者ID
            contact: 联系人对象
        """
        cache_key = f"{message_db_path}_{sender_id}"
        self.contact_cache[cache_key] = contact

    def add_rpa_actions(self, actions: list):
        """线程安全地批量添加RPA动作到队列"""
        if not actions:
            return
        with self.rpa_queue_lock:
            for action in actions:
                self.rpa_task_queue.put(action)
        self.logger.debug(f"批量添加了 {len(actions)} 个RPA动作到队列")

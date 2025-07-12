"""
RPA 控制器模块。
包含令牌桶限流器和 RPA 主控制器。
"""

import logging
import os
import random
import time
from typing import Any, Dict
from threading import Lock

from omni_bot_sdk.services.core.database_service import DatabaseService
from omni_bot_sdk.rpa.action_handlers import RPAAction, RPAActionType
from .image_processor import ImageProcessor
from .input_handler import InputHandler
from .message_sender import MessageSender
from .ocr_processor import OCRProcessor
from .ui_helper import UIInteractionHelper
from .window_manager import WindowManager


class TokenBucket:
    """
    令牌桶限流器。
    用于控制操作速率，适用于单线程环境。
    """

    def __init__(self, rate: float, capacity: float):
        """
        初始化令牌桶。
        Args:
            rate (float): 令牌生成速率（每秒）。
            capacity (float): 令牌桶容量。
        """
        self._rate = rate
        self._capacity = capacity
        self._tokens = capacity
        self._last_update = time.monotonic()

    def _refill(self):
        """
        补充令牌。
        """
        now = time.monotonic()
        elapsed = now - self._last_update
        if elapsed > 0:
            new_tokens = elapsed * self._rate
            self._tokens = min(self._capacity, self._tokens + new_tokens)
            self._last_update = now

    @property
    def tokens(self) -> float:
        """
        获取当前可用令牌数（自动补充）。
        Returns:
            float: 当前可用令牌数。
        """
        self._refill()
        return self._tokens

    def consume(self, amount: int = 1) -> bool:
        """
        消耗指定数量的令牌。
        Args:
            amount (int): 需要消耗的令牌数量。
        Returns:
            bool: 成功消耗返回 True，否则 False。
        """
        if self._tokens >= amount:
            self._tokens -= amount
            return True
        return False


class RPAController:
    """
    RPA 主控制器。
    负责依赖注入、RPA 操作分发、速率限制等。
    """

    def __init__(
        self,
        db: DatabaseService,
        window_manager: WindowManager,
        ocr_processor: OCRProcessor,
        image_processor: ImageProcessor,
        rpa_config: dict,
    ):
        """
        初始化 RPAController。
        Args:
            db (DatabaseService): 数据库服务。
            window_manager (WindowManager): 窗口管理器。
            ocr_processor (OCRProcessor): OCR 处理器。
            image_processor (ImageProcessor): 图像处理器。
            rpa_config (dict): RPA 配置。
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.db = db
        self.window_manager = window_manager
        self.ocr_processor = ocr_processor
        self.image_processor = image_processor
        self.message_sender = MessageSender(self.window_manager)
        self.input_handler = InputHandler()
        self.ui_helper = UIInteractionHelper(self)
        self.action_handlers: Dict[RPAActionType, Any] = {}
        self._register_handlers()
        self.short_term_limiter = TokenBucket(
            rate=rpa_config.get("short_term_rate", 0.2),
            capacity=rpa_config.get("short_term_capacity", 2),
        )
        self.long_term_limiter = TokenBucket(
            rate=rpa_config.get("long_term_rate", 0.25),
            capacity=rpa_config.get("long_term_capacity", 15),
        )
        self.rate_limiter_lock = Lock()
        self.logger.info(
            "RPAController 初始化完成，所有处理器已注册，速率限制器已激活。"
        )

    def _register_handlers(self):
        """
        注册所有 RPA 操作处理器。
        """
        from .action_handlers import (
            DownloadFileHandler,
            DownloadImageHandler,
            DownloadVideoHandler,
            ForwardMessageHandler,
            LeaveRoomHandler,
            PatHandler,
            PublicRoomAnnouncementHandler,
            RemoveRoomMemberHandler,
            RenameNameInRoomHandler,
            RenameRoomNameHandler,
            RenameRoomRemarkHandler,
            SendFileHandler,
            SendImageHandler,
            SendTextMessageHandler,
            SwitchConversationHandler,
        )

        handler_classes = [
            (RPAActionType.PUBLIC_ROOM_ANNOUNCEMENT, PublicRoomAnnouncementHandler),
            (RPAActionType.REMOVE_ROOM_MEMBER, RemoveRoomMemberHandler),
            (RPAActionType.RENAME_ROOM_NAME, RenameRoomNameHandler),
            (RPAActionType.RENAME_ROOM_REMARK, RenameRoomRemarkHandler),
            (RPAActionType.RENAME_NAME_IN_ROOM, RenameNameInRoomHandler),
            (RPAActionType.SEND_TEXT_MESSAGE, SendTextMessageHandler),
            (RPAActionType.SWITCH_CONVERSATION, SwitchConversationHandler),
            (RPAActionType.SEND_FILE, SendFileHandler),
            (RPAActionType.SEND_IMAGE, SendImageHandler),
            (RPAActionType.FORWARD_MESSAGE, ForwardMessageHandler),
            (RPAActionType.DOWNLOAD_IMAGE, DownloadImageHandler),
            (RPAActionType.DOWNLOAD_FILE, DownloadFileHandler),
            (RPAActionType.DOWNLOAD_VIDEO, DownloadVideoHandler),
            (RPAActionType.PAT, PatHandler),
            (RPAActionType.LEAVE_ROOM, LeaveRoomHandler),
        ]
        try:
            from .action_handlers import (
                Invite2RoomHandler,
                NewFriendHandler,
                SendPyqHandler,
            )

            handler_classes.extend(
                [
                    (RPAActionType.INVITE_2_ROOM, Invite2RoomHandler),
                    (RPAActionType.NEW_FRIEND, NewFriendHandler),
                    (RPAActionType.SEND_PYQ, SendPyqHandler),
                ]
            )
        except ImportError:
            pass
        for action_type, handler_class in handler_classes:
            self.action_handlers[action_type] = handler_class(self)

    def _can_send_message(self) -> bool:
        """
        检查并消耗发送消息的令牌（线程安全）。
        Returns:
            bool: 如果可以发送（并已消耗令牌）则返回 True，否则返回 False。
        """
        with self.rate_limiter_lock:
            if (
                self.short_term_limiter.tokens >= 1
                and self.long_term_limiter.tokens >= 1
            ):
                self.short_term_limiter.consume(1)
                self.long_term_limiter.consume(1)
                return True
            else:
                return False

    def execute_action(self, action: RPAAction) -> bool:
        """
        执行 RPA 操作，分发到对应的 Handler。
        对于发送消息的操作，如果被限流，会等待并重试，直到超时。
        Args:
            action (RPAAction): RPA 操作对象。
        Returns:
            bool: 操作是否成功。
        """
        handler = self.action_handlers.get(action.action_type)
        if handler is None:
            self.logger.error(f"未注册的操作类型: {action.action_type}")
            return False

        if action.is_send_message:
            max_wait_seconds = 10
            wait_interval = 1
            start_time = time.monotonic()
            while not self._can_send_message():
                if time.monotonic() - start_time > max_wait_seconds:
                    self.logger.warning(
                        f"操作 {action.action_type.name} 等待速率限制超时 {max_wait_seconds}s，已中止。"
                    )
                    self.logger.debug(
                        f"超时时令牌状态: 短期: {self.short_term_limiter.tokens:.2f}/2, 长期: {self.long_term_limiter.tokens:.2f}/15."
                    )
                    return False
                self.logger.info(f"速率受限，等待 {wait_interval}s 后重试...")
                time.sleep(wait_interval)
            self.logger.info("速率限制通过，继续发送操作。")
            time.sleep(random.uniform(0.5, 1.5))

        try:
            self.logger.info(f"执行 RPA 操作: {action.action_type.name}")
            success = handler.execute(action)
            self.logger.info(
                f"RPA 操作完成: {action.action_type.name}, 成功: {success}"
            )
            return success
        except Exception as e:
            self.logger.error(
                f"执行操作 {action.action_type.name} 时发生未处理异常: {e}",
                exc_info=True,
            )
            return False

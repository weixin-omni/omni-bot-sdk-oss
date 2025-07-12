"""
RPA 包初始化文件。
本包包含 RPA 自动化相关的核心组件与工具类，统一对外导出主要接口。
"""

from omni_bot_sdk.weixin.message_classes import MessageType
from .controller import RPAController
from .image_processor import ImageProcessor
from .input_handler import InputHandler
from .message_sender import MessageSender
from .ocr_processor import OCRProcessor
from .window_manager import WindowManager
from .ui_helper import UIInteractionHelper

__all__ = [
    "WindowManager",
    "MessageSender",
    "ImageProcessor",
    "OCRProcessor",
    "InputHandler",
    "RPAController",
    "MessageType",
    "UIInteractionHelper",
]

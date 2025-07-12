from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict

if TYPE_CHECKING:
    from omni_bot_sdk.rpa.controller import RPAController
    from omni_bot_sdk.rpa.image_processor import ImageProcessor
    from omni_bot_sdk.rpa.input_handler import InputHandler
    from omni_bot_sdk.rpa.ocr_processor import OCRProcessor
    from omni_bot_sdk.rpa.ui_helper import UIInteractionHelper
    from omni_bot_sdk.rpa.window_manager import WindowManager


class RPAActionType(Enum):
    """RPA操作类型枚举"""

    SEND_MESSAGE = "send_message"
    SWITCH_CONVERSATION = "switch_conversation"
    QUOTE_MESSAGE = "quote_message"
    MENTION_USER = "mention_user"
    SEND_IMAGE = "send_image"
    # 总觉得全部统一使用发送文件就可以了，图片，视频都是一样的
    SEND_FILE = "send_file"
    SEND_EMOJI = "send_emoji"
    SEND_LINK = "send_link"
    SEND_VIDEO = "send_video"
    SEND_VOICE = "send_voice"
    FORWARD_MESSAGE = "forward_message"
    DOWNLOAD_IMAGE = "download_image"
    DOWNLOAD_VIDEO = "download_video"
    DOWNLOAD_FILE = "download_file"
    PAT = "pat"
    NEW_FRIEND = "new_friend"
    INVITE_2_ROOM = "invice_2_room"
    REMOVE_ROOM_MEMBER = "remove_room_member"
    SEND_PYQ = "send_pyq"
    PUBLIC_ROOM_ANNOUNCEMENT = "public_room_announcement"
    RENAME_ROOM_NAME = "rename_room_name"
    RENAME_ROOM_REMARK = "rename_room_remark"
    RENAME_NAME_IN_ROOM = "rename_name_in_room"
    LEAVE_ROOM = "leave_room"
    SEND_TEXT_MESSAGE = "send_text_message"


@dataclass
class RPAAction:
    """
    RPA操作的基类。

    Attributes:
        action_type (RPAActionType): 操作类型。
        timestamp (datetime): 操作时间戳。
    """

    action_type: RPAActionType = field(default=None, init=False)
    timestamp: datetime = field(default_factory=datetime.now, init=False)
    is_send_message: bool = field(default=None, init=False)

    def to_dict(self) -> Dict[str, Any]:
        """将RPAAction对象转换为字典。"""
        # 注意这里的 self.action_type 可能还未被 __post_init__ 设置
        # 一个更健壮的实现
        action_type_value = getattr(self, "action_type", None)
        if action_type_value is None:
            raise NotImplementedError(
                f"{self.__class__.__name__} is missing action_type."
            )

        return {
            "action_type": action_type_value.value,
            "timestamp": self.timestamp.isoformat(),
        }


class BaseActionHandler(ABC):
    """
    RPA操作处理器基类，定义所有ActionHandler的接口和通用逻辑。
    """

    def __init__(self, controller: "RPAController"):
        """
        初始化 BaseActionHandler。

        Args:
            controller (Any): RPAController实例。
        """
        self.controller: "RPAController" = controller
        self.window_manager: "WindowManager" = controller.window_manager
        self.image_processor: "ImageProcessor" = controller.image_processor
        self.ocr_processor: "OCRProcessor" = controller.ocr_processor
        self.input_handler: "InputHandler" = controller.input_handler
        self.ui_helper: "UIInteractionHelper" = controller.ui_helper
        self.logger = controller.logger.getChild(self.__class__.__name__)

    @abstractmethod
    def execute(self, action: Any) -> bool:
        """
        执行具体的RPA操作。

        Args:
            action (Any): RPAAction实例。

        Returns:
            bool: 操作是否成功。
        """
        pass

    def _cleanup(self):
        """
        公共清理逻辑：关闭所有弹窗和侧边栏。
        """
        try:
            self.window_manager.close_all_windows()
            self.window_manager.open_close_sidebar(close=True)
        except Exception as e:
            self.logger.warning(f"清理时发生异常: {e}")

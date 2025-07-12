import time
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import pyautogui
from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAAction,
    RPAActionType,
)
from omni_bot_sdk.utils.helpers import copy_file_to_clipboard


@dataclass
class SendImageAction(RPAAction):
    """
    发送图片操作。
    Attributes:
        image_path (str): 图片文件路径。
        target (str): 目标用户或群聊的标识。
        is_chatroom (bool): 是否为群聊。
    """

    image_path: Optional[str] = None
    target: Optional[str] = None
    is_chatroom: bool = False

    def __post_init__(self):
        self.action_type = RPAActionType.SEND_IMAGE
        self.is_send_message = True


class SendImageHandler(BaseActionHandler):
    """
    发送图片操作的处理器。
    """

    def execute(self, action: SendImageAction) -> bool:
        """
        执行发送图片操作。
        Args:
            action (SendImageAction): 操作对象。
        Returns:
            bool: 操作是否成功。
        """
        try:
            if not self.window_manager.switch_session(action.target):
                return False
            if not copy_file_to_clipboard(action.image_path):
                return False
            time.sleep(self.controller.window_manager.action_delay)
            self.window_manager.activate_input_box()
            time.sleep(self.controller.window_manager.action_delay)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(1)
            return self.ui_helper.click_send_button()
        finally:
            self._cleanup()

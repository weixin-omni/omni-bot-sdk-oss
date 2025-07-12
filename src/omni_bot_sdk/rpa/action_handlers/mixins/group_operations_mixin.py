import time
from typing import Tuple

import pyautogui
from omni_bot_sdk.utils.helpers import set_clipboard_text


class GroupOperationsMixin:

    def _get_room_side_bar_region(self) -> Tuple[int, int, int, int]:
        """
        获取群聊侧边栏区域。
        """
        return [
            self.window_manager.size_config.width
            - self.window_manager.ROOM_SIDE_BAR_WIDTH,
            self.window_manager.TITLE_BAR_HEIGHT,
            self.window_manager.ROOM_SIDE_BAR_WIDTH,
            self.window_manager.size_config.height
            - self.window_manager.TITLE_BAR_HEIGHT,
        ]

    def _replace_input_text(self, text: str) -> bool:
        """
        替换输入框文本。
        """
        time.sleep(self.controller.window_manager.action_delay)
        set_clipboard_text(text)
        time.sleep(self.controller.window_manager.action_delay)
        pyautogui.hotkey("ctrl", "a")
        time.sleep(self.controller.window_manager.action_delay)
        pyautogui.hotkey("ctrl", "v")
        time.sleep(self.controller.window_manager.action_delay)
        pyautogui.press("enter")
        time.sleep(self.controller.window_manager.action_delay)

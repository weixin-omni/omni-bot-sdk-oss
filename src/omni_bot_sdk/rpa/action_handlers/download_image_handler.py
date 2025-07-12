from dataclasses import dataclass, field
from typing import Optional

import pyautogui
from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAAction,
    RPAActionType,
)


@dataclass
class DownloadImageAction(RPAAction):
    target: Optional[str] = None
    max_count: int = 1

    def __post_init__(self):
        self.action_type = RPAActionType.DOWNLOAD_IMAGE
        self.is_send_message = False


class DownloadImageHandler(BaseActionHandler):
    """
    下载图片操作的处理器。
    """

    def execute(self, action: DownloadImageAction) -> bool:
        """
        执行下载图片操作。
        Args:
            action (DownloadImageAction): 操作对象。
        Returns:
            bool: 操作是否成功。
        """
        try:
            if not self.window_manager.switch_session(action.target):
                return False
            pyautogui.scroll(-1000)
            # TODO: 实现高清图片下载逻辑
            # 目前仅切换会话并返回True，后续可补充保存图片等功能
            return True
        finally:
            self._cleanup()

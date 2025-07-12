import time
from dataclasses import dataclass
from typing import Any

import pyautogui
from omni_bot_sdk.rpa.ui_helper import BtnType
from omni_bot_sdk.rpa.window_manager import WindowTypeEnum
from omni_bot_sdk.utils.helpers import get_center_point, set_clipboard_text
from omni_bot_sdk.utils.mouse import human_like_mouse_move

from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAAction,
    RPAActionType,
)


@dataclass
class PublicRoomAnnouncementAction(RPAAction):
    """发布群公告操作。"""

    content: str
    target: str
    force_edit: bool = False

    def __post_init__(self):
        self.action_type = RPAActionType.PUBLIC_ROOM_ANNOUNCEMENT
        self.is_send_message = False


class PublicRoomAnnouncementHandler(BaseActionHandler):
    """
    群公告操作的处理器。

    负责发布和编辑微信群公告，结合 OCR、UI 辅助工具和视觉定位。
    """

    def execute(self, action: PublicRoomAnnouncementAction) -> bool:
        """
        执行群公告相关的 RPA 操作。

        Args:
            action (PublicRoomAnnouncementAction): 公告操作动作对象。

        Returns:
            bool: 操作是否成功。
        """
        try:
            if not self._click_announcement_button(action):
                return False
            popup_window = self.window_manager.wait_for_window(
                WindowTypeEnum.PublicAnnouncementWindow, True
            )
            if not popup_window:
                self.logger.error("群公告窗口打开失败")
                return False
            result = self._handle_new_announcement(action, popup_window)
            if result:
                return result
            result = self._handle_edit_announcement(action, popup_window)
            if result:
                return result
            self.logger.error("未找到完成或编辑按钮")
            return False
        finally:
            self._cleanup()

    def _click_announcement_button(self, action: PublicRoomAnnouncementAction) -> bool:
        """
        查找并点击侧边栏的"群公告"按钮。

        Args:
            action (PublicRoomAnnouncementAction): 公告操作动作对象。

        Returns:
            bool: 是否成功点击。
        """
        self.window_manager.switch_session(action.target)
        self.window_manager.open_close_sidebar()
        region = [
            self.window_manager.size_config.width
            - self.window_manager.ROOM_SIDE_BAR_WIDTH,
            self.window_manager.TITLE_BAR_HEIGHT,
            self.window_manager.ROOM_SIDE_BAR_WIDTH,
            self.window_manager.size_config.height,
        ]
        # TODO 只根据文本匹配来查找，这里鲁棒性不高，后续优化
        bbox = self.ui_helper.find_and_click_text_element(
            region=region,
            text="群公告",
        )
        return bbox is not None

    def _handle_new_announcement(
        self, action: PublicRoomAnnouncementAction, popup_window: Any
    ) -> bool:
        """
        处理新建群公告的流程。

        Args:
            action (PublicRoomAnnouncementAction): 公告操作动作对象。
            popup_window (Any): 公告弹窗窗口对象。

        Returns:
            bool: 操作是否成功。
        """
        margin = self.controller.window_manager.window_margin
        region = [
            popup_window.left + margin,
            popup_window.top + margin,
            popup_window.width - 2 * margin,
            popup_window.height - 2 * margin,
        ]
        btn_bbox = self.ui_helper.find_btn_by_text(
            region=region,
            btn_type=BtnType.GREEN,
            text="",  # 如果是第一次发布公告，只有浅绿色的 完成，可以匹配到
        )
        if btn_bbox:
            set_clipboard_text(action.content)
            time.sleep(self.controller.window_manager.action_delay)
            pyautogui.hotkey("ctrl", "v")
            time.sleep(self.controller.window_manager.action_delay)
            center = get_center_point(btn_bbox)
            human_like_mouse_move(target_x=center[0], target_y=center[1])
            pyautogui.click()
            time.sleep(self.controller.window_manager.action_delay)
            btn_bbox = self.ui_helper.find_btn_by_text(
                region=region,
                btn_type=BtnType.GREEN,
                text="发布",
            )
            if btn_bbox:
                center = get_center_point(btn_bbox)
                human_like_mouse_move(target_x=center[0], target_y=center[1])
                pyautogui.click()
                time.sleep(self.controller.window_manager.action_delay)
                return True
        return False

    def _handle_edit_announcement(
        self, action: PublicRoomAnnouncementAction, popup_window: Any
    ) -> bool:
        """
        处理编辑群公告的流程。

        Args:
            action (PublicRoomAnnouncementAction): 公告操作动作对象。
            popup_window (Any): 公告弹窗窗口对象。

        Returns:
            bool: 操作是否成功。
        """
        margin = self.controller.window_manager.window_margin
        region = [
            popup_window.left + margin,
            popup_window.top + margin,
            popup_window.width - 2 * margin,
            popup_window.height - 2 * margin,
        ]
        btn_bbox = self.ui_helper.find_btn_by_text(
            region=region,
            btn_type=BtnType.GRAY,
            text="编辑群公告",
        )
        if btn_bbox:
            center = get_center_point(btn_bbox)
            human_like_mouse_move(target_x=center[0], target_y=center[1])
            pyautogui.click()
            time.sleep(self.controller.window_manager.action_delay)

            set_clipboard_text(action.content)
            time.sleep(self.controller.window_manager.action_delay)
            pyautogui.hotkey("ctrl", "a")
            time.sleep(self.controller.window_manager.action_delay)
            pyautogui.press("delete")
            time.sleep(self.controller.window_manager.action_delay)
            if action.content.strip() != "":
                pyautogui.hotkey("ctrl", "v")
                time.sleep(self.controller.window_manager.action_delay)
            else:
                pyautogui.press("backspace")
                time.sleep(self.controller.window_manager.action_delay)
            btn_bbox = self.ui_helper.find_btn_by_text(
                region=region,
                btn_type=BtnType.GREEN,
                text="",
            )
            if btn_bbox:
                center = get_center_point(btn_bbox)
                human_like_mouse_move(target_x=center[0], target_y=center[1])
                pyautogui.click()
                time.sleep(self.controller.window_manager.action_delay)
            # 根据文本是否为空，判断是清空还是发布
            if action.content.strip() != "":
                btn_bbox = self.ui_helper.find_btn_by_text(
                    region=region,
                    btn_type=BtnType.GREEN,
                    text="",
                )
            else:
                btn_bbox = self.ui_helper.find_btn_by_text(
                    region=region,
                    btn_type=BtnType.RED,
                    text="",
                )
            if btn_bbox:
                center = get_center_point(btn_bbox)
                human_like_mouse_move(target_x=center[0], target_y=center[1])
                pyautogui.click()
                time.sleep(self.controller.window_manager.action_delay)
                return True
        return False

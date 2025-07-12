import time
from dataclasses import dataclass, field

import pyautogui
from omni_bot_sdk.rpa.ui_helper import BtnType
from omni_bot_sdk.rpa.window_manager import WindowTypeEnum
from omni_bot_sdk.utils.helpers import set_clipboard_text
from omni_bot_sdk.utils.mouse import human_like_mouse_move

from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAAction,
    RPAActionType,
)


@dataclass
class RemoveRoomMemberAction(RPAAction):
    """
    移除群成员操作。

    Attributes:
        user_name (str): 被移除的用户名。
        target (str): 目标群聊的名称。
    """

    user_name: str = field(default=None)
    target: str = field(default=None)

    def __post_init__(self):
        self.action_type = RPAActionType.REMOVE_ROOM_MEMBER
        self.is_send_message = False


class RemoveRoomMemberHandler(BaseActionHandler):
    """
    移除群成员操作的处理器。
    """

    def execute(self, action: RemoveRoomMemberAction) -> bool:
        """
        执行移除群成员操作。
        """
        try:
            if not self.window_manager.switch_session(action.target):
                self.logger.error(f"切换到群失败: {action.target}")
                return False
            self.window_manager.open_close_sidebar()
            if not self._click_remove_button():
                self.logger.error("未找到移出按钮")
                return False
            popup_window = self.window_manager.wait_for_window(
                WindowTypeEnum.RemoveMemberWindow
            )
            if not popup_window:
                self.logger.error("移出群成员窗口打开失败")
                return False
            if not self._select_and_confirm_remove(action, popup_window):
                self.logger.error("移除成员失败")
                return False
            return True
        finally:
            self._cleanup()

    def _click_remove_button(self) -> bool:
        """
        在侧边栏查找并点击"移出"按钮。
        """
        region = [
            self.window_manager.size_config.width
            - self.window_manager.ROOM_SIDE_BAR_WIDTH,
            self.window_manager.TITLE_BAR_HEIGHT,
            self.window_manager.ROOM_SIDE_BAR_WIDTH,
            self.window_manager.size_config.height // 2,
        ]
        btns = self.ui_helper.find_text_elements(
            region=region,
            text="移出",
        )
        if btns:
            # 按照坐标排序，优先选Y最大，再选X最大
            btns.sort(
                key=lambda x: (x["pixel_bbox"][3], x["pixel_bbox"][0]), reverse=True
            )
            self.ui_helper.click_element(
                bbox=btns[0].get("pixel_bbox"),
                offset=(0, -30),
            )
            return True
        return False

    def _select_and_confirm_remove(
        self, action: RemoveRoomMemberAction, popup_window
    ) -> bool:
        """
        在弹窗中搜索并选择成员，点击确认移除。
        """
        set_clipboard_text(action.user_name)
        time.sleep(self.controller.window_manager.action_delay)
        self.input_handler.hotkey("ctrl", "v")
        time.sleep(self.controller.window_manager.action_delay)
        region = [
            popup_window.left + self.controller.window_manager.window_margin,
            popup_window.top + self.controller.window_manager.window_margin,
            popup_window.width // 2,
            popup_window.height // 2,
        ]
        # 这里就只截取了左上角1/4的区域进行识别，直接匹配名称，然后按照Y从大到小选择第一个？
        contacts = self.ui_helper.find_text_elements(
            action.user_name, region=region, fuzzy=70
        )
        if contacts:
            contacts.sort(key=lambda x: x.get("pixel_bbox")[1], reverse=True)
            self.ui_helper.click_element(
                bbox=contacts[0].get("pixel_bbox"),
            )

            # 在右下角1/4查找移出按钮
            region = [
                popup_window.left + popup_window.width // 2,
                popup_window.top + popup_window.height // 2,
                popup_window.width // 2,
                popup_window.height // 2,
            ]
            btns = self.ui_helper.find_btn_by_text(
                text="",
                btn_type=BtnType.GREEN,
                region=region,
            )
            if btns:
                self.ui_helper.click_element(bbox=btns)
                return True
        return True

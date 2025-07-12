import time
from dataclasses import dataclass, field

import pyautogui
from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAAction,
    RPAActionType,
)
from omni_bot_sdk.rpa.action_handlers.mixins.group_operations_mixin import (
    GroupOperationsMixin,
)
from omni_bot_sdk.rpa.action_handlers.mixins.window_operations_mixin import (
    WindowOperationsMixin,
)
from omni_bot_sdk.rpa.window_manager import WindowTypeEnum
from omni_bot_sdk.utils.helpers import get_center_point
from omni_bot_sdk.utils.mouse import human_like_mouse_move


@dataclass
class LeaveRoomAction(RPAAction):
    target: str = field(default=None)

    def __post_init__(self):
        self.action_type = RPAActionType.LEAVE_ROOM
        self.is_send_message = False


class LeaveRoomHandler(WindowOperationsMixin, GroupOperationsMixin, BaseActionHandler):
    """
    退群操作的处理器。
    """

    def execute(self, action: LeaveRoomAction) -> bool:
        """
        执行退群操作。
        Args:
            action (LeaveRoomAction): 操作对象。
        Returns:
            bool: 操作是否成功。
        """
        try:
            if not self.window_manager.switch_session(action.target):
                self._cleanup()
                return False
            self.window_manager.open_close_sidebar()
            region = self._get_room_side_bar_region()
            human_like_mouse_move(
                region[0] + region[2] // 2, region[1] + region[3] // 2
            )
            time.sleep(self.controller.window_manager.action_delay)
            pyautogui.scroll(-1500)
            leave_btn = self.ui_helper.find_and_click_text_element(
                region=region,
                text="退出群聊",
            )
            if leave_btn:
                confirm_window = self.window_manager.wait_for_window(
                    WindowTypeEnum.RoomInputConfirmBox
                )
                if confirm_window:
                    region = self.get_window_region(confirm_window)
                    confirm_btn = self.ui_helper.find_and_click_text_element(
                        region=region,
                        text="确定",
                    )
                    if confirm_btn:
                        time.sleep(self.controller.window_manager.action_delay)
                    else:
                        self.logger.error("未找到确定按钮")
                        return False
                else:
                    self.logger.error("未找到确认窗口")
                    return False
            else:
                self.logger.error("未找到退出群聊按钮")
                return False
            return True
        finally:
            self._cleanup()

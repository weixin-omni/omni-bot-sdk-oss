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
from omni_bot_sdk.rpa.window_manager import WindowTypeEnum
from omni_bot_sdk.utils.helpers import get_center_point, set_clipboard_text
from omni_bot_sdk.utils.mouse import human_like_mouse_move


@dataclass
class RenameRoomRemarkAction(RPAAction):
    target: str = ""
    remark: str = ""

    def __post_init__(self):
        self.action_type = RPAActionType.RENAME_ROOM_REMARK
        self.is_send_message = False


class RenameRoomRemarkHandler(GroupOperationsMixin, BaseActionHandler):
    """
    重命名群聊备注操作的处理器。
    """

    def execute(self, action: RenameRoomRemarkAction) -> bool:
        """
        执行重命名群聊备注操作。
        Args:
            action (RenameRoomRemarkAction): 操作对象。
        Returns:
            bool: 操作是否成功。
        """
        try:
            if not self.window_manager.switch_session(action.target):
                self.logger.error(f"切换到群失败: {action.target}")
                return False
            self.window_manager.open_close_sidebar()
            region = self._get_room_side_bar_region()
            room_name_elements = self.ui_helper.find_text_elements(
                text="备注", region=region, fuzzy=100
            )
            if len(room_name_elements) == 1:
                name_bbox = room_name_elements[0].get("pixel_bbox")
                center = get_center_point(bbox=name_bbox)
                # 高度两倍偏移量
                name_input_y = (name_bbox[3] - name_bbox[1]) * 1.5 + center[1]
                human_like_mouse_move(center[0], name_input_y)
                pyautogui.click()
                self._replace_input_text(action.remark)
                return True

            else:
                self.logger.error("没有找到群备注")
                return False
        finally:
            self._cleanup()

import time
from dataclasses import dataclass, field

import pyautogui
from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAAction,
    RPAActionType,
)
from omni_bot_sdk.rpa.action_handlers.mixins.window_operations_mixin import (
    WindowOperationsMixin,
)
from omni_bot_sdk.utils.helpers import get_center_point
from omni_bot_sdk.utils.mouse import human_like_mouse_move


@dataclass
class PatAction(RPAAction):
    target: str = None
    user_name: str = None
    is_chatroom: bool = False

    def __post_init__(self):
        self.action_type = RPAActionType.PAT
        self.is_send_message = True


class PatHandler(WindowOperationsMixin, BaseActionHandler):
    """
    拍一拍操作的处理器。
    """

    def execute(self, action: PatAction) -> bool:
        try:
            if not self.window_manager.switch_session(action.target):
                return False
            region = self.window_manager.get_message_region()
            image = self.image_processor.take_screenshot(region=region)
            if action.is_chatroom:
                # TODO 用名字去找，误差可能性大，配合数据库+YOLO，可以拿到高准确率的结果
                positions = self.ocr_processor.find_text(
                    image=image, target_text=action.user_name
                )
                if len(positions) > 0:
                    avatar_positions = []
                    parsed_result = self.image_processor.detect_objects(image=image)
                    for result in parsed_result:
                        if result.get("label") == "avatar":
                            bbox = result.get("pixel_bbox")
                            if bbox[0] / self.window_manager.MSG_WIDTH < 0.5:
                                avatar_positions.append(result)
                    self.image_processor.draw_boxes_on_screen(
                        self.image_processor.take_screenshot(region=region),
                        parsed_result,
                        "runtime_images/pat.png",
                    )
                    ava = None
                    if len(avatar_positions) > 0:
                        for name in positions:
                            for avatar in avatar_positions:
                                if (
                                    abs(
                                        avatar.get("pixel_bbox")[1]
                                        - name.get("pixel_bbox")[1]
                                    )
                                    < 10
                                ):
                                    ava = avatar
                                    break
                            if ava:
                                break
                    if ava:
                        bbox = ava.get("pixel_bbox")
                        center = get_center_point(bbox=bbox)
                        human_like_mouse_move(
                            center[0] + region[0],
                            center[1] + region[1],
                        )
                        pyautogui.rightClick()
                        time.sleep(self.controller.window_manager.action_delay)
                    else:
                        self.logger.warn(
                            f"找到的消息位置置信度太低，不进行拍一拍: {ava}"
                        )
                        return False
                else:
                    self.logger.warn("对话框都找不到消息啊")
                    return False
            else:
                avatar_position = self.image_processor.detect_objects(image=image)
                find = False
                for result in avatar_position:
                    if result.get("label") == "avatar":
                        avatar_bbox = result.get("pixel_bbox")
                        if (
                            avatar_bbox
                            and avatar_bbox[0] / self.window_manager.MSG_WIDTH < 0.5
                        ):
                            center = get_center_point(avatar_bbox)
                            human_like_mouse_move(
                                center[0] + region[0],
                                center[1] + region[1],
                            )
                            pyautogui.rightClick()
                            time.sleep(self.controller.window_manager.action_delay)
                            find = True
                            break
                if not find:
                    self.logger.warn("私聊没有找到头像")
                    return False
                self.image_processor.draw_boxes_on_screen(
                    self.image_processor.take_screenshot(region=region),
                    avatar_position,
                    "runtime_images/pat.png",
                )
            return self.find_and_click_menu_item("拍一拍")
        finally:
            self._cleanup()

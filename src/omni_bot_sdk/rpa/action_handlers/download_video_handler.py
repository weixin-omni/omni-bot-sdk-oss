from dataclasses import dataclass, field
import time
from typing import Optional

import pyautogui
from omni_bot_sdk.rpa.action_handlers.base_handler import (
    BaseActionHandler,
    RPAAction,
    RPAActionType,
)
from omni_bot_sdk.utils.helpers import get_center_point
from omni_bot_sdk.utils.mouse import human_like_mouse_move


@dataclass
class DownloadVideoAction(RPAAction):
    target: Optional[str] = None
    name: Optional[str] = None
    max_count: int = 1
    is_chatroom: bool = False

    def __post_init__(self):
        self.action_type = RPAActionType.DOWNLOAD_VIDEO
        self.is_send_message = False


class DownloadVideoHandler(BaseActionHandler):
    """
    下载视频操作的处理器。
    """

    def execute(self, action: DownloadVideoAction) -> bool:
        """
        执行下载视频操作。
        Args:
            action (DownloadVideoAction): 操作对象。
        Returns:
            bool: 操作是否成功。
        """
        try:
            if not self.window_manager.switch_session(action.target):
                return False
            # 识别视频, 拿到会话区域，对这个区域进行yolo
            time.sleep(2)
            left, top, w, h = self.window_manager.get_message_region()
            screenshot = self.image_processor.take_screenshot(region=[left, top, w, h])
            detections = self.image_processor.detect_objects(screenshot)
            detections_video = [d for d in detections if d.get("label") == "video"]
            if len(detections_video) == 0:
                self.logger.warn("没有找到视频消息")
                return False
            # 按照Y从大到小排列
            detections_video.sort(key=lambda x: x.get("pixel_bbox")[1], reverse=True)
            for video in detections_video:
                bbox = video.get("pixel_bbox")
                center = get_center_point(bbox)
                human_like_mouse_move(
                    target_x=center[0] + left,
                    target_y=center[1] + top,
                )
                pyautogui.click()
                # TODO: 消息刷新的情况下，视频位置可能会变化，看yolo识别的速度了
            self.image_processor.draw_boxes_on_screen(
                screenshot,
                detections,
                "runtime_images/download_video.png",
            )
            return True
        finally:
            self._cleanup()

"""
UI 交互辅助模块。
提供按钮查找、OCR、点击等自动化 UI 操作能力。
"""

import time
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple

import cv2
import mss
import numpy as np
import pyautogui
from fuzzywuzzy import process
from omni_bot_sdk.utils.helpers import get_center_point
from omni_bot_sdk.utils.mouse import human_like_mouse_move


class BtnType(Enum):
    """
    按钮类型枚举。
    """

    GREEN = "green"  # 完成、确认、发布
    RED = "red"  # 取消、清空
    GRAY = "gray"  # 关闭、返回


COLOR_RANGES = {
    BtnType.GREEN: [(np.array([64, 40, 40]), np.array([84, 255, 255]))],
    BtnType.RED: [
        (np.array([0, 100, 100]), np.array([10, 255, 255])),
        (np.array([170, 100, 100]), np.array([179, 255, 255])),
    ],
    BtnType.GRAY: [(np.array([0, 0, 238]), np.array([0, 5, 245]))],
}


class UIInteractionHelper:
    """
    UI 交互辅助类。
    封装常用窗口和元素操作，如按钮查找、OCR、点击等。
    """

    def __init__(self, controller: Any):
        """
        初始化 UIInteractionHelper。
        Args:
            controller: RPAController 实例。
        """
        self.controller = controller
        self.logger = controller.logger.getChild(self.__class__.__name__)

    def find_btn_by_text(
        self, text: str, btn_type: BtnType, region: Tuple[int, int, int, int]
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        根据文本查找主色调按钮。
        先用 OpenCV 缩小范围，再用 OCR 识别文本。
        Args:
            text (str): 目标文本。
            btn_type (BtnType): 按钮类型。
            region (Tuple[int, int, int, int]): 屏幕区域。
        Returns:
            Optional[Tuple[int, int, int, int]]: 按钮区域。
        """
        centers, bboxes = self._find_areas_by_opencv(region=region, btn_type=btn_type)
        for center, bbox in zip(centers, bboxes):
            if text.strip() == "":
                bbox = [
                    bbox[0] + region[0],
                    bbox[1] + region[1],
                    bbox[2] + region[0],
                    bbox[3] + region[1],
                ]
                return bbox
            ocr_results = self._shot_and_ocr(
                region=[
                    bbox[0] + region[0],
                    bbox[1] + region[1],
                    bbox[2] - bbox[0],
                    bbox[3] - bbox[1],
                ]
            )
            for d in ocr_results:
                if d.get("label") == text:
                    bbox = [
                        bbox[0] + region[0],
                        bbox[1] + region[1],
                        bbox[2] + region[0],
                        bbox[3] + region[1],
                    ]
                    return bbox
        self.logger.error(f"OPENCV没有找到按钮: {text}")
        return None

    def find_text_elements(
        self, text: str, region: Tuple[int, int, int, int], fuzzy: int = 100
    ) -> List[Dict]:
        """
        根据文本查找元素。
        支持模糊匹配。
        Args:
            text (str): 目标文本。
            region (Tuple[int, int, int, int]): 区域。
            fuzzy (int): 模糊匹配阈值。
        Returns:
            List[Dict]: 匹配元素列表。
        """
        ocr_results = self._shot_and_ocr(region=region)
        results = []
        if fuzzy < 100 and ocr_results:
            choices_with_indices = [
                (d.get("label", ""), i) for i, d in enumerate(ocr_results)
            ]
            all_matches = process.extract(
                query=text,
                choices=choices_with_indices,
                processor=lambda item: item[0],
                limit=None,
            )
            for match_item, score in all_matches:
                if score >= fuzzy:
                    original_index = match_item[1]
                    results.append(ocr_results[original_index])
        else:
            for d in ocr_results:
                if d.get("label") == text:
                    results.append(d)
        for d in results:
            d["pixel_bbox"] = [
                d["pixel_bbox"][0] + region[0],
                d["pixel_bbox"][1] + region[1],
                d["pixel_bbox"][2] + region[0],
                d["pixel_bbox"][3] + region[1],
            ]
        return results

    def click_element(
        self, bbox: Tuple[int, int, int, int], offset: Tuple[int, int] = (0, 0)
    ) -> None:
        """
        点击元素。
        Args:
            bbox (Tuple[int, int, int, int]): 元素区域。
            offset (Tuple[int, int]): 偏移量。
        """
        center = get_center_point(bbox)
        human_like_mouse_move(
            target_x=center[0] + offset[0], target_y=center[1] + offset[1]
        )
        pyautogui.click()
        time.sleep(self.controller.window_manager.action_delay)

    def _shot_and_ocr(self, region: List[int]) -> List[Dict]:
        """
        截图并进行 OCR。
        Args:
            region (List[int]): 截图范围。
        Returns:
            List[Dict]: OCR 结果。
        """
        screenshot = self.controller.image_processor.take_screenshot(
            region=region, save_path="runtime_images/shot_and_ocr.png"
        )
        return self.controller.ocr_processor.process_image(image=screenshot)

    def find_and_click_text_element(
        self, text: str, region: Tuple[int, int, int, int]
    ) -> Optional[Tuple[int, int, int, int]]:
        """
        查找并点击指定文本元素。
        Args:
            text (str): 目标文本。
            region (Tuple[int, int, int, int]): 区域。
        Returns:
            Optional[Tuple[int, int, int, int]]: 点击区域。
        """
        ocr_results = self.find_text_elements(text=text, region=region)
        if ocr_results:
            import pyautogui
            from omni_bot_sdk.utils.helpers import get_center_point
            from omni_bot_sdk.utils.mouse import human_like_mouse_move

            bbox = ocr_results[0].get("pixel_bbox")
            center = get_center_point(bbox)
            human_like_mouse_move(target_x=center[0], target_y=center[1])
            pyautogui.click()
            return bbox
        return None

    def _find_areas_by_opencv(
        self, region: Tuple[int, int, int, int], btn_type: BtnType, min_area=500
    ) -> Tuple[List[Tuple[int, int]], List[Tuple[int, int, int, int]]]:
        """
        用 OpenCV 快速查找特定色相的 UI 元素。
        Args:
            region (Tuple[int, int, int, int]): 截图范围。
            btn_type (BtnType): 按钮类型。
            min_area (int): 最小面积阈值。
        Returns:
            Tuple[List[Tuple[int, int]], List[Tuple[int, int, int, int]]]: 按钮中心点和区域列表。
        """
        screenshot = self.controller.image_processor.take_screenshot(
            region=region, save_path="runtime_images/find_areas_by_opencv.png"
        )
        frame_bgr = cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
        hsv_frame = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        ranges = COLOR_RANGES.get(btn_type)
        if not ranges:
            raise ValueError(f"未定义的按钮类型: {btn_type}")
        final_mask = None
        for lower_color, upper_color in ranges:
            mask = cv2.inRange(hsv_frame, lower_color, upper_color)
            if final_mask is None:
                final_mask = mask
            else:
                final_mask = cv2.add(final_mask, mask)
        kernel = np.ones((5, 5), np.uint8)
        mask_processed = cv2.morphologyEx(final_mask, cv2.MORPH_CLOSE, kernel)
        mask_processed = cv2.morphologyEx(mask_processed, cv2.MORPH_OPEN, kernel)
        contours, _ = cv2.findContours(
            mask_processed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        button_centers = []
        button_bboxes = []
        for contour in contours:
            if cv2.contourArea(contour) > min_area:
                x, y, w, h = cv2.boundingRect(contour)
                center_x = x + w // 2
                center_y = y + h // 2
                button_centers.append((center_x, center_y))
                button_bboxes.append((x, y, x + w, y + h))
        return button_centers, button_bboxes

    def find_white_rect(self, region: Tuple[int, int, int, int]):
        """
        查找左右居中、上下位置不定的白色矩形。
        Args:
            region (Tuple[int, int, int, int]): 区域。
        Returns:
            Optional[List[int]]: [left, top, width, height]。
        """
        white_pixel_bgr = np.array([255, 255, 255])
        with mss.mss() as sct:
            monitor = {
                "left": region[0],
                "top": region[1],
                "width": region[2],
                "height": region[3],
            }
            screenshot = sct.grab(monitor)
            img_array = np.array(screenshot)[:, :, :3]
        h, w, _ = img_array.shape
        center_y = h // 2
        center_x = w // 2
        min_x = -1
        for x in range(center_x + 1):
            if np.array_equal(img_array[center_y, x], white_pixel_bgr):
                min_x = x
                break
        if min_x == -1:
            print("水平扫描未找到白色像素，无法确定左右边界。")
            return None
        min_y = -1
        for y in range(h):
            if np.array_equal(img_array[y, center_x], white_pixel_bgr):
                min_y = y
                break
        if min_y == -1:
            print("在中心垂直线上未找到白色像素，无法确定上下边界。")
            return None
        max_y = -1
        for y in range(h - 1, min_y - 1, -1):
            if np.array_equal(img_array[y, center_x], white_pixel_bgr):
                max_y = y
                break
        if max_y == -1:
            max_y = min_y
        rect_width = w - 2 * min_x
        rect_height = max_y - min_y + 1
        abs_left = region[0] + min_x
        abs_top = region[1] + min_y
        return [abs_left, abs_top, rect_width, rect_height]

    def click_send_button(self):
        """
        查找并点击发送按钮。
        Returns:
            bool: 是否成功。
        """
        send_button = self.controller.window_manager.get_icon_position("send_button")
        if send_button:
            center = get_center_point(send_button)
            pyautogui.click(center[0], center[1])
            time.sleep(self.controller.window_manager.action_delay)
            return True
        return False

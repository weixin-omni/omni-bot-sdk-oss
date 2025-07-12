import time
from typing import Tuple

import pyautogui
from omni_bot_sdk.rpa.window_manager import WindowTypeEnum
from omni_bot_sdk.utils.helpers import get_center_point
from omni_bot_sdk.utils.mouse import human_like_mouse_move


class WindowOperationsMixin:

    def get_window_region(self, window: pyautogui.Window) -> Tuple[int, int, int, int]:
        """
        获取窗口区域。
        """
        return [
            window.left
            + self.controller.window_manager.rpa_config.get("window_margin", 20),
            window.top
            + self.controller.window_manager.rpa_config.get("window_margin", 20),
            window.width
            - self.controller.window_manager.rpa_config.get("window_margin", 20) * 2,
            window.height
            - self.controller.window_manager.rpa_config.get("window_margin", 20) * 2,
        ]

    def find_and_click_menu_item(self, menu_text: str) -> bool:
        """
        查找并点击菜单项

        Args:
            menu_text: 菜单项文本

        Returns:
            bool: 是否成功点击
        """
        # 查找激活的会话窗口，判断条件：标题是 Weixin，大小不会很大（有点模糊的判断条件 TODO 等待优化）
        menu_window = self.controller.window_manager.wait_for_window(
            WindowTypeEnum.MenuWindow
        )
        if not menu_window:
            return False
        try:
            region = self.get_window_region(menu_window)
            screenshot = self.controller.image_processor.take_screenshot(
                region=region, save_path="runtime_images/menu.png"
            )
            # 使用OCR查找菜单项
            formatted_results = self.ocr_processor.process_image(image=screenshot)
            formatted_results = [
                d for d in formatted_results if d.get("label") == menu_text
            ]
            if len(formatted_results) > 0:
                bbox = formatted_results[0].get("pixel_bbox")
                center = get_center_point(bbox)
                human_like_mouse_move(
                    target_x=center[0] + region[0],
                    target_y=center[1] + region[1],
                )
                time.sleep(self.controller.window_manager.action_delay)
                pyautogui.click()
                return True
            return False

        except Exception as e:
            self.logger.error(f"查找并点击菜单项时出错: {str(e)}")
            return False

"""
消息发送模块。
提供自动化消息发送、@用户、剪贴板图片处理等能力。
"""

import logging
import time
from typing import Dict, List, Optional, Tuple

import pyautogui
import win32clipboard
import win32con
from Levenshtein import ratio
from omni_bot_sdk.rpa.image_processor import ImageProcessor
from omni_bot_sdk.rpa.ocr_processor import OCRProcessor
from omni_bot_sdk.rpa.window_manager import WindowManager
from omni_bot_sdk.utils.helpers import (
    copy_file_to_clipboard,
    get_center_point,
    read_temp_image,
    save_clipboard_image_to_temp,
    set_clipboard_text,
)
from omni_bot_sdk.utils.mouse import human_like_mouse_move
from PIL import Image


class MessageSender:
    """
    消息发送器。
    支持文本消息、@用户、剪贴板图片等自动化发送。
    """

    def __init__(self, window_manager: WindowManager):
        """
        初始化 MessageSender。
        Args:
            window_manager (WindowManager): 窗口管理器。
        """
        self.logger = logging.getLogger(__name__)
        self.ocr_processor = None
        self.temp_image_path = None
        self.window_manager = window_manager

    def send_message(self, message: str, clear_input_box: bool = True) -> bool:
        """
        发送文本消息。
        Args:
            message (str): 消息内容。
            clear_input_box (bool): 是否先清空输入框。
        Returns:
            bool: 是否发送成功。
        """
        try:
            if not self.window_manager.activate_input_box():
                return False
            if clear_input_box:
                pyautogui.hotkey("ctrl", "a")
                time.sleep(0.3)
                pyautogui.press("delete")
                time.sleep(0.3)
            if not set_clipboard_text(message):
                return False
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.3)
            send_button = self.window_manager.get_icon_position("send_button")
            if send_button:
                center = get_center_point(send_button)
                pyautogui.click(center[0], center[1])
                time.sleep(0.3)
                return True
            return False
        except Exception as e:
            self.logger.error(f"发送消息时出错: {str(e)}")
            return False

    def _calc_similarity(
        self, search_text: str, formatted_results: List[Dict], score_cutoff: float = 0.6
    ) -> List[Dict]:
        """
        计算文本相似度。
        Args:
            search_text (str): 查询文本。
            formatted_results (List[Dict]): OCR 结果。
            score_cutoff (float): 相似度阈值。
        Returns:
            List[Dict]: 匹配结果。
        """
        for result in formatted_results:
            result["similarity"] = ratio(
                search_text,
                result["label"],
                processor=lambda x: x.lower().replace(" ", ""),
                score_cutoff=score_cutoff,
            )
        return [
            result
            for result in formatted_results
            if result["similarity"] >= float(score_cutoff)
        ]

    def read_temp_image(self, image_path: str) -> bool:
        """
        读取临时图片。
        Args:
            image_path (str): 图片路径。
        Returns:
            bool: 是否成功。
        """
        return read_temp_image(image_path)

    def save_clipboard_image_to_temp(self) -> Optional[str]:
        """
        保存剪贴板图片到临时文件。
        Returns:
            Optional[str]: 文件路径。
        """
        return save_clipboard_image_to_temp()

    def mention_user(self, at_str: str) -> bool:
        """
        @用户。
        Args:
            at_str (str): 用户名。
        Returns:
            bool: 是否成功。
        """
        self.window_manager.activate_input_box()
        pyautogui.press("@")
        time.sleep(0.3)
        at_str = at_str.split(" ")
        at_str = max(at_str, key=len)
        at_str = at_str.strip()
        if not set_clipboard_text(f"{at_str}_"):
            self.logger.error(f"设置剪贴板文本时出错")
            return False
        pyautogui.hotkey("ctrl", "v")
        pyautogui.press("space")
        pyautogui.press("backspace")
        pyautogui.press("backspace")
        time.sleep(0.3)
        pyautogui.press("enter")
        time.sleep(0.3)
        return True

    def clear_input_box(self) -> bool:
        """
        清空输入框。
        Returns:
            bool: 是否成功。
        """
        self.window_manager.activate_input_box()
        pyautogui.hotkey("ctrl", "a")
        time.sleep(0.3)
        pyautogui.press("backspace")
        time.sleep(0.3)
        return True

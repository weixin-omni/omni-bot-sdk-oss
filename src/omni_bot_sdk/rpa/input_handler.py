"""
输入处理模块。
提供键盘、鼠标等输入操作的自动化能力。
"""

import ctypes
import logging
import time
from typing import Optional, Tuple

import pyautogui
import win32api
import win32con
import win32gui


class InputHandler:
    """
    输入处理器。
    支持鼠标移动、点击、键盘输入、输入法切换等自动化操作。
    """

    def __init__(self):
        """
        初始化 InputHandler。
        """
        self.logger = logging.getLogger(__name__)

    def move_mouse(self, x: int, y: int, duration: float = 0.5) -> bool:
        """
        移动鼠标到指定坐标。
        Args:
            x (int): 横坐标。
            y (int): 纵坐标。
            duration (float): 移动耗时（秒）。
        Returns:
            bool: 是否成功。
        """
        try:
            pyautogui.moveTo(x, y, duration=duration)
            return True
        except Exception as e:
            self.logger.error(f"移动鼠标时出错: {str(e)}")
            return False

    def click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """
        鼠标左键点击。
        Args:
            x (Optional[int]): 横坐标。
            y (Optional[int]): 纵坐标。
        Returns:
            bool: 是否成功。
        """
        try:
            if x is not None and y is not None:
                pyautogui.click(x, y)
            else:
                pyautogui.click()
            return True
        except Exception as e:
            self.logger.error(f"点击鼠标时出错: {str(e)}")
            return False

    def right_click(self, x: Optional[int] = None, y: Optional[int] = None) -> bool:
        """
        鼠标右键点击。
        Args:
            x (Optional[int]): 横坐标。
            y (Optional[int]): 纵坐标。
        Returns:
            bool: 是否成功。
        """
        try:
            if x is not None and y is not None:
                pyautogui.rightClick(x, y)
            else:
                pyautogui.rightClick()
            return True
        except Exception as e:
            self.logger.error(f"右键点击时出错: {str(e)}")
            return False

    def press_key(self, key: str) -> bool:
        """
        按下指定按键。
        Args:
            key (str): 按键名。
        Returns:
            bool: 是否成功。
        """
        try:
            pyautogui.press(key)
            return True
        except Exception as e:
            self.logger.error(f"按下按键时出错: {str(e)}")
            return False

    def hotkey(self, *keys: str) -> bool:
        """
        组合键操作。
        Args:
            *keys (str): 按键序列。
        Returns:
            bool: 是否成功。
        """
        try:
            pyautogui.hotkey(*keys)
            return True
        except Exception as e:
            self.logger.error(f"组合键时出错: {str(e)}")
            return False

    def switch_to_english_input(self) -> bool:
        """
        切换到英文输入法。
        Returns:
            bool: 是否成功。
        """
        try:
            IMC_GETOPENSTATUS = 0x0005
            IMC_SETOPENSTATUS = 0x0006
            imm32 = ctypes.WinDLL("imm32", use_last_error=True)
            handle = win32gui.GetForegroundWindow()
            hIME = imm32.ImmGetDefaultIMEWnd(handle)
            status = win32api.SendMessage(
                hIME, win32con.WM_IME_CONTROL, IMC_GETOPENSTATUS, 0
            )
            if status:
                win32api.SendMessage(
                    hIME, win32con.WM_IME_CONTROL, IMC_SETOPENSTATUS, 0
                )
                time.sleep(0.3)
                return True
            else:
                win32api.SendMessage(
                    hIME, win32con.WM_IME_CONTROL, IMC_SETOPENSTATUS, 0
                )
                time.sleep(0.3)
                return True
        except Exception as e:
            self.logger.error(f"切换输入法时出错: {str(e)}")
            return False

    def get_mouse_position(self) -> Tuple[int, int]:
        """
        获取当前鼠标坐标。
        Returns:
            Tuple[int, int]: (x, y) 坐标。
        """
        return pyautogui.position()

    def drag_to(self, x: int, y: int, duration: float = 0.5) -> bool:
        """
        拖动鼠标到指定位置。
        Args:
            x (int): 横坐标。
            y (int): 纵坐标。
            duration (float): 拖动耗时（秒）。
        Returns:
            bool: 是否成功。
        """
        try:
            pyautogui.dragTo(x, y, duration=duration)
            return True
        except Exception as e:
            self.logger.error(f"拖动鼠标时出错: {str(e)}")
            return False

    def scroll(self, clicks: int) -> bool:
        """
        滚动鼠标滚轮。
        Args:
            clicks (int): 滚动步数。
        Returns:
            bool: 是否成功。
        """
        try:
            pyautogui.scroll(clicks)
            return True
        except Exception as e:
            self.logger.error(f"滚动鼠标滚轮时出错: {str(e)}")
            return False

    def type_text(self, text: str, interval: float = 0.1) -> bool:
        """
        输入文本。
        Args:
            text (str): 文本内容。
            interval (float): 每个字符间隔（秒）。
        Returns:
            bool: 是否成功。
        """
        try:
            pyautogui.write(text, interval=interval)
            return True
        except Exception as e:
            self.logger.error(f"输入文本时出错: {str(e)}")
            return False

    def hold_key(self, key: str) -> bool:
        """
        按住指定按键。
        Args:
            key (str): 按键名。
        Returns:
            bool: 是否成功。
        """
        try:
            pyautogui.keyDown(key)
            return True
        except Exception as e:
            self.logger.error(f"按住按键时出错: {str(e)}")
            return False

    def release_key(self, key: str) -> bool:
        """
        释放指定按键。
        Args:
            key (str): 按键名。
        Returns:
            bool: 是否成功。
        """
        try:
            pyautogui.keyUp(key)
            return True
        except Exception as e:
            self.logger.error(f"释放按键时出错: {str(e)}")
            return False

    def get_screen_size(self) -> Tuple[int, int]:
        """
        获取屏幕尺寸。
        Returns:
            Tuple[int, int]: (宽, 高)。
        """
        return pyautogui.size()

    def is_mouse_pressed(self) -> bool:
        """
        检查鼠标是否被按下。
        Returns:
            bool: 是否被按下。
        """
        return pyautogui.mouseDown()

    def get_active_window_title(self) -> str:
        """
        获取当前活动窗口标题。
        Returns:
            str: 窗口标题。
        """
        return win32gui.GetWindowText(win32gui.GetForegroundWindow())

    def wait_for_window(self, window_title: str, timeout: float = 10.0) -> bool:
        """
        等待指定窗口出现。
        Args:
            window_title (str): 窗口标题。
            timeout (float): 超时时间（秒）。
        Returns:
            bool: 是否出现。
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if window_title in self.get_active_window_title():
                return True
            time.sleep(0.1)
        return False

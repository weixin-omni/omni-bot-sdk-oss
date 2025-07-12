"""
窗口尺寸配置模块。
用于建议和管理窗口尺寸参数。
"""

import math
from dataclasses import dataclass

import pyautogui

IMAGE_FACTOR = 28
MIN_PIXELS = 4 * 28 * 28
MAX_PIXELS = 16384 * 28 * 28
MAX_RATIO = 200


@dataclass
class SizeConfig:
    width: int
    height: int
    msg_top_x: int
    msg_top_y: int
    msg_width: int
    msg_height: int
    menu_width: int
    menu_height: int


def round_by_factor(number: int, factor: int) -> int:
    """
    将数字四舍五入到指定因子的倍数。

    Args:
        number: 要四舍五入的数字。
        factor: 因子。

    Returns:
        四舍五入后的数字。
    """
    return round(number / factor) * factor


def ceil_by_factor(number: int, factor: int) -> int:
    """
    将数字向上取整到指定因子的倍数。

    Args:
        number: 要向上取整的数字。
        factor: 因子。

    Returns:
        向上取整后的数字。
    """
    return math.ceil(number / factor) * factor


def floor_by_factor(number: int, factor: int) -> int:
    """
    将数字向下取整到指定因子的倍数。

    Args:
        number: 要向下取整的数字。
        factor: 因子。

    Returns:
        向下取整后的数字。
    """
    return math.floor(number / factor) * factor


def smart_resize(
    height: int,
    width: int,
    factor: int = IMAGE_FACTOR,
    min_pixels: int = MIN_PIXELS,
    max_pixels: int = MAX_PIXELS,
) -> tuple[int, int]:
    """
    智能调整图像尺寸，使其满足以下条件：

    1. 高度和宽度都是指定因子的倍数。

    2. 总像素数在 ['min_pixels', 'max_pixels'] 范围内。

    3. 图像的宽高比尽可能接近原始比例。

    Args:
        height: 原始图像高度。
        width: 原始图像宽度。
        factor: 因子，默认为 IMAGE_FACTOR。
        min_pixels: 最小像素数，默认为 MIN_PIXELS。
        max_pixels: 最大像素数，默认为 MAX_PIXELS。

    Returns:
        调整后的高度和宽度。

    Raises:
        ValueError: 如果调整后的宽高比超过 MAX_RATIO。
    """
    if max(height, width) / min(height, width) > MAX_RATIO:
        raise ValueError(
            f"绝对宽高比必须小于 {MAX_RATIO}，当前为 {max(height, width) / min(height, width)}"
        )
    h_bar = max(factor, round_by_factor(height, factor))
    w_bar = max(factor, round_by_factor(width, factor))
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = floor_by_factor(height / beta, factor)
        w_bar = floor_by_factor(width / beta, factor)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = ceil_by_factor(height * beta, factor)
        w_bar = ceil_by_factor(width * beta, factor)
    return h_bar, w_bar


def convert_qwen_size(
    bbox: tuple[int, int, int, int], height: int, width: int
) -> tuple[int, int, int, int]:
    """
    将QwenVL模型的边界框坐标转换为屏幕坐标。

    Args:
        bbox: QwenVL模型的边界框坐标 (x1, y1, x2, y2)。
        height: 原始图像高度。
        width: 原始图像宽度。

    Returns:
        转换后的屏幕坐标边界框 (x1, y1, x2, y2)。
    """
    input_height, input_width = smart_resize(height, width)
    abs_x1 = int(bbox[0] / input_width * width)
    abs_y1 = int(bbox[1] / input_height * height)
    abs_x2 = int(bbox[2] / input_width * width)
    abs_y2 = int(bbox[3] / input_height * height)
    return tuple([abs_x1, abs_y1, abs_x2, abs_y2])


# TODO 历史残留，暂时不改了，后续统一处理，核心是基于QwenVL系列模型的图片需要进行resize之后才能提高detect精度
def suggest_size() -> SizeConfig:
    """
    根据当前屏幕大小，给出建议的窗口大小
    VL模型有最适合的尺寸，不能设置太大或者太小建议是28的倍数
    同时要考虑底部状态栏的影响
    宽度设置为屏幕宽度的一半，最大不能超过1008
    高度设置为屏幕高度减去任务栏的高度，任务栏就认为是100吧
    宽高都需要是28的倍数
    """
    screen_size = pyautogui.size()
    width = screen_size.width // 2
    height = screen_size.height - 80
    width = 1008
    if height < 812:
        height = 812
    if height > 2000:
        height = 2000
    # input_height, input_width = smart_resize(height, width)
    return SizeConfig(width, height, 0, 0, 0, 0, 130, 450)


if __name__ == "__main__":
    print(suggest_size())

"""
鼠标操作工具模块。
提供人类化鼠标移动、点击等自动化能力。
"""

import math
import random
import time

import pyautogui

# --- Default Configuration Parameters ---
# You can override these by passing arguments to the main function

# Range for base speed (pixels per second)
DEFAULT_SPEED_RANGE = (
    700,
    1200,
)  # e.g., mouse moves between 700 and 1200 pixels/sec on average

# List of available tweening functions
DEFAULT_TWEEN_FUNCTIONS = [
    pyautogui.easeInQuad,
    pyautogui.easeOutQuad,
    pyautogui.easeInOutQuad,
    pyautogui.easeInBounce,
    pyautogui.easeInElastic,
    pyautogui.easeOutElastic,
    pyautogui.easeInOutElastic,
    pyautogui.easeOutBounce,
    # pyautogui.linear # Usually too robotic, but can be included for variety
]

# Minimum movement duration (seconds)
DEFAULT_MIN_DURATION = 0.1

# Maximum movement duration (seconds)
DEFAULT_MAX_DURATION = (
    1.0  # Adjusted from 1.2 to make it a bit quicker on average for long moves
)

# Duration randomization factor range (multiplies the base calculated duration)
DEFAULT_DURATION_RANDOM_FACTOR_RANGE = (
    0.75,
    1.25,
)  # e.g., 75% to 125% of calculated time


def human_like_mouse_move(
    target_x,
    target_y,
    speed_range=DEFAULT_SPEED_RANGE,
    tween_functions=DEFAULT_TWEEN_FUNCTIONS,
    min_duration=DEFAULT_MIN_DURATION,
    max_duration=DEFAULT_MAX_DURATION,
    duration_random_factor_range=DEFAULT_DURATION_RANDOM_FACTOR_RANGE,
    verbose=False,  # Set to True to print debug information
):
    """
    模拟人类鼠标移动行为。

    Args:
        target_x (int): 目标x坐标。
        target_y (int): 目标y坐标。
        speed_range (tuple): 鼠标速度范围 (最小像素/秒, 最大像素/秒)。
        tween_functions (list): 可选择的PyAutoGUI缓动函数列表。
        min_duration (float): 鼠标移动的最小持续时间。
        max_duration (float): 鼠标移动的最大持续时间。
        duration_random_factor_range (tuple): 持续时间随机化因子范围 (最小因子, 最大因子)。
        verbose (bool): 如果为True，则打印移动详情。
    """
    current_x, current_y = pyautogui.position()

    # 1. Randomly select a base speed
    selected_base_speed = random.uniform(speed_range[0], speed_range[1])

    # 2. Randomly select a tween function
    selected_tween = random.choice(tween_functions)

    # 3. Calculate distance
    distance = math.sqrt((target_x - current_x) ** 2 + (target_y - current_y) ** 2)

    # 4. Calculate base duration
    if distance == 0:
        # If already at the target, simulate a tiny "adjustment" or "hesitation"
        final_duration = random.uniform(min_duration * 0.5, min_duration * 1.5)
        # Optionally, don't move at all or move by a pixel and back
        # For now, we'll just use a small duration, moveTo will handle no actual move
    else:
        base_duration = distance / selected_base_speed

        # 5. Apply randomization to duration
        random_factor = random.uniform(
            duration_random_factor_range[0], duration_random_factor_range[1]
        )
        randomized_duration = base_duration * random_factor

        # 6. Ensure duration is within min/max bounds
        final_duration = max(min_duration, min(max_duration, randomized_duration))

    if verbose:
        print(
            f"Human-like move from ({current_x},{current_y}) to ({target_x},{target_y}):"
        )
        print(f"  Distance: {distance:.2f} pixels")
        print(f"  Selected Speed: {selected_base_speed:.2f} px/s")
        print(f"  Selected Tween: {selected_tween.__name__}")
        print(
            f"  Calculated Base Duration: {base_duration if distance > 0 else 'N/A':.3f}s"
        )
        print(
            f"  Randomized Duration (before clamp): {randomized_duration if distance > 0 else 'N/A':.3f}s"
        )
        print(f"  Final Duration: {final_duration:.3f}s")

    # 7. Execute the mouse move
    pyautogui.moveTo(target_x, target_y, duration=final_duration, tween=selected_tween)

    if verbose:
        final_pos = pyautogui.position()
        print(f"  Moved to: ({final_pos[0]},{final_pos[1]})")
        print("-" * 30)


# --- Example Usage ---
if __name__ == "__main__":
    print("PyAutoGUI will start moving the mouse in 3 seconds...")
    print("Switch to a window where you can observe the mouse.")
    time.sleep(3)

    screen_width, screen_height = pyautogui.size()

    # Test Case 1: Short move
    print("\n--- Test Case 1: Short Move ---")
    human_like_mouse_move(100, 150, verbose=True)
    time.sleep(random.uniform(0.5, 1.5))  # Human-like pause

    # Test Case 2: Medium move to center
    print("\n--- Test Case 2: Medium Move to Center ---")
    human_like_mouse_move(screen_width // 2, screen_height // 2, verbose=True)
    time.sleep(random.uniform(0.5, 1.5))

    # Test Case 3: Long move to bottom-right
    print("\n--- Test Case 3: Long Move to Bottom-Right ---")
    human_like_mouse_move(screen_width - 50, screen_height - 50, verbose=True)
    time.sleep(random.uniform(0.5, 1.5))

    # Test Case 4: Move to current location (should be very quick)
    print("\n--- Test Case 4: Move to Current Location ---")
    current_x, current_y = pyautogui.position()
    human_like_mouse_move(current_x, current_y, verbose=True)
    time.sleep(random.uniform(0.5, 1.5))

    # Test Case 5: Custom parameters - Slower speed, specific tweens
    print("\n--- Test Case 5: Custom Parameters (Slower) ---")
    custom_tweens = [pyautogui.easeInBounce, pyautogui.easeOutBounce]
    human_like_mouse_move(
        200,
        screen_height - 200,
        speed_range=(300, 500),  # Slower
        tween_functions=custom_tweens,
        min_duration=0.3,
        max_duration=2.0,
        verbose=True,
    )

    print("\nAll tests completed.")

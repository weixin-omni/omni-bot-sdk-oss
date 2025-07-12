import sys
import os


def get_model_path(model_name):
    """
    获取 yolo 模型文件的绝对路径，兼容源码和打包环境。
    """
    if getattr(sys, "frozen", False):
        # 打包后
        base_dir = os.path.dirname(sys.executable)
        model_path = os.path.join(
            base_dir, "omni_bot_sdk", "yolo", "models", model_name
        )
    else:
        # 源码
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, "models", model_name)
    return model_path

"""
日志配置模块。
提供日志初始化与格式化工具。
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

import colorlog


def setup_logging(log_dir: str = "logs", log_level: int = logging.INFO):
    """
    配置日志系统

    Args:
        log_dir: 日志目录
        log_level: 日志级别
    """
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(parents=True, exist_ok=True)

    # 配置根日志记录器
    root_logger.setLevel(log_level)

    # 创建彩色控制台处理器
    console_handler = colorlog.StreamHandler()
    console_handler.setLevel(log_level)

    # 彩色日志格式，增加毫秒
    console_formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s.%(msecs)03d - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
        datefmt="%H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "red,bg_white",
        },
    )
    console_handler.setFormatter(console_formatter)
    root_logger.addHandler(console_handler)

    # 创建文件处理器
    file_handler = RotatingFileHandler(
        log_path / "app.log", maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    file_handler.setLevel(log_level)
    # 文件日志格式（使用模块名和行号）
    file_formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(module)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)

    # 设置第三方库的日志级别
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("werkzeug").setLevel(logging.WARNING)
    logging.getLogger("ultralytics").setLevel(logging.ERROR)
    logging.getLogger("RapidOCR").setLevel(logging.WARNING)

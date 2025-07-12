"""
服务层包初始化文件。
包含数据库、消息、RPA、微信等核心服务模块。
"""

try:
    from omni_bot_sdk.services.pro.new_friend_check_service import NewFriendCheckService
except ImportError:
    from omni_bot_sdk.services.functional.new_friend_check_service import (
        NewFriendCheckService,
    )

__all__ = ["NewFriendCheckService"]

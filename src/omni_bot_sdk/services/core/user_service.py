"""
用户服务模块。
提供用户相关的服务接口。
"""

import json
import os
from pathlib import Path
from typing import Optional, Any, Dict
import psutil

from omni_bot_sdk.models import UserInfo
from omni_bot_sdk.utils.fuck_zxl import WeChatDumper


class UserService:
    """
    用户服务类。
    管理用户信息和授权信息。
    """

    def __init__(self, dbkey: str, user_config: Optional[Dict[str, Any]] = None):
        """
        初始化用户服务。

        Args:
            dbkey: 数据库键。
            user_config: 用户配置字典，包含用户相关配置项。
        """
        self.dbkey = dbkey
        self.user_info: UserInfo = None

        # Use provided user config or empty dict as fallback
        user_cfg = user_config or {}
        fallback_user_info = user_cfg.get("fallback_user_info", {}) or {}

        self.wxdump = WeChatDumper()
        wechat_info = None

        # Try to get pid first
        try:
            pid = self.wxdump._find_main_wechat_pid()
            if pid and pid > 0:
                # Get version info
                try:
                    exe = psutil.Process(pid).exe()
                    version = self.wxdump._get_file_version(exe)
                except Exception:
                    version = ""

                # Try full memory dump
                wechat_info = self.wxdump.find_and_dump()
                if wechat_info:
                    # Ensure pid and version are set correctly
                    wechat_info.pid = pid
                    if not getattr(wechat_info, "version", None):
                        wechat_info.version = version
                elif fallback_user_info:
                    # Memory dump failed but we have fallback config, use it with real pid
                    self.user_info = UserInfo(
                        pid=str(pid),
                        version=version or str(fallback_user_info.get("version", "")),
                        account=str(fallback_user_info.get("account", "")),
                        alias=str(fallback_user_info.get("alias", "")),
                        nickname=str(fallback_user_info.get("nickname", "")),
                        phone=str(fallback_user_info.get("phone", "")),
                        data_dir=str(fallback_user_info.get("data_dir", "")),
                        dbkey=self.dbkey,
                        raw_keys={},
                        dat_key="",
                        dat_xor_key=-1,
                        avatar_url=str(fallback_user_info.get("avatar_url", "")),
                    )
                    return
        except Exception:
            pass

        # If we got wechat_info from memory dump, use it
        if wechat_info:
            self.user_info = UserInfo(
                pid=wechat_info.pid,
                version=wechat_info.version,
                account=wechat_info.account,
                alias=wechat_info.alias,
                nickname=wechat_info.nickname,
                phone=wechat_info.phone,
                data_dir=wechat_info.data_dir,
                dbkey=self.dbkey,
                raw_keys={},
                dat_key="",
                dat_xor_key=-1,
                avatar_url=wechat_info.avatar_url,
            )
        else:
            raise Exception("未找到微信主窗口，请确保微信已登录")

    def get_user_info(self):
        """
        获取当前用户信息。

        Returns:
            用户信息。
        """
        return self.user_info

    def set_user_info(self, user_info: UserInfo):
        """
        更新用户信息。

        Args:
            user_info: 新的用户信息。
        """
        self.user_info = user_info

    def update_raw_key(self, key: str, value: str):
        """
        更新原始密钥。

        Args:
            key: 密钥名称。
            value: 密钥值。
        """
        self.user_info.raw_keys[key] = value

    def get_raw_key(self, key: str) -> Optional[str]:
        """
        获取原始密钥。

        Args:
            key: 密钥名称。

        Returns:
            密钥值，如果不存在则返回None。
        """
        return self.user_info.raw_keys.get(key, None)

    def dump_to_file(self):
        """
        将当前用户信息写入到Windows用户目录下，文件名为account.json，使用pathlib实现。
        """
        if not self.user_info:
            raise Exception("用户信息未初始化")
        # 获取用户目录
        user_home = Path.home()
        # 构造文件路径
        file_path = user_home / f"{self.user_info.account}.json"
        # 转为dict并写入json
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self.user_info.to_dict(), f, ensure_ascii=False, indent=4)

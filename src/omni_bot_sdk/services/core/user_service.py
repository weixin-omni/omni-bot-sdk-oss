"""
用户服务模块。
提供用户相关的服务接口。
"""

import json
import os
from pathlib import Path
from typing import Optional

from omni_bot_sdk.models import UserInfo
from omni_bot_sdk.utils.fuck_zxl import WeChatDumper


class UserService:
    """
    用户服务类。
    管理用户信息和授权信息。
    """

    def __init__(self, dbkey: str):
        """
        初始化用户服务。

        Args:
            dbkey: 数据库键。
        """
        self.dbkey = dbkey
        self.user_info: UserInfo = None
        self.wxdump = WeChatDumper()
        wechat_info = self.wxdump.find_and_dump()
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

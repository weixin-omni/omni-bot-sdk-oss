"""
配置加载与访问模块
"""

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


class Config:
    """
    配置管理类。
    支持YAML配置文件的加载、嵌套访问和字典式访问。
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()

    def _load_config(self):
        """
        加载YAML配置文件。
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"配置文件 {self.config_path} 不存在")

        with open(self.config_path, "r", encoding="utf-8") as f:
            return YAML().load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置项，支持点号分隔的嵌套访问。

        Args:
            key: 配置键，支持点号分隔的嵌套键，如 'plugins.my_plugin'
            default: 默认值，当配置项不存在时返回

        Returns:
            配置项的值，如果不存在则返回默认值
        """
        if "." not in key:
            return self.config.get(key, default)

        # 处理嵌套键
        keys = key.split(".")
        value = self.config

        for k in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(k)
            if value is None:
                return default

        return value

    def set(self, key: str, value: Any):
        """
        设置配置项，支持点号分隔的嵌套访问。
        """
        if "." not in key:
            self.config[key] = value
            with open(self.config_path, "w", encoding="utf-8") as f:
                YAML().dump(self.config, f)
            return

        keys = key.split(".")
        value = self.config
        for k in keys:
            if not isinstance(value, dict):
                return
        value[keys[-1]] = value
        with open(self.config_path, "w", encoding="utf-8") as f:
            YAML().dump(self.config, f)

    def __getitem__(self, key: str) -> Any:
        """
        支持字典式访问配置项。
        """
        return self.config[key]

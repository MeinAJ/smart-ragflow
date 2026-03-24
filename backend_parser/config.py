"""
配置管理模块。

从 common.config 导入配置，保持向后兼容。
"""

from backend_common.config import settings, CommonSettings

__all__ = ["settings", "CommonSettings"]

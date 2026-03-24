"""
Backend Admin 数据库模块。

从 backend_common 导入共享数据库功能。
"""

from backend_common.database import (
    engine,
    SessionLocal,
    get_db,
    get_db_session,
    DatabaseClient
)

__all__ = [
    "engine",
    "SessionLocal",
    "get_db",
    "get_db_session",
    "DatabaseClient"
]

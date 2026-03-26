"""
数据库模块。

提供数据库连接和会话管理。
"""

import logging
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from backend_common.config import settings

logger = logging.getLogger(__name__)

# 创建引擎（添加 utf8mb4 字符集支持中文）
# 确保使用 utf8mb4 字符集
connect_args = {
    "charset": "utf8mb4",
}

# 如果 URL 中没有 charset 参数，添加它
_database_url = settings.DATABASE_URL
if "charset=" not in _database_url:
    if "?" in _database_url:
        _database_url += "&charset=utf8mb4"
    else:
        _database_url += "?charset=utf8mb4"

engine = create_engine(
    _database_url,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.DEBUG,
    connect_args=connect_args
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_db():
    """
    获取数据库会话的上下文管理器。
    
    使用示例：
        with get_db() as db:
            doc = db.query(Document).first()
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        db.rollback()
        raise
    finally:
        db.close()


def get_db_session() -> Session:
    """
    获取数据库会话（需要手动关闭）。
    
    Returns:
        Session: 数据库会话
    """
    return SessionLocal()


class DatabaseClient:
    """
    数据库客户端（单例模式）。
    
    用于 Worker 等需要长连接的场景。
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # 确保使用 utf8mb4 字符集
        _database_url = settings.DATABASE_URL
        if "charset=" not in _database_url:
            if "?" in _database_url:
                _database_url += "&charset=utf8mb4"
            else:
                _database_url += "?charset=utf8mb4"
        
        connect_args = {
            "charset": "utf8mb4",
        }
        
        self.engine = create_engine(
            _database_url,
            pool_size=5,
            max_overflow=10,
            pool_pre_ping=True,
            connect_args=connect_args
        )
        self.SessionLocal = sessionmaker(
            autocommit=False, 
            autoflush=False, 
            bind=self.engine
        )
        self._initialized = True
    
    def get_session(self) -> Session:
        """获取数据库会话。"""
        return self.SessionLocal()

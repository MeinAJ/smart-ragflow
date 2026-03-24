"""
Redis 客户端模块。

提供 Redis 连接和缓存功能。
"""

import logging
import pickle
from typing import Any, Optional
import redis.asyncio as redis
from backend_common.config import settings

logger = logging.getLogger(__name__)


class RedisClient:
    """
    Redis 客户端。
    
    提供异步 Redis 操作。
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._client = None
        return cls._instance
    
    @property
    def client(self) -> redis.Redis:
        """获取 Redis 客户端。"""
        if self._client is None:
            self._client = redis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=False
            )
        return self._client
    
    async def close(self):
        """关闭连接。"""
        if self._client:
            await self._client.close()
            self._client = None
    
    async def get(self, key: str) -> Optional[bytes]:
        """获取值。"""
        try:
            return await self.client.get(key)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
            return None
    
    async def set(
        self, 
        key: str, 
        value: bytes, 
        expire: int = None
    ) -> bool:
        """设置值。"""
        try:
            await self.client.set(key, value, ex=expire)
            return True
        except Exception as e:
            logger.warning(f"Redis set failed: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除键。"""
        try:
            await self.client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Redis delete failed: {e}")
            return False
    
    async def ping(self) -> bool:
        """检查连接。"""
        try:
            return await self.client.ping()
        except Exception as e:
            logger.warning(f"Redis ping failed: {e}")
            return False


# 全局实例
redis_client = RedisClient()

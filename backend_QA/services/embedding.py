"""
Embedding 服务客户端模块。

封装 BGE-M3 HTTP 接口调用，实现文本向量化功能。
返回的向量已经过 L2 归一化。
"""

import logging
from typing import List
import httpx

from backend_common.config import settings
from backend_common.clients.embedding_client import normalize_vector

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """
    BGE-M3 Embedding 服务客户端。

    提供异步文本向量化功能。
    """

    def __init__(self, base_url: str = None, model: str = None, timeout: float = None):
        """
        初始化 Embedding 客户端。

        Args:
            base_url: Embedding 服务地址
            timeout: 请求超时时间（秒）
        """
        self.base_url = base_url or settings.EMBEDDING_URL
        self.model = model or settings.EMBEDDING_MODEL
        self.timeout = timeout or settings.EMBEDDING_TIMEOUT
        self._client: httpx.AsyncClient = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端。"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def embed(self, text: str) -> List[float]:
        """
        将文本转换为归一化向量。

        Args:
            text: 输入文本

        Returns:
            List[float]: 归一化后的向量（L2 范数为 1）

        Raises:
            Exception: 调用失败时抛出
        """
        client = await self._get_client()

        try:
            logger.info(f"Embedding text: {text[:50]}...")
            response = await client.post(
                url=self.base_url,
                json={
                    "model": self.model,
                    "prompt": text
                }
            )
            response.raise_for_status()

            result = response.json()
            vector = result.get("embedding") or result.get("vector") or result

            # L2 归一化
            vector = normalize_vector(vector)

            logger.info(f"Embedding completed, vector dim: {len(vector)}")
            return vector

        except httpx.HTTPStatusError as e:
            logger.error(f"Embedding HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Embedding service HTTP error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"Embedding error: {str(e)}")
            raise Exception(f"Embedding failed: {str(e)}")

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化。

        Args:
            texts: 输入文本列表

        Returns:
            List[List[float]]: 向量列表
        """
        # TODO: 实现批量调用优化
        vectors = []
        for text in texts:
            vector = await self.embed(text)
            vectors.append(vector)
        return vectors

    async def close(self):
        """关闭 HTTP 客户端。"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出。"""
        await self.close()


# 全局客户端实例
embedding_client = EmbeddingClient()

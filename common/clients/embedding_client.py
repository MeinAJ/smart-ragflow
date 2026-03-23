"""
Embedding 客户端模块。

提供文档分块的向量化功能，支持 Redis 缓存。
"""

import asyncio
import hashlib
import json
import logging
from typing import Any, List, Optional

import httpx
import redis.asyncio as redis

from common.config import settings

logger = logging.getLogger(__name__)


def normalize_vector(vector: List[float]) -> List[float]:
    """
    L2 归一化向量。
    
    将向量转换为单位向量（L2 范数为 1），用于 cosine similarity 计算。
    
    Args:
        vector: 输入向量
        
    Returns:
        List[float]: 归一化后的单位向量
    """
    if not vector:
        return vector
    
    # 计算 L2 范数
    norm = sum(x ** 2 for x in vector) ** 0.5
    
    if norm == 0:
        return vector
    
    # 归一化
    return [x / norm for x in vector]


class EmbeddingCache:
    """
    Embedding Redis 缓存。
    
    缓存向量化结果，减少重复计算。
    """
    
    def __init__(
        self,
        redis_url: str = None,
        db: int = None,
        prefix: str = None,
        ttl: int = None,
        enabled: bool = None
    ):
        """
        初始化缓存。
        
        Args:
            redis_url: Redis 连接 URL
            db: Redis 数据库
            prefix: 缓存 key 前缀
            ttl: 缓存过期时间（秒）
            enabled: 是否启用缓存
        """
        self.redis_url = redis_url or settings.REDIS_URL
        self.db = db if db is not None else settings.REDIS_DB
        self.prefix = prefix or settings.EMBEDDING_CACHE_PREFIX
        self.ttl = ttl if ttl is not None else settings.EMBEDDING_CACHE_TTL
        self.enabled = enabled if enabled is not None else settings.EMBEDDING_CACHE_ENABLED
        self._client: Optional[redis.Redis] = None
    
    async def _get_client(self) -> Optional[redis.Redis]:
        """获取或创建 Redis 客户端。"""
        if not self.enabled:
            return None
        if self._client is None:
            try:
                self._client = redis.from_url(
                    self.redis_url,
                    db=self.db,
                    decode_responses=True
                )
            except Exception as e:
                logger.warning(f"Failed to connect to Redis: {e}")
                self.enabled = False
        return self._client
    
    def _make_key(self, text: str) -> str:
        """
        生成缓存 key。
        
        使用文本的 MD5 hash 作为 key。
        
        Args:
            text: 输入文本
            
        Returns:
            str: 缓存 key
        """
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"{self.prefix}{text_hash}"
    
    async def get(self, text: str) -> Optional[List[float]]:
        """
        从缓存获取向量。
        
        Args:
            text: 输入文本
            
        Returns:
            Optional[List[float]]: 缓存的向量，未命中返回 None
        """
        if not self.enabled:
            return None
        
        client = await self._get_client()
        if not client:
            return None
        
        try:
            key = self._make_key(text)
            cached = await client.get(key)
            if cached:
                vector = json.loads(cached)
                logger.debug(f"Cache hit for text: {text[:50]}...")
                return vector
        except Exception as e:
            logger.debug(f"Cache get failed: {e}")
        
        return None
    
    async def set(self, text: str, vector: List[float]) -> bool:
        """
        将向量存入缓存。
        
        Args:
            text: 输入文本
            vector: 向量
            
        Returns:
            bool: 是否成功
        """
        if not self.enabled:
            return False
        
        client = await self._get_client()
        if not client:
            return False
        
        try:
            key = self._make_key(text)
            value = json.dumps(vector)
            await client.setex(key, self.ttl, value)
            logger.debug(f"Cached embedding for text: {text[:50]}...")
            return True
        except Exception as e:
            logger.debug(f"Cache set failed: {e}")
        
        return False
    
    async def close(self):
        """关闭 Redis 连接。"""
        if self._client:
            await self._client.close()
            self._client = None


class EmbeddingClient:
    """
    Embedding 服务客户端。

    提供异步文本向量化功能，支持并发控制、超时重试和 Redis 缓存。
    """

    def __init__(
        self,
        base_url: str = None,
        model: str = None,
        timeout: float = None,
        max_concurrent: int = 5,
        max_retries: int = 3,
        cache_enabled: bool = None
    ):
        """
        初始化 Embedding 客户端。

        Args:
            base_url: Embedding 服务地址
            model: 模型名称
            timeout: 请求超时时间（秒）
            max_concurrent: 最大并发数
            max_retries: 最大重试次数
            cache_enabled: 是否启用缓存
        """
        self.base_url = base_url or settings.EMBEDDING_URL
        self.model = model or settings.EMBEDDING_MODEL
        self.timeout = timeout or settings.EMBEDDING_TIMEOUT
        self.max_concurrent = max_concurrent
        self.max_retries = max_retries
        self._client: Optional[httpx.AsyncClient] = None
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._cache = EmbeddingCache(enabled=cache_enabled)

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端。"""
        if self._client is None or self._client.is_closed:
            timeout = httpx.Timeout(
                connect=10.0,
                read=self.timeout,
                write=10.0,
                pool=5.0
            )
            self._client = httpx.AsyncClient(
                timeout=timeout,
                limits=httpx.Limits(
                    max_connections=20,
                    max_keepalive_connections=10
                )
            )
        return self._client

    def _get_semaphore(self) -> asyncio.Semaphore:
        """获取并发控制信号量。"""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    async def _embed_from_service(self, text: str, retry_count: int = 0) -> List[float]:
        """
        从 Embedding 服务获取向量。
        
        Args:
            text: 输入文本
            retry_count: 当前重试次数
            
        Returns:
            List[float]: 向量
        """
        async with self._get_semaphore():
            client = await self._get_client()

            try:
                logger.debug(f"Embedding text ({len(text)} chars): {text[:50]}...")

                response = await client.post(
                    url=self.base_url,
                    json={
                        "model": self.model,
                        "prompt": text
                    }
                )
                response.raise_for_status()

                result = response.json()

                # 适配不同返回格式
                vector = result.get("embedding") or result.get("vector") or result.get("embeddings")
                if isinstance(vector, list) and len(vector) > 0 and isinstance(vector[0], list):
                    vector = vector[0]

                if not vector:
                    raise ValueError("Empty embedding returned")

                logger.debug(f"Embedding completed, dim: {len(vector)}")
                return vector

            except httpx.TimeoutException as e:
                logger.warning(f"Embedding timeout (attempt {retry_count + 1}): {str(e)}")
                if retry_count < self.max_retries:
                    wait_time = 2 ** retry_count
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    return await self._embed_from_service(text, retry_count + 1)
                raise Exception(f"Embedding timeout after {self.max_retries + 1} attempts: {str(e)}")

            except httpx.HTTPStatusError as e:
                logger.error(f"Embedding HTTP error: {e.response.status_code} - {e.response.text}")
                raise Exception(f"Embedding service HTTP error: {e.response.status_code}")

            except Exception as e:
                logger.error(f"Embedding error: {str(e)}")
                if retry_count < self.max_retries:
                    wait_time = 2 ** retry_count
                    logger.info(f"Retrying in {wait_time} seconds...")
                    await asyncio.sleep(wait_time)
                    return await self._embed_from_service(text, retry_count + 1)
                raise Exception(f"Embedding failed after {self.max_retries + 1} attempts: {str(e)}")

    async def embed(self, text: str) -> List[float]:
        """
        将文本转换为归一化向量（带缓存）。
        
        优先从 Redis 缓存获取，未命中则调用服务、归一化并缓存结果。
        返回的向量已经过 L2 归一化，可直接用于 cosine similarity 计算。

        Args:
            text: 输入文本

        Returns:
            List[float]: 归一化后的向量（L2 范数为 1）
        """
        if not text or not text.strip():
            return [0.0] * settings.EMBEDDING_DIM

        # 1. 尝试从缓存获取（缓存中的向量已经是归一化的）
        cached_vector = await self._cache.get(text)
        if cached_vector is not None:
            return cached_vector

        # 2. 调用 Embedding 服务
        vector = await self._embed_from_service(text)

        # 3. L2 归一化
        vector = normalize_vector(vector)

        # 4. 存入缓存（存储归一化后的向量）
        await self._cache.set(text, vector)

        return vector

    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量文本向量化（带缓存）。
        
        返回的向量已经过 L2 归一化。

        Args:
            texts: 输入文本列表

        Returns:
            List[List[float]]: 归一化后的向量列表
        """
        if not texts:
            return []

        logger.info(f"Embedding {len(texts)} texts with max_concurrent={self.max_concurrent}")

        # 检查缓存命中情况
        cache_hits = 0
        cache_misses = 0

        results = []
        for text in texts:
            cached = await self._cache.get(text)
            if cached:
                results.append(cached)
                cache_hits += 1
            else:
                results.append(None)
                cache_misses += 1

        # 对未命中的文本调用服务
        miss_indices = [i for i, v in enumerate(results) if v is None]
        if miss_indices:
            miss_texts = [texts[i] for i in miss_indices]
            logger.info(f"Cache hits: {cache_hits}, misses: {cache_misses}")

            # 并发调用服务
            tasks = [self._embed_from_service(text) for text in miss_texts]
            vectors = await asyncio.gather(*tasks, return_exceptions=True)

            # 处理结果、归一化并缓存
            for idx, vector in zip(miss_indices, vectors):
                if isinstance(vector, Exception):
                    logger.error(f"Failed to embed text {idx}: {vector}")
                    results[idx] = [0.0] * settings.EMBEDDING_DIM
                else:
                    # L2 归一化
                    vector = normalize_vector(vector)
                    results[idx] = vector
                    await self._cache.set(texts[idx], vector)

        logger.info(f"Batch embedding completed: {cache_hits} from cache, {cache_misses} from service")
        return results

    async def embed_chunks(self, chunks: List[Any]) -> None:
        """
        为文档分块生成向量（原地修改）。

        Args:
            chunks: 文档分块列表（需要有 content 和 embedding 属性）
        """
        if not chunks:
            return

        texts = []
        for chunk in chunks:
            # 支持 dataclass 和 dict 两种格式
            if hasattr(chunk, 'content'):
                texts.append(chunk.content)
            elif isinstance(chunk, dict):
                texts.append(chunk.get('content', ''))
            else:
                texts.append(str(chunk))

        vectors = await self.embed_batch(texts)

        for chunk, vector in zip(chunks, vectors):
            if hasattr(chunk, 'embedding'):
                chunk.embedding = vector
            elif isinstance(chunk, dict):
                chunk['embedding'] = vector

        logger.info(f"Embedded {len(chunks)} chunks")

    async def close(self):
        """关闭 HTTP 客户端和 Redis 连接。"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        await self._cache.close()

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出。"""
        await self.close()


# 全局客户端实例
embedding_client = EmbeddingClient()

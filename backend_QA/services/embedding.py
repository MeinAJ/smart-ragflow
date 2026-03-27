"""
Embedding 服务客户端模块。

本模块提供文本向量化的功能，支持缓存机制以提高性能。
支持多种 Embedding 后端（BGE-M3、Ollama、OpenAI 等）。

使用示例:
    >>> from backend_QA.services.embedding import embedding_client
    >>> vector = await embedding_client.embed("什么是 RAG 技术？")
    >>> print(len(vector))  # 输出: 1024 (BGE-M3 维度)

配置说明:
    通过环境变量配置 Embedding 服务:
    - EMBEDDING_URL: Embedding 服务地址
    - EMBEDDING_MODEL: 模型名称
    - EMBEDDING_DIM: 向量维度
    - EMBEDDING_TIMEOUT: 请求超时时间（秒）
    - EMBEDDING_CACHE_ENABLED: 是否启用缓存
    - EMBEDDING_CACHE_TTL: 缓存有效期（秒）

缓存机制:
    使用 Redis 缓存 Embedding 结果，键格式为: emb:{text_md5}
    缓存可以显著减少重复文本的 Embedding 调用，降低延迟和成本。
"""

import hashlib
import json
import logging
from typing import List, Optional

import httpx

from backend_common.config import settings
from backend_common.clients.redis_client import redis_client

logger = logging.getLogger(__name__)


class EmbeddingClient:
    """
    Embedding 服务客户端。
    
    负责将文本转换为向量表示，支持结果缓存以提高性能。
    
    Attributes:
        client: HTTP 异步客户端
        embedding_url: Embedding 服务端点
        embedding_model: 使用的模型名称
        embedding_dim: 向量维度
        timeout: 请求超时时间
    """
    
    def __init__(self):
        """初始化 Embedding 客户端。"""
        self.client = httpx.AsyncClient(timeout=settings.EMBEDDING_TIMEOUT)
        self.embedding_url = settings.EMBEDDING_URL
        self.embedding_model = settings.EMBEDDING_MODEL
        self.embedding_dim = settings.EMBEDDING_DIM
        self.timeout = settings.EMBEDDING_TIMEOUT
        
        logger.info(
            f"EmbeddingClient 初始化: "
            f"url={self.embedding_url}, "
            f"model={self.embedding_model}, "
            f"dim={self.embedding_dim}"
        )
    
    def _compute_text_hash(self, text: str) -> str:
        """
        计算文本的 MD5 哈希值，用于缓存键。
        
        为什么用 MD5？
        - 速度快：计算效率高
        - 冲突率低：对于文本内容足够安全
        - 长度固定：32 字符，适合作为 Redis 键
        
        Args:
            text: 输入文本
            
        Returns:
            MD5 哈希字符串
            
        Example:
            >>> client._compute_text_hash("hello")
            '5d41402abc4b2a76b9719d911017c592'
        """
        return hashlib.md5(text.encode('utf-8')).hexdigest()
    
    async def _get_from_cache(self, text: str) -> Optional[List[float]]:
        """
        从缓存中获取 Embedding 结果。
        
        Args:
            text: 查询文本
            
        Returns:
            缓存的向量，如果不存在则返回 None
        """
        if not settings.EMBEDDING_CACHE_ENABLED:
            return None
        
        cache_key = f"{settings.EMBEDDING_CACHE_PREFIX}{self._compute_text_hash(text)}"
        
        try:
            cached_data = await redis_client.get(cache_key)
            if cached_data:
                logger.debug(f"缓存命中: {cache_key}")
                return json.loads(cached_data)
        except Exception as e:
            logger.warning(f"读取缓存失败: {e}")
        
        return None
    
    async def _save_to_cache(self, text: str, vector: List[float]) -> None:
        """
        将 Embedding 结果保存到缓存。
        
        Args:
            text: 原始文本
            vector: 向量结果
        """
        if not settings.EMBEDDING_CACHE_ENABLED:
            return
        
        cache_key = f"{settings.EMBEDDING_CACHE_PREFIX}{self._compute_text_hash(text)}"
        
        try:
            await redis_client.setex(
                cache_key,
                settings.EMBEDDING_CACHE_TTL,
                json.dumps(vector)
            )
            logger.debug(f"缓存已保存: {cache_key}")
        except Exception as e:
            logger.warning(f"保存缓存失败: {e}")
    
    async def embed(self, text: str) -> List[float]:
        """
        将文本转换为向量。
        
        执行流程:
        1. 检查缓存，如果命中直接返回
        2. 调用 Embedding 服务获取向量
        3. 保存结果到缓存
        4. 返回向量
        
        Args:
            text: 输入文本
            
        Returns:
            向量表示，浮点数列表
            
        Raises:
            EmbeddingError: Embedding 服务调用失败时抛出
            ValueError: 输入文本为空时抛出
            
        Example:
            >>> vector = await client.embed("机器学习")
            >>> len(vector)
            1024
            >>> type(vector[0])
            <class 'float'>
        """
        if not text or not text.strip():
            raise ValueError("输入文本不能为空")
        
        text = text.strip()
        
        # 1. 尝试从缓存获取
        cached_vector = await self._get_from_cache(text)
        if cached_vector is not None:
            logger.debug(f"Embedding 缓存命中，文本长度: {len(text)}")
            return cached_vector
        
        logger.info(f"调用 Embedding 服务，文本长度: {len(text)}")
        
        # 2. 调用 Embedding 服务
        try:
            response = await self.client.post(
                self.embedding_url,
                json={
                    "model": self.embedding_model,
                    "prompt": text
                }
            )
            response.raise_for_status()
            
            result = response.json()
            
            # 兼容不同 Embedding 服务的响应格式
            if "embedding" in result:
                vector = result["embedding"]
            elif "embeddings" in result:
                vector = result["embeddings"][0]
            else:
                raise ValueError(f"未知的响应格式: {result.keys()}")
            
            # 验证向量维度
            if len(vector) != self.embedding_dim:
                logger.warning(
                    f"向量维度不匹配: 期望 {self.embedding_dim}, 实际 {len(vector)}"
                )
            
            # 3. 保存到缓存
            await self._save_to_cache(text, vector)
            
            logger.info(f"Embedding 成功，向量维度: {len(vector)}")
            return vector
            
        except httpx.HTTPStatusError as e:
            logger.error(f"Embedding 服务 HTTP 错误: {e.response.status_code} - {e.response.text}")
            raise EmbeddingError(f"Embedding 服务返回错误: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"Embedding 服务请求失败: {e}")
            raise EmbeddingError(f"无法连接到 Embedding 服务: {self.embedding_url}") from e
        except Exception as e:
            logger.exception(f"Embedding 处理异常: {e}")
            raise EmbeddingError(f"Embedding 失败: {str(e)}") from e
    
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """
        批量将文本转换为向量。
        
        对于大量文本，批量处理比逐个调用更高效。
        
        Args:
            texts: 文本列表
            
        Returns:
            向量列表，与输入文本一一对应
            
        Example:
            >>> texts = ["文本1", "文本2", "文本3"]
            >>> vectors = await client.embed_batch(texts)
            >>> len(vectors)
            3
        """
        if not texts:
            return []
        
        logger.info(f"批量 Embedding: {len(texts)} 个文本")
        
        # 当前实现是顺序调用，可以根据需要改为并行
        vectors = []
        for i, text in enumerate(texts):
            try:
                vector = await self.embed(text)
                vectors.append(vector)
            except Exception as e:
                logger.error(f"第 {i} 个文本 Embedding 失败: {e}")
                # 使用零向量作为 fallback
                vectors.append([0.0] * self.embedding_dim)
        
        return vectors
    
    async def close(self):
        """关闭 HTTP 客户端。"""
        await self.client.aclose()
        logger.info("EmbeddingClient 已关闭")


class EmbeddingError(Exception):
    """Embedding 服务异常。"""
    pass


# 全局客户端实例
embedding_client = EmbeddingClient()

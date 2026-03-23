"""
文档向量化模块。

从 common.clients.embedding_client 导入，保持向后兼容。
"""

from common.clients.embedding_client import EmbeddingClient, EmbeddingCache, embedding_client

__all__ = ["EmbeddingClient", "EmbeddingCache", "embedding_client"]

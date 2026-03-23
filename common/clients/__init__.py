"""
客户端模块。

提供各种外部服务的客户端封装。
"""

from common.clients.minio_client import MinioClient
from common.clients.opensearch_client import OpenSearchClient, OpenSearchStore
from common.clients.embedding_client import EmbeddingClient, EmbeddingCache

__all__ = [
    "MinioClient",
    "OpenSearchClient",
    "OpenSearchStore", 
    "EmbeddingClient",
    "EmbeddingCache",
]

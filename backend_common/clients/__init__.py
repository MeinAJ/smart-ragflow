"""
基础设施客户端模块。

提供各种基础设施的客户端封装：
- embedding_client: BGE-M3 向量化服务
- minio_client: MinIO 对象存储
- opensearch_client: OpenSearch 搜索引擎
- redis_client: Redis 缓存
"""

from backend_common.clients.embedding_client import (
    embedding_client,
    EmbeddingClient,
    EmbeddingCache,
    normalize_vector,
)
from backend_common.clients.minio_client import (
    minio_client,
    MinioClient,
)
from backend_common.clients.opensearch_client import (
    opensearch_store,
    OpenSearchClient,
    OpenSearchStore,
)
from backend_common.clients.redis_client import (
    redis_client,
    RedisClient,
)

__all__ = [
    "embedding_client",
    "EmbeddingClient",
    "EmbeddingCache",
    "normalize_vector",
    "minio_client",
    "MinioClient",
    "opensearch_store",
    "OpenSearchClient",
    "OpenSearchStore",
    "redis_client",
    "RedisClient",
]

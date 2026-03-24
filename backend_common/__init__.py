"""
Backend Common - 基础设施共享模块。

提供所有后端服务共享的基础设施：
- OpenSearch 客户端
- MinIO 客户端
- Redis 客户端
- Embedding 客户端 (BGE-M3)
- LLM 配置 (OpenAI/DeepSeek API)
- 数据库连接
- 数据模型
- 全局配置 (settings)

使用示例：
    from backend_common import settings, DatabaseClient, opensearch_store
    
    # 访问配置
    settings.OPENAI_API_KEY
    settings.DATABASE_URL
    
    # 使用客户端
    async with opensearch_store as store:
        results = await store.search(...)
"""

# 配置
from backend_common.config import settings, CommonSettings

# 数据库
from backend_common.database import (
    engine,
    SessionLocal,
    get_db,
    get_db_session,
    DatabaseClient,
)

# 数据模型
from backend_common.models import (
    Base,
    Document,
    ParseTask,
)

# 客户端
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
    # 配置
    "settings",
    "CommonSettings",
    
    # 数据库
    "engine",
    "SessionLocal",
    "get_db",
    "get_db_session",
    "DatabaseClient",
    
    # 模型
    "Base",
    "Document",
    "ParseTask",
    
    # 客户端
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

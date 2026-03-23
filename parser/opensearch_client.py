"""
OpenSearch 客户端模块。

提供文档分块的索引和存储功能。
"""

import logging
from typing import List, Dict, Any, Optional

from opensearchpy._async.client import AsyncOpenSearch

from parser.config import settings
from parser.models import DocumentChunk

logger = logging.getLogger(__name__)


class OpenSearchStore:
    """
    OpenSearch 文档存储。

    提供文档分块的索引管理功能。
    """

    def __init__(
            self,
            hosts: str = None,
            index: str = None,
            username: str = None,
            password: str = None
    ):
        """
        初始化 OpenSearch 存储。

        Args:
            hosts: OpenSearch 地址
            index: 索引名称
            username: 用户名
            password: 密码
        """
        self.hosts = hosts or f"{settings.OPENSEARCH_HOST}:{settings.OPENSEARCH_PORT}"
        self.index = index or settings.OPENSEARCH_INDEX
        self.username = username or settings.OPENSEARCH_USER
        self.password = password or settings.OPENSEARCH_PASSWORD
        self._client: Optional[AsyncOpenSearch] = None

    async def _get_client(self) -> AsyncOpenSearch:
        """获取或创建 OpenSearch 客户端。"""
        if self._client is None:
            http_auth = None
            if self.username and self.password:
                http_auth = (self.username, self.password)

            self._client = AsyncOpenSearch(
                hosts=[self.hosts],
                http_auth=http_auth,
                use_ssl=False,
                verify_certs=False,
            )
        return self._client

    async def create_index(self) -> bool:
        """
        创建索引（如果不存在）。

        Returns:
            bool: 是否创建成功
        """
        client = await self._get_client()

        try:
            exists = await client.indices.exists(index=self.index)
            if exists:
                logger.info(f"Index '{self.index}' already exists")
                return True

            # 定义映射
            mapping = {
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "keyword"},
                        "doc_id": {"type": "keyword"},
                        "title": {
                            "type": "text",
                            "analyzer": "standard",
                            "fields": {
                                "keyword": {"type": "keyword"}
                            }
                        },
                        "content": {
                            "type": "text",
                            "analyzer": "standard"
                        },
                        "chunk_index": {"type": "integer"},
                        "token_count": {"type": "integer"},
                        "page_number": {"type": "integer"},
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": settings.EMBEDDING_DIM,
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosinesimil",
                                "engine": "faiss"
                            }
                        },
                        "metadata": {"type": "object"},
                        "created_at": {"type": "date"}
                    }
                },
                "settings": {
                    "index": {
                        "knn": True,
                        "knn.algo_param.ef_search": 100
                    }
                }
            }

            await client.indices.create(index=self.index, body=mapping)
            logger.info(f"Created index '{self.index}'")
            return True

        except Exception as e:
            logger.error(f"Failed to create index: {e}")
            return False

    async def index_chunks(self, chunks: List[DocumentChunk]) -> int:
        """
        索引文档分块（覆盖式更新）。

        如果该文档已存在，会先删除旧的分块，再插入新的分块。
        实现重复解析时的自动覆盖。

        Args:
            chunks: 文档分块列表

        Returns:
            int: 成功索引的数量
        """
        if not chunks:
            return 0

        # 获取文档 ID（所有 chunks 应该属于同一文档）
        doc_id = chunks[0].doc_id if chunks else None
        if not doc_id:
            logger.error("Cannot index chunks without doc_id")
            return 0

        client = await self._get_client()

        # 确保索引存在
        await self.create_index()

        # Step 1: 删除该文档的旧分块（覆盖式更新）
        try:
            delete_query = {
                "query": {
                    "term": {"doc_id": doc_id}
                }
            }
            delete_response = await client.delete_by_query(
                index=self.index,
                body=delete_query,
                refresh=True  # 立即刷新，确保删除对后续操作可见
            )
            deleted_count = delete_response.get("deleted", 0)
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old chunks for doc_id={doc_id}")
        except Exception as e:
            logger.warning(f"Failed to delete old chunks for doc_id={doc_id}: {e}")
            # 继续执行，可能文档不存在

        # Step 2: 批量插入新分块
        from datetime import datetime
        operations = []

        for chunk in chunks:
            doc = chunk.to_opensearch_doc()
            doc["created_at"] = datetime.now().isoformat()
            doc["updated_at"] = datetime.now().isoformat()

            operations.append({"index": {"_index": self.index, "_id": chunk.id}})
            operations.append(doc)

        try:
            response = await client.bulk(body=operations, refresh=True)

            success_count = 0
            if response.get("errors"):
                for item in response.get("items", []):
                    if "index" in item and item["index"].get("result") in ["created", "updated"]:
                        success_count += 1
                    elif "error" in item:
                        logger.error(f"Indexing error: {item['error']}")
            else:
                success_count = len(chunks)

            logger.info(f"Indexed {success_count}/{len(chunks)} chunks for doc_id={doc_id}")
            return success_count

        except Exception as e:
            logger.error(f"Bulk indexing failed: {e}")
            return 0

    async def delete_by_doc_id(self, doc_id: str, refresh: bool = True) -> bool:
        """
        删除指定文档的所有分块。

        Args:
            doc_id: 文档 ID
            refresh: 是否立即刷新索引

        Returns:
            bool: 是否删除成功
        """
        client = await self._get_client()

        try:
            query = {
                "query": {
                    "term": {"doc_id": doc_id}
                }
            }

            response = await client.delete_by_query(
                index=self.index,
                body=query,
                refresh=refresh
            )
            deleted = response.get("deleted", 0)
            if deleted > 0:
                logger.info(f"Deleted {deleted} chunks for doc_id={doc_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to delete chunks: {e}")
            return False

    async def close(self):
        """关闭客户端连接。"""
        if self._client:
            await self._client.close()
            self._client = None

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出。"""
        await self.close()


# 全局存储实例
opensearch_store = OpenSearchStore()

"""
OpenSearch 客户端模块。

提供文档分块的索引和存储功能。
"""

import logging
from typing import List, Dict, Any, Optional, Union

from opensearchpy._async.client import AsyncOpenSearch

from backend_common.config import settings

logger = logging.getLogger(__name__)


class OpenSearchClient:
    """
    OpenSearch 客户端。

    提供基础的数据库操作。
    """

    def __init__(
            self,
            hosts: str = None,
            index: str = None,
            username: str = None,
            password: str = None
    ):
        """
        初始化 OpenSearch 客户端。

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


class OpenSearchStore(OpenSearchClient):
    """
    OpenSearch 文档存储。

    提供文档分块的索引管理功能。
    """

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
                logger.debug(f"Index '{self.index}' already exists")
                return True

            # 定义映射
            mapping = {
                "mappings": {
                    "properties": {
                        "chunk_id": {"type": "keyword"},
                        "doc_id": {"type": "keyword"},
                        "doc_url": {"type": "keyword"},
                        "file_name": {"type": "keyword"},
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

    async def index_chunks(self, chunks: List[Any]) -> int:
        """
        索引文档分块（覆盖式更新）。

        如果该文档已存在，会先删除旧的分块，再插入新的分块。
        实现重复解析时的自动覆盖。

        Args:
            chunks: 文档分块列表（支持 dataclass 和 dict）

        Returns:
            int: 成功索引的数量
        """
        if not chunks:
            return 0

        # 获取文档 ID（所有 chunks 应该属于同一文档）
        first_chunk = chunks[0]
        if hasattr(first_chunk, 'doc_id'):
            doc_id = first_chunk.doc_id
        elif isinstance(first_chunk, dict):
            doc_id = first_chunk.get("doc_id")
        else:
            doc_id = None

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
                refresh=True
            )
            deleted_count = delete_response.get("deleted", 0)
            if deleted_count > 0:
                logger.info(f"Deleted {deleted_count} old chunks for doc_id={doc_id}")
        except Exception as e:
            logger.warning(f"Failed to delete old chunks for doc_id={doc_id}: {e}")

        # Step 2: 批量插入新分块
        from datetime import datetime
        operations = []

        for chunk in chunks:
            # 转换为字典
            if hasattr(chunk, 'to_opensearch_doc'):
                chunk_dict = chunk.to_opensearch_doc()
            elif hasattr(chunk, '__dataclass_fields__'):
                # dataclass 转 dict
                chunk_dict = {
                    'chunk_id': getattr(chunk, 'id', getattr(chunk, 'chunk_id', '')),
                    'doc_id': getattr(chunk, 'doc_id', ''),
                    'doc_url': getattr(chunk, 'doc_url', ''),
                    'file_name': getattr(chunk, 'file_name', ''),
                    'title': getattr(chunk, 'title', ''),
                    'content': getattr(chunk, 'content', ''),
                    'chunk_index': getattr(chunk, 'chunk_index', 0),
                    'token_count': getattr(chunk, 'token_count', 0),
                    'page_number': getattr(chunk, 'page_number', 0),
                    'embedding': getattr(chunk, 'embedding', []),
                    'metadata': getattr(chunk, 'metadata', {}),
                }
            elif isinstance(chunk, dict):
                chunk_dict = chunk.copy()
            else:
                logger.warning(f"Unknown chunk type: {type(chunk)}")
                continue

            chunk_dict["created_at"] = datetime.now().isoformat()
            chunk_dict["updated_at"] = datetime.now().isoformat()

            chunk_id = chunk_dict.get("chunk_id", "")
            operations.append({"index": {"_index": self.index, "_id": chunk_id}})
            operations.append(chunk_dict)

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

    async def search_by_doc_id(self, doc_id: str) -> List[Dict]:
        """
        查询指定文档的分块。

        Args:
            doc_id: 文档 ID

        Returns:
            List[Dict]: 文档列表
        """
        client = await self._get_client()

        try:
            query = {
                "query": {"term": {"doc_id": doc_id}},
                "size": 1000
            }
            response = await client.search(index=self.index, body=query)
            return [hit["_source"] for hit in response.get("hits", {}).get("hits", [])]
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []


# 全局存储实例
opensearch_store = OpenSearchStore()

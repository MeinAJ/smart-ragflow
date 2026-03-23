"""
OpenSearch 服务客户端模块。

封装 OpenSearch 混合检索功能（BM25 + 向量相似度）。
"""

import logging
from typing import List, Dict, Any
from opensearchpy._async.client import AsyncOpenSearch
from pydantic_settings import BaseSettings
from pydantic import Field

logger = logging.getLogger(__name__)


class OpenSearchSettings(BaseSettings):
    """OpenSearch 服务配置。"""
    OPENSEARCH_HOST: str = Field(default="localhost", validation_alias="OPENSEARCH_HOST")
    OPENSEARCH_PORT: int = Field(default=9200, validation_alias="OPENSEARCH_PORT")
    OPENSEARCH_INDEX: str = Field(default="rag_docs", validation_alias="OPENSEARCH_INDEX")
    OPENSEARCH_USER: str = Field(default="", validation_alias="OPENSEARCH_USER")
    OPENSEARCH_PASSWORD: str = Field(default="", validation_alias="OPENSEARCH_PASSWORD")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def host(self) -> str:
        return f"{self.OPENSEARCH_HOST}:{self.OPENSEARCH_PORT}"


settings = OpenSearchSettings()


class OpenSearchClient:
    """
    OpenSearch 客户端。

    提供混合检索（BM25 + KNN）功能。
    """

    def __init__(self, hosts: str = None, index: str = None):
        """
        初始化 OpenSearch 客户端。

        Args:
            hosts: OpenSearch 地址
            index: 索引名称
        """
        self.hosts = hosts or settings.host
        self.index = index or settings.OPENSEARCH_INDEX
        self._client: AsyncOpenSearch = None

    async def _get_client(self) -> AsyncOpenSearch:
        """获取或创建 OpenSearch 客户端。"""
        if self._client is None:
            auth = None
            if settings.OPENSEARCH_USER and settings.OPENSEARCH_PASSWORD:
                auth = (settings.OPENSEARCH_USER, settings.OPENSEARCH_PASSWORD)

            self._client = AsyncOpenSearch(
                hosts=[self.hosts],
                http_auth=auth,
                use_ssl=False,
                verify_certs=False,
            )
        return self._client

    async def hybrid_search(
            self,
            query_text: str,
            query_vector: List[float],
            size: int = 10,
            vector_field: str = "embedding",
            title_field: str = "title",
            text_field: str = "content"
    ) -> List[Dict[str, Any]]:
        """
        执行混合检索（BM25 + 向量相似度）。

        Args:
            query_text: 查询文本（用于 BM25）
            query_vector: 查询向量（用于 KNN）
            size: 返回结果数量
            vector_field: 向量字段名
            text_field: 文本字段名

        Returns:
            List[Dict]: 文档列表，包含文本、元数据、分数
        """
        client = await self._get_client()

        # 构建混合查询：bool 组合 match 和 knn
        search_body = {
            "size": size,
            "query": {
                "bool": {
                    "should": [
                        # BM25 文本匹配
                        {
                            "match": {
                                text_field: {
                                    "query": query_text,
                                    "boost": 1.0
                                }
                            }
                        },
                        # BM25 文本匹配
                        {
                            "match": {
                                title_field: {
                                    "query": query_text,
                                    "boost": 1.0
                                }
                            }
                        },
                        # KNN 向量搜索
                        {
                            "knn": {
                                vector_field: {
                                    "vector": query_vector,
                                    "boost": 1.0,
                                    "k": size
                                }
                            }
                        }
                    ]
                }
            }
        }

        try:
            logger.info(f"Hybrid search: query='{query_text[:50]}...', size={size}")
            response = await client.search(
                index=self.index,
                body=search_body
            )

            hits = response.get("hits", {}).get("hits", [])
            docs = []

            for hit in hits:
                doc = {
                    "id": hit.get("_id"),
                    "content": hit.get("_source", {}).get(text_field, ""),
                    "metadata": {k: v for k, v in hit.get("_source", {}).items() if
                                 k != text_field and k != vector_field},
                    "score": hit.get("_score", 0.0),
                }
                docs.append(doc)

            logger.info(f"Retrieved {len(docs)} documents")
            return docs

        except Exception as e:
            logger.error(f"OpenSearch search error: {str(e)}")
            raise Exception(f"Search failed: {str(e)}")

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


# 全局客户端实例
opensearch_client = OpenSearchClient()

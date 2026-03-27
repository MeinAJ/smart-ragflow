"""
OpenSearch 服务客户端模块。

封装 OpenSearch 混合检索功能（BM25 + 向量相似度）。
"""

import logging
from typing import List, Dict, Any
from opensearchpy._async.client import AsyncOpenSearch

from backend_common.config import settings

logger = logging.getLogger(__name__)


# 为了兼容原有代码，添加 host 属性
class _SettingsWrapper:
    @property
    def host(self) -> str:
        return f"{settings.OPENSEARCH_HOST}:{settings.OPENSEARCH_PORT}"


_settings_wrapper = _SettingsWrapper()


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
        self.hosts = hosts or _settings_wrapper.host
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
            min_score: float = None,
            vector_field: str = "embedding",
            title_field: str = "title",
            text_field: str = "content"
    ) -> List[Dict[str, Any]]:
        """
        执行混合检索（BM25 + 向量相似度），返回归一化分数的结果。

        Args:
            query_text: 查询文本（用于 BM25）
            query_vector: 查询向量（用于 KNN）
            size: 返回结果数量
            min_score: 最小分数阈值（0-1范围，为None则使用配置值）
            vector_field: 向量字段名
            title_field: 标题字段名
            text_field: 文本字段名

        Returns:
            List[Dict]: 文档列表，包含文本、元数据、归一化分数(0-1)
        """
        # 使用配置中的 min_score 如果未指定
        if min_score is None:
            min_score = settings.SEARCH_MIN_SCORE

        client = await self._get_client()

        # 构建混合查询：bool 组合 match 和 knn
        # 使用 function_score 和 boost_mode 来控制分数计算
        search_body = {
            "size": size,
            "query": {
                "bool": {
                    "should": [
                        # BM25 文本匹配（带权重）
                        {
                            "match": {
                                text_field: {
                                    "query": query_text,
                                    "boost": settings.SEARCH_TEXT_BOOST
                                }
                            }
                        },
                        # 标题匹配（更高权重）
                        {
                            "match": {
                                title_field: {
                                    "query": query_text,
                                    "boost": settings.SEARCH_TITLE_BOOST
                                }
                            }
                        },
                        # KNN 向量搜索
                        {
                            "knn": {
                                vector_field: {
                                    "vector": query_vector,
                                    "k": size
                                }
                            }
                        }
                    ]
                }
            }
        }

        try:
            logger.info(f"Hybrid search: query='{query_text[:50]}...', size={size}, min_score={min_score}")
            response = await client.search(
                index=self.index,
                body=search_body
            )

            hits = response.get("hits", {}).get("hits", [])
            if not hits:
                return []

            # 获取最高分数用于归一化
            max_score = max(hit.get("_score", 0.0) for hit in hits)
            if max_score <= 0:
                max_score = 1.0

            docs = []
            for hit in hits:
                raw_score = hit.get("_score", 0.0)
                # 归一化分数到 0-1 范围
                normalized_score = raw_score / max_score if max_score > 0 else 0.0

                # 过滤低于 min_score 的结果
                if normalized_score < min_score:
                    continue

                source = hit.get("_source", {})
                metadata = {k: v for k, v in source.items() if k != text_field}
                
                doc = {
                    "id": hit.get("_id"),
                    "content": source.get(text_field, ""),
                    "title": source.get(title_field, ""),
                    "file_name": source.get("file_name", ""),
                    "doc_url": source.get("doc_url", ""),
                    "metadata": metadata,
                    "score": round(normalized_score, 4),  # 归一化分数 0-1
                    "raw_score": round(raw_score, 4),  # 原始分数（用于调试）
                }
                docs.append(doc)

            logger.info(f"Retrieved {len(docs)} documents (after filtering by min_score={min_score})")
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

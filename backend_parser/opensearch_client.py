"""
OpenSearch 客户端模块。

从 common.clients.opensearch_client 导入，保持向后兼容。
"""

from backend_common.clients.opensearch_client import OpenSearchClient, OpenSearchStore, opensearch_store

__all__ = ["OpenSearchClient", "OpenSearchStore", "opensearch_store"]

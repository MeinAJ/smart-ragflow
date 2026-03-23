"""
MinIO 文件处理模块。

从 common.clients.minio_client 导入，保持向后兼容。
"""

from common.clients.minio_client import MinioClient, minio_client, upload_file, get_file_url

__all__ = ["MinioClient", "minio_client", "upload_file", "get_file_url"]

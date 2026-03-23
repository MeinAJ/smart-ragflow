"""
MinIO 文件处理模块。

提供文件的上传、下载、删除等 CRUD 操作。
"""

import io
import json
import logging
from pathlib import Path
from typing import Optional, BinaryIO
from urllib.parse import urljoin

from minio import Minio
from minio.error import S3Error

from parser.config import settings

logger = logging.getLogger(__name__)


class MinioClient:
    """
    MinIO 客户端封装。

    提供文件 CRUD 操作和 bucket 管理。
    """

    def __init__(
        self,
        endpoint: str = None,
        access_key: str = None,
        secret_key: str = None,
        bucket_name: str = None,
        secure: bool = None
    ):
        """
        初始化 MinIO 客户端。

        Args:
            endpoint: MinIO 服务端点
            access_key: 访问密钥
            secret_key: 密钥
            bucket_name: Bucket 名称
            secure: 是否使用 HTTPS
        """
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.bucket_name = bucket_name or settings.MINIO_BUCKET_NAME
        self.secure = secure if secure is not None else settings.MINIO_SECURE

        self._client: Optional[Minio] = None
        self._initialized = False

    def _get_client(self) -> Minio:
        """获取或创建 MinIO 客户端。"""
        if self._client is None:
            self._client = Minio(
                self.endpoint,
                access_key=self.access_key,
                secret_key=self.secret_key,
                secure=self.secure
            )
        return self._client

    async def initialize(self):
        """
        初始化 MinIO 客户端。

        检查并创建 bucket（如果不存在），设置为 public 访问。
        """
        if self._initialized:
            return

        logger.info(f"Initializing MinIO client, bucket: {self.bucket_name}")

        try:
            client = self._get_client()

            # 检查 bucket 是否存在
            bucket_exists = client.bucket_exists(self.bucket_name)

            if not bucket_exists:
                # 创建 bucket
                logger.info(f"Creating bucket: {self.bucket_name}")
                client.make_bucket(self.bucket_name)

                # 设置 bucket 为 public 访问
                logger.info(f"Setting bucket {self.bucket_name} to public")
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": ["*"]},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket_name}/*"]
                        }
                    ]
                }
                client.set_bucket_policy(self.bucket_name, json.dumps(policy))
                logger.info(f"Bucket {self.bucket_name} is now public")
            else:
                logger.info(f"Bucket {self.bucket_name} already exists")

            self._initialized = True
            logger.info("MinIO client initialized successfully")

        except S3Error as e:
            logger.error(f"MinIO S3 error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize MinIO: {e}")
            raise

    async def upload_file(
        self,
        file_path: str,
        object_name: str = None,
        content_type: str = None
    ) -> str:
        """
        上传文件到 MinIO。

        Args:
            file_path: 本地文件路径
            object_name: 对象名称（如果为 None，使用文件名）
            content_type: 内容类型

        Returns:
            str: 文件的公开访问 URL
        """
        if not self._initialized:
            await self.initialize()

        client = self._get_client()
        path = Path(file_path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # 确定对象名称
        if object_name is None:
            object_name = path.name

        # 确定内容类型
        if content_type is None:
            content_type = self._guess_content_type(path.suffix)

        try:
            logger.info(f"Uploading {file_path} to {self.bucket_name}/{object_name}")

            # 上传文件
            client.fput_object(
                self.bucket_name,
                object_name,
                str(path),
                content_type=content_type
            )

            # 生成公开 URL
            url = self._get_public_url(object_name)
            logger.info(f"File uploaded successfully: {url}")
            return url

        except S3Error as e:
            logger.error(f"Failed to upload file: {e}")
            raise

    async def upload_bytes(
        self,
        data: bytes,
        object_name: str,
        content_type: str = "application/octet-stream"
    ) -> str:
        """
        上传字节数据到 MinIO。

        Args:
            data: 字节数据
            object_name: 对象名称
            content_type: 内容类型

        Returns:
            str: 文件的公开访问 URL
        """
        if not self._initialized:
            await self.initialize()

        client = self._get_client()

        try:
            logger.info(f"Uploading bytes to {self.bucket_name}/{object_name}")

            # 上传数据
            client.put_object(
                self.bucket_name,
                object_name,
                io.BytesIO(data),
                length=len(data),
                content_type=content_type
            )

            # 生成公开 URL
            url = self._get_public_url(object_name)
            logger.info(f"Data uploaded successfully: {url}")
            return url

        except S3Error as e:
            logger.error(f"Failed to upload data: {e}")
            raise

    async def download_file(
        self,
        object_name: str,
        file_path: str = None
    ) -> str:
        """
        从 MinIO 下载文件。

        Args:
            object_name: 对象名称
            file_path: 本地保存路径（如果为 None，保存到临时目录）

        Returns:
            str: 本地文件路径
        """
        if not self._initialized:
            await self.initialize()

        client = self._get_client()

        # 确定保存路径
        if file_path is None:
            import tempfile
            file_path = Path(tempfile.gettempdir()) / object_name

        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            logger.info(f"Downloading {self.bucket_name}/{object_name} to {file_path}")
            client.fget_object(self.bucket_name, object_name, str(file_path))
            logger.info(f"File downloaded successfully: {file_path}")
            return str(file_path)

        except S3Error as e:
            logger.error(f"Failed to download file: {e}")
            raise

    async def get_file_url(self, object_name: str) -> str:
        """
        获取文件的公开访问 URL。

        Args:
            object_name: 对象名称

        Returns:
            str: 公开访问 URL
        """
        return self._get_public_url(object_name)

    async def delete_file(self, object_name: str) -> bool:
        """
        删除 MinIO 中的文件。

        Args:
            object_name: 对象名称

        Returns:
            bool: 是否删除成功
        """
        if not self._initialized:
            await self.initialize()

        client = self._get_client()

        try:
            logger.info(f"Deleting {self.bucket_name}/{object_name}")
            client.remove_object(self.bucket_name, object_name)
            logger.info(f"File deleted successfully: {object_name}")
            return True

        except S3Error as e:
            logger.error(f"Failed to delete file: {e}")
            return False

    async def file_exists(self, object_name: str) -> bool:
        """
        检查文件是否存在于 MinIO。

        Args:
            object_name: 对象名称

        Returns:
            bool: 是否存在
        """
        if not self._initialized:
            await self.initialize()

        client = self._get_client()

        try:
            client.stat_object(self.bucket_name, object_name)
            return True
        except S3Error:
            return False

    async def list_files(self, prefix: str = "") -> list:
        """
        列出 MinIO 中的文件。

        Args:
            prefix: 前缀过滤

        Returns:
            list: 文件列表
        """
        if not self._initialized:
            await self.initialize()

        client = self._get_client()

        try:
            objects = client.list_objects(self.bucket_name, prefix=prefix, recursive=True)
            return [
                {
                    "name": obj.object_name,
                    "size": obj.size,
                    "last_modified": obj.last_modified,
                    "url": self._get_public_url(obj.object_name)
                }
                for obj in objects
            ]
        except S3Error as e:
            logger.error(f"Failed to list files: {e}")
            return []

    def _get_public_url(self, object_name: str) -> str:
        """
        生成文件的公开访问 URL。

        Args:
            object_name: 对象名称

        Returns:
            str: 公开 URL
        """
        protocol = "https" if self.secure else "http"
        # 构建 URL: http://endpoint/bucket-name/object-name
        return f"{protocol}://{self.endpoint}/{self.bucket_name}/{object_name}"

    def _guess_content_type(self, suffix: str) -> str:
        """
        根据文件后缀猜测内容类型。

        Args:
            suffix: 文件后缀（如 .pdf）

        Returns:
            str: 内容类型
        """
        mime_types = {
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".txt": "text/plain",
            ".md": "text/markdown",
            ".html": "text/html",
            ".htm": "text/html",
            ".json": "application/json",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
        }
        return mime_types.get(suffix.lower(), "application/octet-stream")

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出。"""
        pass  # MinIO 客户端无需显式关闭


# 全局 MinIO 客户端实例
minio_client = MinioClient()


# 便捷函数
async def upload_file(file_path: str, object_name: str = None) -> str:
    """
    上传文件的便捷函数。

    Args:
        file_path: 本地文件路径
        object_name: 对象名称

    Returns:
        str: 文件的公开访问 URL
    """
    async with MinioClient() as client:
        return await client.upload_file(file_path, object_name)


async def get_file_url(object_name: str) -> str:
    """
    获取文件 URL 的便捷函数。

    Args:
        object_name: 对象名称

    Returns:
        str: 公开访问 URL
    """
    return minio_client._get_public_url(object_name)

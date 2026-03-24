"""
文件下载模块。

支持从 MinIO 等对象存储下载文件到临时目录。
"""

import logging
import tempfile
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx

from backend_parser.config import settings

logger = logging.getLogger(__name__)


class FileDownloader:
    """
    文件下载器。

    支持从 HTTP/HTTPS URL 下载文件到临时目录。
    """

    def __init__(self, timeout: float = None):
        """
        初始化下载器。

        Args:
            timeout: 下载超时时间（秒）
        """
        self.timeout = timeout or 300.0  # 默认 5 分钟
        self._client: Optional[httpx.AsyncClient] = None
        self._temp_dir: Optional[Path] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端。"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=self.timeout,
                follow_redirects=True
            )
        return self._client

    def _get_temp_dir(self) -> Path:
        """获取临时目录。"""
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.gettempdir()) / "parser_downloads"
            self._temp_dir.mkdir(parents=True, exist_ok=True)
        return self._temp_dir

    def _extract_filename_from_url(self, url: str) -> str:
        """
        从 URL 中提取文件名。

        Args:
            url: 文件 URL

        Returns:
            str: 文件名（限制长度，避免文件系统错误）
        """
        parsed = urlparse(url)
        path = parsed.path
        filename = Path(path).name

        # 如果无法提取文件名，使用默认名称
        if not filename:
            filename = "downloaded_file"

        # 限制文件名长度（避免文件系统错误）
        # macOS/Windows 限制约 255 字符，这里限制 100 字符
        max_len = 100
        if len(filename) > max_len:
            # 保留扩展名
            suffix = Path(filename).suffix
            stem = Path(filename).stem
            # 截取前 (max_len - len(suffix) - 1) 个字符
            stem_max = max_len - len(suffix) - 1
            filename = f"{stem[:stem_max]}{suffix}" if suffix else stem[:max_len]

        return filename

    async def download(self, file_url: str, custom_filename: str = None) -> Path:
        """
        从 URL 下载文件。

        Args:
            file_url: 文件 URL（支持 MinIO 公开 URL）
            custom_filename: 自定义文件名（可选）

        Returns:
            Path: 下载后的本地文件路径

        Raises:
            Exception: 下载失败时抛出
        """
        if not file_url.startswith(("http://", "https://")):
            raise ValueError(f"Invalid URL: {file_url}. Only HTTP/HTTPS URLs are supported.")

        # 确定文件名
        filename = custom_filename or self._extract_filename_from_url(file_url)

        # 确保临时目录存在
        temp_dir = self._get_temp_dir()
        local_path = temp_dir / filename

        # 如果文件已存在，添加序号
        counter = 1
        original_path = local_path
        while local_path.exists():
            stem = original_path.stem
            suffix = original_path.suffix
            new_name = f"{stem}_{counter}{suffix}"
            # 确保加上序号后也不会太长
            if len(new_name) > 100:
                new_name = f"{stem[:90]}_{counter}{suffix}"
            local_path = temp_dir / new_name
            counter += 1

        logger.info(f"Downloading file from {file_url} to {local_path}")

        client = await self._get_client()

        try:
            async with client.stream("GET", file_url) as response:
                response.raise_for_status()

                total_size = 0
                with open(local_path, "wb") as f:
                    async for chunk in response.aiter_bytes(chunk_size=8192):
                        f.write(chunk)
                        total_size += len(chunk)

            logger.info(f"Downloaded {filename} ({total_size} bytes)")
            return local_path

        except httpx.HTTPStatusError as e:
            logger.error(f"Download HTTP error: {e.response.status_code}")
            raise Exception(f"Failed to download file: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"Download failed: {e}")
            raise Exception(f"Failed to download file: {e}")

    async def cleanup(self, file_path: Path = None):
        """
        清理下载的文件。

        Args:
            file_path: 要删除的特定文件路径（为 None 则清理整个临时目录）
        """
        try:
            if file_path and file_path.exists():
                file_path.unlink()
                logger.debug(f"Cleaned up file: {file_path}")
            elif self._temp_dir and self._temp_dir.exists():
                import shutil
                shutil.rmtree(self._temp_dir)
                logger.debug(f"Cleaned up temp directory: {self._temp_dir}")
        except Exception as e:
            logger.warning(f"Failed to cleanup: {e}")

    async def close(self):
        """关闭 HTTP 客户端。"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出。"""
        await self.close()


# 便捷函数
async def download_file(file_url: str, custom_filename: str = None) -> Path:
    """
    下载文件的便捷函数。

    Args:
        file_url: 文件 URL
        custom_filename: 自定义文件名

    Returns:
        Path: 本地文件路径
    """
    async with FileDownloader() as downloader:
        return await downloader.download(file_url, custom_filename)

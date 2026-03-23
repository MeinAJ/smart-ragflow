"""
文档解析服务主入口。

整合解析、分块、向量化和存储的完整流程。
"""

import logging
import asyncio
from pathlib import Path
from typing import List, Optional

from parser.config import settings
from parser.models import Document, DocumentChunk, ParseResult
from parser.deepdoc_parser import deepdoc_parser, DeepDocParser
from parser.chunker import chunk_document
from parser.embedding import embedding_client, EmbeddingClient
from parser.opensearch_client import opensearch_store, OpenSearchStore
from parser.file_downloader import FileDownloader
from parser.minio_client import MinioClient, minio_client

logger = logging.getLogger(__name__)


class DocumentParseService:
    """
    文档解析服务。

    提供完整的文档处理流程：解析 -> 分块 -> 向量化 -> 存储。
    """

    def __init__(
        self,
        parser: DeepDocParser = None,
        embedding_client: EmbeddingClient = None,
        opensearch_store: OpenSearchStore = None,
        minio_client: MinioClient = None
    ):
        """
        初始化解析服务。

        Args:
            parser: 文档解析器
            embedding_client: Embedding 客户端
            opensearch_store: OpenSearch 存储
            minio_client: MinIO 客户端
        """
        self.parser = parser or DeepDocParser()
        self.embedding = embedding_client or EmbeddingClient()
        self.store = opensearch_store or OpenSearchStore()
        self.minio = minio_client or MinioClient()
        self._initialized = False

    async def initialize(self):
        """
        初始化服务。

        检查并创建 OpenSearch 索引和 MinIO Bucket（如果不存在）。
        建议在服务使用前调用一次。
        """
        if self._initialized:
            return

        logger.info("Initializing DocumentParseService...")

        # 检查并创建 OpenSearch 索引
        try:
            created = await self.store.create_index()
            if created:
                logger.info(f"Index '{self.store.index}' is ready")
        except Exception as e:
            logger.error(f"Failed to initialize OpenSearch index: {e}")
            raise

        # 检查并创建 MinIO Bucket
        try:
            await self.minio.initialize()
        except Exception as e:
            logger.warning(f"Failed to initialize MinIO (may be optional): {e}")

        self._initialized = True
        logger.info("DocumentParseService initialized successfully")

    async def download_from_minio(self, object_name: str, file_path: str = None) -> str:
        """
        从 MinIO 下载文件。

        Args:
            object_name: MinIO 对象名称
            file_path: 本地保存路径（可选）

        Returns:
            str: 本地文件路径
        """
        return await self.minio.download_file(object_name, file_path)

    async def upload_to_minio(self, file_path: str, object_name: str = None) -> str:
        """
        上传文件到 MinIO。

        Args:
            file_path: 本地文件路径
            object_name: 对象名称（可选）

        Returns:
            str: 文件的公开访问 URL
        """
        return await self.minio.upload_file(file_path, object_name)

    async def check_document_exists(self, file_url: str) -> Optional[str]:
        """
        检查文档是否已存在于 OpenSearch 中。

        通过文件 URL 或文件名查询，返回已存在的 doc_id（如果找到）。

        Args:
            file_url: 文件 URL

        Returns:
            Optional[str]: 已存在的 doc_id，如果不存在则返回 None
        """
        try:
            client = await self.store._get_client()

            # 从 URL 中提取文件名
            file_name = Path(file_url).name

            query = {
                "query": {
                    "term": {"metadata.file_name.keyword": file_name}
                },
                "size": 1
            }

            response = await client.search(index=self.store.index, body=query)
            hits = response.get("hits", {}).get("hits", [])

            if hits:
                doc_id = hits[0]["_source"].get("doc_id")
                logger.info(f"Found existing document: {file_name} -> doc_id={doc_id}")
                return doc_id

            return None

        except Exception as e:
            logger.warning(f"Failed to check document existence: {e}")
            return None

    async def process(
        self,
        file_url: str,
        doc_id: str = None,
        skip_embedding: bool = False,
        skip_indexing: bool = False,
        force_update: bool = True
    ) -> ParseResult:
        """
        处理单个文档。

        完整流程：下载 -> 解析 -> 分块 -> 向量化 -> 存储

        Args:
            file_url: 文件 URL（支持 MinIO 公开 URL，如 http://localhost:9000/bucket/file.pdf）
            doc_id: 文档唯一标识（为 None 则自动生成 UUID）
            skip_embedding: 是否跳过向量化
            skip_indexing: 是否跳过多存储
            force_update: 是否强制更新（重复解析时覆盖旧数据）

        Returns:
            ParseResult: 处理结果
        """
        logger.info(f"Processing document from URL: {file_url}, doc_id: {doc_id or 'auto'}")

        # 0. 确保服务已初始化（检查并创建索引）
        if not self._initialized:
            await self.initialize()

        # 1. 检查文档是否已存在（通过 doc_id 或 file_url）
        existing_doc_id = None
        if not skip_indexing and doc_id:
            # 如果指定了 doc_id，直接检查该 doc_id 是否存在
            try:
                client = await self.store._get_client()
                query = {"query": {"term": {"doc_id": doc_id}}, "size": 1}
                response = await client.search(index=self.store.index, body=query)
                if response.get("hits", {}).get("hits"):
                    existing_doc_id = doc_id
                    logger.info(f"Found existing document with doc_id: {doc_id}")
            except Exception as e:
                logger.warning(f"Failed to check doc_id existence: {e}")

        # 1. 下载文件到临时目录
        local_file_path = None
        try:
            async with FileDownloader() as downloader:
                local_file_path = await downloader.download(file_url)
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            return ParseResult(
                success=False,
                error_message=f"Download failed: {str(e)}"
            )

        # 2. 解析文档
        parse_result = self.parser.parse(str(local_file_path))
        if not parse_result.success:
            logger.error(f"Parse failed: {parse_result.error_message}")
            # 清理下载的文件
            if local_file_path and local_file_path.exists():
                local_file_path.unlink()
            return parse_result

        document = parse_result.document
        # 使用指定的 doc_id 或保持自动生成的
        if doc_id:
            document.id = doc_id
        # 更新文件路径为 URL
        document.file_path = file_url

        # 如果检测到已存在且 force_update=True
        if existing_doc_id and force_update:
            logger.info(f"Document exists, will overwrite. Old doc_id: {existing_doc_id}, New doc_id: {document.id}")

        logger.info(f"Document parsed: {document.title}, size: {document.file_size} bytes, doc_id: {document.id}")

        # 4. 分块
        chunks = chunk_document(document)
        if not chunks:
            logger.warning("No chunks created")
            parse_result.chunks = []
            return parse_result

        logger.info(f"Created {len(chunks)} chunks")
        parse_result.chunks = chunks

        # 5. 向量化
        if not skip_embedding:
            try:
                logger.info("Generating embeddings...")
                await self.embedding.embed_chunks(chunks)
                logger.info("Embeddings generated")
            except Exception as e:
                logger.error(f"Embedding failed: {e}")
                # 继续处理，使用零向量

        # 6. 存储到 OpenSearch
        if not skip_indexing:
            try:
                # 6.1 如果存在旧数据，先删除（覆盖式更新）
                if existing_doc_id and force_update:
                    logger.info(f"Deleting old chunks for existing doc: {existing_doc_id}")
                    deleted = await self.store.delete_by_doc_id(existing_doc_id)
                    if deleted:
                        logger.info(f"Deleted old chunks successfully")

                # 6.2 插入新数据
                logger.info("Indexing to OpenSearch...")
                indexed_count = await self.store.index_chunks(chunks)
                logger.info(f"Indexed {indexed_count} chunks")
            except Exception as e:
                logger.error(f"Indexing failed: {e}")
                parse_result.error_message = f"Indexing failed: {e}"
                # 标记为部分成功

        # 7. 清理下载的临时文件
        if local_file_path and local_file_path.exists():
            try:
                local_file_path.unlink()
                logger.debug(f"Cleaned up temporary file: {local_file_path}")
            except Exception as e:
                logger.warning(f"Failed to cleanup temp file: {e}")

        return parse_result

    async def process_batch(
        self,
        file_urls: List[str],
        doc_ids: List[str] = None,
        skip_embedding: bool = False,
        skip_indexing: bool = False
    ) -> List[ParseResult]:
        """
        批量处理文档。

        Args:
            file_urls: 文件 URL 列表
            doc_ids: 自定义文档 ID 列表（可选，与 file_urls 一一对应）
            skip_embedding: 是否跳过向量化
            skip_indexing: 是否跳过存储

        Returns:
            List[ParseResult]: 处理结果列表
        """
        logger.info(f"Processing {len(file_urls)} documents")

        # 确保服务已初始化
        if not self._initialized:
            await self.initialize()

        results = []
        for i, file_url in enumerate(file_urls):
            try:
                doc_id = doc_ids[i] if doc_ids and i < len(doc_ids) else None
                result = await self.process(
                    file_url=file_url,
                    doc_id=doc_id,
                    skip_embedding=skip_embedding,
                    skip_indexing=skip_indexing
                )
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {file_url}: {e}")
                results.append(ParseResult(
                    success=False,
                    error_message=str(e)
                ))

        return results

    async def delete_document(self, doc_id: str) -> bool:
        """
        删除文档及其所有分块。

        Args:
            doc_id: 文档 ID

        Returns:
            bool: 是否删除成功
        """
        try:
            return await self.store.delete_by_doc_id(doc_id)
        except Exception as e:
            logger.error(f"Failed to delete document {doc_id}: {e}")
            return False

    async def close(self):
        """关闭所有客户端连接。"""
        await self.embedding.close()
        await self.store.close()

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出。"""
        await self.close()


# 全局服务实例
parse_service = DocumentParseService()


# 便捷函数
async def parse_document(file_url: str, doc_id: str = None) -> ParseResult:
    """
    解析单个文档的便捷函数。

    Args:
        file_url: 文件 URL（支持 MinIO 公开 URL）
        doc_id: 自定义文档 ID（可选）

    Returns:
        ParseResult: 解析结果
    """
    async with DocumentParseService() as service:
        return await service.process(file_url=file_url, doc_id=doc_id)


async def parse_documents(file_urls: List[str], doc_ids: List[str] = None) -> List[ParseResult]:
    """
    批量解析文档的便捷函数。

    Args:
        file_urls: 文件 URL 列表
        doc_ids: 自定义文档 ID 列表（可选，与 file_urls 一一对应）

    Returns:
        List[ParseResult]: 解析结果列表
    """
    async with DocumentParseService() as service:
        results = []
        for i, file_url in enumerate(file_urls):
            doc_id = doc_ids[i] if doc_ids and i < len(doc_ids) else None
            result = await service.process(file_url=file_url, doc_id=doc_id)
            results.append(result)
        return results

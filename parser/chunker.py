"""
文档分块模块。

实现智能分块逻辑，支持按语义边界分割文档。
"""

import logging
import re
from typing import List, Iterator

from parser.config import settings
from parser.models import Document, DocumentSection, DocumentChunk, DocumentElement
from parser.tokenizer import token_counter

logger = logging.getLogger(__name__)


class TextChunker:
    """
    文本分块器。

    支持按分隔符层级进行智能分块。
    """

    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        separators: List[str] = None
    ):
        """
        初始化分块器。

        Args:
            chunk_size: 目标分块大小（字符数）
            chunk_overlap: 分块间重叠字符数
            separators: 分隔符列表（按优先级排序）
        """
        self.chunk_size = chunk_size or settings.CHUNK_SIZE
        self.chunk_overlap = chunk_overlap or settings.CHUNK_OVERLAP
        self.separators = separators or settings.CHUNK_SEPARATORS

    def _split_text(self, text: str) -> List[str]:
        """
        将文本按分隔符分割。

        Args:
            text: 输入文本

        Returns:
            List[str]: 分割后的文本片段
        """
        # 使用第一个分隔符分割
        if not self.separators:
            return [text]

        separator = self.separators[0]
        if separator == "":
            # 字符级分割
            return list(text)

        # 按分隔符分割，保留分隔符
        parts = re.split(f"({re.escape(separator)})", text)
        # 合并分隔符和前一个片段
        result = []
        i = 0
        while i < len(parts):
            if i + 1 < len(parts) and parts[i + 1] == separator:
                result.append(parts[i] + parts[i + 1])
                i += 2
            else:
                if parts[i]:
                    result.append(parts[i])
                i += 1
        return result

    def _merge_chunks(self, chunks: List[str]) -> List[str]:
        """
        合并小片段到目标大小。

        Args:
            chunks: 文本片段列表

        Returns:
            List[str]: 合并后的分块
        """
        result = []
        current_chunk = ""

        for chunk in chunks:
            if len(current_chunk) + len(chunk) <= self.chunk_size:
                current_chunk += chunk
            else:
                if current_chunk:
                    result.append(current_chunk)
                current_chunk = chunk

        if current_chunk:
            result.append(current_chunk)

        return result

    def split(self, text: str) -> List[str]:
        """
        将文本分割成块。

        Args:
            text: 输入文本

        Returns:
            List[str]: 分块列表
        """
        if not text:
            return []

        if len(text) <= self.chunk_size:
            return [text]

        # 递归使用分隔符
        chunks = self._recursive_split(text, self.separators.copy())
        return chunks

    def _recursive_split(self, text: str, separators: List[str]) -> List[str]:
        """
        递归分割文本。

        Args:
            text: 输入文本
            separators: 剩余分隔符列表

        Returns:
            List[str]: 分块列表
        """
        if len(text) <= self.chunk_size:
            return [text]

        if not separators:
            # 没有分隔符了，强制切割
            return [text[i:i + self.chunk_size] for i in range(0, len(text), self.chunk_size - self.chunk_overlap)]

        separator = separators[0]
        remaining_separators = separators[1:]

        # 尝试当前分隔符分割
        if separator == "":
            parts = list(text)
        else:
            parts = re.split(f"({re.escape(separator)})", text)
            # 合并分隔符
            merged = []
            i = 0
            while i < len(parts):
                if i + 1 < len(parts) and parts[i + 1] == separator:
                    merged.append(parts[i] + parts[i + 1])
                    i += 2
                else:
                    if parts[i]:
                        merged.append(parts[i])
                    i += 1
            parts = merged

        # 合并小片段
        result = []
        current = ""
        for part in parts:
            if len(current) + len(part) <= self.chunk_size:
                current += part
            else:
                if current:
                    # 如果当前片段超过限制，递归处理
                    if len(current) > self.chunk_size:
                        result.extend(self._recursive_split(current, remaining_separators))
                    else:
                        result.append(current)
                current = part

        if current:
            if len(current) > self.chunk_size:
                result.extend(self._recursive_split(current, remaining_separators))
            else:
                result.append(current)

        return result

    def create_chunks_with_overlap(self, text: str) -> List[str]:
        """
        创建带重叠的分块。

        当只有一个分块时，直接返回原内容，不添加重叠。

        Args:
            text: 输入文本

        Returns:
            List[str]: 带重叠的分块列表（单块时无重叠）
        """
        chunks = self.split(text)
        if not chunks:
            return []

        # 单块场景：直接返回，不添加重叠
        if len(chunks) == 1:
            return chunks

        # 多块场景：为后续块添加重叠
        result = [chunks[0]]  # 第一个块无重叠
        for i in range(1, len(chunks)):
            prev_chunk = chunks[i - 1]
            curr_chunk = chunks[i]

            # 计算重叠文本
            overlap = prev_chunk[-self.chunk_overlap:] if len(prev_chunk) > self.chunk_overlap else prev_chunk

            # 如果当前块不以重叠文本开头，则添加
            if not curr_chunk.startswith(overlap):
                result.append(overlap + curr_chunk)
            else:
                result.append(curr_chunk)

        return result


def chunk_document(document: Document, chunker: TextChunker = None, file_url: str = None) -> List[DocumentChunk]:
    """
    对文档进行分块。

    Args:
        document: 解析后的文档
        chunker: 可选的分块器实例（用于自定义配置）
        file_url: 文件 URL（可选，用于保存到 chunk 中）

    Returns:
        List[DocumentChunk]: 分块列表
    """
    logger.info(f"Chunking document: {document.file_name} (doc_id={document.id})")

    chunker = chunker or TextChunker()
    chunks = []
    chunk_index = 0

    # 按章节分块
    for section in document.sections:
        section_text = section.content
        if not section_text.strip():
            continue

        # 分块
        text_chunks = chunker.create_chunks_with_overlap(section_text)

        for text_chunk in text_chunks:
            content = text_chunk.strip()
            chunk = DocumentChunk(
                doc_id=document.id,
                doc_url=file_url or document.file_path,  # 优先使用传入的 file_url
                title=section.title or document.title,
                content=content,
                chunk_index=chunk_index,
                token_count=token_counter.count_tokens(content),  # 使用 tiktoken 计算
                page_number=section.start_page,
                metadata={
                    "section_level": section.level,
                    "file_name": document.file_name,
                    "file_type": document.file_type,
                }
            )
            chunks.append(chunk)
            chunk_index += 1

    # 如果没有章节，直接对全文分块
    if not chunks and document.content:
        text_chunks = chunker.create_chunks_with_overlap(document.content)
        for text_chunk in text_chunks:
            content = text_chunk.strip()
            chunk = DocumentChunk(
                doc_id=document.id,
                doc_url=file_url or document.file_path,  # 优先使用传入的 file_url
                title=document.title,
                content=content,
                chunk_index=chunk_index,
                token_count=token_counter.count_tokens(content),  # 使用 tiktoken 计算
                page_number=0,
                metadata={
                    "file_name": document.file_name,
                    "file_type": document.file_type,
                }
            )
            chunks.append(chunk)
            chunk_index += 1

    logger.info(f"Created {len(chunks)} chunks with token counts: "
                f"{[c.token_count for c in chunks[:5]]}{'...' if len(chunks) > 5 else ''}")
    return chunks

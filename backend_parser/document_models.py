"""
数据模型定义模块。

定义文档解析过程中的数据模型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
import uuid


@dataclass
class DocumentElement:
    """
    文档元素（段落、表格、图片等）。

    Attributes:
        element_type: 元素类型（paragraph, table, image, title 等）
        content: 文本内容
        page_number: 所在页码
        bbox: 边界框坐标 (x1, y1, x2, y2)
        metadata: 额外元数据
    """
    element_type: str
    content: str
    page_number: int = 0
    bbox: Optional[tuple] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DocumentSection:
    """
    文档章节。

    Attributes:
        title: 章节标题
        level: 标题级别（1, 2, 3...）
        content: 章节内容
        elements: 章节包含的元素列表
        start_page: 起始页码
        end_page: 结束页码
    """
    title: str
    level: int = 1
    content: str = ""
    elements: List[DocumentElement] = field(default_factory=list)
    start_page: int = 0
    end_page: int = 0


@dataclass
class Document:
    """
    解析后的文档对象。

    Attributes:
        id: 文档唯一标识
        title: 文档标题
        file_name: 原始文件名
        file_type: 文件类型（pdf, docx 等）
        file_path: 文件路径
        file_size: 文件大小（字节）
        content: 完整文本内容
        sections: 文档章节列表
        elements: 文档元素列表（扁平化）
        metadata: 文档元数据
        created_at: 创建时间
        parsed_at: 解析时间
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    title: str = ""
    file_name: str = ""
    file_type: str = ""
    file_path: str = ""
    file_size: int = 0
    content: str = ""
    sections: List[DocumentSection] = field(default_factory=list)
    elements: List[DocumentElement] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    parsed_at: Optional[datetime] = None


@dataclass
class DocumentChunk:
    """
    文档分块。

    Attributes:
        id: 分块唯一标识
        doc_id: 所属文档 ID
        doc_url: 文档地址
        file_name: 原始文件名（包含扩展名）
        title: 所属章节标题
        content: 分块内容
        chunk_index: 分块序号
        token_count: 预估 token 数量
        page_number: 所在页码
        embedding: 向量表示（原始值，未归一化）
        metadata: 分块元数据
    """
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    doc_id: str = ""
    doc_url: str = ""
    file_name: str = ""
    title: str = ""
    content: str = ""
    chunk_index: int = 0
    token_count: int = 0
    page_number: int = 0
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_opensearch_doc(self) -> Dict[str, Any]:
        """
        转换为 OpenSearch 文档格式。
        
        注意：embedding 字段应该已经过 L2 归一化（由 EmbeddingClient 处理）。

        Returns:
            Dict: OpenSearch 文档字典
        """
        return {
            "chunk_id": self.id,
            "doc_id": self.doc_id,
            "doc_url": self.doc_url,
            "file_name": self.file_name,
            "title": self.title,
            "content": self.content,
            "chunk_index": self.chunk_index,
            "token_count": self.token_count,
            "page_number": self.page_number,
            "embedding": self.embedding or [],
            "metadata": self.metadata,
        }


@dataclass
class ParseResult:
    """
    解析结果。

    Attributes:
        document: 解析后的文档
        chunks: 分块列表
        success: 是否成功
        error_message: 错误信息
    """
    document: Optional[Document] = None
    chunks: List[DocumentChunk] = field(default_factory=list)
    success: bool = False
    error_message: str = ""

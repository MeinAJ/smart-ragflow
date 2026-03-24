"""
Backend Parser - 文档解析模块。

提供文档解析、分块、向量化等功能。
"""

from backend_parser.document_models import (
    DocumentElement,
    DocumentSection,
    Document,
    DocumentChunk,
    ParseResult
)

__all__ = [
    "DocumentElement",
    "DocumentSection",
    "Document",
    "DocumentChunk",
    "ParseResult"
]

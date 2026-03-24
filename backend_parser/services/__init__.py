"""
服务模块。

提供文档解析服务。
"""

from backend_parser.service import DocumentParseService, parse_document, parse_documents

__all__ = ["DocumentParseService", "parse_document", "parse_documents"]

"""
核心解析模块。

提供文档解析、分块等核心功能。
"""

from backend_parser.chunker import chunk_document, TextChunker
from backend_parser.tokenizer import token_counter

__all__ = ["chunk_document", "TextChunker", "token_counter"]

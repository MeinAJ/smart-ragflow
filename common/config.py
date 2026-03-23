"""
公共配置模块。

管理所有客户端的配置项。
"""

import os
from pathlib import Path
from typing import List

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# 加载 .env 文件
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)


class CommonSettings(BaseSettings):
    """公共客户端配置。"""

    # OpenSearch 配置
    OPENSEARCH_HOST: str = Field(default="localhost", validation_alias="OPENSEARCH_HOST")
    OPENSEARCH_PORT: int = Field(default=9200, validation_alias="OPENSEARCH_PORT")
    OPENSEARCH_INDEX: str = Field(default="rag_docs", validation_alias="OPENSEARCH_INDEX")
    OPENSEARCH_USER: str = Field(default="", validation_alias="OPENSEARCH_USER")
    OPENSEARCH_PASSWORD: str = Field(default="", validation_alias="OPENSEARCH_PASSWORD")

    # Embedding 配置
    EMBEDDING_URL: str = Field(default="http://localhost:8080/embed", validation_alias="EMBEDDING_URL")
    EMBEDDING_MODEL: str = Field(default="bge-m3", validation_alias="EMBEDDING_MODEL")
    EMBEDDING_DIM: int = Field(default=1024, validation_alias="EMBEDDING_DIM")
    EMBEDDING_TIMEOUT: float = Field(default=120.0, validation_alias="EMBEDDING_TIMEOUT")

    # Redis 配置
    REDIS_URL: str = Field(default="redis://localhost:6379", validation_alias="REDIS_URL")
    REDIS_DB: int = Field(default=0, validation_alias="REDIS_DB")
    
    # Embedding 缓存配置
    EMBEDDING_CACHE_ENABLED: bool = Field(default=True, validation_alias="EMBEDDING_CACHE_ENABLED")
    EMBEDDING_CACHE_TTL: int = Field(default=864000, validation_alias="EMBEDDING_CACHE_TTL")  # 10天
    EMBEDDING_CACHE_PREFIX: str = Field(default="emb:", validation_alias="EMBEDDING_CACHE_PREFIX")

    # MinIO 配置
    MINIO_ENDPOINT: str = Field(default="localhost:9000", validation_alias="MINIO_ENDPOINT")
    MINIO_ACCESS_KEY: str = Field(default="minioadmin", validation_alias="MINIO_ACCESS_KEY")
    MINIO_SECRET_KEY: str = Field(default="minioadmin", validation_alias="MINIO_SECRET_KEY")
    MINIO_BUCKET_NAME: str = Field(default="smart-ragflow", validation_alias="MINIO_BUCKET_NAME")
    MINIO_SECURE: bool = Field(default=False, validation_alias="MINIO_SECURE")

    # 搜索配置
    SEARCH_MIN_SCORE: float = Field(default=0.4, validation_alias="SEARCH_MIN_SCORE")
    SEARCH_TEXT_BOOST: float = Field(default=1.0, validation_alias="SEARCH_TEXT_BOOST")
    SEARCH_TITLE_BOOST: float = Field(default=2.0, validation_alias="SEARCH_TITLE_BOOST")

    # 分块配置（Parser 使用）
    CHUNK_SIZE: int = Field(default=512, validation_alias="CHUNK_SIZE")
    CHUNK_OVERLAP: int = Field(default=100, validation_alias="CHUNK_OVERLAP")
    CHUNK_SEPARATORS: List[str] = Field(
        default=["\n\n", "\n", "。", "；", " ", ""],
        validation_alias="CHUNK_SEPARATORS"
    )

    # Tokenizer 配置（Parser 使用）
    TOKENIZER_TYPE: str = Field(default="tiktoken", validation_alias="TOKENIZER_TYPE")
    TIKTOKEN_ENCODING: str = Field(default="cl100k_base", validation_alias="TIKTOKEN_ENCODING")

    # 支持的文件类型（Parser 使用）
    SUPPORTED_EXTENSIONS: List[str] = Field(
        default=[".pdf", ".docx", ".doc", ".txt", ".md", ".html", ".htm"],
        validation_alias="SUPPORTED_EXTENSIONS"
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 全局配置实例
settings = CommonSettings()

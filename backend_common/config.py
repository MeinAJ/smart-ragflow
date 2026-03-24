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

    # 调试模式
    DEBUG: bool = Field(default=False, validation_alias="DEBUG")

    # 数据库配置
    DATABASE_URL: str = Field(
        default="mysql+pymysql://root:password@localhost:3306/ragflow?charset=utf8mb4",
        validation_alias="DATABASE_URL"
    )

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

    # LLM 配置（QA 服务使用）
    OPENAI_API_KEY: str = Field(default="", validation_alias="OPENAI_API_KEY")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", validation_alias="OPENAI_BASE_URL")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo", validation_alias="OPENAI_MODEL")
    LLM_REQUEST_TIMEOUT: float = Field(default=60.0, validation_alias="LLM_REQUEST_TIMEOUT")

    # Admin 服务配置
    ADMIN_HOST: str = Field(default="0.0.0.0", validation_alias="ADMIN_HOST")
    ADMIN_PORT: int = Field(default=8001, validation_alias="ADMIN_PORT")
    
    # 文件上传配置
    MAX_FILE_SIZE: int = Field(default=50 * 1024 * 1024, validation_alias="MAX_FILE_SIZE")  # 50MB
    ALLOWED_EXTENSIONS: set = Field(
        default={"pdf", "docx", "doc", "txt", "md", "xlsx", "xls", "pptx", "ppt"},
        validation_alias="ALLOWED_EXTENSIONS"
    )
    
    # CORS 配置
    CORS_ORIGINS: List[str] = Field(default=["*"], validation_alias="CORS_ORIGINS")
    
    # MinIO Bucket（Admin 使用，兼容旧配置名）
    MINIO_BUCKET: str = Field(default="documents", validation_alias="MINIO_BUCKET")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


# 全局配置实例
settings = CommonSettings()

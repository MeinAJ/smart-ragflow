"""
数据模型定义模块。

共享的数据库模型，用于 backend_admin 和 backend_parser。
"""

from sqlalchemy import Column, String, BigInteger, DateTime, Text, Integer, SmallInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class Document(Base):
    """
    文档模型。
    
    存储文档元数据和解析状态。
    """
    
    __tablename__ = "documents"
    
    # 解析状态常量
    STATUS_PENDING = 0      # 未解析
    STATUS_PARSING = 1      # 正在解析
    STATUS_FAILED = 2       # 解析异常
    STATUS_COMPLETED = 3    # 解析完成
    
    STATUS_TEXT = {
        STATUS_PENDING: "未解析",
        STATUS_PARSING: "正在解析",
        STATUS_FAILED: "解析异常",
        STATUS_COMPLETED: "解析完成"
    }
    
    id = Column(String(64), primary_key=True, comment="主键")
    file_name = Column(String(255), nullable=False, comment="文件名")
    file_size = Column(BigInteger, nullable=False, default=0, comment="文件大小")
    file_md5 = Column(String(32), nullable=False, comment="文件MD5摘要")
    file_ext = Column(String(20), nullable=False, comment="文件后缀")
    file_url = Column(String(500), nullable=False, comment="MinIO文件URL")
    parse_status = Column(SmallInteger, nullable=False, default=STATUS_PENDING, comment="解析状态")
    parse_message = Column(Text, nullable=True, comment="解析状态消息")
    chunk_count = Column(Integer, default=0, comment="分块数量")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="修改时间")
    
    def to_dict(self):
        """转换为字典。"""
        return {
            "doc_id": self.id,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_md5": self.file_md5,
            "file_ext": self.file_ext,
            "file_url": self.file_url,
            "status": self.parse_status,
            "status_text": self.STATUS_TEXT.get(self.parse_status, "未知"),
            "parse_message": self.parse_message,
            "chunk_count": self.chunk_count,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }


class ParseTask(Base):
    """
    解析任务模型。
    
    存储文档解析任务状态。
    """
    
    __tablename__ = "parse_tasks"
    
    # 状态常量
    STATUS_PENDING = 0      # 未解析
    STATUS_WAITING = 1      # 待解析
    STATUS_PARSING = 2      # 解析中
    STATUS_FAILED = 3       # 解析异常
    STATUS_COMPLETED = 4    # 解析完成
    
    STATUS_TEXT = {
        STATUS_PENDING: "未解析",
        STATUS_WAITING: "待解析",
        STATUS_PARSING: "解析中",
        STATUS_FAILED: "解析异常",
        STATUS_COMPLETED: "解析完成"
    }
    
    id = Column(String(64), primary_key=True, comment="主键")
    doc_id = Column(String(64), nullable=False, comment="文档ID")
    file_name = Column(String(255), nullable=False, comment="文件名")
    file_size = Column(BigInteger, nullable=False, default=0, comment="文件大小")
    file_ext = Column(String(20), nullable=False, comment="文件后缀")
    file_url = Column(String(500), nullable=False, comment="MinIO文件URL")
    file_md5 = Column(String(32), nullable=False, comment="文件MD5摘要")
    status = Column(SmallInteger, nullable=False, default=STATUS_PENDING, comment="解析状态")
    error_message = Column(Text, nullable=True, comment="错误信息")
    started_at = Column(DateTime, nullable=True, comment="开始解析时间")
    completed_at = Column(DateTime, nullable=True, comment="完成解析时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="修改时间")
    
    def to_dict(self):
        """转换为字典。"""
        return {
            "task_id": self.id,
            "doc_id": self.doc_id,
            "file_name": self.file_name,
            "file_size": self.file_size,
            "file_ext": self.file_ext,
            "file_url": self.file_url,
            "status": self.status,
            "status_text": self.STATUS_TEXT.get(self.status, "未知"),
            "error_message": self.error_message,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

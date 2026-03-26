"""
数据模型定义模块。

共享的数据库模型，用于 backend_admin 和 backend_parser。
"""

from sqlalchemy import Column, String, BigInteger, DateTime, Text, Integer, SmallInteger, Index, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()


class User(Base):
    """
    用户模型。
    
    存储用户信息和认证数据。
    """
    
    __tablename__ = "users"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键ID")
    username = Column(String(50), unique=True, nullable=False, index=True, comment="用户名")
    email = Column(String(100), unique=True, nullable=True, comment="邮箱")
    password_hash = Column(String(255), nullable=False, comment="密码哈希")
    nickname = Column(String(50), nullable=True, comment="昵称")
    avatar = Column(String(500), nullable=True, comment="头像URL")
    is_active = Column(Boolean, default=True, comment="是否激活")
    is_admin = Column(Boolean, default=False, comment="是否管理员")
    last_login_at = Column(DateTime, nullable=True, comment="最后登录时间")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    def to_dict(self):
        """转换为字典（不包含敏感信息）"""
        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "nickname": self.nickname,
            "avatar": self.avatar,
            "is_admin": self.is_admin,
            "last_login_at": self.last_login_at.isoformat() if self.last_login_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


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


class ChatHistory(Base):
    """
    对话历史记录模型。
    
    存储用户提问和 AI 回答的消息记录。
    """
    
    __tablename__ = "chat_history"
    
    # 角色常量
    ROLE_USER = "user"           # 用户
    ROLE_ASSISTANT = "assistant" # AI助手
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键ID")
    user_id = Column(BigInteger, nullable=False, index=True, comment="用户ID")
    session_id = Column(String(64), nullable=False, index=True, comment="会话ID，用于关联同一对话")
    role = Column(String(20), nullable=False, default=ROLE_USER, comment="角色类型：user/assistant")
    content = Column(Text, nullable=False, comment="消息内容")
    model = Column(String(50), nullable=True, comment="使用的模型名称")
    tokens_used = Column(Integer, default=0, comment="本次对话消耗的token数")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    
    # 复合索引，加速按用户和会话查询
    __table_args__ = (
        Index('idx_user_session', 'user_id', 'session_id'),
        Index('idx_user_created', 'user_id', 'created_at'),
        Index('idx_session_role', 'session_id', 'role'),
    )
    
    def to_dict(self):
        """转换为字典。"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "model": self.model,
            "tokens_used": self.tokens_used,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
    
    def to_message(self):
        """
        转换为消息格式，用于 LLM 上下文。
        
        Returns:
            dict: {"role": "user"/"assistant", "content": ...}
        """
        return {
            "role": self.role,
            "content": self.content
        }


class UserSession(Base):
    """
    用户会话模型。
    
    存储用户的会话信息，每个会话对应一个对话线程。
    """
    
    __tablename__ = "user_session"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True, comment="自增主键ID")
    user_id = Column(BigInteger, nullable=False, index=True, comment="用户ID")
    session_id = Column(String(64), nullable=False, unique=True, index=True, comment="会话ID，UUID格式")
    session_name = Column(String(200), nullable=True, comment="会话名称，用户可自定义")
    message_count = Column(Integer, default=0, comment="消息数量")
    last_message_at = Column(DateTime, nullable=True, comment="最后一条消息时间")
    is_pinned = Column(SmallInteger, default=0, comment="是否置顶：0-否，1-是")
    created_at = Column(DateTime, server_default=func.now(), comment="创建时间")
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now(), comment="更新时间")
    
    # 复合索引
    __table_args__ = (
        Index('idx_user_last_msg', 'user_id', 'last_message_at'),
        Index('idx_user_pinned', 'user_id', 'is_pinned', 'last_message_at'),
    )
    
    def to_dict(self):
        """转换为字典。"""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "session_name": self.session_name,
            "message_count": self.message_count,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
            "is_pinned": bool(self.is_pinned),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }

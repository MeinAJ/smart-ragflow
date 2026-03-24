"""
文档服务。

提供文档的增删改查和解析任务管理。
"""

import asyncio
import hashlib
import uuid
import logging
from typing import List, Optional, Tuple
from sqlalchemy import desc
from sqlalchemy.orm import Session
from backend_admin.models import Document, ParseTask
from backend_common import minio_client

logger = logging.getLogger(__name__)


def calculate_md5(file_data: bytes) -> str:
    """
    计算文件 MD5。
    
    Args:
        file_data: 文件二进制数据
        
    Returns:
        str: MD5 摘要
    """
    return hashlib.md5(file_data).hexdigest()


def get_object_name_from_url(url: str, bucket_name: str) -> Optional[str]:
    """
    从 URL 提取对象名称。
    
    Args:
        url: MinIO URL
        bucket_name: Bucket 名称
        
    Returns:
        str: 对象名称
    """
    try:
        # URL 格式: http://host/bucket/object-name
        parts = url.split(f"/{bucket_name}/")
        if len(parts) == 2:
            return parts[1]
        return None
    except Exception:
        return None


class DocumentService:
    """文档服务。"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_documents(
        self,
        page: int = 1,
        size: int = 10,
        keyword: str = None,
        status: int = None
    ) -> Tuple[List[Document], int]:
        """
        获取文档列表。
        
        Args:
            page: 页码
            size: 每页数量
            keyword: 搜索关键词
            status: 解析状态筛选
            
        Returns:
            Tuple[List[Document], int]: 文档列表和总数
        """
        query = self.db.query(Document)
        
        if keyword:
            query = query.filter(Document.file_name.contains(keyword))
        
        if status is not None:
            query = query.filter(Document.parse_status == status)
        
        total = query.count()
        
        documents = query.order_by(desc(Document.created_at)) \
                        .offset((page - 1) * size) \
                        .limit(size) \
                        .all()
        
        return documents, total
    
    def get_document_by_id(self, doc_id: str) -> Optional[Document]:
        """根据ID获取文档。"""
        return self.db.query(Document).filter(Document.id == doc_id).first()
    
    def get_document_by_md5(self, file_md5: str) -> Optional[Document]:
        """根据MD5获取文档。"""
        return self.db.query(Document).filter(Document.file_md5 == file_md5).first()
    
    def create_document(
        self,
        file_name: str,
        file_data: bytes,
        file_ext: str,
        file_url: str,
        title: str = None
    ) -> Document:
        """
        创建文档（支持覆盖）。
        
        Args:
            file_name: 文件名
            file_data: 文件数据
            file_ext: 文件后缀
            file_url: MinIO URL
            title: 文档标题
            
        Returns:
            Document: 创建的文档
        """
        file_md5 = calculate_md5(file_data)
        file_size = len(file_data)
        
        # 检查 MD5 是否存在
        existing_doc = self.get_document_by_md5(file_md5)
        
        if existing_doc:
            # 覆盖更新
            logger.info(f"MD5 exists, overwriting document: {existing_doc.id}")
            
            # 删除旧文件
            old_object_name = get_object_name_from_url(
                existing_doc.file_url, 
                minio_client.bucket_name
            )
            if old_object_name:
                try:
                    # 使用 asyncio.run 调用异步方法
                    asyncio.run(minio_client.delete_file(old_object_name))
                except Exception as e:
                    logger.warning(f"Failed to delete old file: {e}")
            
            # 删除关联的任务
            self.db.query(ParseTask).filter(ParseTask.doc_id == existing_doc.id).delete()
            
            # 更新文档
            existing_doc.file_name = file_name
            existing_doc.file_size = file_size
            existing_doc.file_ext = file_ext
            existing_doc.file_url = file_url
            existing_doc.parse_status = Document.STATUS_PENDING
            existing_doc.parse_message = None
            existing_doc.chunk_count = 0
            
            self.db.commit()
            self.db.refresh(existing_doc)
            return existing_doc
        
        # 创建新文档
        doc = Document(
            id=str(uuid.uuid4()),
            file_name=file_name,
            file_size=file_size,
            file_md5=file_md5,
            file_ext=file_ext,
            file_url=file_url,
            parse_status=Document.STATUS_PENDING
        )
        
        self.db.add(doc)
        self.db.commit()
        self.db.refresh(doc)
        
        logger.info(f"Created document: {doc.id}, name: {file_name}")
        return doc
    
    def update_document(self, doc_id: str, title: str = None, description: str = None) -> Optional[Document]:
        """
        更新文档信息。
        
        Args:
            doc_id: 文档ID
            title: 标题
            description: 描述
            
        Returns:
            Document: 更新后的文档
        """
        doc = self.get_document_by_id(doc_id)
        if not doc:
            return None
        
        if title:
            doc.file_name = title
        
        self.db.commit()
        self.db.refresh(doc)
        
        logger.info(f"Updated document: {doc_id}")
        return doc
    
    def delete_document(self, doc_id: str) -> bool:
        """
        删除文档。
        
        Args:
            doc_id: 文档ID
            
        Returns:
            bool: 是否删除成功
        """
        doc = self.get_document_by_id(doc_id)
        if not doc:
            return False
        
        # 删除 MinIO 文件
        object_name = get_object_name_from_url(doc.file_url, minio_client.bucket_name)
        if object_name:
            try:
                # 使用 asyncio.run 调用异步方法
                asyncio.run(minio_client.delete_file(object_name))
            except Exception as e:
                logger.warning(f"Failed to delete file from MinIO: {e}")
        
        # 删除文档（关联的任务会自动删除）
        self.db.delete(doc)
        self.db.commit()
        
        logger.info(f"Deleted document: {doc_id}")
        return True
    
    def create_parse_task(self, doc_id: str) -> ParseTask:
        """
        创建解析任务。
        
        Args:
            doc_id: 文档ID
            
        Returns:
            ParseTask: 创建的任务
        """
        doc = self.get_document_by_id(doc_id)
        if not doc:
            raise ValueError(f"Document not found: {doc_id}")
        
        # 检查是否已有待处理或处理中的任务
        existing_task = self.db.query(ParseTask).filter(
            ParseTask.doc_id == doc_id,
            ParseTask.status.in_([ParseTask.STATUS_WAITING, ParseTask.STATUS_PARSING])
        ).first()
        
        if existing_task:
            logger.info(f"Task already exists: {existing_task.id}")
            return existing_task
        
        # 创建新任务
        task = ParseTask(
            id=str(uuid.uuid4()),
            doc_id=doc_id,
            file_name=doc.file_name,
            file_size=doc.file_size,
            file_ext=doc.file_ext,
            file_url=doc.file_url,
            file_md5=doc.file_md5,
            status=ParseTask.STATUS_WAITING
        )
        
        self.db.add(task)
        
        # 更新文档状态
        doc.parse_status = Document.STATUS_PENDING
        
        self.db.commit()
        self.db.refresh(task)
        
        logger.info(f"Created parse task: {task.id} for doc: {doc_id}")
        return task
    
    def get_task_by_id(self, task_id: str) -> Optional[ParseTask]:
        """根据ID获取任务。"""
        return self.db.query(ParseTask).filter(ParseTask.id == task_id).first()
    
    def get_waiting_tasks(self, limit: int = 10) -> List[ParseTask]:
        """
        获取待处理的任务。
        
        Args:
            limit: 数量限制
            
        Returns:
            List[ParseTask]: 任务列表
        """
        return self.db.query(ParseTask) \
                     .filter(ParseTask.status == ParseTask.STATUS_WAITING) \
                     .order_by(ParseTask.created_at) \
                     .limit(limit) \
                     .all()

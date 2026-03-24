"""
文档管理 API。

提供5个核心接口：
1. GET    /api/documents       - 查询文档列表
2. POST   /api/documents       - 上传/创建文档
3. DELETE /api/documents/{id}  - 删除文档
4. PUT    /api/documents/{id}  - 更新文档
5. POST   /api/documents/{id}/parse - 解析文档（创建解析任务）
"""

import os
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, File, UploadFile, Form, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend_admin.database import get_db_session
from backend_admin.models import Document
from backend_admin.services.document_service import DocumentService
from backend_common import settings, minio_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/documents", tags=["documents"])


# ========== 请求/响应模型 ==========

class DocumentResponse(BaseModel):
    """文档响应模型。"""
    doc_id: str
    file_name: str
    file_size: int
    file_md5: str
    file_ext: str
    file_url: str
    status: int
    status_text: str
    parse_message: Optional[str]
    chunk_count: int
    created_at: Optional[str]
    updated_at: Optional[str]


class DocumentListResponse(BaseModel):
    """文档列表响应。"""
    total: int
    items: List[DocumentResponse]


class UpdateDocumentRequest(BaseModel):
    """更新文档请求。"""
    title: Optional[str] = None
    description: Optional[str] = None


class ParseResponse(BaseModel):
    """解析响应。"""
    message: str
    task_id: str
    doc_id: str


# ========== 接口实现 ==========

@router.get("", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页数量"),
    keyword: str = Query(None, description="搜索关键词"),
    status: int = Query(None, description="解析状态筛选"),
    db: Session = Depends(get_db_session)
):
    """
    1. 获取文档列表。
    
    支持分页、搜索和状态筛选。
    """
    service = DocumentService(db)
    documents, total = service.get_documents(
        page=page,
        size=size,
        keyword=keyword,
        status=status
    )
    
    return {
        "total": total,
        "items": [doc.to_dict() for doc in documents]
    }


@router.post("", response_model=DocumentResponse)
async def upload_document(
    file: UploadFile = File(..., description="上传的文件"),
    title: str = Form(None, description="文档标题"),
    description: str = Form(None, description="文档描述"),
    parse_immediately: bool = Form(True, description="是否立即解析"),
    db: Session = Depends(get_db_session)
):
    """
    2. 上传/创建文档。
    
    - 如果文件 MD5 已存在，则覆盖更新
    - 支持自动创建解析任务
    """
    # 检查文件类型
    file_ext = os.path.splitext(file.filename)[1][1:].lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {file_ext}，支持的类型: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )
    
    # 读取文件数据
    file_data = await file.read()
    
    # 检查文件大小
    if len(file_data) > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"文件大小超过限制: {settings.MAX_FILE_SIZE / 1024 / 1024}MB"
        )
    
    try:
        # 生成对象名称
        import hashlib
        import time
        timestamp = int(time.time())
        md5_prefix = hashlib.md5(file_data).hexdigest()[:8]
        object_name = f"{timestamp}_{md5_prefix}_{file.filename}"
        
        # 上传文件到 MinIO
        file_url = await minio_client.upload_bytes(
            data=file_data,
            object_name=object_name,
            content_type=file.content_type or "application/octet-stream"
        )
        
        # 创建/更新文档记录
        service = DocumentService(db)
        doc = service.create_document(
            file_name=title or file.filename,
            file_data=file_data,
            file_ext=file_ext,
            file_url=file_url,
            title=title
        )
        
        # 如果需要立即解析，创建解析任务
        if parse_immediately:
            service.create_parse_task(doc.id)
        
        return doc.to_dict()
        
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: str,
    db: Session = Depends(get_db_session)
):
    """
    3. 删除文档。
    
    会同时删除 MinIO 中的文件和关联的解析任务。
    """
    service = DocumentService(db)
    
    doc = service.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    success = service.delete_document(doc_id)
    if not success:
        raise HTTPException(status_code=500, detail="删除失败")
    
    return {"message": "删除成功", "doc_id": doc_id}


@router.put("/{doc_id}", response_model=DocumentResponse)
async def update_document(
    doc_id: str,
    request: UpdateDocumentRequest,
    db: Session = Depends(get_db_session)
):
    """
    4. 更新文档信息。
    
    仅支持修改标题和描述，不支持修改文件。
    """
    service = DocumentService(db)
    
    doc = service.update_document(
        doc_id=doc_id,
        title=request.title,
        description=request.description
    )
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    return doc.to_dict()


@router.post("/{doc_id}/parse", response_model=ParseResponse)
async def parse_document(
    doc_id: str,
    db: Session = Depends(get_db_session)
):
    """
    5. 解析文档。
    
    创建一个状态为"待解析"的任务，等待后台服务处理。
    """
    service = DocumentService(db)
    
    # 检查文档是否存在
    doc = service.get_document_by_id(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    # 检查是否已在解析中
    if doc.parse_status == Document.STATUS_PARSING:
        raise HTTPException(status_code=400, detail="文档正在解析中")
    
    try:
        # 创建解析任务（状态为待解析）
        task = service.create_parse_task(doc_id)
        
        return {
            "message": "解析任务已创建",
            "task_id": task.id,
            "doc_id": doc_id
        }
        
    except Exception as e:
        logger.error(f"Failed to create parse task: {e}")
        raise HTTPException(status_code=500, detail=f"创建解析任务失败: {str(e)}")


@router.get("/{doc_id}/status")
async def get_document_status(
    doc_id: str,
    db: Session = Depends(get_db_session)
):
    """
    获取文档解析状态。
    """
    service = DocumentService(db)
    doc = service.get_document_by_id(doc_id)
    
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")
    
    return {
        "doc_id": doc_id,
        "status": doc.parse_status,
        "status_text": Document.STATUS_TEXT.get(doc.parse_status, "未知"),
        "parse_message": doc.parse_message,
        "chunk_count": doc.chunk_count
    }

"""
文件下载接口模块。

提供文件下载代理服务，解决前端跨域访问 MinIO 的问题。
"""

import logging
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import StreamingResponse
import httpx

from backend_common import Document, DatabaseClient

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["files"])

# 数据库客户端
db_client = DatabaseClient()


@router.get("/download/{doc_id}")
async def download_file(doc_id: str):
    """
    下载文档文件。
    
    通过 doc_id 从 MinIO 获取文件并返回给前端，解决跨域问题。
    
    Args:
        doc_id: 文档 ID
        
    Returns:
        StreamingResponse: 文件流
    """
    logger.info(f"Download request for doc_id: {doc_id}")
    
    # 查询文档信息
    db = db_client.get_session()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            raise HTTPException(status_code=404, detail="文档不存在")
        
        file_url = doc.file_url
        file_name = doc.file_name
        file_ext = doc.file_ext
        
        logger.info(f"Found document: {file_name}, URL: {file_url}")
    finally:
        db.close()
    
    # 从 MinIO 下载文件
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(file_url, timeout=60.0)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch file from MinIO: {response.status_code}")
                raise HTTPException(
                    status_code=502, 
                    detail=f"无法从存储服务获取文件: {response.status_code}"
                )
            
            # 确定 Content-Type
            content_type_map = {
                'pdf': 'application/pdf',
                'doc': 'application/msword',
                'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                'xls': 'application/vnd.ms-excel',
                'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                'ppt': 'application/vnd.ms-powerpoint',
                'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
                'txt': 'text/plain',
                'md': 'text/markdown',
                'json': 'application/json',
                'xml': 'application/xml',
                'csv': 'text/csv',
                'jpg': 'image/jpeg',
                'jpeg': 'image/jpeg',
                'png': 'image/png',
                'gif': 'image/gif',
                'webp': 'image/webp',
                'svg': 'image/svg+xml',
            }
            
            content_type = content_type_map.get(file_ext.lower(), 'application/octet-stream')
            
            logger.info(f"Returning file: {file_name}, type: {content_type}, size: {len(response.content)}")
            
            return Response(
                content=response.content,
                media_type=content_type,
                headers={
                    "Content-Disposition": f'inline; filename="{file_name}"',
                    "Cache-Control": "public, max-age=3600",
                }
            )
            
    except httpx.RequestError as e:
        logger.error(f"Error fetching file from MinIO: {str(e)}")
        raise HTTPException(status_code=502, detail="无法连接到存储服务")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        raise HTTPException(status_code=500, detail="文件下载失败")


@router.get("/preview/{doc_id}")
async def preview_file(doc_id: str):
    """
    预览文档文件（用于 iframe 嵌入）。
    
    与 download 接口相同，但 Content-Disposition 设置为 inline。
    
    Args:
        doc_id: 文档 ID
        
    Returns:
        Response: 文件内容
    """
    return await download_file(doc_id)

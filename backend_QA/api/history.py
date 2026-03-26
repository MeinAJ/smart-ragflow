"""
对话历史查询接口模块。

提供对话历史的查询和管理功能。
"""

import logging
from typing import List, Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Query, Depends

from backend_QA.services.chat_history import chat_history_service
from backend_QA.api.auth import get_current_user_id, get_current_user
from backend_common import User

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["history"])


class ChatHistoryResponse(BaseModel):
    """对话历史响应模型。"""
    id: int
    session_id: str
    role: str
    content: str
    model: Optional[str]
    tokens_used: int
    created_at: str


class SessionListResponse(BaseModel):
    """会话列表响应模型。"""
    id: int
    user_id: int
    session_id: str
    session_name: Optional[str]
    message_count: int
    last_message_at: Optional[str]
    is_pinned: bool
    created_at: str
    updated_at: str


class UpdateSessionNameRequest(BaseModel):
    """更新会话名称请求模型。"""
    session_name: str = Field(..., min_length=1, max_length=200, description="会话名称")


class PinSessionRequest(BaseModel):
    """置顶会话请求模型。"""
    is_pinned: bool = Field(..., description="是否置顶")


class SessionActionResponse(BaseModel):
    """会话操作响应模型。"""
    success: bool
    message: str


class HistoryListResponse(BaseModel):
    """历史记录列表响应模型。"""
    total: int
    items: List[ChatHistoryResponse]


class MessagesResponse(BaseModel):
    """消息列表响应模型。"""
    session_id: str
    message_count: int
    messages: List[dict]


@router.get("/sessions", response_model=List[SessionListResponse])
async def list_sessions(
    limit: int = Query(default=50, ge=1, le=100, description="返回条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    获取当前用户的会话列表。
    
    按最近活动时间排序返回会话列表。
    """
    try:
        sessions = chat_history_service.get_session_list(
            user_id=current_user_id,
            limit=limit, 
            offset=offset
        )
        return sessions
    except Exception as e:
        logger.error(f"Error listing sessions: {str(e)}")
        raise HTTPException(status_code=500, detail="获取会话列表失败")


@router.get("/sessions/{session_id}", response_model=HistoryListResponse)
async def get_session_history(
    session_id: str,
    limit: int = Query(default=20, ge=1, le=100, description="每页条数"),
    offset: int = Query(default=0, ge=0, description="偏移量"),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    获取当前用户指定会话的历史对话记录。
    """
    try:
        logger.info(f"Getting history for user {current_user_id}, session: {session_id}")
        
        # 从 MySQL 获取历史记录
        records = chat_history_service.get_history_from_mysql(
            user_id=current_user_id,
            session_id=session_id,
            limit=limit,
            offset=offset
        )
        
        return HistoryListResponse(
            total=len(records),
            items=[ChatHistoryResponse(**r) for r in records]
        )
        
    except Exception as e:
        logger.error(f"Error getting session history: {str(e)}")
        raise HTTPException(status_code=500, detail="获取对话历史失败")


@router.get("/sessions/{session_id}/messages", response_model=MessagesResponse)
async def get_session_messages(
    session_id: str,
    limit: int = Query(default=20, ge=1, le=200, description="最近N轮对话"),
    current_user_id: int = Depends(get_current_user_id)
):
    """
    获取当前用户指定会话的消息列表（用于LLM上下文）。
    
    返回格式化的消息列表，可直接用于 LLM 上下文。
    """
    try:
        logger.info(f"Getting messages for user {current_user_id}, session: {session_id}")
        
        # 从 Redis 获取（更快）
        messages = await chat_history_service.get_history_from_redis(
            user_id=current_user_id,
            session_id=session_id,
            limit=limit
        )
        
        return MessagesResponse(
            session_id=session_id,
            message_count=len(messages),
            messages=messages
        )
        
    except Exception as e:
        logger.error(f"Error getting session messages: {str(e)}")
        raise HTTPException(status_code=500, detail="获取消息列表失败")


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: str,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    删除当前用户指定会话的所有历史记录。
    
    只删除该用户自己的会话数据。
    """
    try:
        logger.info(f"Deleting session for user {current_user_id}: {session_id}")
        
        # 删除 MySQL 记录（只删除该用户的）
        success = chat_history_service.delete_session(
            user_id=current_user_id,
            session_id=session_id
        )
        
        if not success:
            raise HTTPException(status_code=500, detail="删除失败")
        
        # 删除 Redis 记录
        redis_key = f"chat_history:{current_user_id}:{session_id}"
        from backend_common import redis_client
        await redis_client.client.delete(redis_key)
        logger.info(f"Deleted Redis key: {redis_key}")
        
        return {
            "success": True,
            "session_id": session_id,
            "message": "删除成功"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {str(e)}")
        raise HTTPException(status_code=500, detail="删除会话失败")


@router.put("/sessions/{session_id}/name", response_model=SessionActionResponse)
async def update_session_name(
    session_id: str,
    request: UpdateSessionNameRequest,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    更新当前用户指定会话的名称。
    """
    try:
        logger.info(f"Updating session name for user {current_user_id}: {session_id} -> {request.session_name}")
        
        success = chat_history_service.update_session_name(
            user_id=current_user_id,
            session_id=session_id,
            session_name=request.session_name
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        return SessionActionResponse(
            success=True,
            message="会话名称已更新"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating session name: {str(e)}")
        raise HTTPException(status_code=500, detail="更新会话名称失败")


@router.put("/sessions/{session_id}/pin", response_model=SessionActionResponse)
async def pin_session(
    session_id: str,
    request: PinSessionRequest,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    置顶/取消置顶当前用户的指定会话。
    """
    try:
        logger.info(f"Pinning session for user {current_user_id}: {session_id} -> {request.is_pinned}")
        
        success = chat_history_service.pin_session(
            user_id=current_user_id,
            session_id=session_id,
            is_pinned=request.is_pinned
        )
        
        if not success:
            raise HTTPException(status_code=404, detail="会话不存在")
        
        action = "置顶" if request.is_pinned else "取消置顶"
        return SessionActionResponse(
            success=True,
            message=f"会话已{action}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pinning session: {str(e)}")
        raise HTTPException(status_code=500, detail="置顶会话失败")

"""
问答流式接口模块。

实现 POST /v1/chat/completions 接口，支持 SSE 流式输出。
"""

import json
import logging
import time
import uuid
from typing import List, Optional, Literal, AsyncIterator
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import StreamingResponse

from backend_QA.core.graph import rag_graph
from backend_QA.core.state import GraphState
from backend_QA.services.llm import llm_client
from backend_QA.services.chat_history import chat_history_service
from backend_QA.api.auth import get_current_user_id, get_current_user

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1", tags=["chat"])


class ChatMessage(BaseModel):
    """聊天消息模型。"""
    role: Literal["system", "user", "assistant"] = Field(..., description="消息角色")
    content: str = Field(..., description="消息内容")


class ChatCompletionRequest(BaseModel):
    """聊天完成请求模型。"""
    messages: List[ChatMessage] = Field(..., description="消息列表")
    stream: bool = Field(default=True, description="是否流式输出")
    model: Optional[str] = Field(default="deepseek-chat", description="模型名称")
    temperature: Optional[float] = Field(default=0.2, description="采样温度")
    session_id: Optional[str] = Field(default=None, description="会话ID，用于关联历史对话")


class ChatCompletionResponse(BaseModel):
    """聊天完成响应模型（非流式）。"""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[dict]


def extract_question(messages: List[ChatMessage]) -> str:
    """
    从消息列表中提取用户问题。

    取最后一条用户消息作为问题。

    Args:
        messages: 消息列表

    Returns:
        str: 提取的问题
    """
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content
    return ""


def get_friendly_error(error_msg: str) -> str:
    """
    将技术性错误转换为用户友好的提示。
    
    Args:
        error_msg: 原始错误信息
        
    Returns:
        str: 友好的错误提示
    """
    error_lower = error_msg.lower()
    
    # 匹配常见错误模式
    if "connection" in error_lower or "connect" in error_lower:
        return "无法连接到检索服务，请稍后再试"
    elif "timeout" in error_lower or "timed out" in error_lower:
        return "服务响应超时，请稍后再试"
    elif "embedding" in error_lower:
        return "文本向量化服务暂时不可用，请稍后再试"
    elif "opensearch" in error_lower or "elasticsearch" in error_lower:
        return "文档检索服务暂时不可用，请稍后再试"
    elif "llm" in error_lower or "openai" in error_lower or "deepseek" in error_lower:
        return "AI 服务暂时不可用，请稍后再试"
    elif "no relevant" in error_lower or "not found" in error_lower:
        return "未找到相关参考资料，请尝试用其他方式描述您的问题"
    elif "permission" in error_lower or "unauthorized" in error_lower:
        return "没有权限访问该服务"
    elif "rate limit" in error_lower or "too many" in error_lower:
        return "请求过于频繁，请稍后再试"
    
    # 如果没有匹配到特定模式，返回通用友好提示
    if len(error_msg) > 100:
        return "服务处理过程中出现问题，请稍后再试"
    
    return error_msg


async def stream_rag_with_context(
    question: str, 
    history_messages: List[dict] = None,
    user_id: int = None
) -> AsyncIterator[tuple[str, any]]:
    """
    流式生成 RAG 答案。

    先 yield 文档元数据，然后 yield 生成的文本片段。

    Args:
        question: 用户问题
        history_messages: 历史对话消息列表

    Yields:
        tuple: ("docs", docs_list) 或 ("token", text)
    """
    state: GraphState = {
        "question": question,
        "question_vector": [],
        "retrieved_docs": [],
        "reranked_docs": [],
        "answer": None,
        "error": None
    }
    
    try:
        # 1. 向量化
        logger.info("Stream RAG: Step 1 - Vectorize")
        from backend_QA.core.nodes import vectorize_node
        result = await vectorize_node(state)
        state.update(result)
        
        if state.get("error"):
            yield ("error", get_friendly_error(state['error']))
            return
        
        # 2. 检索
        logger.info("Stream RAG: Step 2 - Retrieve")
        from backend_QA.core.nodes import retrieve_node
        result = await retrieve_node(state)
        state.update(result)
        
        if state.get("error"):
            yield ("error", get_friendly_error(state['error']))
            return
        
        # 3. 重排序
        logger.info("Stream RAG: Step 3 - Rerank")
        from backend_QA.core.nodes import rerank_node
        result = await rerank_node(state)
        state.update(result)
        
        if state.get("error"):
            yield ("error", get_friendly_error(state['error']))
            return
        
        # 4. 准备生成
        logger.info("Stream RAG: Step 4 - Generate (streaming)")
        docs = state.get("reranked_docs", [])
        
        if not docs:
            yield ("error", "未找到相关参考资料，请尝试用其他方式描述您的问题")
            return
        
        # 先返回文档元数据
        docs_meta = []
        for i, doc in enumerate(docs):
            metadata = doc.get("metadata", {})
            docs_meta.append({
                "index": i + 1,
                "doc_id": doc.get("doc_id") or metadata.get("doc_id"),  # 文档ID，用于下载
                "title": doc.get("title") or metadata.get("title", f"文档 {i+1}"),
                "doc_url": doc.get("doc_url") or metadata.get("doc_url", ""),
                "file_name": doc.get("file_name") or metadata.get("file_name", ""),  # 原始文件名（包含扩展名）
                "metadata": metadata
            })
        yield ("docs", docs_meta)
        
        # 然后流式返回答案（传入历史对话）
        async for token in llm_client.generate_stream(
            question=question,
            context_docs=docs,
            history_messages=history_messages
        ):
            yield ("token", token)
            
    except Exception as e:
        logger.error(f"Stream RAG error: {str(e)}")
        yield ("error", get_friendly_error(str(e)))


@router.post("/chat/completions")
async def chat_completions(
    request: ChatCompletionRequest,
    current_user_id: int = Depends(get_current_user_id)
):
    """
    智能问答流式接口。

    接收用户问题，经 RAG 流程处理后返回流式答案。
    支持 session_id 关联历史对话。

    Args:
        request: 聊天完成请求

    Returns:
        StreamingResponse: SSE 流式响应
    """
    try:
        question = extract_question(request.messages)
        session_id = request.session_id

        if not question:
            return StreamingResponse(
                content=iter(["event: error\ndata: {\"message\": \"请输入您的问题\"}\n\n"]),
                media_type="text/event-stream"
            )

        logger.info(f"Chat completions request: question={question[:50]}..., session_id={session_id}")

        # 获取历史对话上下文
        history_messages = []
        if session_id:
            history_messages = await chat_history_service.get_context_with_trim(
                user_id=current_user_id,
                session_id=session_id
            )
            logger.info(f"Loaded {len(history_messages)} messages from history for user {current_user_id}, session {session_id}")

        if request.stream:
            # 流式响应
            async def generate_sse():
                chat_id = f"chatcmpl-{uuid.uuid4().hex}"
                created = int(time.time())
                full_answer = ""  # 收集完整答案
                
                async for item_type, data in stream_rag_with_context(question, history_messages, current_user_id):
                    if item_type == "docs":
                        # 发送文档元数据作为特殊事件
                        event_data = json.dumps({"docs": data}, ensure_ascii=False)
                        yield f"event: context_docs\ndata: {event_data}\n\n"
                    
                    elif item_type == "token":
                        # 收集答案
                        full_answer += data
                        # 发送标准 OpenAI 格式的 SSE 消息
                        chunk = {
                            "id": chat_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": request.model,
                            "choices": [
                                {
                                    "index": 0,
                                    "delta": {"content": data},
                                    "finish_reason": None
                                }
                            ]
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"
                    
                    elif item_type == "error":
                        # 发送错误事件
                        error_data = json.dumps({"message": data}, ensure_ascii=False)
                        yield f"event: error\ndata: {error_data}\n\n"
                        return
                
                # 结束标记
                yield "data: [DONE]\n\n"
                
                # 保存对话历史（在流结束后）
                if session_id:
                    try:
                        tokens_used = chat_history_service.count_tokens(question + full_answer)
                        await chat_history_service.save_chat(
                            user_id=current_user_id,
                            session_id=session_id,
                            user_message=question,
                            assistant_message=full_answer,
                            model=request.model,
                            tokens_used=tokens_used
                        )
                        logger.info(f"Saved chat history for session {session_id}")
                    except Exception as e:
                        logger.error(f"Failed to save chat history: {str(e)}")
            
            return StreamingResponse(
                content=generate_sse(),
                media_type="text/event-stream"
            )
        else:
            # 非流式响应
            initial_state: GraphState = {
                "question": question,
                "question_vector": [],
                "retrieved_docs": [],
                "reranked_docs": [],
                "answer": None,
                "error": None
            }

            # 执行图
            final_state = await rag_graph.ainvoke(initial_state)
            
            if final_state.get("error"):
                raise HTTPException(
                    status_code=500,
                    detail=get_friendly_error(final_state["error"])
                )
            
            answer = final_state.get("answer", "")

            # 保存对话历史
            if session_id:
                try:
                    tokens_used = chat_history_service.count_tokens(question + answer)
                    await chat_history_service.save_chat(
                        user_id=current_user_id,
                        session_id=session_id,
                        user_message=question,
                        assistant_message=answer,
                        model=request.model,
                        tokens_used=tokens_used
                    )
                    logger.info(f"Saved chat history for session {session_id}")
                except Exception as e:
                    logger.error(f"Failed to save chat history: {str(e)}")

            response = {
                "id": f"chatcmpl-{uuid.uuid4().hex}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": request.model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": answer
                        },
                        "finish_reason": "stop"
                    }
                ]
            }

            return response
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Chat completions error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=get_friendly_error(str(e))
        )

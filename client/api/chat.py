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
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from client.core.graph import rag_graph
from client.core.state import GraphState
from client.services.llm import llm_client

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


async def stream_rag_with_context(question: str) -> AsyncIterator[tuple[str, any]]:
    """
    流式生成 RAG 答案。

    先 yield 文档元数据，然后 yield 生成的文本片段。

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
        from client.core.nodes import vectorize_node
        result = await vectorize_node(state)
        state.update(result)
        
        if state.get("error"):
            yield ("error", get_friendly_error(state['error']))
            return
        
        # 2. 检索
        logger.info("Stream RAG: Step 2 - Retrieve")
        from client.core.nodes import retrieve_node
        result = await retrieve_node(state)
        state.update(result)
        
        if state.get("error"):
            yield ("error", get_friendly_error(state['error']))
            return
        
        # 3. 重排序
        logger.info("Stream RAG: Step 3 - Rerank")
        from client.core.nodes import rerank_node
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
            docs_meta.append({
                "index": i + 1,
                "title": doc.get("title", "") or doc.get("metadata", {}).get("title", f"文档 {i+1}"),
                "doc_url": doc.get("doc_url", "") or doc.get("metadata", {}).get("doc_url", ""),
                "metadata": doc.get("metadata", {})
            })
        yield ("docs", docs_meta)
        
        # 然后流式返回答案
        async for token in llm_client.generate_stream(
            question=question,
            context_docs=docs
        ):
            yield ("token", token)
            
    except Exception as e:
        logger.error(f"Stream RAG error: {str(e)}")
        yield ("error", get_friendly_error(str(e)))


@router.post("/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """
    智能问答流式接口。

    接收用户问题，经 RAG 流程处理后返回流式答案。

    Args:
        request: 聊天完成请求

    Returns:
        StreamingResponse: SSE 流式响应
    """
    try:
        question = extract_question(request.messages)

        if not question:
            return StreamingResponse(
                content=iter(["event: error\ndata: {\"message\": \"请输入您的问题\"}\n\n"]),
                media_type="text/event-stream"
            )

        logger.info(f"Chat completions request: {question[:50]}...")

        if request.stream:
            # 流式响应
            async def generate_sse():
                chat_id = f"chatcmpl-{uuid.uuid4().hex}"
                created = int(time.time())
                
                async for item_type, data in stream_rag_with_context(question):
                    if item_type == "docs":
                        # 发送文档元数据作为特殊事件
                        event_data = json.dumps({"docs": data}, ensure_ascii=False)
                        yield f"event: context_docs\ndata: {event_data}\n\n"
                    
                    elif item_type == "token":
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

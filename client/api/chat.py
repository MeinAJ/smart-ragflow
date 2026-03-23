"""
问答流式接口模块。

实现 POST /v1/chat/completions 接口，支持 SSE 流式输出。
"""

import logging
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from client.core.graph import stream_rag_answer
from client.utils.sse import openai_sse_stream

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
    question = extract_question(request.messages)

    if not question:
        return StreamingResponse(
            content=iter(["data: {\"error\": \"No user message found\"}\n\n"]),
            media_type="text/event-stream"
        )

    logger.info(f"Chat completions request: {question[:50]}...")

    if request.stream:
        # 流式响应
        content_stream = stream_rag_answer(question)
        sse_stream = openai_sse_stream(
            content_iterator=content_stream,
            model=request.model
        )

        return StreamingResponse(
            content=sse_stream,
            media_type="text/event-stream"
        )
    else:
        # TODO: 实现非流式响应
        # 非流式响应需要调用 rag_graph 执行完整流程
        from client.core.graph import rag_graph
        from client.core.state import GraphState
        import time
        import uuid

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

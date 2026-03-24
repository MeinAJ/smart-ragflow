"""
SSE 流式响应辅助函数模块。

提供符合 OpenAI API 规范的 SSE 流式响应格式化功能。
"""

import json
import logging
from typing import AsyncIterator

logger = logging.getLogger(__name__)


def format_sse_event(data: dict) -> str:
    """
    格式化 SSE 事件数据。

    Args:
        data: 事件数据字典

    Returns:
        str: 格式化后的 SSE 事件字符串
    """
    json_data = json.dumps(data, ensure_ascii=False)
    return f"data: {json_data}\n\n"


async def openai_sse_stream(
    content_iterator: AsyncIterator[str],
    model: str = "gpt-3.5-turbo",
    message_id: str = None
) -> AsyncIterator[str]:
    """
    将内容流转换为 OpenAI 风格的 SSE 流。

    Args:
        content_iterator: 内容异步迭代器
        model: 模型名称
        message_id: 消息 ID

    Yields:
        str: SSE 格式的事件字符串
    """
    import uuid
    
    message_id = message_id or f"chatcmpl-{uuid.uuid4().hex}"
    created = int(__import__('time').time())
    
    # 发送起始事件（role）
    start_chunk = {
        "id": message_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {"role": "assistant"},
                "finish_reason": None
            }
        ]
    }
    yield format_sse_event(start_chunk)
    
    # 发送内容事件
    async for content in content_iterator:
        content_chunk = {
            "id": message_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": model,
            "choices": [
                {
                    "index": 0,
                    "delta": {"content": content},
                    "finish_reason": None
                }
            ]
        }
        yield format_sse_event(content_chunk)
    
    # 发送结束事件
    end_chunk = {
        "id": message_id,
        "object": "chat.completion.chunk",
        "created": created,
        "model": model,
        "choices": [
            {
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }
        ]
    }
    yield format_sse_event(end_chunk)
    
    # 发送 [DONE] 标记
    yield "data: [DONE]\n\n"


async def simple_sse_stream(
    content_iterator: AsyncIterator[str]
) -> AsyncIterator[str]:
    """
    简单 SSE 流，只返回内容文本。

    Args:
        content_iterator: 内容异步迭代器

    Yields:
        str: SSE 格式的事件字符串
    """
    async for content in content_iterator:
        data = {"choices": [{"delta": {"content": content}}]}
        yield format_sse_event(data)
    
    yield "data: [DONE]\n\n"

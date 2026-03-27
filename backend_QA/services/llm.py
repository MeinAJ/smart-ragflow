"""
LLM (大语言模型) 服务客户端模块。

本模块提供与 LLM 服务交互的功能，支持：
- 标准请求（非流式）
- 流式请求（SSE）
- 上下文构建（RAG）
- 对话历史处理

兼容 OpenAI API 格式，支持多种后端（OpenAI、DeepSeek、Azure 等）。

使用示例:
    >>> from backend_QA.services.llm import llm_client
    >>> 
    >>> # 标准请求
    >>> answer = await llm_client.generate(
    ...     question="什么是 RAG？",
    ...     context_docs=[{"content": "RAG 是..."}]
    ... )
    >>> 
    >>> # 流式请求
    >>> async for token in llm_client.generate_stream(
    ...     question="什么是 RAG？",
    ...     context_docs=docs
    ... ):
    ...     print(token, end="")

配置说明:
    通过环境变量配置 LLM 服务:
    - OPENAI_API_KEY: API 密钥
    - OPENAI_BASE_URL: 服务地址
    - OPENAI_MODEL: 模型名称
    - LLM_REQUEST_TIMEOUT: 请求超时（秒）

Prompt 设计:
    系统使用精心设计的 Prompt 模板来引导 LLM 生成高质量答案：
    - 包含系统角色定义
    - 提供检索到的上下文
    - 要求引用来源
    - 限制回答风格
"""

import logging
from typing import List, Dict, Any, Optional, AsyncIterator

import httpx

from backend_common.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """
    LLM 服务客户端。
    
    提供与 OpenAI 兼容 API 的交互，支持流式和非流式两种模式。
    
    Attributes:
        client: HTTP 异步客户端
        api_key: API 密钥
        base_url: API 基础地址
        model: 使用的模型名称
        timeout: 请求超时时间
    """
    
    # 系统 Prompt 模板
    SYSTEM_PROMPT = """你是一个智能助手，基于提供的参考资料回答用户问题。

要求：
1. 仅基于提供的参考资料回答，不要添加外部知识
2. 如果参考资料不足以回答问题，请明确说明
3. 回答应准确、简洁、有帮助
4. 适当引用参考资料的来源

参考资料：
{context}
"""

    def __init__(self):
        """初始化 LLM 客户端。"""
        self.client = httpx.AsyncClient(timeout=settings.LLM_REQUEST_TIMEOUT)
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_BASE_URL.rstrip('/')
        self.model = settings.OPENAI_MODEL
        self.timeout = settings.LLM_REQUEST_TIMEOUT
        
        logger.info(
            f"LLMClient 初始化: "
            f"base_url={self.base_url}, "
            f"model={self.model}"
        )
    
    def _build_messages(
        self,
        question: str,
        context_docs: List[Dict[str, Any]],
        history_messages: Optional[List[Dict[str, str]]] = None
    ) -> List[Dict[str, str]]:
        """
        构建请求的消息列表。
        
        消息格式遵循 OpenAI Chat API 规范：
        - system: 系统提示词，定义助手行为
        - user: 用户输入
        - assistant: 助手回复（历史记录）
        
        Args:
            question: 当前用户问题
            context_docs: 检索到的参考文档
            history_messages: 历史对话消息（可选）
            
        Returns:
            消息列表，可直接用于 API 请求
            
        Example:
            >>> messages = client._build_messages(
            ...     "什么是 RAG？",
            ...     [{"content": "RAG 是..."}],
            ...     [{"role": "user", "content": "你好"}]
            ... )
        """
        messages = []
        
        # 1. 系统消息：定义助手角色和行为
        if context_docs:
            # 格式化上下文文档
            context_parts = []
            for i, doc in enumerate(context_docs, 1):
                content = doc.get("content", "")
                title = doc.get("title", f"文档{i}")
                context_parts.append(f"[{i}] 《{title}》：{content}")
            
            context_text = "\n\n".join(context_parts)
            system_content = self.SYSTEM_PROMPT.format(context=context_text)
        else:
            system_content = "你是一个有帮助的助手。"
        
        messages.append({"role": "system", "content": system_content})
        
        # 2. 历史消息（如果有）
        if history_messages:
            # 限制历史消息长度，避免超出模型上下文
            max_history = 10  # 最多保留 10 轮对话
            recent_history = history_messages[-max_history:]
            messages.extend(recent_history)
        
        # 3. 当前问题
        messages.append({"role": "user", "content": question})
        
        logger.debug(f"构建消息列表: {len(messages)} 条消息")
        return messages
    
    async def generate(
        self,
        question: str,
        context_docs: List[Dict[str, Any]],
        history_messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.2
    ) -> str:
        """
        生成答案（非流式）。
        
        适用于不需要实时显示的场景，如后台任务。
        
        Args:
            question: 用户问题
            context_docs: 参考文档列表
            history_messages: 历史对话（可选）
            temperature: 采样温度，默认 0.2（更确定性）
            
        Returns:
            生成的答案文本
            
        Raises:
            LLMError: LLM 服务调用失败时抛出
            
        Example:
            >>> answer = await llm_client.generate(
            ...     question="什么是 RAG？",
            ...     context_docs=[{"content": "RAG 是检索增强生成..."}]
            ... )
            >>> print(answer)
            RAG（Retrieval-Augmented Generation）是一种...
        """
        messages = self._build_messages(question, context_docs, history_messages)
        
        logger.info(f"LLM 生成请求: model={self.model}, messages={len(messages)}")
        
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": False
                }
            )
            response.raise_for_status()
            
            result = response.json()
            answer = result["choices"][0]["message"]["content"]
            
            # 记录 token 使用情况
            usage = result.get("usage", {})
            logger.info(
                f"LLM 生成完成: "
                f"prompt_tokens={usage.get('prompt_tokens', 0)}, "
                f"completion_tokens={usage.get('completion_tokens', 0)}"
            )
            
            return answer.strip()
            
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM API HTTP 错误: {e.response.status_code} - {e.response.text}")
            raise LLMError(f"LLM 服务返回错误: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"LLM API 请求失败: {e}")
            raise LLMError(f"无法连接到 LLM 服务: {self.base_url}") from e
        except Exception as e:
            logger.exception(f"LLM 生成异常: {e}")
            raise LLMError(f"LLM 生成失败: {str(e)}") from e
    
    async def generate_stream(
        self,
        question: str,
        context_docs: List[Dict[str, Any]],
        history_messages: Optional[List[Dict[str, str]]] = None,
        temperature: float = 0.2
    ) -> AsyncIterator[str]:
        """
        流式生成答案。
        
        适用于需要实时显示答案的场景，如 Web 界面。
        使用 SSE (Server-Sent Events) 格式返回。
        
        Args:
            question: 用户问题
            context_docs: 参考文档列表
            history_messages: 历史对话（可选）
            temperature: 采样温度
            
        Yields:
            生成的文本片段
            
        Raises:
            LLMError: 流式请求失败时抛出
            
        Example:
            >>> async for token in llm_client.generate_stream(
            ...     question="什么是 RAG？",
            ...     context_docs=docs
            ... ):
            ...     print(token, end="", flush=True)
        """
        messages = self._build_messages(question, context_docs, history_messages)
        
        logger.info(f"LLM 流式生成请求: model={self.model}")
        
        try:
            async with self.client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "stream": True
                },
                timeout=self.timeout
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    line = line.strip()
                    
                    # SSE 格式: data: {...}
                    if line.startswith("data: "):
                        data = line[6:]
                        
                        # 流结束标记
                        if data == "[DONE]":
                            logger.info("LLM 流式生成完成")
                            break
                        
                        try:
                            import json
                            chunk = json.loads(data)
                            
                            # 提取增量内容
                            delta = chunk["choices"][0].get("delta", {})
                            content = delta.get("content", "")
                            
                            if content:
                                yield content
                                
                        except (json.JSONDecodeError, KeyError) as e:
                            logger.warning(f"解析 SSE 数据失败: {e}, data={data}")
                            continue
        
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM 流式请求 HTTP 错误: {e.response.status_code}")
            raise LLMError(f"LLM 服务返回错误: {e.response.status_code}") from e
        except httpx.RequestError as e:
            logger.error(f"LLM 流式请求失败: {e}")
            raise LLMError(f"无法连接到 LLM 服务") from e
        except Exception as e:
            logger.exception(f"LLM 流式生成异常: {e}")
            raise LLMError(f"流式生成失败: {str(e)}") from e
    
    async def close(self):
        """关闭 HTTP 客户端。"""
        await self.client.aclose()
        logger.info("LLMClient 已关闭")


class LLMError(Exception):
    """LLM 服务异常。"""
    pass


# 全局客户端实例
llm_client = LLMClient()

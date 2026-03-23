"""
LLM 服务客户端模块。

封装 OpenAI 兼容 API 调用，支持流式输出。
"""

import logging
from typing import AsyncIterator, List, Dict, Any, Optional
import httpx
from pydantic_settings import BaseSettings
from pydantic import Field

logger = logging.getLogger(__name__)


class LLMSettings(BaseSettings):
    """LLM 服务配置。"""
    OPENAI_API_KEY: str = Field(default="", validation_alias="OPENAI_API_KEY")
    OPENAI_BASE_URL: str = Field(default="https://api.openai.com/v1", validation_alias="OPENAI_BASE_URL")
    OPENAI_MODEL: str = Field(default="gpt-3.5-turbo", validation_alias="OPENAI_MODEL")
    REQUEST_TIMEOUT: float = Field(default=60.0, validation_alias="LLM_REQUEST_TIMEOUT")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = LLMSettings()


class LLMClient:
    """
    LLM 客户端（OpenAI 兼容 API）。

    支持同步和流式文本生成。
    """

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = None,
        timeout: float = None
    ):
        """
        初始化 LLM 客户端。

        Args:
            api_key: API 密钥
            base_url: API 基础地址
            model: 模型名称
            timeout: 请求超时时间
        """
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = base_url or settings.OPENAI_BASE_URL
        self.model = model or settings.OPENAI_MODEL
        self.timeout = timeout or settings.REQUEST_TIMEOUT
        self._client: httpx.AsyncClient = None

    async def _get_client(self) -> httpx.AsyncClient:
        """获取或创建 HTTP 客户端。"""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    def _build_messages(
        self,
        question: str,
        context_docs: List[Dict[str, Any]],
        system_prompt: str = None
    ) -> List[Dict[str, str]]:
        """
        构建 LLM 消息列表。

        Args:
            question: 用户问题
            context_docs: 上下文文档
            system_prompt: 系统提示词

        Returns:
            List[Dict]: 消息列表
        """
        if system_prompt is None:
            system_prompt = """你是一个智能助手，基于提供的参考资料回答用户问题。
请严格根据参考资料内容回答，如果参考资料不足以回答问题，请明确说明。
回答要简洁、准确、有条理。"""
        
        # 构建上下文
        context_text = "\n\n".join([
            f"[文档 {i+1}]\n{doc.get('content', '')}"
            for i, doc in enumerate(context_docs)
        ])
        
        user_prompt = f"""参考资料：
{context_text}

用户问题：{question}

请根据参考资料回答问题："""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        return messages

    async def generate_stream(
        self,
        question: str,
        context_docs: List[Dict[str, Any]],
        system_prompt: str = None,
        temperature: float = 0.7
    ) -> AsyncIterator[str]:
        """
        流式生成答案。

        Args:
            question: 用户问题
            context_docs: 上下文文档
            system_prompt: 系统提示词
            temperature: 采样温度

        Yields:
            str: 生成的文本片段
        """
        client = await self._get_client()
        messages = self._build_messages(question, context_docs, system_prompt)
        
        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True
        }
        
        try:
            logger.info(f"LLM stream generation started, model={self.model}")
            
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=request_body
            ) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line or line == "data: [DONE]":
                        continue
                    
                    if line.startswith("data: "):
                        data = line[6:]  # 去掉 "data: " 前缀
                        
                        # 解析 SSE 数据
                        import json
                        try:
                            chunk = json.loads(data)
                            delta = chunk.get("choices", [{}])[0].get("delta", {})
                            content = delta.get("content", "")
                            if content:
                                yield content
                        except json.JSONDecodeError:
                            continue
            
            logger.info("LLM stream generation completed")
            
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"LLM service error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"LLM generation error: {str(e)}")
            raise Exception(f"LLM generation failed: {str(e)}")

    async def generate(
        self,
        question: str,
        context_docs: List[Dict[str, Any]],
        system_prompt: str = None,
        temperature: float = 0.7
    ) -> str:
        """
        非流式生成答案。

        Args:
            question: 用户问题
            context_docs: 上下文文档
            system_prompt: 系统提示词
            temperature: 采样温度

        Returns:
            str: 生成的完整答案
        """
        client = await self._get_client()
        messages = self._build_messages(question, context_docs, system_prompt)
        
        request_body = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": False
        }
        
        try:
            logger.info(f"LLM generation started, model={self.model}")
            
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json=request_body
            )
            response.raise_for_status()
            
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            logger.info("LLM generation completed")
            return content
            
        except httpx.HTTPStatusError as e:
            logger.error(f"LLM HTTP error: {e.response.status_code} - {e.response.text}")
            raise Exception(f"LLM service error: {e.response.status_code}")
        except Exception as e:
            logger.error(f"LLM generation error: {str(e)}")
            raise Exception(f"LLM generation failed: {str(e)}")

    async def close(self):
        """关闭 HTTP 客户端。"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def __aenter__(self):
        """异步上下文管理器入口。"""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器退出。"""
        await self.close()


# 全局客户端实例
llm_client = LLMClient()

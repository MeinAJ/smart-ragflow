"""
LLM 服务客户端模块。

封装 OpenAI 兼容 API 调用，支持流式输出。
"""

import logging
from typing import AsyncIterator, List, Dict, Any, Optional
import httpx

from backend_common import settings

logger = logging.getLogger(__name__)


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
        self.timeout = timeout or settings.LLM_REQUEST_TIMEOUT
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
            context_docs: 上下文文档（包含 content, title, doc_url 等字段）
            system_prompt: 系统提示词

        Returns:
            List[Dict]: 消息列表
        """
        if system_prompt is None:
            system_prompt = """你是一个智能助手，基于提供的参考资料回答用户问题。

**重要规则：**
1. 请严格根据参考资料内容回答，如果参考资料不足以回答问题，请明确说明。
2. 回答要简洁、准确、有条理。
3. **必须在回答中标注数据来源**：当你引用某个文档的内容时，请在引用处使用 Markdown 链接格式标注来源，格式为 `[引用N](文档URL地址)`，其中 N 是文档编号（从1开始）。
4. 如果答案来自多个文档，请在相应段落分别标注来源。
5. 文档标题和 URL 信息已在参考资料中提供，请确保链接格式正确，以便前端可以渲染成可点击的链接。

**标注示例：**
- 单个来源：Java 内存模型定义了线程和主内存之间的抽象关系（[引用1](http://localhost:9000/rag-files/java-memory.pdf)）。
- 多个来源：垃圾回收器的选择对性能有重要影响（[引用1](http://localhost:9000/rag-files/jvm-perf.pdf)[引用3](http://localhost:9000/rag-files/g1-gc.pdf)），而 G1 垃圾回收器适用于大内存场景（[引用2](http://localhost:9000/rag-files/g1-details.pdf)）。

**注意：** 引用编号必须与参考资料中的 `[文档 N]` 编号对应。"""
        
        # 构建上下文，包含文档元数据（标题、URL）
        context_parts = []
        for i, doc in enumerate(context_docs):
            title = doc.get('title', '') or doc.get("metadata", {}).get('title', '') or f'文档 {i+1}'
            doc_url = doc.get('doc_url', '') or doc.get("metadata", {}).get('doc_url', '')
            content = doc.get('content', '')
            
            doc_header = f"[文档 {i+1}]"
            if title:
                doc_header += f" 标题: {title}"
            if doc_url:
                doc_header += f"\nURL: {doc_url}"
            
            context_parts.append(f"{doc_header}\n{content}")
        
        context_text = "\n\n---\n\n".join(context_parts)
        
        user_prompt = f"""参考资料：

{context_text}

---

用户问题：{question}

请根据以上参考资料回答问题。记得在引用文档内容时使用 Markdown 链接格式标注来源，格式为 `[引用N](文档URL地址)`，这样用户可以直接点击链接访问原始文档。"""
        
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

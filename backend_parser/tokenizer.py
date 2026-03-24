"""
Tokenizer 模块。

提供业界标准的 LLM token 计算方式。
"""

import logging
from typing import List, Optional

logger = logging.getLogger(__name__)


class TokenCounter:
    """
    Token 计数器。

    支持多种业界常用 tokenizer：
    - tiktoken: OpenAI GPT 系列 (cl100k_base, p50k_base 等)
    - transformers: Hugging Face 模型 tokenizer
    - 简单估算: 字符数/4 作为 fallback
    """

    # 常用 tokenizer 映射
    ENCODING_MAP = {
        "gpt-4": "cl100k_base",
        "gpt-3.5-turbo": "cl100k_base",
        "text-embedding-ada-002": "cl100k_base",
        "text-embedding-3-small": "cl100k_base",
        "text-embedding-3-large": "cl100k_base",
        "bge-m3": "cl100k_base",  # BGE-M3 使用与 GPT 相似的 tokenizer
    }

    def __init__(self, encoding: str = "cl100k_base"):
        """
        初始化 TokenCounter。

        Args:
            encoding: tokenizer 名称或模型名称
        """
        self.encoding_name = self.ENCODING_MAP.get(encoding, encoding)
        self._encoder = None
        self._fallback_mode = False

    def _get_encoder(self):
        """获取或创建 encoder。"""
        if self._encoder is None and not self._fallback_mode:
            try:
                import tiktoken
                self._encoder = tiktoken.get_encoding(self.encoding_name)
                logger.info(f"Using tiktoken encoder: {self.encoding_name}")
            except ImportError:
                logger.warning("tiktoken not installed, using fallback estimation")
                self._fallback_mode = True
            except Exception as e:
                logger.warning(f"Failed to load tiktoken encoder: {e}, using fallback")
                self._fallback_mode = True
        return self._encoder

    def count_tokens(self, text: str) -> int:
        """
        计算文本的 token 数量。

        Args:
            text: 输入文本

        Returns:
            int: token 数量
        """
        if not text:
            return 0

        encoder = self._get_encoder()

        if encoder:
            try:
                tokens = encoder.encode(text)
                return len(tokens)
            except Exception as e:
                logger.debug(f"Tokenization failed: {e}, using fallback")

        # Fallback: 简单估算
        # 英文约 4 字符/token，中文约 1-2 字符/token
        # 这里使用混合估算：总字符数 / 3.5
        return max(1, int(len(text) / 3.5))

    def count_tokens_batch(self, texts: List[str]) -> List[int]:
        """
        批量计算 token 数量。

        Args:
            texts: 文本列表

        Returns:
            List[int]: token 数量列表
        """
        return [self.count_tokens(text) for text in texts]

    def truncate_text(self, text: str, max_tokens: int) -> str:
        """
        按最大 token 数截断文本。

        Args:
            text: 输入文本
            max_tokens: 最大 token 数

        Returns:
            str: 截断后的文本
        """
        if not text:
            return text

        encoder = self._get_encoder()

        if encoder:
            try:
                tokens = encoder.encode(text)
                if len(tokens) <= max_tokens:
                    return text
                truncated_tokens = tokens[:max_tokens]
                return encoder.decode(truncated_tokens)
            except Exception as e:
                logger.debug(f"Truncate failed: {e}, using fallback")

        # Fallback: 按字符估算截断
        estimated_chars = int(max_tokens * 3.5)
        return text[:estimated_chars]

    def get_token_ids(self, text: str) -> List[int]:
        """
        获取文本的 token ID 列表。

        Args:
            text: 输入文本

        Returns:
            List[int]: token ID 列表
        """
        if not text:
            return []

        encoder = self._get_encoder()

        if encoder:
            try:
                return encoder.encode(text)
            except Exception:
                pass

        return []


# 全局 token counter 实例（使用 cl100k_base，即 GPT-4/GPT-3.5 的 tokenizer）
token_counter = TokenCounter("cl100k_base")


# 便捷函数
def count_tokens(text: str) -> int:
    """
    计算文本 token 数量的便捷函数。

    Args:
        text: 输入文本

    Returns:
        int: token 数量
    """
    return token_counter.count_tokens(text)


def estimate_cost(text: str, price_per_1k_tokens: float = 0.0015) -> float:
    """
    估算文本处理成本（USD）。

    Args:
        text: 输入文本
        price_per_1k_tokens: 每 1000 tokens 的价格

    Returns:
        float: 估算成本（美元）
    """
    tokens = count_tokens(text)
    return (tokens / 1000) * price_per_1k_tokens

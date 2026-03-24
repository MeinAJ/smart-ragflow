"""
LangGraph 状态定义模块。

定义图执行过程中流转的状态数据结构。
"""

from typing import TypedDict, List, Optional


class GraphState(TypedDict):
    """
    智能问答流程的状态定义。

    Attributes:
        question: 原始问题
        question_vector: 向量化结果（1024维向量）
        retrieved_docs: 检索到的文档块（带文本、元数据、分数）
        reranked_docs: MMR 重排序后的文档块
        answer: 最终生成的答案（流式时可能不存储完整内容）
        error: 错误信息
    """
    question: str
    question_vector: List[float]
    retrieved_docs: List[dict]
    reranked_docs: List[dict]
    answer: Optional[str]
    error: Optional[str]

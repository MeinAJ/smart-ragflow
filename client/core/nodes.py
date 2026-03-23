"""
LangGraph 节点函数模块。

实现 RAG 流程的各个节点：向量化、检索、重排序、生成。
"""

import logging
from typing import Dict, Any

from client.core.state import GraphState
from client.services.embedding import embedding_client
from client.services.opensearch import opensearch_client
from client.services.mmr import mmr_rerank
from client.services.llm import llm_client

logger = logging.getLogger(__name__)


async def vectorize_node(state: GraphState) -> Dict[str, Any]:
    """
    向量化节点：将问题转换为向量。

    Args:
        state: 当前状态

    Returns:
        Dict: 更新后的状态片段
    """
    try:
        question = state.get("question", "")
        if not question:
            return {"error": "Empty question"}

        logger.info(f"Vectorize node: {question}...")

        # 调用 embedding 服务
        vector = await embedding_client.embed(question)

        return {"question_vector": vector}

    except Exception as e:
        logger.error(f"Vectorize node error: {str(e)}")
        return {"error": f"Vectorization failed: {str(e)}"}


async def retrieve_node(state: GraphState) -> Dict[str, Any]:
    """
    检索节点：执行混合检索（BM25 + 向量）。

    Args:
        state: 当前状态

    Returns:
        Dict: 更新后的状态片段
    """
    try:
        question = state.get("question", "")
        vector = state.get("question_vector", [])

        if not question or not vector:
            return {"error": "Missing question or vector"}

        logger.info(f"Retrieve node: question='{question[:50]}...'")

        # 执行混合检索
        docs = await opensearch_client.hybrid_search(
            query_text=question,
            query_vector=vector,
            size=10
        )

        return {"retrieved_docs": docs}

    except Exception as e:
        logger.error(f"Retrieve node error: {str(e)}")
        return {"error": f"Retrieval failed: {str(e)}"}


async def rerank_node(state: GraphState) -> Dict[str, Any]:
    """
    重排序节点：执行 MMR 重排序。

    Args:
        state: 当前状态

    Returns:
        Dict: 更新后的状态片段
    """
    try:
        docs = state.get("retrieved_docs", [])
        vector = state.get("question_vector", [])

        if not docs:
            return {"reranked_docs": []}

        logger.info(f"Rerank node: {len(docs)} documents")

        # 执行 MMR 重排序
        reranked = mmr_rerank(
            query_vector=vector,
            documents=docs,
            lambda_param=0.7,
            top_k=5
        )

        return {"reranked_docs": reranked}

    except Exception as e:
        logger.error(f"Rerank node error: {str(e)}")
        return {"error": f"Reranking failed: {str(e)}"}


async def generate_node(state: GraphState) -> Dict[str, Any]:
    """
    生成节点：调用 LLM 生成答案（非流式）。

    注：流式输出在 API 层处理，节点本身返回完整结果。

    Args:
        state: 当前状态

    Returns:
        Dict: 更新后的状态片段
    """
    try:
        question = state.get("question", "")
        docs = state.get("reranked_docs", [])

        if not docs:
            return {"answer": "未找到相关参考资料，无法回答问题。"}

        logger.info(f"Generate node: {len(docs)} context docs")

        # 调用 LLM 生成答案
        answer = await llm_client.generate(
            question=question,
            context_docs=docs
        )

        return {"answer": answer}

    except Exception as e:
        logger.error(f"Generate node error: {str(e)}")
        return {"error": f"Generation failed: {str(e)}"}


def error_handler(state: GraphState) -> Dict[str, Any]:
    """
    错误处理节点：处理执行过程中的错误。

    Args:
        state: 当前状态

    Returns:
        Dict: 包含错误信息的状态
    """
    error = state.get("error", "Unknown error")
    logger.error(f"Graph execution error: {error}")
    return {"answer": f"处理过程中出现错误: {error}"}


def should_continue(state: GraphState) -> str:
    """
    路由函数：判断是否继续执行或跳转到错误处理。

    Args:
        state: 当前状态

    Returns:
        str: 下一个节点的名称
    """
    if state.get("error"):
        return "error_handler"
    return "continue"

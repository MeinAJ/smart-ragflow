"""
LangGraph 工作流定义模块。

定义 RAG 流程的状态图结构。
"""

import logging
from typing import AsyncIterator

from langgraph.graph import StateGraph, END

from client.core.state import GraphState
from client.core.nodes import (
    vectorize_node,
    retrieve_node,
    rerank_node,
    generate_node,
    error_handler,
    should_continue
)
from client.services.llm import llm_client

logger = logging.getLogger(__name__)


def build_rag_graph():
    """
    构建 RAG 状态图。

    流程：vectorize -> retrieve -> rerank -> generate

    Returns:
        CompiledGraph: 编译后的图对象
    """
    workflow = StateGraph(GraphState)

    # 添加节点
    workflow.add_node("vectorize", vectorize_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("error_handler", error_handler)

    # 设置入口
    workflow.set_entry_point("vectorize")

    # 添加边和条件路由
    workflow.add_conditional_edges(
        "vectorize",
        should_continue,
        {
            "continue": "retrieve",
            "error_handler": "error_handler"
        }
    )
    
    workflow.add_conditional_edges(
        "retrieve",
        should_continue,
        {
            "continue": "rerank",
            "error_handler": "error_handler"
        }
    )
    
    workflow.add_conditional_edges(
        "rerank",
        should_continue,
        {
            "continue": "generate",
            "error_handler": "error_handler"
        }
    )
    
    workflow.add_edge("generate", END)
    workflow.add_edge("error_handler", END)

    return workflow.compile()


# 编译后的图实例
rag_graph = build_rag_graph()


async def stream_rag_answer(
    question: str
) -> AsyncIterator[str]:
    """
    流式生成 RAG 答案。

    按节点顺序执行，在生成阶段使用流式输出。

    Args:
        question: 用户问题

    Yields:
        str: 生成的文本片段
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
            yield f"错误: {state['error']}"
            return
        
        # 2. 检索
        logger.info("Stream RAG: Step 2 - Retrieve")
        from client.core.nodes import retrieve_node
        result = await retrieve_node(state)
        state.update(result)
        
        if state.get("error"):
            yield f"错误: {state['error']}"
            return
        
        # 3. 重排序
        logger.info("Stream RAG: Step 3 - Rerank")
        from client.core.nodes import rerank_node
        result = await rerank_node(state)
        state.update(result)
        
        if state.get("error"):
            yield f"错误: {state['error']}"
            return
        
        # 4. 流式生成
        logger.info("Stream RAG: Step 4 - Generate (streaming)")
        docs = state.get("reranked_docs", [])
        
        if not docs:
            yield "未找到相关参考资料，无法回答问题。"
            return
        
        async for token in llm_client.generate_stream(
            question=question,
            context_docs=docs
        ):
            yield token
            
    except Exception as e:
        logger.error(f"Stream RAG error: {str(e)}")
        yield f"处理过程中出现错误: {str(e)}"

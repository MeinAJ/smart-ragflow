"""
MMR (Maximal Marginal Relevance) 重排序算法模块。

本模块实现了 MMR 算法，用于在检索结果中平衡相关性和多样性，
避免返回内容高度相似的文档。

使用示例:
    >>> from backend_QA.services.mmr import mmr_rerank
    >>> query_vector = [0.1, 0.2, ...]
    >>> docs = [{"id": "doc1", "vector": [...], "content": "..."}, ...]
    >>> result = mmr_rerank(query_vector, docs, lambda_param=0.7, top_k=5)

算法原理:
    MMR 公式: MMR = λ * Sim(query, doc) - (1-λ) * max Sim(doc, selected)
    
    - λ (lambda_param): 多样性权重参数
        - λ = 1.0: 只考虑与查询的相关性，不考虑文档间多样性
        - λ = 0.0: 只考虑文档间多样性，不考虑查询相关性
        - λ = 0.5~0.7: 平衡相关性和多样性（推荐值）
    
    - Sim(query, doc): 查询与文档的相似度
    - max Sim(doc, selected): 文档与已选文档的最大相似度

应用场景:
    - 用户提问涉及多个方面时，返回覆盖不同角度的文档
    - 避免检索结果中重复内容过多
    - 提高答案的全面性和信息覆盖度

参考论文:
    Carbonell, J., & Goldstein, J. (1998). The use of MMR, diversity-based 
    reranking for reordering documents and producing summaries. 
    In SIGIR'98.
"""

import logging
from typing import List, Dict, Any
import numpy as np

logger = logging.getLogger(__name__)


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    计算两个向量的余弦相似度。
    
    余弦相似度衡量两个向量方向的相似程度，取值范围 [-1, 1]。
    在文本检索中，通常用于衡量查询与文档的语义相似度。
    
    公式: cos(θ) = (A·B) / (||A|| * ||B||)
    
    Args:
        vec1: 第一个向量
        vec2: 第二个向量
        
    Returns:
        余弦相似度值，范围 [-1, 1]
        
    Raises:
        ValueError: 输入向量维度不匹配或为零向量时抛出
        
    Example:
        >>> vec1 = [1.0, 0.0, 0.0]
        >>> vec2 = [0.9, 0.1, 0.0]
        >>> cosine_similarity(vec1, vec2)
        0.993...
    """
    if len(vec1) != len(vec2):
        raise ValueError(f"向量维度不匹配: {len(vec1)} vs {len(vec2)}")

    # 转换为 numpy 数组以提高计算效率
    v1 = np.array(vec1)
    v2 = np.array(vec2)

    # 计算向量的 L2 范数（长度）
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)

    # 处理零向量情况
    if norm1 == 0 or norm2 == 0:
        return 0.0

    # 计算余弦相似度
    return float(np.dot(v1, v2) / (norm1 * norm2))


def mmr_rerank(
        query_vector: List[float],
        documents: List[Dict[str, Any]],
        lambda_param: float = 0.7,
        top_k: int = 5
) -> List[Dict[str, Any]]:
    """
    使用 MMR 算法对检索结果进行重排序。
    
    该算法在保持高相关性的同时，增加结果的多样性，避免返回内容相似的文档。
    
    Args:
        query_vector: 查询向量，用于计算与文档的相似度
        documents: 候选文档列表，每个文档应包含 "vector" 字段（向量表示）
        lambda_param: 多样性权重参数，范围 [0, 1]，默认 0.7
            - 值越大越注重相关性，值越小越注重多样性
        top_k: 返回的文档数量，默认 5
        
    Returns:
        重排序后的文档列表，按 MMR 分数降序排列
        
    Raises:
        ValueError: 参数不合法时抛出（如 lambda_param 超出范围）
        
    Example:
        >>> query_vec = [1.0, 0.0, 0.0]
        >>> docs = [
        ...     {"id": "doc1", "vector": [0.9, 0.1, 0.0], "content": "RAG介绍"},
        ...     {"id": "doc2", "vector": [0.85, 0.15, 0.0], "content": "RAG详解"},
        ...     {"id": "doc3", "vector": [0.1, 0.9, 0.0], "content": "LLM基础"},
        ... ]
        >>> result = mmr_rerank(query_vec, docs, lambda_param=0.5, top_k=2)
        >>> # 结果会包含 doc1（最相关）和 doc3（多样性好），而非 doc2（与 doc1 相似）
        >>> [doc["id"] for doc in result]
        ['doc1', 'doc3']
        
    Note:
        - 输入文档列表会被复制，不会被修改
        - 如果文档数量少于 top_k，返回所有文档
        - 文档必须包含 "vector" 字段，否则会被跳过
    """
    # 参数校验
    if not 0 <= lambda_param <= 1:
        raise ValueError(f"lambda_param 必须在 [0, 1] 范围内，当前值: {lambda_param}")

    if not documents:
        logger.warning("MMR 重排序收到空文档列表")
        return []

    # 过滤掉没有向量的文档
    valid_docs = [
        doc for doc in documents
        if doc.get("metadata", {}).get("embedding", "") and len(doc.get("metadata", {}).get("embedding", "")) > 0
    ]

    if len(valid_docs) < len(documents):
        logger.warning(f"过滤了 {len(documents) - len(valid_docs)} 个无效文档（缺少向量）")

    if not valid_docs:
        logger.error("没有有效的文档可供重排序")
        return []

    # 限制返回数量
    if top_k > len(valid_docs):
        top_k = len(valid_docs)

    logger.info(f"MMR 重排序: {len(valid_docs)} 个文档，lambda={lambda_param}, top_k={top_k}")

    # 预计算查询与所有文档的相似度
    query_similarities = {}
    for doc in valid_docs:
        try:
            query_similarities[id(doc)] = cosine_similarity(query_vector, doc.get("metadata", {}).get("embedding", []))
        except Exception as e:
            logger.warning(f"计算查询与文档相似度失败: {e}")
            query_similarities[id(doc)] = 0.0

    selected: List[Dict[str, Any]] = []
    remaining = valid_docs.copy()

    # 贪心选择 top_k 个文档
    for i in range(top_k):
        if not remaining:
            break

        # 计算每个候选文档的 MMR 分数
        mmr_scores = []

        for doc in remaining:
            # 与查询的相似度（相关性）
            query_sim = query_similarities.get(id(doc), 0.0)

            # 与已选文档的最大相似度（冗余度）
            max_selected_sim = 0.0
            if selected:
                similarities = []
                for sel_doc in selected:
                    try:
                        sim = cosine_similarity(doc["vector"], sel_doc["vector"])
                        similarities.append(sim)
                    except Exception as e:
                        logger.debug(f"计算文档间相似度失败: {e}")
                        similarities.append(0.0)
                max_selected_sim = max(similarities) if similarities else 0.0

            # MMR 分数计算
            # λ * 相关性 - (1-λ) * 冗余度
            mmr_score = lambda_param * query_sim - (1 - lambda_param) * max_selected_sim
            mmr_scores.append((doc, mmr_score))

            logger.debug(
                f"文档 {doc.get('id', 'unknown')}: "
                f"query_sim={query_sim:.4f}, "
                f"max_selected_sim={max_selected_sim:.4f}, "
                f"mmr_score={mmr_score:.4f}"
            )

        # 选择 MMR 分数最高的文档
        best_doc, best_score = max(mmr_scores, key=lambda x: x[1])
        selected.append(best_doc)
        remaining.remove(best_doc)

        logger.info(
            f"第 {i + 1} 轮选择: doc_id={best_doc.get('id', 'unknown')}, "
            f"mmr_score={best_score:.4f}"
        )

    logger.info(f"MMR 重排序完成，返回 {len(selected)} 个文档")
    return selected


def mmr_rerank_with_scores(
        query_vector: List[float],
        documents: List[Dict[str, Any]],
        lambda_param: float = 0.7,
        top_k: int = 5
) -> List[tuple[Dict[str, Any], float]]:
    """
    使用 MMR 算法重排序，并返回分数。
    
    与 mmr_rerank 功能相同，但额外返回每个文档的 MMR 分数，
    便于调试和分析。
    
    Args:
        query_vector: 查询向量
        documents: 候选文档列表
        lambda_param: 多样性权重参数
        top_k: 返回文档数量
        
    Returns:
        元组列表，每个元组为 (文档, MMR分数)
        
    Example:
        >>> result = mmr_rerank_with_scores(query_vec, docs, top_k=3)
        >>> for doc, score in result:
        ...     print(f"{doc['id']}: {score:.4f}")
    """
    # 参数校验（与 mmr_rerank 相同）
    if not 0 <= lambda_param <= 1:
        raise ValueError(f"lambda_param 必须在 [0, 1] 范围内")

    if not documents:
        return []

    valid_docs = [doc for doc in documents if doc.get("vector")]

    if not valid_docs:
        return []

    if top_k > len(valid_docs):
        top_k = len(valid_docs)

    # 预计算相似度
    query_similarities = {
        id(doc): cosine_similarity(query_vector, doc["vector"])
        for doc in valid_docs
    }

    selected: List[tuple[Dict[str, Any], float]] = []
    remaining = valid_docs.copy()

    for _ in range(top_k):
        if not remaining:
            break

        mmr_scores = []

        for doc in remaining:
            query_sim = query_similarities.get(id(doc), 0.0)

            max_selected_sim = 0.0
            if selected:
                similarities = [
                    cosine_similarity(doc["vector"], sel_doc["vector"])
                    for sel_doc, _ in selected
                ]
                max_selected_sim = max(similarities)

            mmr_score = lambda_param * query_sim - (1 - lambda_param) * max_selected_sim
            mmr_scores.append((doc, mmr_score))

        best_doc, best_score = max(mmr_scores, key=lambda x: x[1])
        selected.append((best_doc, best_score))
        remaining.remove(best_doc)

    return selected

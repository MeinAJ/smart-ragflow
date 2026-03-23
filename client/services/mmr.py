"""
MMR（最大边际相关性）重排序模块。

实现 MMR 算法，在相关性和多样性之间取得平衡。
"""

import logging
from typing import List, Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field
import numpy as np

logger = logging.getLogger(__name__)


class MMRSettings(BaseSettings):
    """MMR 算法配置。"""
    MMR_LAMBDA: float = Field(default=0.7, validation_alias="MMR_LAMBDA")  # 多样性权重
    MMR_TOP_K: int = Field(default=5, validation_alias="MMR_TOP_K")       # 返回文档数

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


settings = MMRSettings()


def cosine_similarity(vec1: List[float], vec2: List[float]) -> float:
    """
    计算两个向量的余弦相似度。

    Args:
        vec1: 向量1
        vec2: 向量2

    Returns:
        float: 余弦相似度 [-1, 1]
    """
    v1 = np.array(vec1)
    v2 = np.array(vec2)
    
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(np.dot(v1, v2) / (norm1 * norm2))


def mmr_rerank(
    query_vector: List[float],
    documents: List[Dict[str, Any]],
    lambda_param: float = None,
    top_k: int = None
) -> List[Dict[str, Any]]:
    """
    使用 MMR 算法对文档进行重排序。

    MMR = λ * Sim(d, q) - (1-λ) * max(Sim(d, d_i))

    Args:
        query_vector: 查询向量
        documents: 文档列表，每个文档需包含 'embedding' 或 'vector' 字段
        lambda_param: 相关性权重（0-1，越大越注重相关性）
        top_k: 返回文档数量

    Returns:
        List[Dict]: 重排序后的文档列表
    """
    if not documents:
        return []
    
    lambda_param = lambda_param if lambda_param is not None else settings.MMR_LAMBDA
    top_k = top_k if top_k is not None else settings.MMR_TOP_K
    
    logger.info(f"MMR reranking: {len(documents)} docs, lambda={lambda_param}, top_k={top_k}")
    
    # 提取文档向量
    doc_vectors = []
    for doc in documents:
        vec = doc.get("embedding") or doc.get("vector")
        if vec is None:
            # 如果没有向量，使用零向量（会被排在后面）
            vec = [0.0] * len(query_vector)
        doc_vectors.append(vec)
    
    selected_indices = []
    remaining_indices = list(range(len(documents)))
    
    while len(selected_indices) < min(top_k, len(documents)):
        mmr_scores = []
        
        for idx in remaining_indices:
            # 计算与查询的相似度（相关性）
            relevance = cosine_similarity(doc_vectors[idx], query_vector)
            
            # 计算与已选文档的最大相似度（冗余度）
            if selected_indices:
                max_sim = max(
                    cosine_similarity(doc_vectors[idx], doc_vectors[s])
                    for s in selected_indices
                )
            else:
                max_sim = 0.0
            
            # MMR 分数
            mmr_score = lambda_param * relevance - (1 - lambda_param) * max_sim
            mmr_scores.append((idx, mmr_score))
        
        # 选择分数最高的文档
        best_idx, best_score = max(mmr_scores, key=lambda x: x[1])
        selected_indices.append(best_idx)
        remaining_indices.remove(best_idx)
        
        logger.debug(f"Selected doc {best_idx} with MMR score {best_score:.4f}")
    
    # 按选择顺序返回文档
    reranked = [documents[i] for i in selected_indices]
    
    # 添加 MMR 分数到文档
    for i, doc in enumerate(reranked):
        doc["mmr_rank"] = i + 1
    
    logger.info(f"MMR reranking completed, returned {len(reranked)} documents")
    return reranked

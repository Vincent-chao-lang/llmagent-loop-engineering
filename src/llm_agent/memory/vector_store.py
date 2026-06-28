"""
向量记忆存储系统 - 支持语义相似度搜索的记忆系统
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import numpy as np
from collections import deque


class SimilarityMetric(Enum):
    """相似度计算方法"""
    COSINE = "cosine"           # 余弦相似度
    EUCLIDEAN = "euclidean"     # 欧几里得距离
    DOT_PRODUCT = "dot_product" # 点积
    JACCARD = "jaccard"         # Jaccard相似度


@dataclass
class VectorMemoryItem:
    """向量记忆项"""
    id: str
    content: Any
    embedding: List[float]           # 向量嵌入
    timestamp: datetime
    importance: float = 0.5
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class VectorMemoryStore:
    """
    向量记忆存储系统

    基于向量嵌入的智能记忆检索，大幅提升检索效率。
    """

    def __init__(
        self,
        embedding_dimension: int = 1536,  # 默认OpenAI ada维度
        similarity_threshold: float = 0.7,
        max_memories: int = 10000
    ):
        """初始化向量记忆存储

        Args:
            embedding_dimension: 嵌入向量维度
            similarity_threshold: 相似度阈值
            max_memories: 最大记忆数量
        """
        self.embedding_dimension = embedding_dimension
        self.similarity_threshold = similarity_threshold
        self.max_memories = max_memories

        # 记忆存储
        self.memories: Dict[str, VectorMemoryItem] = {}

        # 向量索引（简化版，生产环境可用FAISS）
        self.vector_index: List[tuple[str, np.ndarray]] = []

    async def store_with_embedding(
        self,
        content: Any,
        embedding: List[float],
        importance: float = 0.5,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> str:
        """存储带向量嵌入的记忆

        Args:
            content: 记忆内容
            embedding: 向量嵌入
            importance: 重要性评分
            tags: 标签列表
            metadata: 元数据

        Returns:
            str: 记忆ID
        """
        # 生成记忆ID
        memory_id = self._generate_memory_id(content, embedding)

        # 创建记忆项
        memory_item = VectorMemoryItem(
            id=memory_id,
            content=content,
            embedding=np.array(embedding),
            timestamp=datetime.now(),
            importance=importance,
            tags=tags or [],
            metadata=metadata or {}
        )

        # 存储记忆
        self.memories[memory_id] = memory_item

        # 添加到向量索引
        self.vector_index.append((memory_id, memory_item.embedding))

        # 检查是否需要清理（FIFO）
        if len(self.memories) > self.max_memories:
            await self._remove_oldest()

        return memory_id

    async def similarity_search(
        self,
        query: str,
        query_embedding: List[float],
        top_k: int = 5,
        similarity_threshold: float = None
    ) -> List[VectorMemoryItem]:
        """相似度搜索

        Args:
            query: 查询内容
            query_embedding: 查询向量
            top_k: 返回top-k结果
            similarity_threshold: 相似度阈值

        Returns:
            List[VectorMemoryItem]: 相似记忆列表
        """
        if not self.vector_index:
            return []

        threshold = similarity_threshold or self.similarity_threshold
        query_vector = np.array(query_embedding)

        # 计算相似度
        similarities = []
        for memory_id, embedding in self.vector_index:
            similarity = self._calculate_similarity(query_vector, embedding)
            if similarity >= threshold:
                similarities.append((memory_id, similarity))

        # 按相似度排序，取top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        top_similarities = similarities[:top_k]

        # 返回记忆项
        results = []
        for memory_id, similarity in top_similarities:
            if memory_id in self.memories:
                memory = self.memories[memory_id]
                memory.access_count += 1
                results.append(memory)

        return results

    def _calculate_similarity(self, vec1: np.ndarray, vec2: np.ndarray) -> float:
        """计算向量相似度（余弦相似度）

        Args:
            vec1: 第一个向量
            vec2: 第二个向量

        Returns:
            float: 相似度（0-1）
        """
        # 余弦相似度
        dot_product = np.dot(vec1, vec2)
        norm = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        return dot_product / norm if norm > 0 else 0

    async def _generate_embedding(self, text: str) -> List[float]:
        """生成文本嵌入（模拟实现）

        Args:
            text: 输入文本

        Returns:
            List[float]: 嵌入向量
        """
        # 模拟实现：基于文本hash生成伪嵌入
        # 生产环境应该使用真实的嵌入模型
        text_hash = hashlib.md5(text.encode()).hexdigest()
        # 将hash转换为向量
        vector = [float(ord(c) / 255.0) for c in text_hash[:self.embedding_dimension]]
        # 补齐或截断到目标维度
        if len(vector) < self.embedding_dimension:
            vector.extend([0.0] * (self.embedding_dimension - len(vector)))
        else:
            vector = vector[:self.embedding_dimension]

        return vector

    async def _remove_oldest(self):
        """移除最旧的记忆"""
        if not self.memories:
            return

        # 按时间排序，移除最旧的
        sorted_memories = sorted(
            self.memories.items(),
            key=lambda x: x[1].timestamp
        )

        # 移除最旧的10%
        to_remove = len(sorted_memories) // 10 + 1
        for memory_id, _ in sorted_memories[:to_remove]:
            if memory_id in self.memories:
                del self.memories[memory_id]

        # 重建向量索引
        self._rebuild_index()

    def _rebuild_index(self):
        """重建向量索引"""
        self.vector_index = [
            (mid, memory.embedding)
            for mid, memory in self.memories.items()
        ]

    def _generate_memory_id(self, content: Any, embedding: List[float]) -> str:
        """生成记忆ID

        Args:
            content: 记忆内容
            embedding: 嵌入向量

        Returns:
            str: 记忆ID
        """
        # 基于内容和嵌入的确定性ID
        content_str = str(content)[:100]  # 限制长度
        embedding_str = str(embedding[:10])  # 嵌入的前几个元素
        combined = f"{content_str}:{embedding_str}"
        return hashlib.md5(combined.encode()).hexdigest()

    async def get_memory_by_id(self, memory_id: str) -> Optional[VectorMemoryItem]:
        """通过ID获取记忆

        Args:
            memory_id: 记忆ID

        Returns:
            VectorMemoryItem: 记忆项或None
        """
        return self.memories.get(memory_id)

    async def update_importance(self, memory_id: str, new_importance: float):
        """更新记忆重要性

        Args:
            memory_id: 记忆ID
            new_importance: 新的重要性值
        """
        if memory_id in self.memories:
            self.memories[memory_id].importance = new_importance

    async def get_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息

        Returns:
            Dict: 统计信息
        """
        if not self.memories:
            return {
                "total_memories": 0,
                "vector_index_size": 0,
                "average_importance": 0
            }

        total_importance = sum(m.importance for m in self.memories.values())
        avg_importance = total_importance / len(self.memories)

        return {
            "total_memories": len(self.memories),
            "vector_index_size": len(self.vector_index),
            "max_memories": self.max_memories,
            "average_importance": avg_importance
        }

    async def clear(self):
        """清空所有记忆"""
        self.memories.clear()
        self.vector_index.clear()

    async def batch_store(self, items: List[Dict[str, Any]]) -> List[str]:
        """批量存储记忆

        Args:
            items: 记忆项列表

        Returns:
            List[str]: 存储的记忆ID列表
        """
        memory_ids = []
        for item in items:
            memory_id = await self.store_with_embedding(
                content=item.get("content"),
                embedding=item.get("embedding", []),
                importance=item.get("importance", 0.5),
                tags=item.get("tags", []),
                metadata=item.get("metadata", {})
            )
            memory_ids.append(memory_id)

        return memory_ids


# 工厂函数
def create_vector_memory_store(
    embedding_dimension: int = 1536,
    similarity_threshold: float = 0.7,
    max_memories: int = 10000
) -> VectorMemoryStore:
    """创建向量记忆存储

    Args:
        embedding_dimension: 嵌入向量维度
        similarity_threshold: 相似度阈值
        max_memories: 最大记忆数量

    Returns:
        VectorMemoryStore: 向量存储实例
    """
    return VectorMemoryStore(
        embedding_dimension=embedding_dimension,
        similarity_threshold=similarity_threshold,
        max_memories=max_memories
    )
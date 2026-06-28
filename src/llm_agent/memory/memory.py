"""
LLM Agent记忆系统

提供短期、长期和工作记忆的完整实现。
"""

import asyncio
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import deque
import uuid


@dataclass
class MemoryConfig:
    """记忆配置"""
    short_term_capacity: int = 100      # 短期记忆容量
    long_term_capacity: int = 1000      # 长期记忆容量
    working_memory_capacity: int = 10   # 工作记忆容量
    memory_ttl_hours: int = 24          # 记忆过期时间（小时）


@dataclass
class MemoryItem:
    """记忆项"""
    id: str
    content: Any
    timestamp: datetime
    importance: float = 0.5
    access_count: int = 0
    tags: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None


class Memory:
    """LLM Agent记忆系统

    提供三种类型的记忆：
    - 短期记忆：最近的对话和事件
    - 长期记忆：重要的经验和知识
    - 工作记忆：当前任务的相关信息
    """

    def __init__(self, config: MemoryConfig):
        """初始化记忆系统

        Args:
            config: 记忆配置
        """
        self.config = config

        # 短期记忆：使用队列，FIFO策略
        self.short_term = deque(maxlen=config.short_term_capacity)

        # 长期记忆：使用列表+重要性排序
        self.long_term = []

        # 工作记忆：当前任务相关的临时信息
        self.working_memory = {}

    async def retrieve(self, query: str) -> Dict:
        """检索相关记忆

        Args:
            query: 查询内容

        Returns:
            相关记忆的上下文
        """
        # 1. 从工作记忆中检索
        working_results = self._search_working(query)

        # 2. 从短期记忆中检索
        short_term_results = self._search_short_term(query)

        # 3. 从长期记忆中检索
        long_term_results = await self._search_long_term(query)

        return {
            "working": working_results,
            "short_term": short_term_results,
            "long_term": long_term_results
        }

    async def store(self, experience: Dict) -> str:
        """存储新经验

        Args:
            experience: 要存储的经验

        Returns:
            记忆ID
        """
        # 创建记忆项
        memory_item = MemoryItem(
            id=str(uuid.uuid4()),
            content=experience,
            timestamp=datetime.now(),
            importance=await self._assess_importance(experience)
        )

        # 根据重要性决定存储策略
        if memory_item.importance > 0.7:
            # 重要经验存入长期记忆
            await self._store_long_term(memory_item)
        else:
            # 普通经验存入短期记忆
            self._store_short_term(memory_item)

        return memory_item.id

    async def get_recent(self, k: int = 5) -> List[MemoryItem]:
        """获取最近的记忆

        Args:
            k: 返回的记忆数量

        Returns:
            最近的k个记忆项
        """
        return list(self.short_term)[-k:]

    def clear_working_memory(self):
        """清空工作记忆"""
        self.working_memory.clear()

    def add_to_working_memory(self, key: str, value: Any):
        """添加到工作记忆

        Args:
            key: 键
            value: 值
        """
        self.working_memory[key] = value

    # === 私有方法 ===

    def _search_working(self, query: str) -> Dict[str, Any]:
        """搜索工作记忆"""
        if not self.working_memory:
            return {}

        # 简化的匹配逻辑
        results = {}
        query_lower = query.lower()

        for key, value in self.working_memory.items():
            if query_lower in str(value).lower() or query_lower in key.lower():
                results[key] = value

        return results

    def _search_short_term(self, query: str) -> List[Dict]:
        """搜索短期记忆"""
        results = []
        query_lower = query.lower()

        for memory_item in self.short_term:
            content_str = str(memory_item.content).lower()
            if query_lower in content_str:
                results.append({
                    "id": memory_item.id,
                    "content": memory_item.content,
                    "timestamp": memory_item.timestamp,
                    "importance": memory_item.importance
                })

        return results

    async def _search_long_term(self, query: str) -> List[Dict]:
        """搜索长期记忆"""
        results = []
        query_lower = query.lower()

        for memory_item in self.long_term:
            content_str = str(memory_item.content).lower()
            if query_lower in content_str:
                results.append({
                    "id": memory_item.id,
                    "content": memory_item.content,
                    "timestamp": memory_item.timestamp,
                    "importance": memory_item.importance
                })

        # 按重要性排序
        results.sort(key=lambda x: x["importance"], reverse=True)

        return results

    def _store_short_term(self, memory_item: MemoryItem):
        """存储到短期记忆"""
        self.short_term.append(memory_item)

    async def _store_long_term(self, memory_item: MemoryItem):
        """存储到长期记忆"""
        self.long_term.append(memory_item)

        # 如果超过容量，删除最不重要的记忆
        if len(self.long_term) > self.config.long_term_capacity:
            self.long_term.sort(key=lambda x: x.importance, reverse=True)
            self.long_term = self.long_term[:self.config.long_term_capacity]

    async def _assess_importance(self, experience: Dict) -> float:
        """评估经验的重要性

        Args:
            experience: 要评估的经验

        Returns:
            重要性分数 (0.0-1.0)
        """
        # 简化的重要性评估逻辑
        importance = 0.5  # 默认中等重要性

        content = str(experience.get("content", ""))

        # 包含错误或失败的信息更重要
        if any(keyword in content.lower() for keyword in
               ["错误", "失败", "error", "fail", "问题"]):
            importance += 0.3

        # 包含成功或完成的信息也较重要
        if any(keyword in content.lower() for keyword in
               ["成功", "完成", "success", "完成", "解决"]):
            importance += 0.2

        # 包含数字或数据的信息稍重要
        if any(char.isdigit() for char in content):
            importance += 0.1

        return min(importance, 1.0)  # 确保不超过1.0

    def get_stats(self) -> Dict[str, Any]:
        """获取记忆统计信息"""
        return {
            "short_term_count": len(self.short_term),
            "long_term_count": len(self.long_term),
            "working_memory_count": len(self.working_memory),
            "short_term_capacity": self.config.short_term_capacity,
            "long_term_capacity": self.config.long_term_capacity
        }


class SimpleMemory:
    """简化版记忆系统

    用于快速原型开发
    """

    def __init__(self, max_items: int = 50):
        """初始化简化记忆系统

        Args:
            max_items: 最大记忆数量
        """
        self.max_items = max_items
        self.memories = []

    async def retrieve(self, query: str) -> Dict:
        """检索相关记忆"""
        query_lower = query.lower()

        # 简单的关键词匹配
        results = [
            memory for memory in self.memories
            if query_lower in str(memory).lower()
        ]

        return {
            "long_term": results[:5],
            "short_term": [],
            "working": {}
        }

    async def store(self, experience: Dict) -> str:
        """存储新经验"""
        memory_id = str(uuid.uuid4())

        self.memories.append({
            "id": memory_id,
            "content": experience,
            "timestamp": datetime.now()
        })

        # 超过容量时删除最旧的
        if len(self.memories) > self.max_items:
            self.memories = self.memories[-self.max_items:]

        return memory_id

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_memories": len(self.memories),
            "max_capacity": self.max_items
        }

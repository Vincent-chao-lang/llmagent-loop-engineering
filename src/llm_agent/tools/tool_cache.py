"""
智能工具缓存系统 - 提供高效的工具执行结果缓存
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json


class CacheStrategy(Enum):
    """缓存策略"""
    LRU = "lru"                    # 最近最少使用
    LFU = "lfu"                    # 最少使用频率
    TTL = "ttl"                    # 生存时间
    ADAPTIVE = "adaptive"          # 自适应策略


@dataclass
class CacheEntry:
    """缓存条目"""
    key: str
    value: Any
    hit_count: int = 0
    created_at: datetime = field(default_factory=datetime.now)
    last_accessed: datetime = field(default_factory=datetime.now)
    ttl: Optional[int] = None  # 生存时间（秒）
    access_frequency: float = 1.0  # 访问频率

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl is None:
            return False
        return (datetime.now() - self.created_at).total_seconds() > self.ttl

    def update_access(self):
        """更新访问信息"""
        self.hit_count += 1
        self.last_accessed = datetime.now()
        # 简单的频率计算
        age_hours = (datetime.now() - self.created_at).total_seconds() / 3600
        self.access_frequency = self.hit_count / max(age_hours, 0.1)


class CacheBackend:
    """缓存后端接口"""

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        raise NotImplementedError

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存值"""
        raise NotImplementedError

    async def delete(self, key: str):
        """删除缓存值"""
        raise NotImplementedError

    async def clear(self):
        """清空缓存"""
        raise NotImplementedError

    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        raise NotImplementedError


class MemoryCacheBackend(CacheBackend):
    """内存缓存后端"""

    def __init__(self, max_size: int = 1000):
        """初始化内存缓存

        Args:
            max_size: 最大缓存条目数
        """
        self.max_size = max_size
        self.cache: Dict[str, CacheEntry] = {}
        self.access_order: List[str] = []

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key not in self.cache:
            return None

        entry = self.cache[key]

        # 检查是否过期
        if entry.is_expired():
            await self.delete(key)
            return None

        # 更新访问信息
        entry.update_access()
        self._update_access_order(key)

        return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """设置缓存值"""
        # 如果缓存已满，移除最少使用的条目
        if len(self.cache) >= self.max_size and key not in self.cache:
            await self._evict_lru()

        entry = CacheEntry(
            key=key,
            value=value,
            ttl=ttl
        )

        self.cache[key] = entry
        if key not in self.access_order:
            self.access_order.append(key)

    async def delete(self, key: str):
        """删除缓存值"""
        if key in self.cache:
            del self.cache[key]
            if key in self.access_order:
                self.access_order.remove(key)

    async def clear(self):
        """清空缓存"""
        self.cache.clear()
        self.access_order.clear()

    async def get_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        total_hits = sum(entry.hit_count for entry in self.cache.values())
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
            "hit_rate": total_hits / max(total_hits, 1),
            "access_order_length": len(self.access_order)
        }

    def _update_access_order(self, key: str):
        """更新访问顺序（用于LRU）"""
        if key in self.access_order:
            self.access_order.remove(key)
        self.access_order.append(key)

    async def _evict_lru(self):
        """驱逐最近最少使用的条目"""
        if not self.access_order:
            return

        # 移除最老的访问记录
        lru_key = self.access_order.pop(0)
        if lru_key in self.cache:
            del self.cache[lru_key]


class ToolCache:
    """
    智能工具缓存系统

    提供高效的工具执行结果缓存，支持多种策略和后端。
    """

    def __init__(
        self,
        backend: CacheBackend = None,
        strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
        default_ttl: int = 3600  # 默认1小时TTL
    ):
        """初始化工具缓存

        Args:
            backend: 缓存后端
            strategy: 缓存策略
            default_ttl: 默认生存时间
        """
        self.backend = backend or MemoryCacheBackend()
        self.strategy = strategy
        self.default_ttl = default_ttl

        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_lookups": 0
        }

    async def get(self, tool_name: str, parameters: Dict[str, Any]) -> Optional[Any]:
        """获取缓存的工具结果

        Args:
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            Any: 缓存的结果，如果不存在返回None
        """
        cache_key = self._generate_cache_key(tool_name, parameters)
        self.cache_stats["total_lookups"] += 1

        result = await self.backend.get(cache_key)

        if result is not None:
            self.cache_stats["hits"] += 1
            return result
        else:
            self.cache_stats["misses"] += 1
            return None

    async def set(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        result: Any,
        ttl: Optional[int] = None
    ):
        """设置工具结果缓存

        Args:
            tool_name: 工具名称
            parameters: 工具参数
            result: 执行结果
            ttl: 生存时间（可选）
        """
        cache_key = self._generate_cache_key(tool_name, parameters)
        await self.backend.set(cache_key, result, ttl or self.default_ttl)

    async def delete(self, tool_name: str, parameters: Dict[str, Any]):
        """删除工具缓存

        Args:
            tool_name: 工具名称
            parameters: 工具参数
        """
        cache_key = self._generate_cache_key(tool_name, parameters)
        await self.backend.delete(cache_key)

    async def invalidate_pattern(self, pattern: str):
        """按模式失效缓存

        Args:
            pattern: 工具名称模式（支持通配符）
        """
        if not hasattr(self.backend, 'cache'):
            return

        keys_to_delete = []
        for key in self.backend.cache.keys():
            if self._matches_pattern(key, pattern):
                keys_to_delete.append(key)

        for key in keys_to_delete:
            await self.backend.delete(key)
            self.cache_stats["evictions"] += 1

    async def warmup(self, tools: List[str], params_dict: Dict[str, Dict[str, Any]]):
        """缓存预热

        Args:
            tools: 工具列表
            params_dict: 工具参数字典
        """
        for tool_name in tools:
            if tool_name in params_dict:
                for params in params_dict[tool_name]:
                    # 这里应该执行实际的工具调用
                    # 为了预热，我们创建一个占位符结果
                    warmup_result = {
                        "tool": tool_name,
                        "parameters": params,
                        "status": "warmed_up",
                        "timestamp": datetime.now().isoformat()
                    }
                    await self.set(tool_name, params, warmup_result)

    async def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息

        Returns:
            Dict: 缓存统计
        """
        backend_stats = await self.backend.get_stats()
        hit_rate = (
            self.cache_stats["hits"] / max(self.cache_stats["total_lookups"], 1)
        )

        return {
            **self.cache_stats,
            "hit_rate": hit_rate,
            "miss_rate": 1 - hit_rate,
            "backend_stats": backend_stats
        }

    async def optimize_cache(self):
        """优化缓存（根据策略）"""
        if self.strategy == CacheStrategy.LRU:
            await self._apply_lru_optimization()
        elif self.strategy == CacheStrategy.LFU:
            await self._apply_lfu_optimization()
        elif self.strategy == CacheStrategy.TTL:
            await self._apply_ttl_optimization()

    async def _apply_lru_optimization(self):
        """应用LRU优化"""
        # 内存缓存后端已经实现了LRU
        pass

    async def _apply_lfu_optimization(self):
        """应用LFU优化"""
        if not hasattr(self.backend, 'cache'):
            return

        # 按访问频率排序，保留高频条目
        sorted_entries = sorted(
            self.backend.cache.values(),
            key=lambda e: e.access_frequency,
            reverse=True
        )

        # 保留前80%的高频条目
        keep_count = int(len(sorted_entries) * 0.8)
        entries_to_keep = set(entry.key for entry in sorted_entries[:keep_count])

        for key in list(self.backend.cache.keys()):
            if key not in entries_to_keep:
                await self.backend.delete(key)
                self.cache_stats["evictions"] += 1

    async def _apply_ttl_optimization(self):
        """应用TTL优化"""
        # TTL由缓存条目自己管理
        pass

    def _generate_cache_key(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """生成缓存键

        Args:
            tool_name: 工具名称
            parameters: 工具参数

        Returns:
            str: 缓存键
        """
        # 创建确定性的键
        params_str = json.dumps(parameters, sort_keys=True)
        cache_string = f"{tool_name}:{params_str}"
        return hashlib.sha256(cache_string.encode()).hexdigest()

    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """匹配键和模式

        Args:
            key: 缓存键
            pattern: 工具名称模式

        Returns:
            bool: 是否匹配
        """
        # 简化实现：检查工具名称部分
        tool_part = key.split(":")[0] if ":" in key else key
        return tool_part == pattern or pattern in tool_part

    async def clear(self):
        """清空所有缓存"""
        await self.backend.clear()
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "total_lookups": 0
        }


class CacheWarmingStrategy:
    """缓存预热策略"""

    @staticmethod
    async def predictive_warming(
        cache: ToolCache,
        historical_usage: List[Dict[str, Any]],
        top_n: int = 20
    ):
        """预测性预热 - 基于历史使用情况预热缓存

        Args:
            cache: 缓存实例
            historical_usage: 历史使用记录
            top_n: 预热的工具数量
        """
        # 统计工具使用频率
        tool_usage = {}
        for record in historical_usage:
            tool_name = record.get("tool_name")
            if tool_name:
                tool_usage[tool_name] = tool_usage.get(tool_name, 0) + 1

        # 选择top N工具进行预热
        top_tools = sorted(tool_usage.items(), key=lambda x: x[1], reverse=True)[:top_n]

        # 为每个工具预热一些常用参数
        for tool_name, usage_count in top_tools:
            # 获取该工具的常用参数（从历史记录中）
            common_params = CacheWarmingStrategy._extract_common_params(
                tool_name, historical_usage
            )

            for params in common_params[:3]:  # 每个工具预热3组参数
                # 创建模拟结果用于预热
                warmup_result = {
                    "tool": tool_name,
                    "parameters": params,
                    "status": "pre_warmed",
                    "predicted_usage": usage_count
                }
                await cache.set(tool_name, params, warmup_result)

    @staticmethod
    def _extract_common_params(tool_name: str, historical_usage: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """提取常用参数

        Args:
            tool_name: 工具名称
            historical_usage: 历史使用记录

        Returns:
            List[Dict]: 常用参数列表
        """
        params_list = []
        params_count = {}

        # 统计参数组合
        for record in historical_usage:
            if record.get("tool_name") == tool_name:
                params = record.get("parameters", {})
                params_str = json.dumps(params, sort_keys=True)
                params_count[params_str] = params_count.get(params_str, 0) + 1

        # 返回最常用的参数组合
        sorted_params = sorted(params_count.items(), key=lambda x: x[1], reverse=True)
        for params_str, count in sorted_params[:5]:  # top 5
            params_list.append(json.loads(params_str))

        return params_list


# 工厂函数
def create_tool_cache(
    backend: CacheBackend = None,
    strategy: CacheStrategy = CacheStrategy.ADAPTIVE,
    max_size: int = 1000,
    default_ttl: int = 3600
) -> ToolCache:
    """创建工具缓存

    Args:
        backend: 缓存后端
        strategy: 缓存策略
        max_size: 最大缓存大小
        default_ttl: 默认TTL

    Returns:
        ToolCache: 缓存实例
    """
    if backend is None:
        backend = MemoryCacheBackend(max_size=max_size)

    return ToolCache(
        backend=backend,
        strategy=strategy,
        default_ttl=default_ttl
    )
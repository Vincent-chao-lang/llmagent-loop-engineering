"""
动态上下文管理器 - 实时优化上下文空间使用
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AllocationStrategy(Enum):
    """空间分配策略"""
    IMPORTANCE_BASED = "importance_based"  # 基于重要性
    RECENCY_BASED = "recency_based"  # 基于时间
    HYBRID = "hybrid"  # 混合策略
    INTELLIGENT = "intelligent"  # 智能分配


@dataclass
class WindowConfig:
    """窗口配置"""
    max_window_size: int = 8000  # 最大窗口大小（tokens）
    reserve_space: int = 1000   # 预留空间（tokens）
    allocation_strategy: AllocationStrategy = AllocationStrategy.INTELLIGENT
    allow_partial_compression: bool = True  # 允许部分压缩
    compression_threshold: float = 0.8  # 压缩触发阈值（使用率）


@dataclass
class ContextAllocation:
    """上下文分配结果"""
    messages_to_remove: List[int]  # 要移除的消息索引
    messages_to_compress: List[int]  # 要压缩的消息索引
    compression_strategy: Optional[str] = None
    estimated_savings: int = 0  # 预估节省的token数
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpaceRequirement:
    """空间需求"""
    minimum_required: int  # 最小需求
    recommended: int  # 推荐空间
    maximum_allowed: int  # 最大允许
    reason: str = ""  # 需求原因


class ContextAnalyzer:
    """上下文分析器"""

    def __init__(self):
        """初始化上下文分析器"""
        self.analysis_cache = {}

    async def analyze_usage(self, messages: List['Message']) -> Dict[str, Any]:
        """分析上下文使用情况

        Args:
            messages: 消息列表

        Returns:
            使用情况分析
        """
        if not messages:
            return {
                'total_messages': 0,
                'total_tokens': 0,
                'average_message_length': 0,
                'role_distribution': {},
                'usage_pattern': 'empty'
            }

        # 基础统计
        total_tokens = sum(msg.token_count for msg in messages)
        total_messages = len(messages)
        average_length = total_tokens / total_messages if total_messages > 0 else 0

        # 角色分布
        role_distribution = {}
        for msg in messages:
            role_distribution[msg.role] = role_distribution.get(msg.role, 0) + 1

        # 使用模式识别
        usage_pattern = self._identify_usage_pattern(messages, total_tokens)

        return {
            'total_messages': total_messages,
            'total_tokens': total_tokens,
            'average_message_length': average_length,
            'role_distribution': role_distribution,
            'usage_pattern': usage_pattern,
            'memory_intensity': self._calculate_memory_intensity(messages),
            'growth_rate': self._estimate_growth_rate(messages)
        }

    def _identify_usage_pattern(self, messages: List['Message'], total_tokens: int) -> str:
        """识别使用模式"""
        if not messages:
            return 'empty'

        # 检查模式
        recent_messages = messages[-5:] if len(messages) >= 5 else messages
        recent_tokens = sum(msg.token_count for msg in recent_messages)

        # 如果最近的消息占用大部分空间，说明是活跃模式
        if recent_tokens > total_tokens * 0.7:
            return 'active_recent'

        # 如果消息平均长度很长，说明是内容密集模式
        avg_length = total_tokens / len(messages)
        if avg_length > 500:
            return 'content_intensive'

        # 如果消息很多但平均长度短，说明是对话密集模式
        if len(messages) > 20 and avg_length < 200:
            return 'conversation_intensive'

        return 'normal'

    def _calculate_memory_intensity(self, messages: List['Message']) -> float:
        """计算内存强度"""
        if not messages:
            return 0.0

        # 基于消息密度和长度计算强度
        total_tokens = sum(msg.token_count for msg in messages)
        message_density = len(messages) / max(total_tokens, 1)

        # 归一化强度值
        intensity = min(1.0, (total_tokens / 10000 + message_density * 100))
        return intensity

    def _estimate_growth_rate(self, messages: List['Message']) -> float:
        """估算增长率"""
        if len(messages) < 3:
            return 0.0

        # 计算最近几条消息的平均长度趋势
        recent_messages = messages[-3:]
        recent_avg = sum(msg.token_count for msg in recent_messages) / len(recent_messages)

        older_messages = messages[-6:-3] if len(messages) >= 6 else messages[:-3]
        if older_messages:
            older_avg = sum(msg.token_count for msg in older_messages) / len(older_messages)
            growth_rate = (recent_avg - older_avg) / max(older_avg, 1)
        else:
            growth_rate = 0.0

        return growth_rate


class DynamicContextManager:
    """
    动态上下文管理器

    实时优化上下文空间使用，在有限窗口下最大化对话质量。
    """

    def __init__(self, config: WindowConfig = None):
        """初始化动态上下文管理器

        Args:
            config: 窗口配置
        """
        self.config = config or WindowConfig()
        self.analyzer = ContextAnalyzer()

        # 管理历史
        self.allocation_history = []
        self.compression_results = []

    async def allocate_context_space(
        self,
        current_context: List['Message'],
        new_request: 'Message',
        constraints: Dict[str, Any] = None
    ) -> ContextAllocation:
        """为新的请求分配上下文空间

        Args:
            current_context: 当前上下文
            new_request: 新请求
            constraints: 约束条件

        Returns:
            上下文分配结果
        """
        # 1. 分析当前上下文使用情况
        current_usage = await self.analyzer.analyze_usage(current_context)

        # 2. 估算新请求的空间需求
        space_requirement = self._estimate_space_requirement(new_request, current_usage)

        # 3. 计算可用空间
        available_space = self._calculate_available_space(current_usage, space_requirement)

        # 4. 判断是否需要压缩
        if available_space['needs_compression']:
            # 生成压缩计划
            allocation = await self._generate_compression_plan(
                current_context,
                space_requirement,
                available_space,
                constraints
            )
        else:
            # 不需要压缩
            allocation = ContextAllocation(
                messages_to_remove=[],
                messages_to_compress=[],
                estimated_savings=0,
                metadata={'reason': 'sufficient_space'}
            )

        # 5. 记录分配历史
        self.allocation_history.append({
            'timestamp': datetime.now(),
            'current_usage': current_usage,
            'space_requirement': space_requirement,
            'allocation_result': allocation,
            'strategy_used': self.config.allocation_strategy.value
        })

        return allocation

    def _estimate_space_requirement(
        self,
        new_request: 'Message',
        current_usage: Dict[str, Any]
    ) -> SpaceRequirement:
        """估算空间需求"""
        # 基础需求：消息本身的长度
        base_requirement = new_request.token_count

        # 考虑响应空间（通常是请求的2-3倍）
        response_estimate = base_requirement * 2.5

        # 考虑系统开销
        system_overhead = 200  # 系统提示、格式化等

        # 总需求
        total_requirement = base_requirement + response_estimate + system_overhead

        return SpaceRequirement(
            minimum_required=int(total_requirement * 0.7),  # 最小需求
            recommended=int(total_requirement),  # 推荐需求
            maximum_allowed=int(total_requirement * 1.3),  # 最大允许
            reason=f"请求: {base_requirement} tokens, 预估响应: {response_estimate} tokens"
        )

    def _calculate_available_space(
        self,
        current_usage: Dict[str, Any],
        space_requirement: SpaceRequirement
    ) -> Dict[str, Any]:
        """计算可用空间"""
        max_window = self.config.max_window_size
        used_space = current_usage['total_tokens']
        reserve_space = self.config.reserve_space

        # 实际可用空间
        actual_available = max_window - used_space - reserve_space

        # 是否需要压缩
        needs_compression = actual_available < space_requirement.minimum_required

        # 压缩压力评估
        if needs_compression:
            compression_pressure = (space_requirement.minimum_required - actual_available) / max_window
        else:
            compression_pressure = 0.0

        return {
            'max_window': max_window,
            'used_space': used_space,
            'reserve_space': reserve_space,
            'actual_available': actual_available,
            'required_space': space_requirement.recommended,
            'needs_compression': needs_compression,
            'compression_pressure': compression_pressure,
            'utilization_rate': used_space / max_window
        }

    async def _generate_compression_plan(
        self,
        current_context: List['Message'],
        space_requirement: SpaceRequirement,
        available_space: Dict[str, Any],
        constraints: Dict[str, Any]
    ) -> ContextAllocation:
        """生成压缩计划"""
        # 计算需要释放的空间
        space_to_free = space_requirement.minimum_required - available_space['actual_available']

        # 根据分配策略选择压缩方法
        if self.config.allocation_strategy == AllocationStrategy.IMPORTANCE_BASED:
            return await self._importance_based_compression(current_context, space_to_free, constraints)
        elif self.config.allocation_strategy == AllocationStrategy.RECENCY_BASED:
            return await self._recency_based_compression(current_context, space_to_free, constraints)
        elif self.config.allocation_strategy == AllocationStrategy.HYBRID:
            return await self._hybrid_compression(current_context, space_to_free, constraints)
        else:  # INTELLIGENT
            return await self._intelligent_compression(current_context, space_to_free, constraints)

    async def _importance_based_compression(
        self,
        messages: List['Message'],
        space_to_free: int,
        constraints: Dict[str, Any]
    ) -> ContextAllocation:
        """基于重要性的压缩"""
        # 简化实现：假设已经计算了重要性分数
        # 在实际应用中，这里需要调用ContextCompressor来获取重要性分数

        # 按消息长度排序（优先压缩长消息）
        sorted_messages = sorted(
            enumerate(messages),
            key=lambda x: x[1].token_count,
            reverse=True
        )

        messages_to_compress = []
        freed_space = 0

        for msg_idx, message in sorted_messages:
            if freed_space >= space_to_free:
                break

            # 估算压缩后能释放的空间（假设压缩到50%）
            estimated_saving = message.token_count * 0.5
            messages_to_compress.append(msg_idx)
            freed_space += estimated_saving

        return ContextAllocation(
            messages_to_remove=[],
            messages_to_compress=messages_to_compress,
            compression_strategy='importance_based_compression',
            estimated_savings=int(freed_space),
            metadata={
                'target_space_to_free': space_to_free,
                'actual_freed': freed_space
            }
        )

    async def _recency_based_compression(
        self,
        messages: List['Message'],
        space_to_free: int,
        constraints: Dict[str, Any]
    ) -> ContextAllocation:
        """基于时间的压缩"""
        # 优先压缩最旧的消息
        messages_to_remove = []
        freed_space = 0

        for i in range(len(messages)):
            if freed_space >= space_to_free:
                break

            message = messages[i]
            messages_to_remove.append(i)
            freed_space += message.token_count

        return ContextAllocation(
            messages_to_remove=messages_to_remove,
            messages_to_compress=[],
            compression_strategy='recency_based_removal',
            estimated_savings=int(freed_space),
            metadata={
                'target_space_to_free': space_to_free,
                'actual_freed': freed_space
            }
        )

    async def _hybrid_compression(
        self,
        messages: List['Message'],
        space_to_free: int,
        constraints: Dict[str, Any]
    ) -> ContextAllocation:
        """混合压缩策略"""
        # 结合重要性和时间，分阶段压缩
        messages_to_remove = []
        messages_to_compress = []
        freed_space = 0

        # 第一阶段：移除非常旧且不重要的消息
        old_messages = messages[:len(messages)//3]  # 前1/3的消息
        for i, message in enumerate(old_messages):
            if freed_space >= space_to_free * 0.6:  # 先达到60%目标
                break

            if message.token_count < 200:  # 短消息直接移除
                messages_to_remove.append(i)
                freed_space += message.token_count

        # 第二阶段：压缩剩余的重要消息
        if freed_space < space_to_free:
            remaining_space = space_to_free - freed_space
            for i in range(len(messages_to_remove), len(messages)):
                if freed_space >= space_to_free:
                    break

                message = messages[i]
                if message not in [messages[idx] for idx in messages_to_remove]:
                    estimated_saving = message.token_count * 0.4  # 压缩到60%
                    messages_to_compress.append(i)
                    freed_space += estimated_saving

        return ContextAllocation(
            messages_to_remove=messages_to_remove,
            messages_to_compress=messages_to_compress,
            compression_strategy='hybrid_compression',
            estimated_savings=int(freed_space),
            metadata={
                'target_space_to_free': space_to_free,
                'actual_freed': freed_space,
                'phases': {
                    'removal_phase': len(messages_to_remove),
                    'compression_phase': len(messages_to_compress)
                }
            }
        )

    async def _intelligent_compression(
        self,
        messages: List['Message'],
        space_to_free: int,
        constraints: Dict[str, Any]
    ) -> ContextAllocation:
        """智能压缩策略"""
        # 分析消息的重要性和特征
        message_scores = []

        for i, message in enumerate(messages):
            score = await self._calculate_message_intelligence_score(message, i, messages)
            message_scores.append((i, message, score))

        # 按智能评分排序
        message_scores.sort(key=lambda x: x[2], reverse=True)

        # 分层压缩
        messages_to_remove = []
        messages_to_compress = []
        freed_space = 0

        for msg_idx, message, score in message_scores:
            if freed_space >= space_to_free:
                break

            if score < 0.3:  # 低分直接移除
                messages_to_remove.append(msg_idx)
                freed_space += message.token_count
            elif score < 0.6:  # 中分压缩
                estimated_saving = message.token_count * 0.5
                messages_to_compress.append(msg_idx)
                freed_space += estimated_saving

        return ContextAllocation(
            messages_to_remove=messages_to_remove,
            messages_to_compress=messages_to_compress,
            compression_strategy='intelligent_compression',
            estimated_savings=int(freed_space),
            metadata={
                'target_space_to_free': space_to_free,
                'actual_freed': freed_space,
                'intelligence_scores': [score for _, _, score in message_scores[:5]]
            }
        )

    async def _calculate_message_intelligence_score(
        self,
        message: 'Message',
        index: int,
        all_messages: List['Message']
    ) -> float:
        """计算消息的智能评分"""
        score = 0.5  # 基础分

        # 1. 时间新鲜度 (0-0.3分)
        recency_score = (index + 1) / len(all_messages) * 0.3
        score += recency_score

        # 2. 内容重要性 (0-0.3分)
        if message.role == "system":
            score += 0.3  # 系统消息重要
        elif message.role == "user" and any(
            keyword in message.content
            for keyword in ['决定', '选择', '确认', 'decide', 'choose', 'confirm']
        ):
            score += 0.25  # 决策类用户消息重要

        # 3. 交互价值 (0-0.2分)
        if index > 0 and all_messages[index-1].role == "user":
            # 对用户问题的回答
            score += 0.15

        # 4. 内容丰富度 (0-0.2分)
        if message.token_count > 300:
            score += 0.2
        elif message.token_count > 100:
            score += 0.1

        return min(1.0, score)

    async def apply_allocation(
        self,
        current_context: List['Message'],
        allocation: ContextAllocation,
        compressor: 'ContextCompressor' = None
    ) -> List['Message']:
        """应用分配结果

        Args:
            current_context: 当前上下文
            allocation: 分配结果
            compressor: 压缩器（可选）

        Returns:
            处理后的上下文
        """
        if not allocation.messages_to_remove and not allocation.messages_to_compress:
            return current_context

        result_context = current_context.copy()

        # 1. 移除消息
        if allocation.messages_to_remove:
            # 按索引逆序移除，避免索引变化
            for idx in sorted(allocation.messages_to_remove, reverse=True):
                if 0 <= idx < len(result_context):
                    result_context.pop(idx)

        # 2. 压缩消息
        if allocation.messages_to_compress and compressor:
            # 简化实现：这里应该调用压缩器进行实际压缩
            # 在实际应用中，需要集成ContextCompressor
            pass

        # 3. 记录压缩结果
        self.compression_results.append({
            'timestamp': datetime.now(),
            'original_count': len(current_context),
            'result_count': len(result_context),
            'strategy': allocation.compression_strategy,
            'estimated_savings': allocation.estimated_savings
        })

        return result_context

    def get_allocation_statistics(self) -> Dict[str, Any]:
        """获取分配统计信息"""
        if not self.allocation_history:
            return {}

        recent_allocations = self.allocation_history[-20:]  # 最近20次

        # 计算统计指标
        total_compressions = len([a for a in recent_allocations if a['allocation_result'].messages_to_remove or a['allocation_result'].messages_to_compress])
        compression_rate = total_compressions / len(recent_allocations) if recent_allocations else 0

        average_savings = sum(
            a['allocation_result'].estimated_savings
            for a in recent_allocations
        ) / len(recent_allocations) if recent_allocations else 0

        return {
            'total_allocations': len(self.allocation_history),
            'recent_compression_rate': compression_rate,
            'average_savings': average_savings,
            'most_used_strategy': self._get_most_used_strategy(recent_allocations),
            'compression_frequency': self._calculate_compression_frequency()
        }

    def _get_most_used_strategy(self, allocations: List[Dict]) -> str:
        """获取最常用的策略"""
        strategies = [a['strategy_used'] for a in allocations]
        if not strategies:
            return "none"

        from collections import Counter
        strategy_counts = Counter(strategies)
        return strategy_counts.most_common(1)[0][0]

    def _calculate_compression_frequency(self) -> float:
        """计算压缩频率"""
        if not self.compression_results:
            return 0.0

        # 计算最近1小时的压缩次数
        one_hour_ago = datetime.now() - timedelta(hours=1)
        recent_compressions = [
            c for c in self.compression_results
            if c['timestamp'] > one_hour_ago
        ]

        return len(recent_compressions)


# 导入Message类型
from .compressor import Message
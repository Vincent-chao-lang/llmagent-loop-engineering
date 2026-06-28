"""
上下文压缩器 - 智能压缩对话历史，在有限窗口下支持更长对话
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import re
import math


class CompressionStrategy(Enum):
    """压缩策略"""
    INTELLIGENT = "intelligent"  # 智能压缩
    IMPORTANCE_BASED = "importance_based"  # 基于重要性
    RECENCY_BASED = "recency_based"  # 基于时间
    HIERARCHICAL = "hierarchical"  # 层级压缩
    SUMMARIZATION = "summarization"  # 摘要化


@dataclass
class Message:
    """消息数据结构"""
    role: str  # "system", "user", "assistant"
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    token_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.role}: {self.content[:100]}..."


@dataclass
class CompressedContext:
    """压缩后的上下文"""
    messages: List[Message]
    compression_ratio: float  # 压缩比例 (0.0-1.0)
    information_retention: float  # 信息保留率 (0.0-1.0)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def total_tokens(self) -> int:
        """计算总token数"""
        return sum(msg.token_count for msg in self.messages)


@dataclass
class ImportanceScore:
    """重要性评分"""
    message_id: int
    importance: float  # 0.0-1.0
    factors: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""


@dataclass
class KeyInformation:
    """关键信息"""
    content: str
    importance: float
    category: str  # "entity", "decision", "preference", "constraint"
    source_message_id: int


class ContextCompressor:
    """
    上下文压缩器

    智能压缩对话历史，在有限的上下文窗口下支持更长轮次的对话。
    """

    def __init__(self, compression_strategy: CompressionStrategy = CompressionStrategy.INTELLIGENT):
        """初始化压缩器

        Args:
            compression_strategy: 压缩策略
        """
        self.strategy = compression_strategy
        self.compression_history = []

        # 重要性权重配置
        self.importance_weights = {
            'recency': 0.3,  # 时间新鲜度
            'content_richness': 0.25,  # 内容丰富度
            'interaction_value': 0.2,  # 交互价值
            'uniqueness': 0.15,  # 独特性
            'query_relevance': 0.1  # 查询相关性
        }

    async def compress_context(
        self,
        messages: List[Message],
        target_length: int,
        preserve_key_info: bool = True
    ) -> CompressedContext:
        """
        智能压缩上下文

        Args:
            messages: 原始消息列表
            target_length: 目标长度（token数）
            preserve_key_info: 是否保留关键信息

        Returns:
            压缩后的上下文
        """
        original_length = sum(msg.token_count for msg in messages)

        # 如果不需要压缩
        if original_length <= target_length:
            return CompressedContext(
                messages=messages,
                compression_ratio=0.0,
                information_retention=1.0,
                metadata={
                    'original_length': original_length,
                    'compressed_length': original_length,
                    'compression_needed': False
                }
            )

        # 1. 分析消息重要性
        importance_scores = await self._analyze_importance(messages)

        # 2. 识别关键信息
        key_information = []
        if preserve_key_info:
            key_information = await self._extract_key_information(messages, importance_scores)

        # 3. 选择压缩策略并执行
        compressed = await self._apply_compression_strategy(
            messages, importance_scores, target_length, key_information
        )

        # 4. 确保关键信息保留
        if preserve_key_info and key_information:
            compressed = await self._ensure_key_information_retention(
                compressed.messages, key_information, target_length
            )

        # 5. 计算压缩指标
        compressed_length = sum(msg.token_count for msg in compressed.messages)
        compression_ratio = 1.0 - (compressed_length / original_length)
        information_retention = await self._calculate_information_retention(
            messages, compressed.messages, key_information
        )

        # 6. 记录压缩历史
        self.compression_history.append({
            'timestamp': datetime.now(),
            'original_length': original_length,
            'compressed_length': compressed_length,
            'compression_ratio': compression_ratio,
            'strategy': self.strategy.value
        })

        return CompressedContext(
            messages=compressed.messages,
            compression_ratio=compression_ratio,
            information_retention=information_retention,
            metadata={
                'original_length': original_length,
                'compressed_length': compressed_length,
                'compression_needed': True,
                'strategy_used': self.strategy.value,
                'key_info_preserved': len(key_information),
                'importance_scores': [score.importance for score in importance_scores]
            }
        )

    async def _analyze_importance(self, messages: List[Message]) -> List[ImportanceScore]:
        """分析消息重要性

        Args:
            messages: 消息列表

        Returns:
            重要性评分列表
        """
        scores = []

        for i, message in enumerate(messages):
            # 计算各个因子
            factors = {}

            # 1. 时间新鲜度
            factors['recency'] = self._calculate_recency(message, messages)

            # 2. 内容丰富度
            factors['content_richness'] = self._calculate_content_richness(message)

            # 3. 交互价值
            factors['interaction_value'] = self._calculate_interaction_value(message, messages, i)

            # 4. 独特性
            factors['uniqueness'] = await self._calculate_uniqueness(message, messages[:i])

            # 5. 查询相关性
            factors['query_relevance'] = self._calculate_query_relevance(message, messages)

            # 加权计算总重要性
            importance = sum(
                factors[factor] * self.importance_weights[factor]
                for factor in factors
            )

            scores.append(ImportanceScore(
                message_id=i,
                importance=importance,
                factors=factors,
                reasoning=self._generate_importance_reasoning(factors)
            ))

        return scores

    def _calculate_recency(self, message: Message, all_messages: List[Message]) -> float:
        """计算时间新鲜度"""
        if not all_messages:
            return 1.0

        # 最新消息权重最高
        message_index = all_messages.index(message)
        recency = 1.0 - (message_index / len(all_messages))
        return max(0.1, recency)  # 保证最低权重0.1

    def _calculate_content_richness(self, message: Message) -> float:
        """计算内容丰富度"""
        if not message.content:
            return 0.0

        # 基于多个维度计算丰富度
        richness_score = 0.0

        # 1. 内容长度（归一化）
        length_score = min(1.0, len(message.content) / 500)  # 500字符为满分
        richness_score += length_score * 0.3

        # 2. 信息密度（关键词数量）
        keywords = self._extract_keywords(message.content)
        density_score = min(1.0, len(keywords) / 20)  # 20个关键词为满分
        richness_score += density_score * 0.4

        # 3. 结构复杂度
        structure_score = self._analyze_structure_complexity(message.content)
        richness_score += structure_score * 0.3

        return min(1.0, richness_score)

    def _calculate_interaction_value(self, message: Message, all_messages: List[Message], index: int) -> float:
        """计算交互价值"""
        if not all_messages or index == 0:
            return 0.5

        # 检查是否是对问题的回答
        if message.role == "assistant" and index > 0:
            prev_message = all_messages[index - 1]
            if prev_message.role == "user" and self._is_question(prev_message.content):
                return 0.9  # 回答问题价值高

        # 检查是否是重要的用户输入
        if message.role == "user":
            if self._contains_decision(message.content):
                return 0.9  # 决策类输入价值高
            elif self._contains_preference(message.content):
                return 0.8  # 偏好类输入价值较高

        return 0.5  # 默认中等价值

    async def _calculate_uniqueness(self, message: Message, previous_messages: List[Message]) -> float:
        """计算独特度（避免重复信息）"""
        if not previous_messages:
            return 1.0  # 第一条消息完全独特

        # 简单相似度检测（基于关键词重叠）
        current_keywords = set(self._extract_keywords(message.content))
        max_similarity = 0.0

        for prev_msg in previous_messages:
            prev_keywords = set(self._extract_keywords(prev_msg.content))
            if not prev_keywords:
                continue

            # 计算Jaccard相似度
            intersection = len(current_keywords & prev_keywords)
            union = len(current_keywords | prev_keywords)
            similarity = intersection / union if union > 0 else 0.0

            max_similarity = max(max_similarity, similarity)

        # 独特性 = 1 - 最大相似度
        return 1.0 - max_similarity

    def _calculate_query_relevance(self, message: Message, all_messages: List[Message]) -> float:
        """计算查询相关性"""
        if not all_messages:
            return 0.5

        # 检查是否与最近的话题相关
        recent_messages = all_messages[-5:] if len(all_messages) >= 5 else all_messages

        # 如果是最近的几条消息之一，相关性高
        if message in recent_messages:
            return 0.8

        # 检查是否回应了前面的话题
        relevance = self._check_topic_continuity(message, recent_messages)
        return relevance

    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        if not text:
            return []

        # 简单的关键词提取（基于词性和频率）
        words = re.findall(r'\b\w{3,}\b', text.lower())

        # 过滤常见停用词
        stopwords = {'the', 'and', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
                     'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should',
                     'can', 'could', 'may', 'might', 'must', 'shall', 'this', 'that',
                     'these', 'those', 'a', 'an', 'in', 'on', 'at', 'to', 'for', 'of',
                     'with', 'by', 'from', 'as', 'into', 'through', 'during', 'before',
                     'after', 'above', 'below', 'between', 'under', 'again', 'further',
                     'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how',
                     'all', 'both', 'each', 'few', 'more', 'most', 'other', 'some',
                     'such', 'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than',
                     'too', 'very', 'just', 'but', 'also', 'now', 'get', 'like', 'make'}

        keywords = [word for word in words if word not in stopwords]

        # 统计频率并返回高频词
        from collections import Counter
        keyword_freq = Counter(keywords)
        return [word for word, _ in keyword_freq.most_common(10)]

    def _analyze_structure_complexity(self, text: str) -> float:
        """分析文本结构复杂度"""
        if not text:
            return 0.0

        complexity_score = 0.0

        # 1. 句子结构（是否包含复杂句式）
        if any(pattern in text for pattern in ['because', 'although', 'while', 'if', 'when']):
            complexity_score += 0.3

        # 2. 列举和结构
        if re.search(r'\d+\.\s+|[•\-\*]', text):
            complexity_score += 0.2

        # 3. 代码或数据
        if '```' in text or any(code in text for code in ['def ', 'class ', 'function']):
            complexity_score += 0.3

        # 4. 多段落
        paragraph_count = len([p for p in text.split('\n\n') if p.strip()])
        if paragraph_count > 1:
            complexity_score += min(0.2, (paragraph_count - 1) * 0.1)

        return min(1.0, complexity_score)

    def _is_question(self, text: str) -> bool:
        """判断是否是问题"""
        question_indicators = ['?', '如何', '怎么', '什么', '为什么', 'whether', 'how', 'what', 'why', 'when', 'where']
        return any(indicator in text.lower() for indicator in question_indicators)

    def _contains_decision(self, text: str) -> bool:
        """判断是否包含决策"""
        decision_words = ['决定', '选择', '采用', '使用', 'decide', 'choose', 'select', 'adopt']
        return any(word in text.lower() for word in decision_words)

    def _contains_preference(self, text: str) -> bool:
        """判断是否包含偏好"""
        preference_words = ['喜欢', '偏好', '希望', 'prefer', 'like', 'want', 'wish']
        return any(word in text.lower() for word in preference_words)

    def _check_topic_continuity(self, message: Message, context_messages: List[Message]) -> float:
        """检查话题连续性"""
        if not context_messages:
            return 0.5

        # 提取当前消息和上下文消息的关键词
        current_keywords = set(self._extract_keywords(message.content))
        context_keywords = set()

        for msg in context_messages:
            context_keywords.update(self._extract_keywords(msg.content))

        if not context_keywords:
            return 0.5

        # 计算关键词重叠度
        overlap = len(current_keywords & context_keywords)
        total = len(current_keywords | context_keywords)

        return overlap / total if total > 0 else 0.5

    def _generate_importance_reasoning(self, factors: Dict[str, float]) -> str:
        """生成重要性评估的理由"""
        reasoning_parts = []

        if factors.get('recency', 0) > 0.7:
            reasoning_parts.append("最近的消息")
        if factors.get('content_richness', 0) > 0.7:
            reasoning_parts.append("内容丰富")
        if factors.get('interaction_value', 0) > 0.7:
            reasoning_parts.append("高交互价值")
        if factors.get('uniqueness', 0) > 0.7:
            reasoning_parts.append("独特内容")
        if factors.get('query_relevance', 0) > 0.7:
            reasoning_parts.append("与当前话题相关")

        return "; ".join(reasoning_parts) if reasoning_parts else "一般重要性"

    async def _extract_key_information(
        self,
        messages: List[Message],
        importance_scores: List[ImportanceScore]
    ) -> List[KeyInformation]:
        """提取关键信息

        Args:
            messages: 消息列表
            importance_scores: 重要性评分

        Returns:
            关键信息列表
        """
        key_info_list = []

        for i, (message, score) in enumerate(zip(messages, importance_scores)):
            # 只从高重要性消息中提取关键信息
            if score.importance < 0.6:
                continue

            # 提取不同类型的关键信息
            entities = self._extract_entities(message.content, i)
            decisions = self._extract_decisions(message.content, i)
            preferences = self._extract_preferences(message.content, i)
            constraints = self._extract_constraints(message.content, i)

            key_info_list.extend([entities, decisions, preferences, constraints])

        return key_info_list

    def _extract_entities(self, content: str, message_id: int) -> KeyInformation:
        """提取实体信息"""
        # 简单的实体提取（识别专有名词、数字等）
        entities = re.findall(r'\b[A-Z][a-z]+\b|\d+\.?\d*', content)
        if entities:
            return KeyInformation(
                content=f"实体: {', '.join(entities[:5])}",  # 最多5个实体
                importance=0.7,
                category="entity",
                source_message_id=message_id
            )
        return None

    def _extract_decisions(self, content: str, message_id: int) -> KeyInformation:
        """提取决策信息"""
        if self._contains_decision(content):
            # 提取决策相关的句子
            sentences = content.split('。')
            for sentence in sentences:
                if any(word in sentence for word in ['决定', '选择', '采用', 'decide', 'choose']):
                    return KeyInformation(
                        content=f"决策: {sentence.strip()}",
                        importance=0.9,
                        category="decision",
                        source_message_id=message_id
                    )
        return None

    def _extract_preferences(self, content: str, message_id: int) -> KeyInformation:
        """提取偏好信息"""
        if self._contains_preference(content):
            # 提取偏好相关的句子
            sentences = content.split('。')
            for sentence in sentences:
                if any(word in sentence for word in ['喜欢', '偏好', '希望', 'prefer', 'like']):
                    return KeyInformation(
                        content=f"偏好: {sentence.strip()}",
                        importance=0.8,
                        category="preference",
                        source_message_id=message_id
                    )
        return None

    def _extract_constraints(self, content: str, message_id: int) -> KeyInformation:
        """提取约束信息"""
        constraint_indicators = ['限制', '约束', '不能', '必须', 'limit', 'constraint', 'must', 'cannot']
        if any(indicator in content.lower() for indicator in constraint_indicators):
            # 提取约束相关的句子
            sentences = content.split('。')
            for sentence in sentences:
                if any(word in sentence for word in constraint_indicators):
                    return KeyInformation(
                        content=f"约束: {sentence.strip()}",
                        importance=0.85,
                        category="constraint",
                        source_message_id=message_id
                    )
        return None

    async def _apply_compression_strategy(
        self,
        messages: List[Message],
        importance_scores: List[ImportanceScore],
        target_length: int,
        key_information: List[KeyInformation]
    ) -> CompressedContext:
        """应用压缩策略

        Args:
            messages: 原始消息列表
            importance_scores: 重要性评分
            target_length: 目标长度
            key_information: 关键信息

        Returns:
            压缩后的上下文
        """
        if self.strategy == CompressionStrategy.IMPORTANCE_BASED:
            return await self._importance_based_compression(
                messages, importance_scores, target_length
            )
        elif self.strategy == CompressionStrategy.RECENCY_BASED:
            return await self._recency_based_compression(messages, target_length)
        elif self.strategy == CompressionStrategy.SUMMARIZATION:
            return await self._summarization_compression(
                messages, importance_scores, target_length
            )
        else:  # INTELLIGENT or HIERARCHICAL
            return await self._intelligent_compression(
                messages, importance_scores, target_length, key_information
            )

    async def _importance_based_compression(
        self,
        messages: List[Message],
        importance_scores: List[ImportanceScore],
        target_length: int
    ) -> CompressedContext:
        """基于重要性的压缩"""
        # 按重要性排序
        scored_messages = list(zip(messages, importance_scores))
        scored_messages.sort(key=lambda x: x[1].importance, reverse=True)

        # 选择最重要的消息直到达到目标长度
        selected_messages = []
        current_length = 0

        for message, score in scored_messages:
            if current_length + message.token_count <= target_length:
                selected_messages.append(message)
                current_length += message.token_count
            else:
                # 尝试截断这条消息
                remaining_space = target_length - current_length
                if remaining_space > 50:  # 至少留50 tokens
                    truncated_message = self._truncate_message(message, remaining_space)
                    selected_messages.append(truncated_message)
                break

        # 按原始顺序排列
        selected_messages.sort(key=lambda m: messages.index(m) if m in messages else float('inf'))

        # 计算压缩指标
        original_length = sum(msg.token_count for msg in messages)
        compressed_length = sum(msg.token_count for msg in selected_messages)
        compression_ratio = 1.0 - (compressed_length / original_length) if original_length > 0 else 0
        information_retention = len(selected_messages) / len(messages) if messages else 1.0

        return CompressedContext(
            messages=selected_messages,
            compression_ratio=compression_ratio,
            information_retention=information_retention
        )

    async def _recency_based_compression(
        self,
        messages: List[Message],
        target_length: int
    ) -> CompressedContext:
        """基于时间的压缩（保留最新消息）"""
        # 从最新消息开始选择
        selected_messages = []
        current_length = 0

        for message in reversed(messages):
            if current_length + message.token_count <= target_length:
                selected_messages.insert(0, message)  # 保持时间顺序
                current_length += message.token_count
            else:
                break

        # 计算压缩指标
        original_length = sum(msg.token_count for msg in messages)
        compressed_length = sum(msg.token_count for msg in selected_messages)
        compression_ratio = 1.0 - (compressed_length / original_length) if original_length > 0 else 0
        information_retention = len(selected_messages) / len(messages) if messages else 1.0

        return CompressedContext(
            messages=selected_messages,
            compression_ratio=compression_ratio,
            information_retention=information_retention
        )

    async def _summarization_compression(
        self,
        messages: List[Message],
        importance_scores: List[ImportanceScore],
        target_length: int
    ) -> CompressedContext:
        """基于摘要的压缩（需要LLM支持，这里提供简化版本）"""
        # 将旧消息分组摘要
        recent_messages = messages[-3:]  # 保留最近3条完整消息
        old_messages = messages[:-3]

        if old_messages:
            # 创建摘要（简化版：合并内容）
            summary_content = "对话历史摘要: " + "; ".join([
                f"{msg.role}: {msg.content[:50]}..." for msg in old_messages
            ])

            summary_message = Message(
                role="system",
                content=summary_content,
                timestamp=datetime.now(),
                token_count=len(summary_content.split())
            )

            selected_messages = [summary_message] + recent_messages
        else:
            selected_messages = messages

        # 如果还是太长，就按重要性压缩
        total_length = sum(msg.token_count for msg in selected_messages)
        if total_length > target_length:
            return await self._importance_based_compression(
                selected_messages, importance_scores, target_length
            )

        return CompressedContext(messages=selected_messages)

    async def _intelligent_compression(
        self,
        messages: List[Message],
        importance_scores: List[ImportanceScore],
        target_length: int,
        key_information: List[KeyInformation]
    ) -> CompressedContext:
        """智能压缩（综合多种策略）"""
        # 1. 保留关键信息源消息
        key_message_ids = {info.source_message_id for info in key_information}

        # 2. 对消息分层
        high_importance = []
        medium_importance = []
        low_importance = []

        for message, score in zip(messages, importance_scores):
            if message.token_count == 0:  # 跳过空消息
                continue

            if score.importance >= 0.7 or (score.message_id in key_message_ids):
                high_importance.append((message, score))
            elif score.importance >= 0.4:
                medium_importance.append((message, score))
            else:
                low_importance.append((message, score))

        # 3. 构建压缩结果
        selected_messages = []
        current_length = 0

        # 优先选择高重要性消息
        for message, score in high_importance:
            if current_length + message.token_count <= target_length:
                selected_messages.append(message)
                current_length += message.token_count

        # 如果还有空间，选择中等重要性消息
        if current_length < target_length * 0.8:  # 留20%缓冲
            for message, score in medium_importance:
                if current_length + message.token_count <= target_length:
                    selected_messages.append(message)
                    current_length += message.token_count

        # 按原始时间顺序排列
        selected_messages.sort(key=lambda m: messages.index(m))

        # 计算压缩指标
        original_length = sum(msg.token_count for msg in messages)
        compressed_length = sum(msg.token_count for msg in selected_messages)
        compression_ratio = 1.0 - (compressed_length / original_length) if original_length > 0 else 0
        information_retention = len(selected_messages) / len(messages) if messages else 1.0

        return CompressedContext(
            messages=selected_messages,
            compression_ratio=compression_ratio,
            information_retention=information_retention
        )

    def _truncate_message(self, message: Message, max_tokens: int) -> Message:
        """截断消息到指定token数"""
        # 简化实现：按字符比例截断
        ratio = max_tokens / message.token_count if message.token_count > 0 else 0.5
        truncated_content = message.content[:int(len(message.content) * ratio)]

        return Message(
            role=message.role,
            content=truncated_content + "...",
            timestamp=message.timestamp,
            token_count=max_tokens,
            metadata={**message.metadata, 'truncated': True}
        )

    async def _ensure_key_information_retention(
        self,
        compressed_messages: List[Message],
        key_information: List[KeyInformation],
        target_length: int
    ) -> CompressedContext:
        """确保关键信息被保留"""
        # 检查关键信息是否在压缩的消息中
        missing_info = []
        for info in key_information:
            # 检查信息源消息是否还存在
            source_exists = any(
                i == info.source_message_id
                for i, msg in enumerate(compressed_messages)
                if i < len(compressed_messages)
            )

            if not source_exists:
                missing_info.append(info)

        if not missing_info:
            # 计算压缩指标
            original_length = sum(msg.token_count for msg in compressed_messages) * 2  # 估算原始长度
            compressed_length = sum(msg.token_count for msg in compressed_messages)
            compression_ratio = 1.0 - (compressed_length / original_length) if original_length > 0 else 0
            information_retention = 1.0  # 没有信息丢失

            return CompressedContext(
                messages=compressed_messages,
                compression_ratio=compression_ratio,
                information_retention=information_retention
            )

        # 重新注入丢失的关键信息
        # 这里简化处理：创建一个包含丢失信息的系统消息
        if missing_info and compressed_messages:
            missing_content = "重要历史信息: " + "; ".join([
                f"{info.category}: {info.content}" for info in missing_info
            ])

            missing_message = Message(
                role="system",
                content=missing_content,
                timestamp=datetime.now(),
                token_count=len(missing_content.split())
            )

            # 检查添加后是否超出限制
            current_total = sum(msg.token_count for msg in compressed_messages)
            if current_total + missing_message.token_count <= target_length:
                compressed_messages.insert(0, missing_message)  # 在开头插入

        # 计算压缩指标
        original_length = sum(msg.token_count for msg in compressed_messages) * 2  # 估算原始长度
        compressed_length = sum(msg.token_count for msg in compressed_messages)
        compression_ratio = 1.0 - (compressed_length / original_length) if original_length > 0 else 0
        information_retention = 0.9  # 重新注入后保留率较高

        return CompressedContext(
            messages=compressed_messages,
            compression_ratio=compression_ratio,
            information_retention=information_retention
        )

    async def _calculate_information_retention(
        self,
        original_messages: List[Message],
        compressed_messages: List[Message],
        key_information: List[KeyInformation]
    ) -> float:
        """计算信息保留率"""
        if not original_messages:
            return 1.0

        # 1. 关键信息保留率
        key_info_retention = 0.0
        if key_information:
            preserved_key_info = 0
            for info in key_information:
                # 检查信息是否在压缩的消息中找到
                if any(info.content in msg.content for msg in compressed_messages):
                    preserved_key_info += 1

            key_info_retention = preserved_key_info / len(key_information)

        # 2. 消息数量保留率
        message_retention = len(compressed_messages) / len(original_messages)

        # 3. Token保留率
        original_tokens = sum(msg.token_count for msg in original_messages)
        compressed_tokens = sum(msg.token_count for msg in compressed_messages)
        token_retention = compressed_tokens / original_tokens if original_tokens > 0 else 0

        # 综合计算（关键信息权重最高）
        return (
            key_info_retention * 0.5 +
            message_retention * 0.3 +
            token_retention * 0.2
        )

    def get_compression_stats(self) -> Dict[str, Any]:
        """获取压缩统计信息"""
        if not self.compression_history:
            return {}

        recent_compressions = self.compression_history[-10:]  # 最近10次

        return {
            'total_compressions': len(self.compression_history),
            'average_compression_ratio': sum(c['compression_ratio'] for c in recent_compressions) / len(recent_compressions),
            'average_original_length': sum(c['original_length'] for c in recent_compressions) / len(recent_compressions),
            'average_compressed_length': sum(c['compressed_length'] for c in recent_compressions) / len(recent_compressions),
            'most_used_strategy': max(
                set(c['strategy'] for c in recent_compressions),
                key=lambda s: [c['strategy'] for c in recent_compressions].count(s)
            ) if recent_compressions else None
        }


# 工具函数
def estimate_token_count(text: str) -> int:
    """估算文本的token数量"""
    if not text:
        return 0
    # 简单估算：英文约4字符/token，中文约1.5字符/token
    char_count = len(text)
    chinese_chars = len([c for c in text if '一' <= c <= '鿿'])
    english_chars = char_count - chinese_chars

    return int(chinese_chars / 1.5 + english_chars / 4)


def create_message(role: str, content: str, **kwargs) -> Message:
    """创建消息对象"""
    return Message(
        role=role,
        content=content,
        token_count=estimate_token_count(content),
        **kwargs
    )
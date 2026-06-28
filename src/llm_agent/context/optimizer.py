"""
对话历史优化器 - 优化对话结构，去除冗余，保持连贯性
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
from collections import Counter


class ConversationPhase(Enum):
    """对话阶段"""
    OPENING = "opening"        # 开场
    EXPLORATION = "exploration"  # 探索
    DISCUSSION = "discussion"    # 讨论
    DECISION = "decision"      # 决策
    CLOSING = "closing"        # 结束
    UNKNOWN = "unknown"        # 未知


@dataclass
class TopicTransition:
    """话题转换"""
    before_topic: str
    after_topic: str
    transition_point: int  # 消息索引
    transition_type: str   # "abrupt", "gradual", "natural"
    confidence: float


@dataclass
class RepetitiveInfo:
    """重复信息"""
    content: str
    occurrences: List[int]  # 出现位置
    similarity: float
    importance: float


@dataclass
class OptimizedHistory:
    """优化后的历史"""
    messages: List['Message']
    phases: List[ConversationPhase]
    metadata: Dict[str, Any] = field(default_factory=dict)


class TopicShiftDetector:
    """话题转换检测器"""

    def __init__(self):
        """初始化话题转换检测器"""
        self.transition_keywords = {
            'abrupt': ['另外', '换个话题', '说点别的', 'anyway', 'by the way'],
            'gradual': ['接下来', '然后', '还有', 'next', 'then'],
            'natural': ['关于', '说到', 'regarding', 'speaking of']
        }

    async def detect_topic_shifts(
        self,
        messages: List['Message']
    ) -> List[TopicTransition]:
        """检测话题转换点

        Args:
            messages: 消息列表

        Returns:
            话题转换列表
        """
        if len(messages) < 3:
            return []

        transitions = []
        previous_topics = []

        for i in range(1, len(messages)):
            current_message = messages[i]
            previous_message = messages[i-1]

            # 提取当前消息的话题
            current_topic = self._extract_topic(current_message.content)

            # 检查话题是否改变
            if previous_topics and current_topic != previous_topics[-1]:
                # 检测转换类型
                transition_type = self._classify_transition(
                    current_message.content,
                    previous_message.content
                )

                transition = TopicTransition(
                    before_topic=previous_topics[-1] if previous_topics else "unknown",
                    after_topic=current_topic,
                    transition_point=i,
                    transition_type=transition_type,
                    confidence=self._calculate_confidence(current_message.content)
                )

                transitions.append(transition)

            previous_topics.append(current_topic)

        return transitions

    def _extract_topic(self, text: str) -> str:
        """提取文本的话题"""
        if not text:
            return "unknown"

        # 简单的关键词提取作为话题
        keywords = re.findall(r'\b\w{3,}\b', text.lower())

        if not keywords:
            return "unknown"

        # 使用最常见的关键词作为话题
        keyword_freq = Counter(keywords)
        most_common = keyword_freq.most_common(1)

        return most_common[0][0] if most_common else "unknown"

    def _classify_transition(self, current_text: str, previous_text: str) -> str:
        """分类转换类型"""
        for transition_type, keywords in self.transition_keywords.items():
            if any(keyword in current_text for keyword in keywords):
                return transition_type

        # 基于内容相似度判断
        similarity = self._calculate_content_similarity(current_text, previous_text)
        if similarity < 0.3:
            return "abrupt"
        elif similarity < 0.6:
            return "gradual"
        else:
            return "natural"

    def _calculate_content_similarity(self, text1: str, text2: str) -> float:
        """计算内容相似度"""
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    def _calculate_confidence(self, text: str) -> float:
        """计算检测置信度"""
        # 基于文本长度和关键词置信度
        text_length = len(text.split())
        if text_length < 5:
            return 0.5
        elif text_length < 15:
            return 0.7
        else:
            return 0.9


class RepetitionRemover:
    """重复信息去除器"""

    def __init__(self, similarity_threshold: float = 0.8):
        """初始化重复信息去除器

        Args:
            similarity_threshold: 相似度阈值
        """
        self.similarity_threshold = similarity_threshold

    async def identify_repetitive_content(
        self,
        messages: List['Message']
    ) -> List[RepetitiveInfo]:
        """识别重复内容

        Args:
            messages: 消息列表

        Returns:
            重复信息列表
        """
        if len(messages) < 2:
            return []

        repetitive_infos = []
        compared_pairs = set()

        for i, message_i in enumerate(messages):
            for j, message_j in enumerate(messages[i+1:], i+1):
                # 计算消息相似度
                similarity = self._calculate_message_similarity(
                    message_i.content,
                    message_j.content
                )

                if similarity >= self.similarity_threshold:
                    # 检查是否已经记录
                    pair_key = (min(i, j), max(i, j))
                    if pair_key not in compared_pairs:
                        repetitive_info = RepetitiveInfo(
                            content=message_i.content[:100],  # 存储前100字符
                            occurrences=[i, j],
                            similarity=similarity,
                            importance=self._assess_importance(message_i, message_j)
                        )
                        repetitive_infos.append(repetitive_info)
                        compared_pairs.add(pair_key)

        return repetitive_infos

    def _calculate_message_similarity(self, text1: str, text2: str) -> float:
        """计算消息相似度"""
        # 1. 词汇相似度
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))

        if not words1 or not words2:
            return 0.0

        # Jaccard相似度
        intersection = len(words1 & words2)
        union = len(words1 | words2)
        word_similarity = intersection / union if union > 0 else 0.0

        # 2. 结构相似度（简化版）
        structure_similarity = self._calculate_structure_similarity(text1, text2)

        # 综合相似度
        overall_similarity = word_similarity * 0.7 + structure_similarity * 0.3

        return overall_similarity

    def _calculate_structure_similarity(self, text1: str, text2: str) -> float:
        """计算结构相似度"""
        # 比较句子数量、段落结构等
        sentences1 = len(re.split(r'[。！？.!?]', text1))
        sentences2 = len(re.split(r'[。！？.!?]', text2))

        if sentences1 == 0 and sentences2 == 0:
            return 1.0

        # 句子数量相似度
        sentence_similarity = 1.0 - abs(sentences1 - sentences2) / max(sentences1, sentences2)

        return sentence_similarity

    def _assess_importance(self, message1: 'Message', message2: 'Message') -> float:
        """评估重复信息的重要性"""
        # 基于消息角色和长度
        importance = 0.5

        # 系统消息的重复更重要
        if message1.role == "system" or message2.role == "system":
            importance += 0.3

        # 长消息的重复更重要
        avg_length = (message1.token_count + message2.token_count) / 2
        if avg_length > 200:
            importance += 0.2

        return min(1.0, importance)

    async def remove_repetitions(
        self,
        messages: List['Message'],
        repetitive_infos: List[RepetitiveInfo]
    ) -> List['Message']:
        """去除重复信息

        Args:
            messages: 原始消息列表
            repetitive_infos: 重复信息列表

        Returns:
            去重后的消息列表
        """
        if not repetitive_infos:
            return messages

        # 收集要移除的消息索引
        indices_to_remove = set()

        for repetitive_info in repetitive_infos:
            if len(repetitive_info.occurrences) > 1:
                # 保留第一个，移除其余的
                indices_to_remove.update(repetitive_info.occurrences[1:])

        # 按索引逆序移除
        result_messages = [
            msg for i, msg in enumerate(messages)
            if i not in indices_to_remove
        ]

        return result_messages


class ConversationHistoryOptimizer:
    """
    对话历史优化器

    优化对话结构，去除冗余信息，检测话题转换，保持对话连贯性。
    """

    def __init__(self):
        """初始化对话历史优化器"""
        self.topic_detector = TopicShiftDetector()
        self.repetition_remover = RepetitionRemover()

        # 优化历史
        self.optimization_history = []

    async def optimize_history(
        self,
        messages: List['Message'],
        window_size: int = None,
        preserve_key_info: bool = True
    ) -> OptimizedHistory:
        """优化对话历史

        Args:
            messages: 原始消息列表
            window_size: 窗口大小限制
            preserve_key_info: 是否保留关键信息

        Returns:
            优化后的历史
        """
        if not messages:
            return OptimizedHistory(
                messages=[],
                phases=[],
                metadata={'optimization_needed': False}
            )

        original_count = len(messages)

        # 1. 识别对话阶段
        phases = await self._identify_conversation_phases(messages)

        # 2. 检测话题转换
        topic_transitions = await self.topic_detector.detect_topic_shifts(messages)

        # 3. 识别重复信息
        repetitive_info = await self.repetition_remover.identify_repetitive_content(messages)

        # 4. 去除重复信息
        optimized_messages = await self.repetition_remover.remove_repetitions(
            messages, repetitive_info
        )

        # 5. 如果有窗口大小限制，进行长度优化
        if window_size and len(optimized_messages) > window_size:
            optimized_messages = await self._optimize_for_window(
                optimized_messages, window_size, phases, topic_transitions
            )

        # 6. 记录优化历史
        self.optimization_history.append({
            'timestamp': datetime.now(),
            'original_count': original_count,
            'optimized_count': len(optimized_messages),
            'phases_identified': len(phases),
            'topic_transitions': len(topic_transitions),
            'repetitive_removed': len(repetitive_info),
            'compression_ratio': 1.0 - (len(optimized_messages) / original_count) if original_count > 0 else 0
        })

        return OptimizedHistory(
            messages=optimized_messages,
            phases=phases,
            metadata={
                'original_count': original_count,
                'optimized_count': len(optimized_messages),
                'optimization_needed': True,
                'phases': [phase.value for phase in phases],
                'topic_transitions': len(topic_transitions),
                'repetitive_removed': len(repetitive_info),
                'compression_ratio': 1.0 - (len(optimized_messages) / original_count) if original_count > 0 else 0
            }
        )

    async def _identify_conversation_phases(
        self,
        messages: List['Message']
    ) -> List[ConversationPhase]:
        """识别对话阶段"""
        if not messages:
            return []

        phases = []

        # 基于消息内容和位置识别阶段
        total_messages = len(messages)

        for i, message in enumerate(messages):
            # 开场阶段（前20%）
            if i < total_messages * 0.2:
                phases.append(ConversationPhase.OPENING)

            # 探索阶段（20%-50%）
            elif i < total_messages * 0.5:
                # 检查是否包含探索性关键词
                if any(keyword in message.content.lower()
                      for keyword in ['如何', '怎么', 'what', 'how', 'explore']):
                    phases.append(ConversationPhase.EXPLORATION)
                else:
                    phases.append(ConversationPhase.DISCUSSION)

            # 讨论阶段（50%-80%）
            elif i < total_messages * 0.8:
                phases.append(ConversationPhase.DISCUSSION)

            # 决策阶段（最后20%）
            else:
                # 检查是否包含决策关键词
                if any(keyword in message.content.lower()
                      for keyword in ['决定', '确认', '选择', 'decide', 'confirm']):
                    phases.append(ConversationPhase.DECISION)
                else:
                    phases.append(ConversationPhase.CLOSING)

        return phases

    async def _optimize_for_window(
        self,
        messages: List['Message'],
        window_size: int,
        phases: List[ConversationPhase],
        topic_transitions: List[TopicTransition]
    ) -> List['Message']:
        """为窗口大小优化消息"""
        if len(messages) <= window_size:
            return messages

        # 优先保留重要阶段的消息
        phase_importance = {
            ConversationPhase.OPENING: 0.7,
            ConversationPhase.EXPLORATION: 0.6,
            ConversationPhase.DISCUSSION: 0.8,
            ConversationPhase.DECISION: 0.9,
            ConversationPhase.CLOSING: 0.75,
            ConversationPhase.UNKNOWN: 0.5
        }

        # 为每条消息计算重要性分数
        message_scores = []
        for i, message in enumerate(messages):
            # 基础分数
            base_score = 0.5

            # 阶段重要性
            if i < len(phases):
                phase_score = phase_importance.get(phases[i], 0.5)
                base_score += phase_score * 0.3

            # 时间新鲜度
            recency_score = (i + 1) / len(messages) * 0.2
            base_score += recency_score

            # 消息长度
            if message.token_count > 100:
                base_score += 0.1

            message_scores.append((i, message, base_score))

        # 按分数排序并选择前N条
        message_scores.sort(key=lambda x: x[2], reverse=True)
        selected_indices = {idx for idx, _, _ in message_scores[:window_size]}

        # 按原始顺序排列
        optimized_messages = [
            msg for i, msg in enumerate(messages)
            if i in selected_indices
        ]
        optimized_messages.sort(key=lambda m: messages.index(m) if m in messages else float('inf'))

        return optimized_messages

    def get_optimization_statistics(self) -> Dict[str, Any]:
        """获取优化统计信息"""
        if not self.optimization_history:
            return {}

        recent_optimizations = self.optimization_history[-10:]  # 最近10次

        return {
            'total_optimizations': len(self.optimization_history),
            'average_compression_ratio': sum(
                o['compression_ratio'] for o in recent_optimizations
            ) / len(recent_optimizations) if recent_optimizations else 0,
            'average_repetitive_removed': sum(
                o['repetitive_removed'] for o in recent_optimizations
            ) / len(recent_optimizations) if recent_optimizations else 0,
            'most_common_phase_count': self._get_most_common_phase_count(recent_optimizations)
        }

    def _get_most_common_phase_count(self, optimizations: List[Dict]) -> int:
        """获取最常见的阶段数量"""
        phase_counts = [o['phases_identified'] for o in optimizations]
        if not phase_counts:
            return 0

        from collections import Counter
        counter = Counter(phase_counts)
        return counter.most_common(1)[0][0]


# 导入Message类型
from .compressor import Message
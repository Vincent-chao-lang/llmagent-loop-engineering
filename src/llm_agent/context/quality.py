"""
多轮对话质量维护器 - 确保长对话的质量和连贯性
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re


class QualityDimension(Enum):
    """质量维度"""
    COHERENCE = "coherence"           # 连贯性
    RELEVANCE = "relevance"          # 相关性
    CONSISTENCY = "consistency"      # 一致性
    SATISFACTION = "satisfaction"    # 满意度
    COMPLETENESS = "completeness"    # 完整性


@dataclass
class QualityMetrics:
    """质量指标"""
    coherence: float = 0.0           # 连贯性 (0.0-1.0)
    context_relevance: float = 0.0   # 上下文相关性 (0.0-1.0)
    decision_consistency: float = 0.0 # 决策一致性 (0.0-1.0)
    user_satisfaction: float = 0.0   # 用户满意度 (0.0-1.0)
    completeness: float = 0.0         # 完整性 (0.0-1.0)

    def overall_score(self) -> float:
        """计算总体质量分数"""
        return (
            self.coherence * 0.3 +
            self.context_relevance * 0.25 +
            self.decision_consistency * 0.2 +
            self.user_satisfaction * 0.15 +
            self.completeness * 0.1
        )


@dataclass
class QualityReport:
    """质量报告"""
    metrics: QualityMetrics
    overall_score: float
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Conversation:
    """对话对象"""
    def __init__(self, messages: List['Message']):
        """初始化对话对象

        Args:
            messages: 消息列表
        """
        self.messages = messages
        self.metadata = {}

    def get_recent_context(self, window_size: int = 5) -> str:
        """获取最近的上下文"""
        recent_messages = self.messages[-window_size:] if len(self.messages) >= window_size else self.messages
        return " ".join([msg.content for msg in recent_messages])

    def __len__(self) -> int:
        return len(self.messages)


class MultiTurnQualityMaintainer:
    """
    多轮对话质量维护器

    监控和维护多轮对话的质量，确保长对话的连贯性和满意度。
    """

    def __init__(self):
        """初始化质量维护器"""
        self.quality_history = []
        self.thresholds = {
            'coherence': 0.7,
            'relevance': 0.75,
            'consistency': 0.8,
            'satisfaction': 0.7,
            'completeness': 0.6
        }

    async def maintain_quality(self, conversation: Conversation) -> QualityReport:
        """维护对话质量

        Args:
            conversation: 对话对象

        Returns:
            质量报告
        """
        if len(conversation) < 2:
            return QualityReport(
                metrics=QualityMetrics(coherence=1.0, context_relevance=1.0),
                overall_score=1.0,
                recommendations=["对话太短，无法进行质量评估"],
                metadata={'conversation_length': len(conversation)}
            )

        # 1. 检查信息连贯性
        coherence = await self._check_coherence(conversation)

        # 2. 检查上下文相关性
        context_relevance = await self._check_context_relevance(conversation)

        # 3. 检查决策一致性
        decision_consistency = await self._check_decision_consistency(conversation)

        # 4. 估算用户满意度
        user_satisfaction = await self._estimate_user_satisfaction(conversation)

        # 5. 检查完整性
        completeness = await self._check_completeness(conversation)

        # 构建质量指标
        metrics = QualityMetrics(
            coherence=coherence,
            context_relevance=context_relevance,
            decision_consistency=decision_consistency,
            user_satisfaction=user_satisfaction,
            completeness=completeness
        )

        overall_score = metrics.overall_score()

        # 生成建议和警告
        recommendations, warnings = self._generate_recommendations_and_warnings(metrics, overall_score)

        # 记录质量历史
        self.quality_history.append({
            'timestamp': datetime.now(),
            'conversation_length': len(conversation),
            'metrics': metrics,
            'overall_score': overall_score
        })

        return QualityReport(
            metrics=metrics,
            overall_score=overall_score,
            recommendations=recommendations,
            warnings=warnings,
            metadata={
                'conversation_length': len(conversation),
                'thresholds': self.thresholds,
                'quality_trend': self._analyze_quality_trend()
            }
        )

    async def _check_coherence(self, conversation: Conversation) -> float:
        """检查对话连贯性"""
        if len(conversation) < 2:
            return 1.0

        coherence_scores = []

        for i in range(1, len(conversation.messages)):
            prev_message = conversation.messages[i-1]
            curr_message = conversation.messages[i]

            # 1. 话题连贯性
            topic_coherence = self._check_topic_coherence(prev_message, curr_message)

            # 2. 逻辑连贯性
            logical_coherence = self._check_logical_coherence(prev_message, curr_message)

            # 3. 语言连贯性
            linguistic_coherence = self._check_linguistic_coherence(prev_message, curr_message)

            # 综合连贯性
            message_coherence = (
                topic_coherence * 0.4 +
                logical_coherence * 0.4 +
                linguistic_coherence * 0.2
            )

            coherence_scores.append(message_coherence)

        return sum(coherence_scores) / len(coherence_scores) if coherence_scores else 0.5

    def _check_topic_coherence(self, prev_message: 'Message', curr_message: 'Message') -> float:
        """检查话题连贯性"""
        # 提取关键词
        prev_keywords = set(re.findall(r'\b\w{3,}\b', prev_message.content.lower()))
        curr_keywords = set(re.findall(r'\b\w{3,}\b', curr_message.content.lower()))

        if not prev_keywords or not curr_keywords:
            return 0.5

        # 计算关键词重叠度
        overlap = len(prev_keywords & curr_keywords)
        union = len(prev_keywords | curr_keywords)

        return overlap / union if union > 0 else 0.5

    def _check_logical_coherence(self, prev_message: 'Message', curr_message: 'Message') -> float:
        """检查逻辑连贯性"""
        # 检查是否回答了问题
        if prev_message.role == "user" and self._is_question(prev_message.content):
            if curr_message.role == "assistant":
                # 检查是否包含回答
                if any(indicator in curr_message.content
                      for indicator in ['是', '不是', '可以', '不可以', 'yes', 'no', '因为', '所以']):
                    return 0.9
                return 0.6
            return 0.3

        # 检查对话流程的合理性
        if curr_message.role == "user":
            # 用户消息应该有某种关联
            return 0.7  # 默认给予中等连贯性

        return 0.8  # 默认较高连贯性

    def _check_linguistic_coherence(self, prev_message: 'Message', curr_message: 'Message') -> float:
        """检查语言连贯性"""
        # 简化实现：检查引用词的使用
        reference_words = ['它', '这', '那', '他', '她', 'it', 'this', 'that', 'he', 'she']
        has_reference = any(word in curr_message.content for word in reference_words)

        if has_reference:
            return 0.8  # 使用引用词表示连贯性较好
        else:
            return 0.6  # 没有引用词，连贯性一般

    def _is_question(self, text: str) -> bool:
        """判断是否是问题"""
        question_indicators = ['?', '？', '如何', '怎么', '什么', '为什么', 'how', 'what', 'why', 'when', 'where']
        return any(indicator in text for indicator in question_indicators)

    async def _check_context_relevance(self, conversation: Conversation) -> float:
        """检查上下文相关性"""
        if len(conversation) < 2:
            return 1.0

        relevance_scores = []

        for i, message in enumerate(conversation.messages):
            # 计算与上下文的相关性
            context_window = conversation.messages[:i]
            if context_window:
                relevance = self._calculate_message_context_relevance(message, context_window)
                relevance_scores.append(relevance)
            else:
                relevance_scores.append(1.0)  # 第一条消息默认完全相关

        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.5

    def _calculate_message_context_relevance(self, message: 'Message', context: List['Message']) -> float:
        """计算消息与上下文的相关性"""
        if not context:
            return 1.0

        # 提取当前消息的关键词
        message_keywords = set(re.findall(r'\b\w{3,}\b', message.content.lower()))

        # 提取上下文的关键词
        context_keywords = set()
        for ctx_msg in context:
            context_keywords.update(re.findall(r'\b\w{3,}\b', ctx_msg.content.lower()))

        if not message_keywords or not context_keywords:
            return 0.5

        # 计算相关性
        overlap = len(message_keywords & context_keywords)
        relevance = overlap / len(message_keywords) if message_keywords else 0

        return min(1.0, relevance * 2)  # 放大相关性

    async def _check_decision_consistency(self, conversation: Conversation) -> float:
        """检查决策一致性"""
        if len(conversation) < 3:
            return 1.0

        # 提取所有决策
        decisions = []
        for i, message in enumerate(conversation.messages):
            if self._contains_decision(message.content):
                decision_content = self._extract_decision_content(message.content)
                if decision_content:
                    decisions.append({
                        'index': i,
                        'content': decision_content,
                        'timestamp': message.timestamp
                    })

        if len(decisions) < 2:
            return 1.0  # 没有足够决策，默认一致

        # 检查决策之间的一致性
        consistency_scores = []
        for i in range(len(decisions) - 1):
            decision1 = decisions[i]
            decision2 = decisions[i + 1]

            consistency = self._compare_decisions(decision1['content'], decision2['content'])
            consistency_scores.append(consistency)

        return sum(consistency_scores) / len(consistency_scores) if consistency_scores else 0.5

    def _contains_decision(self, text: str) -> bool:
        """判断是否包含决策"""
        decision_words = ['决定', '选择', '采用', '确认', 'decide', 'choose', 'select', 'confirm']
        return any(word in text.lower() for word in decision_words)

    def _extract_decision_content(self, text: str) -> str:
        """提取决策内容"""
        # 简化实现：提取包含决策词的句子
        sentences = re.split(r'[。！？.!?]', text)
        for sentence in sentences:
            if self._contains_decision(sentence):
                return sentence.strip()
        return ""

    def _compare_decisions(self, decision1: str, decision2: str) -> float:
        """比较两个决策的一致性"""
        # 提取关键词
        keywords1 = set(re.findall(r'\b\w{3,}\b', decision1.lower()))
        keywords2 = set(re.findall(r'\b\w{3,}\b', decision2.lower()))

        if not keywords1 or not keywords2:
            return 0.5

        # 检查是否有冲突
        conflict_indicators = ['但是', '然而', '改变', '撤销', 'but', 'however', 'change', 'revert']
        has_conflict = any(
            indicator in decision1.lower() or indicator in decision2.lower()
            for indicator in conflict_indicators
        )

        if has_conflict:
            return 0.3  # 有冲突，一致性低

        # 计算相似度
        overlap = len(keywords1 & keywords2)
        union = len(keywords1 | keywords2)

        similarity = overlap / union if union > 0 else 0

        return 0.5 + similarity * 0.5  # 基础0.5 + 相似度加成

    async def _estimate_user_satisfaction(self, conversation: Conversation) -> float:
        """估算用户满意度"""
        if not conversation.messages:
            return 0.5

        satisfaction_indicators = 0
        total_user_messages = 0

        for message in conversation.messages:
            if message.role == "user":
                total_user_messages += 1

                # 检查满意度指标
                if any(word in message.content for word in ['好', '不错', '谢谢', '满意', 'good', 'thanks', 'great']):
                    satisfaction_indicators += 1

                # 检查不满意指标
                elif any(word in message.content for word in ['不好', '不满意', '问题', '错误', 'bad', 'problem', 'wrong']):
                    satisfaction_indicators -= 1

        if total_user_messages == 0:
            return 0.5

        # 归一化到0-1范围
        satisfaction_ratio = satisfaction_indicators / total_user_messages
        normalized = (satisfaction_ratio + 1) / 2  # 从[-1,1]映射到[0,1]

        return max(0.0, min(1.0, normalized))

    async def _check_completeness(self, conversation: Conversation) -> float:
        """检查完整性"""
        if len(conversation) < 2:
            return 0.5

        # 检查是否所有问题都得到了回答
        questions_asked = 0
        questions_answered = 0

        for i, message in enumerate(conversation.messages):
            if message.role == "user" and self._is_question(message.content):
                questions_asked += 1

                # 检查下一条消息是否是回答
                if i + 1 < len(conversation.messages):
                    next_message = conversation.messages[i + 1]
                    if next_message.role == "assistant":
                        # 简化判断：只要有回应就算回答
                        questions_answered += 1

        if questions_asked == 0:
            return 1.0  # 没有问题，完整性满分

        completeness = questions_answered / questions_asked
        return completeness

    def _generate_recommendations_and_warnings(
        self,
        metrics: QualityMetrics,
        overall_score: float
    ) -> Tuple[List[str], List[str]]:
        """生成建议和警告"""
        recommendations = []
        warnings = []

        # 基于各个指标生成建议
        if metrics.coherence < self.thresholds['coherence']:
            recommendations.append("建议改进对话连贯性，保持话题一致性")
            warnings.append(f"连贯性({metrics.coherence:.2f})低于阈值({self.thresholds['coherence']})")

        if metrics.context_relevance < self.thresholds['relevance']:
            recommendations.append("建议增强与上下文的相关性")
            warnings.append(f"相关性({metrics.context_relevance:.2f})低于阈值({self.thresholds['relevance']})")

        if metrics.decision_consistency < self.thresholds['consistency']:
            recommendations.append("建议保持决策的一致性，避免频繁改变")
            warnings.append(f"决策一致性({metrics.decision_consistency:.2f})低于阈值({self.thresholds['consistency']})")

        if metrics.user_satisfaction < self.thresholds['satisfaction']:
            recommendations.append("建议关注用户反馈，提升响应质量")
            warnings.append(f"用户满意度({metrics.user_satisfaction:.2f})低于阈值({self.thresholds['satisfaction']})")

        if metrics.completeness < self.thresholds['completeness']:
            recommendations.append("建议确保回答所有用户问题")
            warnings.append(f"完整性({metrics.completeness:.2f})低于阈值({self.thresholds['completeness']})")

        # 基于总体评分生成建议
        if overall_score < 0.5:
            recommendations.append("对话质量严重偏低，建议重新审视整体对话策略")
        elif overall_score < 0.7:
            recommendations.append("对话质量需要改进，建议重点优化薄弱环节")

        return recommendations, warnings

    def _analyze_quality_trend(self) -> str:
        """分析质量趋势"""
        if len(self.quality_history) < 3:
            return "insufficient_data"

        recent_scores = [record['overall_score'] for record in self.quality_history[-5:]]

        # 简单趋势分析
        if len(recent_scores) < 2:
            return "stable"

        # 计算趋势
        first_half = recent_scores[:len(recent_scores)//2]
        second_half = recent_scores[len(recent_scores)//2:]

        avg_first = sum(first_half) / len(first_half)
        avg_second = sum(second_half) / len(second_half)

        if avg_second > avg_first * 1.1:
            return "improving"
        elif avg_second < avg_first * 0.9:
            return "declining"
        else:
            return "stable"

    def get_quality_statistics(self) -> Dict[str, Any]:
        """获取质量统计信息"""
        if not self.quality_history:
            return {}

        recent_records = self.quality_history[-20:]  # 最近20次

        return {
            'total_evaluations': len(self.quality_history),
            'average_quality': sum(r['overall_score'] for r in recent_records) / len(recent_records) if recent_records else 0,
            'quality_trend': self._analyze_quality_trend(),
            'below_threshold_count': len([
                r for r in recent_records
                if r['overall_score'] < 0.7
            ]),
            'dimension_averages': self._calculate_dimension_averages(recent_records)
        }

    def _calculate_dimension_averages(self, records: List[Dict]) -> Dict[str, float]:
        """计算各维度平均值"""
        if not records:
            return {}

        dimension_sums = {
            'coherence': 0,
            'context_relevance': 0,
            'decision_consistency': 0,
            'user_satisfaction': 0,
            'completeness': 0
        }

        for record in records:
            metrics = record['metrics']
            dimension_sums['coherence'] += metrics.coherence
            dimension_sums['context_relevance'] += metrics.context_relevance
            dimension_sums['decision_consistency'] += metrics.decision_consistency
            dimension_sums['user_satisfaction'] += metrics.user_satisfaction
            dimension_sums['completeness'] += metrics.completeness

        count = len(records)
        return {dim: total / count for dim, total in dimension_sums.items()}


# 导入Message类型
from .compressor import Message
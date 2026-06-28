"""
关键信息保留器 - 确保压缩过程中关键信息不丢失
"""

import asyncio
from typing import List, Dict, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import re
from collections import Counter


class EntityType(Enum):
    """实体类型"""
    USER = "user"           # 用户信息
    SYSTEM = "system"       # 系统信息
    PREFERENCE = "preference"  # 偏好设置
    CONSTRAINT = "constraint"  # 约束条件
    DECISION = "decision"   # 决策信息
    DOMAIN = "domain"       # 领域知识
    METADATA = "metadata"   # 元数据


@dataclass
class RetentionConfig:
    """保留配置"""
    # 要保留的实体类型
    entity_types: List[EntityType] = field(default_factory=lambda: [
        EntityType.USER,
        EntityType.PREFERENCE,
        EntityType.CONSTRAINT,
        EntityType.DECISION
    ])

    # 重要性阈值
    min_importance_threshold: float = 0.6

    # 最大保留数量
    max_entities_per_type: int = 10

    # 是否启用语义相似度检测
    enable_semantic_similarity: bool = True

    # 相似度阈值（用于去重）
    similarity_threshold: float = 0.8


@dataclass
class KeyEntity:
    """关键实体"""
    id: str
    content: str
    entity_type: EntityType
    importance: float
    source_message_id: int
    confidence: float = 0.8
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.entity_type.value}: {self.content} (importance: {self.importance})"


@dataclass
class EntityPattern:
    """实体识别模式"""
    pattern: str
    entity_type: EntityType
    importance_boost: float = 0.1
    description: str = ""


class EntityExtractor:
    """实体提取器"""

    def __init__(self):
        """初始化实体提取器"""
        self.patterns = self._initialize_patterns()

    def _initialize_patterns(self) -> List[EntityPattern]:
        """初始化实体识别模式"""
        return [
            # 用户相关
            EntityPattern(
                r'(用户|客户端|client|user)\s*[:：]?\s*([A-Za-z0-9_\-]+)',
                EntityType.USER,
                0.2,
                "用户标识符"
            ),
            EntityPattern(
                r'(我叫|我是|我的名字|my name is|i am)\s*([A-Za-z一-鿿]+)',
                EntityType.USER,
                0.15,
                "用户姓名"
            ),

            # 偏好相关
            EntityPattern(
                r'(我喜欢|我偏好|我倾向|i prefer|i like)\s*([^，。！？.!?]+)',
                EntityType.PREFERENCE,
                0.1,
                "用户偏好"
            ),
            EntityPattern(
                r'(希望|想要|期望|want|wish)\s*([^，。！？.!?]+)',
                EntityType.PREFERENCE,
                0.1,
                "用户期望"
            ),

            # 约束相关
            EntityPattern(
                r'(限制|约束|不能|必须|要求|limit|constraint|must|cannot)\s*([^，。！？.!?]+)',
                EntityType.CONSTRAINT,
                0.2,
                "约束条件"
            ),
            EntityPattern(
                r'(最大|最小|最多|至少|max|min|maximum|minimum)\s*([^，。！？.!?]+)',
                EntityType.CONSTRAINT,
                0.15,
                "数值约束"
            ),

            # 决策相关
            EntityPattern(
                r'(决定|选择|采用|使用|decide|choose|select|adopt)\s*([^，。！？.!?]+)',
                EntityType.DECISION,
                0.25,
                "决策内容"
            ),
            EntityPattern(
                r'(确认|确定|agree|confirm)\s*([^，。！？.!?]+)',
                EntityType.DECISION,
                0.2,
                "确认内容"
            ),

            # 领域相关
            EntityPattern(
                r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)',  # 专有名词
                EntityType.DOMAIN,
                0.1,
                "专业术语"
            ),
            EntityPattern(
                r'(\d+\.?\d*)\s*(?:元|美元|百分比|%)',
                EntityType.METADATA,
                0.1,
                "数值信息"
            ),
        ]

    async def extract_entities(
        self,
        text: str,
        message_id: int,
        base_importance: float = 0.5
    ) -> List[KeyEntity]:
        """从文本中提取实体

        Args:
            text: 要分析的文本
            message_id: 消息ID
            base_importance: 基础重要性

        Returns:
            提取的实体列表
        """
        entities = []

        for pattern_obj in self.patterns:
            matches = re.finditer(pattern_obj.pattern, text, re.IGNORECASE)
            for match in matches:
                # 提取实体内容
                if len(match.groups()) >= 2:
                    entity_content = match.group(2).strip()
                else:
                    entity_content = match.group(1).strip()

                if not entity_content or len(entity_content) < 2:
                    continue

                # 计算重要性
                importance = min(1.0, base_importance + pattern_obj.importance_boost)

                # 创建实体
                entity = KeyEntity(
                    id=self._generate_entity_id(pattern_obj.entity_type, entity_content, message_id),
                    content=entity_content,
                    entity_type=pattern_obj.entity_type,
                    importance=importance,
                    source_message_id=message_id,
                    confidence=0.8,
                    metadata={
                        'pattern_type': pattern_obj.description,
                        'match_position': match.start(),
                        'extraction_method': 'pattern_matching'
                    }
                )

                entities.append(entity)

        return entities

    def _generate_entity_id(self, entity_type: EntityType, content: str, message_id: int) -> str:
        """生成实体ID"""
        import hashlib
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        return f"{entity_type.value}_{message_id}_{content_hash}"


class PatternRecognizer:
    """模式识别器"""

    def __init__(self):
        """初始化模式识别器"""
        self.patterns = {
            'question': r'[？?]',
            'command': r'^(请|帮我|help|please)',
            'confirmation': r'(好的|可以|确认|okay|yes|confirm)',
            'rejection': r'(不|不行|拒绝|no|reject)',
            'clarification': r'(也就是说|换句话说|clarify)',
            'transition': r'(接下来|然后|另外|next|then|also)',
        }

    def recognize_patterns(self, text: str) -> Dict[str, List[int]]:
        """识别文本中的模式

        Args:
            text: 要分析的文本

        Returns:
            模式位置字典
        """
        pattern_positions = {}

        for pattern_name, pattern in self.patterns.items():
            matches = list(re.finditer(pattern, text))
            if matches:
                pattern_positions[pattern_name] = [m.start() for m in matches]

        return pattern_positions


class KeyInformationRetainer:
    """
    关键信息保留器

    确保在上下文压缩过程中，重要的关键信息不会丢失。
    """

    def __init__(self, config: RetentionConfig = None):
        """初始化关键信息保留器

        Args:
            config: 保留配置
        """
        self.config = config or RetentionConfig()
        self.entity_extractor = EntityExtractor()
        self.pattern_recognizer = PatternRecognizer()

        # 存储已识别的关键实体
        self.key_entities: Dict[str, KeyEntity] = {}

        # 存储实体使用统计
        self.entity_usage_stats: Dict[str, Dict] = {}

    async def extract_key_entities(
        self,
        messages: List['Message'],
        importance_scores: List['ImportanceScore'] = None
    ) -> List[KeyEntity]:
        """从消息列表中提取关键实体

        Args:
            messages: 消息列表
            importance_scores: 重要性评分（可选）

        Returns:
            关键实体列表
        """
        all_entities = []

        for i, message in enumerate(messages):
            # 获取基础重要性
            base_importance = 0.5
            if importance_scores and i < len(importance_scores):
                base_importance = importance_scores[i].importance

            # 提取实体
            entities = await self.entity_extractor.extract_entities(
                message.content,
                i,
                base_importance
            )

            # 过滤低重要性实体
            filtered_entities = [
                entity for entity in entities
                if entity.importance >= self.config.min_importance_threshold
            ]

            all_entities.extend(filtered_entities)

        # 去重和合并相似实体
        unique_entities = await self._deduplicate_entities(all_entities)

        # 按类型和重要性排序
        unique_entities.sort(key=lambda e: (e.entity_type.value, -e.importance))

        return unique_entities

    async def ensure_retention(
        self,
        compressed_context: List['Message'],
        key_entities: List[KeyEntity],
        max_length: int = None
    ) -> List['Message']:
        """确保关键实体被保留在压缩后的上下文中

        Args:
            compressed_context: 压缩后的上下文
            key_entities: 关键实体列表
            max_length: 最大长度限制

        Returns:
            增强后的上下文
        """
        if not key_entities:
            return compressed_context

        # 检查哪些关键实体丢失了
        missing_entities = await self._find_missing_entities(compressed_context, key_entities)

        if not missing_entities:
            return compressed_context

        # 重新注入丢失的关键实体
        enhanced_context = await self._reinject_key_entities(
            compressed_context,
            missing_entities,
            max_length
        )

        return enhanced_context

    async def _deduplicate_entities(self, entities: List[KeyEntity]) -> List[KeyEntity]:
        """去重和合并相似实体

        Args:
            entities: 实体列表

        Returns:
            去重后的实体列表
        """
        if not entities:
            return []

        # 按类型分组
        entities_by_type: Dict[EntityType, List[KeyEntity]] = {}
        for entity in entities:
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity)

        # 对每种类型进行去重
        deduplicated = []

        for entity_type, type_entities in entities_by_type.items():
            # 按重要性排序
            type_entities.sort(key=lambda e: e.importance, reverse=True)

            # 去重相似实体
            unique_entities = []
            seen_contents = set()

            for entity in type_entities:
                # 检查是否与已有实体相似
                is_duplicate = False
                for seen_content in seen_contents:
                    if self._calculate_similarity(entity.content, seen_content) > self.config.similarity_threshold:
                        is_duplicate = True
                        # 更新已有实体的使用统计
                        self._update_entity_usage(entity.id)
                        break

                if not is_duplicate:
                    unique_entities.append(entity)
                    seen_contents.add(entity.content)

                    # 限制每种类型的数量
                    if len(unique_entities) >= self.config.max_entities_per_type:
                        break

            deduplicated.extend(unique_entities)

        return deduplicated

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """计算文本相似度"""
        # 简单的Jaccard相似度计算
        words1 = set(text1.lower().split())
        words2 = set(text2.lower().split())

        if not words1 or not words2:
            return 0.0

        intersection = len(words1 & words2)
        union = len(words1 | words2)

        return intersection / union if union > 0 else 0.0

    async def _find_missing_entities(
        self,
        compressed_context: List['Message'],
        key_entities: List[KeyEntity]
    ) -> List[KeyEntity]:
        """查找丢失的关键实体

        Args:
            compressed_context: 压缩后的上下文
            key_entities: 关键实体列表

        Returns:
            丢失的实体列表
        """
        missing_entities = []

        # 构建上下文文本集合
        context_texts = [msg.content for msg in compressed_context]

        for entity in key_entities:
            # 检查实体是否在上下文中
            entity_found = False
            for context_text in context_texts:
                if entity.content in context_text:
                    entity_found = True
                    # 更新使用统计
                    self._update_entity_usage(entity.id, found_in_context=True)
                    break

            if not entity_found:
                missing_entities.append(entity)
                # 记录丢失
                self._update_entity_usage(entity.id, found_in_context=False)

        return missing_entities

    async def _reinject_key_entities(
        self,
        compressed_context: List['Message'],
        missing_entities: List[KeyEntity],
        max_length: int = None
    ) -> List['Message']:
        """重新注入丢失的关键实体

        Args:
            compressed_context: 压缩后的上下文
            missing_entities: 丢失的实体列表
            max_length: 最大长度限制

        Returns:
            增强后的上下文
        """
        if not missing_entities:
            return compressed_context

        # 按重要性排序丢失的实体
        missing_entities.sort(key=lambda e: e.importance, reverse=True)

        # 构建关键信息摘要
        key_info_summary = self._build_key_info_summary(missing_entities)

        # 创建关键信息消息
        key_info_message = Message(
            role="system",
            content=key_info_summary,
            timestamp=datetime.now(),
            token_count=self._estimate_tokens(key_info_summary),
            metadata={
                'type': 'key_information_reinjection',
                'entity_count': len(missing_entities),
                'entity_types': [e.entity_type.value for e in missing_entities]
            }
        )

        # 检查长度限制
        if max_length:
            current_length = sum(msg.token_count for msg in compressed_context)
            if current_length + key_info_message.token_count > max_length:
                # 尝试只保留最重要的实体
                top_entities = missing_entities[:3]  # 只保留前3个最重要的
                key_info_summary = self._build_key_info_summary(top_entities)
                key_info_message.content = key_info_summary
                key_info_message.token_count = self._estimate_tokens(key_info_summary)

                # 如果还是太长，就放弃注入
                if current_length + key_info_message.token_count > max_length:
                    return compressed_context

        # 在开头插入关键信息消息
        enhanced_context = [key_info_message] + compressed_context

        return enhanced_context

    def _build_key_info_summary(self, entities: List[KeyEntity]) -> str:
        """构建关键信息摘要"""
        if not entities:
            return ""

        # 按类型分组
        entities_by_type: Dict[EntityType, List[str]] = {}
        for entity in entities:
            if entity.entity_type not in entities_by_type:
                entities_by_type[entity.entity_type] = []
            entities_by_type[entity.entity_type].append(entity.content)

        # 构建摘要文本
        summary_parts = ["重要历史信息："]

        type_descriptions = {
            EntityType.USER: "用户信息",
            EntityType.PREFERENCE: "偏好设置",
            EntityType.CONSTRAINT: "约束条件",
            EntityType.DECISION: "决策记录",
            EntityType.DOMAIN: "专业术语",
            EntityType.METADATA: "关键数据"
        }

        for entity_type, contents in entities_by_type.items():
            type_desc = type_descriptions.get(entity_type, entity_type.value)
            summary_parts.append(f"{type_desc}: {', '.join(contents[:3])}")

        return " | ".join(summary_parts)

    def _estimate_tokens(self, text: str) -> int:
        """估算文本的token数量"""
        if not text:
            return 0
        # 简单估算：平均每个词1.3个token
        return int(len(text.split()) * 1.3)

    def _update_entity_usage(self, entity_id: str, found_in_context: bool = True):
        """更新实体使用统计"""
        if entity_id not in self.entity_usage_stats:
            self.entity_usage_stats[entity_id] = {
                'total_checks': 0,
                'found_count': 0,
                'missing_count': 0,
                'last_updated': datetime.now()
            }

        stats = self.entity_usage_stats[entity_id]
        stats['total_checks'] += 1
        stats['last_updated'] = datetime.now()

        if found_in_context:
            stats['found_count'] += 1
        else:
            stats['missing_count'] += 1

    async def evaluate_retention_quality(
        self,
        original_entities: List[KeyEntity],
        final_context: List['Message']
    ) -> Dict[str, Any]:
        """评估保留质量

        Args:
            original_entities: 原始实体列表
            final_context: 最终上下文

        Returns:
            保留质量指标
        """
        if not original_entities:
            return {
                'total_entities': 0,
                'retained_entities': 0,
                'retention_rate': 1.0,
                'by_type': {}
            }

        # 检查每个实体是否被保留
        retained_by_type: Dict[EntityType, int] = {}
        total_by_type: Dict[EntityType, int] = {}

        for entity in original_entities:
            # 统计总数
            if entity.entity_type not in total_by_type:
                total_by_type[entity.entity_type] = 0
            total_by_type[entity.entity_type] += 1

            # 检查是否被保留
            entity_found = any(entity.content in msg.content for msg in final_context)
            if entity_found:
                if entity.entity_type not in retained_by_type:
                    retained_by_type[entity.entity_type] = 0
                retained_by_type[entity.entity_type] += 1

        # 计算总保留率
        total_retained = sum(retained_by_type.values())
        total_entities = len(original_entities)
        overall_retention_rate = total_retained / total_entities if total_entities > 0 else 1.0

        # 计算各类别保留率
        by_type_retention = {}
        for entity_type, total in total_by_type.items():
            retained = retained_by_type.get(entity_type, 0)
            by_type_retention[entity_type.value] = retained / total if total > 0 else 0

        return {
            'total_entities': total_entities,
            'retained_entities': total_retained,
            'retention_rate': overall_retention_rate,
            'by_type': by_type_retention,
            'missing_entities': total_entities - total_retained
        }

    def get_entity_statistics(self) -> Dict[str, Any]:
        """获取实体统计信息"""
        if not self.entity_usage_stats:
            return {}

        # 计算统计指标
        total_entities = len(self.entity_usage_stats)
        retention_rates = []

        for entity_id, stats in self.entity_usage_stats.items():
            if stats['total_checks'] > 0:
                retention_rate = stats['found_count'] / stats['total_checks']
                retention_rates.append(retention_rate)

        average_retention_rate = (
            sum(retention_rates) / len(retention_rates)
            if retention_rates else 0
        )

        return {
            'total_entities_tracked': total_entities,
            'average_retention_rate': average_retention_rate,
            'high_risk_entities': len([
                e for e, s in self.entity_usage_stats.items()
                if s.get('missing_count', 0) > s.get('found_count', 0)
            ]),
            'most_missed_entities': self._get_most_missed_entities(limit=5)
        }

    def _get_most_missed_entities(self, limit: int = 5) -> List[Dict[str, Any]]:
        """获取最容易丢失的实体"""
        entity_miss_rates = []

        for entity_id, stats in self.entity_usage_stats.items():
            if stats['total_checks'] > 0:
                miss_rate = stats['missing_count'] / stats['total_checks']
                entity_miss_rates.append({
                    'entity_id': entity_id,
                    'miss_rate': miss_rate,
                    'total_checks': stats['total_checks'],
                    'missing_count': stats['missing_count']
                })

        # 按丢失率排序
        entity_miss_rates.sort(key=lambda x: x['miss_rate'], reverse=True)

        return entity_miss_rates[:limit]


# 导入Message类型（避免循环导入）
from .compressor import Message
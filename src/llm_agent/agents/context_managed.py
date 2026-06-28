"""
增强版LLM Agent - 集成窗口上下文管理功能

在原有LLMAgent基础上，添加智能上下文压缩和管理能力，
支持在有限窗口下进行更长的对话。
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime
import uuid
import sys
sys.path.insert(0, 'src')

from llm_agent.agents.base import LLMAgent, AgentResponse, ExecutionPlan, ExecutionResult, Reflection
from llm_agent.context import (
    ContextCompressor, CompressionStrategy,
    KeyInformationRetainer, EntityType, RetentionConfig,
    DynamicContextManager, WindowConfig,
    ConversationHistoryOptimizer,
    MultiTurnQualityMaintainer, Conversation,
    Message, create_message
)


@dataclass
class ContextManagementConfig:
    """上下文管理配置"""
    # 是否启用上下文管理
    enabled: bool = True

    # 窗口配置
    max_window_size: int = 8000  # 最大窗口大小
    reserve_space: int = 1000     # 预留空间

    # 压缩配置
    compression_strategy: CompressionStrategy = CompressionStrategy.INTELLIGENT
    preserve_key_info: bool = True
    auto_compress_threshold: float = 0.8  # 使用率达到80%时自动压缩

    # 质量监控
    enable_quality_monitoring: bool = True
    min_quality_threshold: float = 0.6

    # 关键信息保护
    entity_types_to_protect: List[EntityType] = field(default_factory=lambda: [
        EntityType.USER, EntityType.DECISION, EntityType.CONSTRAINT
    ])
    min_entity_importance: float = 0.6


class ContextManagedLLMAgent(LLMAgent):
    """
    具备上下文管理能力的增强版LLM Agent

    在原有LLMAgent基础上添加：
    - 自动上下文压缩
    - 关键信息保护
    - 动态窗口管理
    - 对话质量监控
    """

    def __init__(
        self,
        llm_client,
        system_prompt: str,
        agent_role: str,
        memory,
        tools=None,
        planning_strategy: str = "auto",
        context_config: ContextManagementConfig = None
    ):
        """初始化增强版LLM Agent

        Args:
            llm_client: LLM客户端
            system_prompt: 系统提示词
            agent_role: Agent角色
            memory: 记忆系统
            tools: 工具列表（可选）
            planning_strategy: 规划策略（可选）
            context_config: 上下文管理配置（可选）
        """
        # 初始化父类
        super().__init__(
            llm_client=llm_client,
            system_prompt=system_prompt,
            agent_role=agent_role,
            memory=memory,
            tools=tools,
            planning_strategy=planning_strategy
        )

        # 上下文管理配置
        self.context_config = context_config or ContextManagementConfig()

        # 对话历史
        self.conversation_history: List[Message] = []

        # 初始化上下文管理组件
        if self.context_config.enabled:
            self._init_context_managers()

        # 上下文管理统计
        self.context_stats = {
            'total_compressions': 0,
            'total_key_entities_protected': 0,
            'average_quality_score': 0.0,
            'last_compression_time': None
        }

    def _init_context_managers(self):
        """初始化上下文管理组件"""
        # 压缩器
        self.compressor = ContextCompressor(self.context_config.compression_strategy)

        # 关键信息保留器
        retainer_config = RetentionConfig(
            entity_types=self.context_config.entity_types_to_protect,
            min_importance_threshold=self.context_config.min_entity_importance
        )
        self.key_retainer = KeyInformationRetainer(retainer_config)

        # 动态管理器
        window_config = WindowConfig(
            max_window_size=self.context_config.max_window_size,
            reserve_space=self.context_config.reserve_space,
            allocation_strategy="intelligent"
        )
        self.dynamic_manager = DynamicContextManager(window_config)

        # 对话优化器
        self.conversation_optimizer = ConversationHistoryOptimizer()

        # 质量维护器
        if self.context_config.enable_quality_monitoring:
            self.quality_maintainer = MultiTurnQualityMaintainer()

    async def think(self, input: str, enable_context_management: bool = None) -> AgentResponse:
        """增强版思考能力 - 支持上下文管理

        Args:
            input: 输入信息
            enable_context_management: 是否启用上下文管理（可选，默认使用配置）

        Returns:
            AgentResponse: Agent的思考结果
        """
        # 确定是否启用上下文管理
        should_manage_context = enable_context_management
        if should_manage_context is None:
            should_manage_context = self.context_config.enabled

        # 如果启用上下文管理，使用增强流程
        if should_manage_context and self.context_config.enabled:
            # 确保管理器已初始化
            if not hasattr(self, 'dynamic_manager'):
                self._init_context_managers()
            return await self._think_with_context_management(input)
        else:
            # 否则使用原始流程
            return await super().think(input)

    async def _think_with_context_management(self, input: str) -> AgentResponse:
        """带上下文管理的思考流程"""
        # 0. 检查思考次数限制
        self.think_call_count += 1
        if self.think_call_count > self.max_think_calls:
            raise Exception(
                f"已达到最大思考次数限制 ({self.max_think_calls})，"
                f"可能陷入无限循环。当前任务: {input[:100]}"
            )

        # 1. 添加新输入到对话历史
        new_message = create_message("user", input)
        self.conversation_history.append(new_message)

        # 2. 智能上下文管理
        managed_context = await self._manage_conversation_context(new_message)

        # 3. 检索相关记忆
        memory_context = await self._retrieve_context(input)

        # 4. 构建完整提示
        full_prompt = self._build_enhanced_prompt(input, managed_context, memory_context)

        # 5. LLM推理
        try:
            response = await self.llm.chat(
                prompt=full_prompt,
                system_prompt=self.system_prompt
            )

            # 6. 添加响应到对话历史
            assistant_message = create_message("assistant", response.content)
            self.conversation_history.append(assistant_message)

            # 7. 存储新记忆
            await self._store_memory(input, response)

            # 8. 更新状态
            self.execution_count += 1
            self.last_activity = datetime.now()

            # 9. 质量监控（如果启用）
            if self.context_config.enable_quality_monitoring:
                await self._monitor_conversation_quality()

            return AgentResponse(
                content=response.content,
                reasoning=response.reasoning,
                confidence=response.confidence,
                metadata={
                    "agent_id": self.agent_id,
                    "agent_role": self.agent_role,
                    "timestamp": datetime.now().isoformat(),
                    "context_managed": True,
                    "conversation_length": len(self.conversation_history),
                    "context_compression_applied": self._was_compression_applied()
                }
            )

        except Exception as e:
            return AgentResponse(
                content=f"思考过程出错: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )

    async def _manage_conversation_context(self, new_message: Message) -> List[Message]:
        """管理对话上下文

        Args:
            new_message: 新的消息

        Returns:
            管理后的上下文列表
        """
        if not self.conversation_history:
            return []

        # 1. 分析当前上下文使用情况
        current_usage = await self.dynamic_manager.analyzer.analyze_usage(
            self.conversation_history
        )

        # 2. 检查是否需要压缩
        utilization_rate = current_usage['total_tokens'] / self.context_config.max_window_size

        if utilization_rate < self.context_config.auto_compress_threshold:
            # 不需要压缩，直接返回当前历史
            return self.conversation_history

        # 3. 需要压缩，执行智能压缩流程
        return await self._intelligent_context_compression()

    async def _intelligent_context_compression(self) -> List[Message]:
        """智能上下文压缩流程"""
        original_length = len(self.conversation_history)
        original_tokens = sum(msg.token_count for msg in self.conversation_history)

        # 1. 分析重要性
        importance_scores = await self.compressor._analyze_importance(
            self.conversation_history
        )

        # 2. 提取关键信息
        key_entities = await self.key_retainer.extract_key_entities(
            self.conversation_history, importance_scores
        )

        # 3. 压缩上下文
        target_length = int(self.context_config.max_window_size * 0.7)  # 压缩到70%
        compressed = await self.compressor.compress_context(
            self.conversation_history,
            target_length=target_length,
            preserve_key_info=True
        )

        # 4. 确保关键信息保留
        enhanced_context = await self.key_retainer.ensure_retention(
            compressed.messages,
            key_entities,
            max_length=int(self.context_config.max_window_size * 0.8)
        )

        # 5. 优化对话历史
        optimized = await self.conversation_optimizer.optimize_history(
            enhanced_context,
            window_size=int(self.context_config.max_window_size * 0.75)
        )

        # 6. 更新对话历史
        self.conversation_history = optimized.messages

        # 7. 更新统计
        self.context_stats['total_compressions'] += 1
        self.context_stats['total_key_entities_protected'] += len(key_entities)
        self.context_stats['last_compression_time'] = datetime.now()

        # 8. 记录压缩效果
        compression_ratio = 1.0 - (len(self.conversation_history) / original_length)
        print(f"🔄 上下文压缩: {original_length} → {len(self.conversation_history)} "
              f"(压缩比例: {compression_ratio:.1%})")

        return self.conversation_history

    def _build_enhanced_prompt(
        self,
        input: str,
        managed_context: List[Message],
        memory_context: Dict
    ) -> str:
        """构建增强版提示词

        Args:
            input: 用户输入
            managed_context: 管理后的对话上下文
            memory_context: 记忆上下文

        Returns:
            完整的提示词
        """
        prompt_parts = []

        # 1. 添加对话历史（如果有的话）
        if managed_context:
            prompt_parts.append("以下是相关对话历史：")
            for message in managed_context:
                prompt_parts.append(f"{message.role}: {message.content}")
            prompt_parts.append("")  # 空行分隔

        # 2. 添加记忆上下文（如果有的话）
        if memory_context and (memory_context.get('short_term') or memory_context.get('long_term')):
            prompt_parts.append("相关背景信息：")

            if memory_context.get('short_term'):
                for item in memory_context['short_term'][:3]:  # 最多3条短期记忆
                    prompt_parts.append(f"- {item}")

            if memory_context.get('long_term'):
                for item in memory_context['long_term'][:2]:  # 最多2条长期记忆
                    prompt_parts.append(f"- {item}")

            prompt_parts.append("")  # 空行分隔

        # 3. 添加当前输入
        prompt_parts.append(f"当前问题：{input}")

        return "\n".join(prompt_parts)

    def _was_compression_applied(self) -> bool:
        """检查是否应用了压缩"""
        return self.context_stats['total_compressions'] > 0

    async def _monitor_conversation_quality(self):
        """监控对话质量"""
        if not hasattr(self, 'quality_maintainer'):
            return

        # 只在有足够对话历史时才监控
        if len(self.conversation_history) >= 4:
            conversation = Conversation(self.conversation_history)
            report = await self.quality_maintainer.maintain_quality(conversation)

            # 更新平均质量分数
            self.context_stats['average_quality_score'] = report.overall_score

            # 如果质量低于阈值，发出警告
            if report.overall_score < self.context_config.min_quality_threshold:
                print(f"⚠️ 对话质量偏低: {report.overall_score:.2f}")
                if report.recommendations:
                    print(f"💡 建议: {report.recommendations[0]}")

    def get_context_statistics(self) -> Dict[str, Any]:
        """获取上下文管理统计信息"""
        stats = self.context_stats.copy()

        # 添加当前对话状态
        stats['current_conversation_length'] = len(self.conversation_history)
        stats['current_token_count'] = sum(msg.token_count for msg in self.conversation_history)
        stats['window_utilization'] = stats['current_token_count'] / self.context_config.max_window_size

        return stats

    async def get_conversation_quality_report(self) -> Optional[Dict]:
        """获取对话质量报告"""
        if not hasattr(self, 'quality_maintainer'):
            return None

        if len(self.conversation_history) < 2:
            return None

        conversation = Conversation(self.conversation_history)
        report = await self.quality_maintainer.maintain_quality(conversation)

        return {
            'overall_score': report.overall_score,
            'coherence': report.metrics.coherence,
            'context_relevance': report.metrics.context_relevance,
            'decision_consistency': report.metrics.decision_consistency,
            'user_satisfaction': report.metrics.user_satisfaction,
            'completeness': report.metrics.completeness,
            'recommendations': report.recommendations,
            'warnings': report.warnings
        }

    def reset_conversation(self):
        """重置对话历史"""
        self.conversation_history = []
        print("🔄 对话历史已重置")


# 工厂函数，便于创建增强版Agent
def create_context_managed_agent(
    llm_client,
    system_prompt: str,
    agent_role: str,
    memory,
    context_config: ContextManagementConfig = None,
    **kwargs
) -> ContextManagedLLMAgent:
    """创建具备上下文管理能力的LLM Agent

    Args:
        llm_client: LLM客户端
        system_prompt: 系统提示词
        agent_role: Agent角色
        memory: 记忆系统
        context_config: 上下文管理配置（可选）
        **kwargs: 其他传递给LLMAgent的参数

    Returns:
        ContextManagedLLMAgent: 增强版LLM Agent实例
    """
    return ContextManagedLLMAgent(
        llm_client=llm_client,
        system_prompt=system_prompt,
        agent_role=agent_role,
        memory=memory,
        context_config=context_config,
        **kwargs
    )
"""
增强版LLM客户端 - 支持自动上下文管理

在原有LLMClient基础上，添加自动上下文压缩和智能token管理功能。
"""

import asyncio
from typing import Dict, List, Any, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import sys
sys.path.insert(0, 'src')

from llm_agent.llm.client import LLMClient, LLMResponse
from llm_agent.context import (
    ContextCompressor, CompressionStrategy,
    KeyInformationRetainer, RetentionConfig,
    DynamicContextManager, WindowConfig,
    Message, create_message, estimate_token_count
)


@dataclass
class ContextManagedLLMConfig:
    """上下文管理LLM配置"""
    # 上下文管理开关
    enable_auto_compression: bool = True

    # Token限制
    max_tokens: int = 4000  # 最大输入tokens
    reserve_tokens: int = 500  # 预留tokens

    # 压缩策略
    compression_strategy: CompressionStrategy = CompressionStrategy.INTELLIGENT
    compression_threshold: float = 0.8  # 使用率阈值

    # 监控
    track_token_usage: bool = True
    log_compression_events: bool = True


class ContextManagedLLMClient(LLMClient):
    """
    支持上下文管理的增强版LLM客户端

    自动管理输入上下文长度，确保不超过模型限制，
    同时保留最重要的信息。
    """

    def __init__(
        self,
        provider: str = "mock",
        model_name: str = "llm-agent-model",
        config: Dict[str, Any] = None,
        context_config: ContextManagedLLMConfig = None
    ):
        """初始化上下文管理LLM客户端

        Args:
            provider: LLM提供商
            model_name: 模型名称
            config: 额外配置
            context_config: 上下文管理配置
        """
        # 初始化父类
        super().__init__(provider, model_name, config)

        # 上下文管理配置
        self.context_config = context_config or ContextManagedLLMConfig()

        # 初始化上下文管理组件
        if self.context_config.enable_auto_compression:
            self.compressor = ContextCompressor(self.context_config.compression_strategy)
            self.dynamic_manager = DynamicContextManager(WindowConfig(
                max_window_size=self.context_config.max_tokens + self.context_config.reserve_tokens,
                reserve_space=self.context_config.reserve_tokens
            ))

        # 使用统计
        self.usage_stats = {
            'total_requests': 0,
            'total_compressions': 0,
            'total_tokens_processed': 0,
            'total_tokens_saved': 0
        }

    async def chat(
        self,
        prompt: str,
        system_prompt: str = "",
        conversation_history: List[Dict] = None,
        enable_context_management: bool = None
    ) -> LLMResponse:
        """增强版chat接口 - 支持自动上下文管理

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            conversation_history: 对话历史（可选）
            enable_context_management: 是否启用上下文管理（可选）

        Returns:
            LLMResponse: LLM响应
        """
        # 确定是否启用上下文管理
        should_manage = enable_context_management
        if should_manage is None:
            should_manage = self.context_config.enable_auto_compression

        # 更新统计
        self.usage_stats['total_requests'] += 1

        # 如果启用上下文管理
        if should_manage and conversation_history:
            managed_prompt, managed_history, compression_info = await self._manage_chat_context(
                prompt, conversation_history
            )
        else:
            managed_prompt = prompt
            managed_history = conversation_history
            compression_info = None

        try:
            # 调用父类的chat方法
            response = await super().chat(
                prompt=managed_prompt,
                system_prompt=system_prompt,
                conversation_history=managed_history
            )

            # 添加上下文管理元数据
            if compression_info:
                response.metadata = response.metadata or {}
                response.metadata.update({
                    'context_managed': True,
                    'original_prompt_length': len(prompt),
                    'managed_prompt_length': len(managed_prompt),
                    'compression_ratio': compression_info['compression_ratio'],
                    'tokens_saved': compression_info['tokens_saved'],
                    'compression_strategy': compression_info['strategy']
                })

            # 更新token统计
            if self.context_config.track_token_usage:
                self._update_token_stats(prompt, managed_prompt, compression_info)

            return response

        except Exception as e:
            # 错误时返回失败响应
            return LLMResponse(
                content="",
                success=False,
                error=str(e),
                metadata={'context_management_failed': True}
            )

    async def _manage_chat_context(
        self,
        prompt: str,
        conversation_history: List[Dict]
    ) -> tuple:
        """管理chat上下文

        Args:
            prompt: 当前提示
            conversation_history: 对话历史

        Returns:
            (managed_prompt, managed_history, compression_info)
        """
        # 1. 转换为Message格式
        messages = []
        for item in conversation_history:
            role = item.get('role', 'user')
            content = item.get('content', '')
            messages.append(create_message(role, content))

        # 添加当前prompt
        current_message = create_message("user", prompt)
        messages.append(current_message)

        # 2. 估算当前token使用
        current_tokens = sum(msg.token_count for msg in messages)

        # 3. 检查是否需要压缩
        max_allowed = self.context_config.max_tokens
        needs_compression = current_tokens > max_allowed * self.context_config.compression_threshold

        if not needs_compression:
            # 不需要压缩
            managed_messages = messages
            compression_info = {
                'compressed': False,
                'compression_ratio': 0.0,
                'tokens_saved': 0,
                'strategy': None
            }
        else:
            # 需要压缩
            managed_messages, compression_info = await self._compress_chat_messages(
                messages, max_allowed
            )

        # 4. 转换回原始格式
        managed_history = []
        for msg in managed_messages[:-1]:  # 排除最后一条（当前prompt）
            managed_history.append({
                'role': msg.role,
                'content': msg.content
            })

        managed_prompt = managed_messages[-1].content  # 最后一条是当前prompt

        return managed_prompt, managed_history, compression_info

    async def _compress_chat_messages(
        self,
        messages: List[Message],
        max_tokens: int
    ) -> tuple:
        """压缩聊天消息

        Args:
            messages: 消息列表
            max_tokens: 最大允许tokens

        Returns:
            (compressed_messages, compression_info)
        """
        original_tokens = sum(msg.token_count for msg in messages)

        # 使用智能压缩
        compressed = await self.compressor.compress_context(
            messages,
            target_length=max_tokens,
            preserve_key_info=True
        )

        compressed_tokens = sum(msg.token_count for msg in compressed.messages)
        tokens_saved = original_tokens - compressed_tokens
        compression_ratio = 1.0 - (compressed_tokens / original_tokens) if original_tokens > 0 else 0

        compression_info = {
            'compressed': True,
            'compression_ratio': compression_ratio,
            'tokens_saved': tokens_saved,
            'strategy': self.context_config.compression_strategy.value,
            'original_messages': len(messages),
            'compressed_messages': len(compressed.messages)
        }

        # 记录压缩事件
        self.usage_stats['total_compressions'] += 1
        self.usage_stats['total_tokens_saved'] += tokens_saved

        if self.context_config.log_compression_events:
            print(f"🔄 LLM上下文压缩: {len(messages)} → {len(compressed.messages)} 条消息 "
                  f"(节省 {tokens_saved} tokens, {compression_ratio:.1%} 压缩)")

        return compressed.messages, compression_info

    async def reason(
        self,
        prompt: str,
        context: str = "",
        enable_context_management: bool = None
    ) -> LLMResponse:
        """增强版reason接口 - 支持上下文管理

        Args:
            prompt: 推理提示
            context: 上下文信息
            enable_context_management: 是否启用上下文管理

        Returns:
            LLMResponse: 推理结果
        """
        # 如果上下文很长且启用了管理
        should_manage = enable_context_management
        if should_manage is None:
            should_manage = self.context_config.enable_auto_compression

        if should_manage and len(context) > 1000:  # 上下文超过1000字符
            managed_context = await self._compress_text(context)
        else:
            managed_context = context

        # 调用父类方法
        return await super().reason(prompt, managed_context)

    async def plan(
        self,
        goal: str,
        context: str = "",
        constraints: List[str] = None,
        enable_context_management: bool = None
    ) -> LLMResponse:
        """增强版plan接口 - 支持上下文管理

        Args:
            goal: 规划目标
            context: 上下文信息
            constraints: 约束条件
            enable_context_management: 是否启用上下文管理

        Returns:
            LLMResponse: 规划结果
        """
        # 处理上下文管理
        should_manage = enable_context_management
        if should_manage is None:
            should_manage = self.context_config.enable_auto_compression

        if should_manage and context and len(context) > 800:
            managed_context = await self._compress_text(context)
        else:
            managed_context = context

        # 调用父类方法
        return await super().plan(goal, managed_context, constraints)

    async def reflect(
        self,
        experience: str,
        outcome: str = "",
        enable_context_management: bool = None
    ) -> LLMResponse:
        """增强版reflect接口 - 支持上下文管理

        Args:
            experience: 经验描述
            outcome: 结果描述
            enable_context_management: 是否启用上下文管理

        Returns:
            LLMResponse: 反思结果
        """
        # 反思通常不需要上下文管理，因为输入相对较短
        return await super().reflect(experience, outcome)

    async def _compress_text(self, text: str) -> str:
        """压缩长文本

        Args:
            text: 原始文本

        Returns:
            压缩后的文本
        """
        if len(text) <= 500:
            return text

        # 简化文本压缩：保留前后部分，中间摘要
        if len(text) <= 1500:
            # 中等长度：保留开头和结尾
            half_length = 300
            return text[:half_length] + "\n...\n" + text[-half_length:]
        else:
            # 长文本：保留开头和结尾，中间部分压缩
            quarter_length = 250
            middle_start = len(text) // 2 - 100
            middle_end = len(text) // 2 + 100

            compressed = (
                text[:quarter_length] +
                "\n...[中间省略]...\n" +
                text[middle_start:middle_end] +
                "\n...[中间省略]...\n" +
                text[-quarter_length:]
            )

            return compressed

    def _update_token_stats(self, original_prompt: str, managed_prompt: str, compression_info: Dict = None):
        """更新token使用统计

        Args:
            original_prompt: 原始提示
            managed_prompt: 管理后的提示
            compression_info: 压缩信息
        """
        original_tokens = estimate_token_count(original_prompt)
        managed_tokens = estimate_token_count(managed_prompt)

        self.usage_stats['total_tokens_processed'] += original_tokens

        if compression_info and compression_info.get('compressed'):
            self.usage_stats['total_tokens_saved'] += compression_info.get('tokens_saved', 0)

    def get_usage_statistics(self) -> Dict[str, Any]:
        """获取使用统计信息"""
        stats = self.usage_stats.copy()

        # 计算平均值
        if stats['total_requests'] > 0:
            stats['average_compressions_per_request'] = (
                stats['total_compressions'] / stats['total_requests']
            )
            stats['average_tokens_per_request'] = (
                stats['total_tokens_processed'] / stats['total_requests']
            )

        # 计算节省率
        if stats['total_tokens_processed'] > 0:
            stats['token_saving_rate'] = (
                stats['total_tokens_saved'] / stats['total_tokens_processed']
            )

        return stats

    def reset_statistics(self):
        """重置使用统计"""
        self.usage_stats = {
            'total_requests': 0,
            'total_compressions': 0,
            'total_tokens_processed': 0,
            'total_tokens_saved': 0
        }


# 工厂函数
def create_context_managed_llm_client(
    provider: str = "mock",
    model_name: str = "llm-agent-model",
    config: Dict[str, Any] = None,
    context_config: ContextManagedLLMConfig = None
) -> ContextManagedLLMClient:
    """创建上下文管理LLM客户端

    Args:
        provider: LLM提供商
        model_name: 模型名称
        config: 额外配置
        context_config: 上下文管理配置

    Returns:
        ContextManagedLLMClient: 增强版LLM客户端实例
    """
    return ContextManagedLLMClient(
        provider=provider,
        model_name=model_name,
        config=config,
        context_config=context_config
    )
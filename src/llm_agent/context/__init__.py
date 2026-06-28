"""
LLM Agent上下文管理系统

提供智能上下文压缩、关键信息保留和动态窗口管理功能。
"""

from .compressor import ContextCompressor, CompressedContext, CompressionStrategy, Message, create_message, estimate_token_count
from .retainer import KeyInformationRetainer, KeyEntity, RetentionConfig, EntityType
from .manager import DynamicContextManager, ContextAllocation, WindowConfig
from .optimizer import ConversationHistoryOptimizer, OptimizedHistory
from .quality import MultiTurnQualityMaintainer, QualityReport, Conversation

# 从集成模块导入
try:
    from llm_agent.agents.context_managed import ContextManagementConfig
    from llm_agent.llm.context_managed_client import ContextManagedLLMConfig
    context_managed_available = True
except ImportError:
    context_managed_available = False

__all__ = [
    # 压缩器
    "ContextCompressor",
    "CompressedContext",
    "CompressionStrategy",
    "Message",
    "create_message",
    "estimate_token_count",

    # 关键信息保留器
    "KeyInformationRetainer",
    "KeyEntity",
    "EntityType",
    "RetentionConfig",

    # 动态管理器
    "DynamicContextManager",
    "ContextAllocation",
    "WindowConfig",

    # 优化器
    "ConversationHistoryOptimizer",
    "OptimizedHistory",

    # 质量维护器
    "MultiTurnQualityMaintainer",
    "QualityReport",
    "Conversation",
]

# 如果集成模块可用，添加到导出列表
if context_managed_available:
    __all__.extend([
        "ContextManagementConfig",
        "ContextManagedLLMConfig"
    ])
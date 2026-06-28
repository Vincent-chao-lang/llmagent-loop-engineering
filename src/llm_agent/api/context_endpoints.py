"""
上下文管理API端点

提供上下文管理相关的HTTP API接口。
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional
import sys
sys.path.insert(0, 'src')

from llm_agent.agents.context_managed import (
    ContextManagedLLMAgent,
    ContextManagementConfig,
    create_context_managed_agent
)
from llm_agent.llm.context_managed_client import (
    ContextManagedLLMClient,
    ContextManagedLLMConfig,
    create_context_managed_llm_client
)
from llm_agent.context import CompressionStrategy, EntityType


# Pydantic模型
class ContextConfigRequest(BaseModel):
    """上下文配置请求"""
    enabled: bool = True
    max_window_size: int = 8000
    reserve_space: int = 1000
    compression_strategy: str = "intelligent"
    preserve_key_info: bool = True
    auto_compress_threshold: float = 0.8
    enable_quality_monitoring: bool = True
    min_quality_threshold: float = 0.6


class ContextConfigResponse(BaseModel):
    """上下文配置响应"""
    agent_id: str
    config: Dict[str, Any]
    statistics: Dict[str, Any]
    status: str


class CompressionRequest(BaseModel):
    """压缩请求"""
    messages: List[Dict[str, str]] = Field(..., description="要压缩的消息列表")
    target_length: int = Field(4000, description="目标长度（tokens）")
    strategy: str = Field("intelligent", description="压缩策略")
    preserve_key_info: bool = Field(True, description="是否保留关键信息")


class CompressionResponse(BaseModel):
    """压缩响应"""
    original_count: int
    compressed_count: int
    compression_ratio: float
    information_retention: float
    compressed_messages: List[Dict[str, str]]
    key_entities_found: int
    processing_time: float


class QualityReportRequest(BaseModel):
    """质量报告请求"""
    conversation: List[Dict[str, str]] = Field(..., description="对话消息列表")


class ContextStatsResponse(BaseModel):
    """上下文统计响应"""
    current_conversation_length: int
    current_token_count: int
    window_utilization: float
    total_compressions: int
    total_key_entities_protected: int
    average_quality_score: float
    last_compression_time: Optional[str]


# 创建路由器
router = APIRouter(prefix="/api/v1/context", tags=["context"])


# 存储Agent实例的简化版本（实际应用中应该使用数据库）
agent_sessions: Dict[str, ContextManagedLLMAgent] = {}


@router.post("/config", response_model=ContextConfigResponse)
async def configure_context_management(
    agent_id: str,
    config: ContextConfigRequest
):
    """配置Agent的上下文管理

    Args:
        agent_id: Agent ID
        config: 上下文配置

    Returns:
        ContextConfigResponse: 配置结果
    """
    try:
        # 获取或创建Agent（简化版本）
        if agent_id not in agent_sessions:
            # 这里应该从session管理器获取现有Agent
            # 为了演示，我们创建一个新Agent
            from llm_agent.llm.client import LLMClient
            from llm_agent.memory import Memory, MemoryConfig

            llm_client = LLMClient(provider="mock")
            memory = Memory(MemoryConfig())

            agent = create_context_managed_agent(
                llm_client=llm_client,
                system_prompt="你是一个AI助手",
                agent_role="助手",
                memory=memory
            )
            agent_sessions[agent_id] = agent

        agent = agent_sessions[agent_id]

        # 更新配置
        agent.context_config = ContextManagementConfig(
            enabled=config.enabled,
            max_window_size=config.max_window_size,
            reserve_space=config.reserve_space,
            compression_strategy=CompressionStrategy(config.compression_strategy),
            preserve_key_info=config.preserve_key_info,
            auto_compress_threshold=config.auto_compress_threshold,
            enable_quality_monitoring=config.enable_quality_monitoring,
            min_quality_threshold=config.min_quality_threshold
        )

        # 重新初始化管理器
        if config.enabled:
            agent._init_context_managers()

        return ContextConfigResponse(
            agent_id=agent_id,
            config={
                "enabled": agent.context_config.enabled,
                "max_window_size": agent.context_config.max_window_size,
                "compression_strategy": agent.context_config.compression_strategy.value,
                "quality_monitoring": agent.context_config.enable_quality_monitoring
            },
            statistics=agent.get_context_statistics(),
            status="configured"
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config/{agent_id}", response_model=ContextConfigResponse)
async def get_context_config(agent_id: str):
    """获取Agent的上下文配置

    Args:
        agent_id: Agent ID

    Returns:
        ContextConfigResponse: 配置信息
    """
    if agent_id not in agent_sessions:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agent_sessions[agent_id]

    return ContextConfigResponse(
        agent_id=agent_id,
        config={
            "enabled": agent.context_config.enabled,
            "max_window_size": agent.context_config.max_window_size,
            "compression_strategy": agent.context_config.compression_strategy.value,
            "quality_monitoring": agent.context_config.enable_quality_monitoring
        },
        statistics=agent.get_context_statistics(),
        status="active"
    )


@router.post("/compress", response_model=CompressionResponse)
async def compress_conversation(request: CompressionRequest):
    """压缩对话上下文

    Args:
        request: 压缩请求

    Returns:
        CompressionResponse: 压缩结果
    """
    import time
    from llm_agent.context import ContextCompressor, Message, create_message

    start_time = time.time()

    try:
        # 转换消息格式
        messages = []
        for msg_data in request.messages:
            messages.append(create_message(
                msg_data.get('role', 'user'),
                msg_data.get('content', '')
            ))

        # 创建压缩器
        compressor = ContextCompressor(CompressionStrategy(request.strategy))

        # 执行压缩
        compressed = await compressor.compress_context(
            messages,
            target_length=request.target_length,
            preserve_key_info=request.preserve_key_info
        )

        # 转换回原始格式
        compressed_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in compressed.messages
        ]

        # 估算关键实体数量
        key_entities_count = len([
            entity for entity in await compressor._extract_key_information(messages, [])
            if entity.importance > 0.6
        ])

        processing_time = time.time() - start_time

        return CompressionResponse(
            original_count=len(messages),
            compressed_count=len(compressed_messages),
            compression_ratio=compressed.compression_ratio,
            information_retention=compressed.information_retention,
            compressed_messages=compressed_messages,
            key_entities_found=key_entities_count,
            processing_time=processing_time
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/{agent_id}", response_model=ContextStatsResponse)
async def get_context_statistics(agent_id: str):
    """获取上下文使用统计

    Args:
        agent_id: Agent ID

    Returns:
        ContextStatsResponse: 统计信息
    """
    if agent_id not in agent_sessions:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agent_sessions[agent_id]
    stats = agent.get_context_statistics()

    return ContextStatsResponse(
        current_conversation_length=stats['current_conversation_length'],
        current_token_count=stats['current_token_count'],
        window_utilization=stats['window_utilization'],
        total_compressions=stats['total_compressions'],
        total_key_entities_protected=stats['total_key_entities_protected'],
        average_quality_score=stats['average_quality_score'],
        last_compression_time=stats.get('last_compression_time')
    )


@router.post("/quality/{agent_id}")
async def get_conversation_quality(
    agent_id: str,
    request: QualityReportRequest
):
    """获取对话质量报告

    Args:
        agent_id: Agent ID
        request: 质量报告请求

    Returns:
        Dict: 质量报告
    """
    if agent_id not in agent_sessions:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agent_sessions[agent_id]

    try:
        # 转换对话格式
        from llm_agent.context import Conversation, create_message

        messages = [
            create_message(msg.get('role', 'user'), msg.get('content', ''))
            for msg in request.conversation
        ]

        conversation = Conversation(messages)

        if not hasattr(agent, 'quality_maintainer'):
            return {
                "error": "Quality monitoring not enabled for this agent",
                "suggestion": "Enable quality monitoring in agent configuration"
            }

        report = await agent.quality_maintainer.maintain_quality(conversation)

        return {
            "overall_score": report.overall_score,
            "metrics": {
                "coherence": report.metrics.coherence,
                "context_relevance": report.metrics.context_relevance,
                "decision_consistency": report.metrics.decision_consistency,
                "user_satisfaction": report.metrics.user_satisfaction,
                "completeness": report.metrics.completeness
            },
            "recommendations": report.recommendations,
            "warnings": report.warnings
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset/{agent_id}")
async def reset_conversation(agent_id: str):
    """重置Agent的对话历史

    Args:
        agent_id: Agent ID

    Returns:
        Dict: 重置结果
    """
    if agent_id not in agent_sessions:
        raise HTTPException(status_code=404, detail="Agent not found")

    agent = agent_sessions[agent_id]
    agent.reset_conversation()

    return {
        "status": "success",
        "message": "Conversation history reset",
        "agent_id": agent_id
    }


@router.get("/strategies")
async def list_compression_strategies():
    """列出可用的压缩策略

    Returns:
        Dict: 可用策略列表
    """
    return {
        "strategies": [
            {
                "name": "intelligent",
                "description": "智能混合策略，综合考虑重要性和时间",
                "best_for": "通用场景"
            },
            {
                "name": "importance_based",
                "description": "基于内容重要性的压缩",
                "best_for": "内容密集型对话"
            },
            {
                "name": "recency_based",
                "description": "基于时间的新鲜度压缩",
                "best_for": "快速响应场景"
            },
            {
                "name": "hierarchical",
                "description": "层级压缩，平衡各类信息",
                "best_for": "复杂对话场景"
            }
        ]
    }


@router.get("/entity-types")
async def list_entity_types():
    """列出可保护的实体类型

    Returns:
        Dict: 实体类型列表
    """
    return {
        "entity_types": [
            {
                "name": "user",
                "description": "用户信息和身份",
                "priority": "高"
            },
            {
                "name": "decision",
                "description": "决策和选择信息",
                "priority": "高"
            },
            {
                "name": "constraint",
                "description": "约束条件和限制",
                "priority": "中"
            },
            {
                "name": "preference",
                "description": "用户偏好和倾向",
                "priority": "中"
            },
            {
                "name": "domain",
                "description": "专业术语和领域知识",
                "priority": "低"
            }
        ]
    }
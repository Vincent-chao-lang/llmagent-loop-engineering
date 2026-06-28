"""
团队协作相关Schema
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class CollaborationStyle(str, Enum):
    """协作模式"""

    HIERARCHICAL = "hierarchical"  # 层级协作
    PEER_TO_PEER = "peer_to_peer"  # 点对点协作
    DIRECT = "direct"  # 直接协作


class AgentConfig(BaseModel):
    """Agent配置（用于团队协作）"""

    system_prompt: str = Field(..., description="系统提示词")
    agent_role: str = Field(..., description="Agent角色")
    provider: Optional[str] = Field(default="mock", description="LLM提供商")


class CollaborateRequest(BaseModel):
    """团队协作请求"""

    task: str = Field(..., description="协作任务描述")
    agent_configs: List[AgentConfig] = Field(..., description="参与Agent的配置列表")
    style: CollaborationStyle = Field(default=CollaborationStyle.PEER_TO_PEER, description="协作模式")


class VoteRequest(BaseModel):
    """团队投票请求"""

    proposal: str = Field(..., description="提案内容")
    agent_configs: List[AgentConfig] = Field(..., description="参与Agent的配置列表")


class CollaborateResponse(BaseModel):
    """团队协作响应（映射TeamResult）"""

    team_id: str = Field(description="团队ID")
    goal: str = Field(description="协作目标")
    success: bool = Field(description="是否成功")
    individual_results: List[Any] = Field(default_factory=list, description="个人结果列表")
    consensus: Optional[str] = Field(default=None, description="达成的共识")
    conflict_count: int = Field(default=0, description="冲突次数")
    collaboration_quality: float = Field(default=0.0, description="协作质量评分")
    time_taken: float = Field(default=0.0, description="耗时（秒）")
    error: Optional[str] = Field(default=None, description="错误信息")


class VoteResponse(BaseModel):
    """投票响应"""

    proposal: str = Field(description="提案内容")
    results: Dict[str, bool] = Field(description="投票结果 {agent_id: vote}")
    agreed_count: int = Field(description="同意数量")
    total_count: int = Field(description="总投票数")
    consensus_reached: bool = Field(description="是否达成共识")

"""
Agent相关Schema
"""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# ==================== Request Schema ====================

class CreateAgentRequest(BaseModel):
    """创建Agent请求"""

    system_prompt: str = Field(..., description="系统提示词")
    agent_role: str = Field(..., description="Agent角色")
    provider: Optional[str] = Field(default="mock", description="LLM提供商")
    model: Optional[str] = Field(default=None, description="模型名称（可选）")
    api_key: Optional[str] = Field(default=None, description="API密钥（可选）")

    # 记忆配置（可选）
    memory_short_term_capacity: Optional[int] = Field(default=100, description="短期记忆容量")
    memory_long_term_capacity: Optional[int] = Field(default=1000, description="长期记忆容量")
    memory_working_capacity: Optional[int] = Field(default=10, description="工作记忆容量")


class ThinkRequest(BaseModel):
    """思考请求"""

    input: str = Field(..., description="输入问题或任务描述")
    session_id: Optional[str] = Field(default=None, description="会话ID（可选，不传则创建临时Agent）")


class PlanRequest(BaseModel):
    """规划请求"""

    goal: str = Field(..., description="目标描述")
    session_id: Optional[str] = Field(default=None, description="会话ID（可选）")


class ExecuteRequest(BaseModel):
    """执行请求"""

    task: str = Field(..., description="任务描述")
    session_id: Optional[str] = Field(default=None, description="会话ID（可选）")


class ReflectRequest(BaseModel):
    """反思请求"""

    task: str = Field(..., description="执行的任务")
    results: List[Any] = Field(..., description="执行结果列表")
    session_id: Optional[str] = Field(default=None, description="会话ID（可选）")


# ==================== Response Schema ====================

class AgentInfo(BaseModel):
    """Agent信息"""

    agent_id: str = Field(description="Agent ID")
    agent_role: str = Field(description="Agent角色")
    created_at: str = Field(description="创建时间")
    last_access: str = Field(description="最后访问时间")
    is_active: bool = Field(description="是否活跃")


class ThinkResponse(BaseModel):
    """思考响应（映射AgentResponse）"""

    content: str = Field(description="思考结果内容")
    reasoning: Optional[str] = Field(default="", description="推理过程")
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list, description="工具调用")
    confidence: float = Field(default=0.0, description="置信度")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")


class PlanResponse(BaseModel):
    """规划响应（映射ExecutionPlan）"""

    goal: str = Field(description="目标")
    steps: List[Dict[str, Any]] = Field(description="执行步骤列表")
    estimated_time: int = Field(description="预估时间（秒）")
    required_tools: List[str] = Field(default_factory=list, description="所需工具")


class ExecuteResponse(BaseModel):
    """执行响应（映射ExecutionResult）"""

    success: bool = Field(description="执行是否成功")
    steps: List[Any] = Field(description="执行步骤结果列表")
    reflection: Optional[str] = Field(default=None, description="反思总结")
    error: Optional[str] = Field(default=None, description="错误信息")


class ReflectResponse(BaseModel):
    """反思响应（映射Reflection）"""

    insights: str = Field(description="洞察和发现")
    improvements: str = Field(description="改进建议")
    lessons_learned: str = Field(description="学到的经验")

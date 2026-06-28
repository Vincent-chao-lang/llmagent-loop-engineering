"""
Agent核心能力路由
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Annotated

from llm_agent.api.deps import SessionManagerDep
from llm_agent.api.session import SessionManager
from llm_agent.schemas.common import BaseResponse
from llm_agent.schemas.agent import (
    ThinkRequest,
    PlanRequest,
    ExecuteRequest,
    ReflectRequest,
    ThinkResponse,
    PlanResponse,
    ExecuteResponse,
    ReflectResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def get_or_create_agent(
    session_id: str | None,
    session_mgr: SessionManager,
) -> tuple:
    """获取或创建Agent

    Returns:
        (agent, is_temporary): Agent实例和是否为临时会话
    """
    if session_id:
        agent = await session_mgr.get_session(session_id)
        if not agent:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="会话不存在或已过期"
            )
        return agent, False
    else:
        # 创建临时Agent（一次性）
        from llm_agent.llm.client import LLMClient
        from llm_agent.agents.base import LLMAgent
        from llm_agent.memory.memory import Memory, MemoryConfig
        from uuid import uuid4

        temp_id = str(uuid4())
        llm_client = LLMClient(provider="mock")
        memory = Memory(MemoryConfig())
        agent = LLMAgent(
            llm_client=llm_client,
            system_prompt="你是临时助手",
            agent_role="助手",
            memory=memory,
        )
        agent.agent_id = temp_id
        return agent, True


@router.post("/agent/think", response_model=BaseResponse[ThinkResponse])
async def agent_think(
    request: ThinkRequest,
    session_mgr: SessionManagerDep,
):
    """Agent思考能力"""
    try:
        agent, _ = await get_or_create_agent(request.session_id, session_mgr)

        response = await agent.think(request.input)

        return BaseResponse(
            success=True,
            data=ThinkResponse(
                content=response.content,
                reasoning=response.reasoning,
                tool_calls=response.tool_calls,
                confidence=response.confidence,
                metadata=response.metadata,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"思考失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/plan", response_model=BaseResponse[PlanResponse])
async def agent_plan(
    request: PlanRequest,
    session_mgr: SessionManagerDep,
):
    """Agent规划能力"""
    try:
        agent, _ = await get_or_create_agent(request.session_id, session_mgr)

        plan = await agent.plan(request.goal)

        return BaseResponse(
            success=True,
            data=PlanResponse(
                goal=plan.goal,
                steps=[s if isinstance(s, dict) else {"description": str(s)} for s in plan.steps],
                estimated_time=plan.estimated_time,
                required_tools=plan.required_tools,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"规划失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/execute", response_model=BaseResponse[ExecuteResponse])
async def agent_execute(
    request: ExecuteRequest,
    session_mgr: SessionManagerDep,
):
    """Agent执行能力"""
    try:
        agent, _ = await get_or_create_agent(request.session_id, session_mgr)

        result = await agent.execute(request.task)

        return BaseResponse(
            success=True,
            data=ExecuteResponse(
                success=result.success,
                steps=result.steps,
                reflection=result.reflection,
                error=result.error,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"执行失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/agent/reflect", response_model=BaseResponse[ReflectResponse])
async def agent_reflect(
    request: ReflectRequest,
    session_mgr: SessionManagerDep,
):
    """Agent反思能力"""
    try:
        agent, _ = await get_or_create_agent(request.session_id, session_mgr)

        reflection = await agent.reflect(request.task, request.results)

        return BaseResponse(
            success=True,
            data=ReflectResponse(
                insights=reflection.insights,
                improvements=reflection.improvements,
                lessons_learned=reflection.lessons_learned,
            ),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"反思失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

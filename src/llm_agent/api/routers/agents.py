"""
Agent会话管理路由
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, Depends
from typing import Annotated

from llm_agent.api.deps import SessionManagerDep
from llm_agent.api.session import SessionManager
from llm_agent.schemas.common import BaseResponse
from llm_agent.schemas.agent import CreateAgentRequest, AgentInfo

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/agents", response_model=BaseResponse[str])
async def create_agent(
    request: CreateAgentRequest,
    session_mgr: SessionManagerDep,
):
    """创建Agent会话

    返回session_id用于后续调用
    """
    try:
        session_id = await session_mgr.create_session(
            system_prompt=request.system_prompt,
            agent_role=request.agent_role,
            provider=request.provider,
            model=request.model,
            api_key=request.api_key,
        )

        return BaseResponse(
            success=True,
            data=session_id,
        )
    except Exception as e:
        logger.error(f"创建Agent失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agents/{session_id}", response_model=BaseResponse[AgentInfo])
async def get_agent(
    session_id: str,
    session_mgr: SessionManagerDep,
):
    """获取Agent信息"""
    agent = await session_mgr.get_session(session_id)
    if not agent:
        raise HTTPException(status_code=404, detail="会话不存在或已过期")

    return BaseResponse(
        success=True,
        data=AgentInfo(
            agent_id=agent.agent_id,
            agent_role=agent.agent_role,
            created_at=str(agent.created_at) if hasattr(agent, "created_at") else str(datetime.now()),
            last_access=str(datetime.now()),
            is_active=True,
        ),
    )


@router.delete("/agents/{session_id}", response_model=BaseResponse[bool])
async def delete_agent(
    session_id: str,
    session_mgr: SessionManagerDep,
):
    """销毁Agent会话"""
    destroyed = await session_mgr.destroy_session(session_id)
    if not destroyed:
        raise HTTPException(status_code=404, detail="会话不存在")

    return BaseResponse(success=True, data=True)

"""
团队协作路由
"""

import logging
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Depends, status
from typing import Annotated

from llm_agent.api.deps import SessionManagerDep
from llm_agent.api.session import SessionManager
from llm_agent.schemas.common import BaseResponse
from llm_agent.schemas.team import (
    CollaborateRequest,
    VoteRequest,
    CollaborateResponse,
    VoteResponse,
    CollaborationStyle,
)

logger = logging.getLogger(__name__)
router = APIRouter()


async def create_temp_agents(
    agent_configs: list,
    session_mgr: SessionManager,
) -> dict:
    """创建临时Agent实例

    Args:
        agent_configs: Agent配置列表
        session_mgr: 会话管理器

    Returns:
        {id: agent} 字典
    """
    from llm_agent.agents.base import LLMAgent
    from llm_agent.llm.client import LLMClient
    from llm_agent.memory.memory import Memory, MemoryConfig

    agents = {}
    for config in agent_configs:
        temp_id = str(uuid4())
        llm_client = LLMClient(provider=config.provider)
        memory = Memory(MemoryConfig())
        agent = LLMAgent(
            llm_client=llm_client,
            system_prompt=config.system_prompt,
            agent_role=config.agent_role,
            memory=memory,
        )
        agent.agent_id = temp_id
        agents[temp_id] = agent

    return agents


@router.post("/team/collaborate", response_model=BaseResponse[CollaborateResponse])
async def team_collaborate(
    request: CollaborateRequest,
    session_mgr: SessionManagerDep,
):
    """团队协作"""
    try:
        # 创建临时Agent
        agents = await create_temp_agents(request.agent_configs, session_mgr)

        # 创建临时团队
        from llm_agent.collaboration.team import LLMAgentTeam, TeamConfig, TeamRole

        team_config = TeamConfig(
            team_id=str(uuid4()),
            team_name="临时团队",
            goal=request.task,
            max_members=len(agents),
        )
        team = LLMAgentTeam(team_config)

        # 添加成员（都设为SPECIALIST）
        for agent_id in agents:
            team.add_member(agent_id, TeamRole.SPECIALIST)

        # 协作
        style_map = {
            CollaborationStyle.HIERARCHICAL: "hierarchical",
            CollaborationStyle.PEER_TO_PEER: "peer_to_peer",
            CollaborationStyle.DIRECT: "direct",
        }
        result = await team.collaborate(request.task, agents, style_map[request.style])

        return BaseResponse(
            success=result.success,
            data=CollaborateResponse(
                team_id=result.team_id,
                goal=result.goal,
                success=result.success,
                individual_results=result.individual_results,
                consensus=result.consensus,
                conflict_count=result.conflict_count,
                collaboration_quality=result.collaboration_quality,
                time_taken=result.time_taken,
                error=getattr(result, "error", None),
            ),
        )
    except Exception as e:
        logger.error(f"团队协作失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/team/vote", response_model=BaseResponse[VoteResponse])
async def team_vote(
    request: VoteRequest,
    session_mgr: SessionManagerDep,
):
    """团队投票"""
    try:
        # 创建临时Agent
        agents = await create_temp_agents(request.agent_configs, session_mgr)

        # 创建临时团队
        from llm_agent.collaboration.team import LLMAgentTeam, TeamConfig, TeamRole

        team_config = TeamConfig(
            team_id=str(uuid4()),
            team_name="临时团队",
            goal=request.proposal,
            max_members=len(agents),
        )
        team = LLMAgentTeam(team_config)

        # 添加成员
        for agent_id in agents:
            team.add_member(agent_id, TeamRole.SPECIALIST)

        # 投票
        votes = await team.vote(request.proposal, agents)

        # 统计结果
        agreed_count = sum(1 for v in votes.values() if v)
        total_count = len(votes)
        consensus_reached = agreed_count > total_count / 2

        return BaseResponse(
            success=True,
            data=VoteResponse(
                proposal=request.proposal,
                results=votes,
                agreed_count=agreed_count,
                total_count=total_count,
                consensus_reached=consensus_reached,
            ),
        )
    except Exception as e:
        logger.error(f"团队投票失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

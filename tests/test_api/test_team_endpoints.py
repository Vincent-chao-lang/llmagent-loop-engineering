"""
团队协作端点测试
"""

import pytest
from llm_agent.schemas.team import CollaborationStyle


@pytest.mark.asyncio
async def test_team_collaborate_peer_to_peer(client):
    """测试团队协作（点对点模式）"""
    request_data = {
        "task": "设计一个微服务架构",
        "agent_configs": [
            {
                "system_prompt": "你是架构专家",
                "agent_role": "架构师",
                "provider": "mock",
            },
            {
                "system_prompt": "你是安全专家",
                "agent_role": "安全专家",
                "provider": "mock",
            },
        ],
        "style": CollaborationStyle.PEER_TO_PEER,
    }

    response = await client.post("/api/v1/team/collaborate", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "team_id" in data["data"]
    assert "goal" in data["data"]
    assert "individual_results" in data["data"]
    assert data["data"]["goal"] == "设计一个微服务架构"


@pytest.mark.asyncio
async def test_team_collaborate_hierarchical(client):
    """测试团队协作（层级模式）"""
    request_data = {
        "task": "制定项目计划",
        "agent_configs": [
            {
                "system_prompt": "你是项目经理",
                "agent_role": "经理",
                "provider": "mock",
            },
            {
                "system_prompt": "你是开发人员",
                "agent_role": "开发者",
                "provider": "mock",
            },
        ],
        "style": CollaborationStyle.HIERARCHICAL,
    }

    response = await client.post("/api/v1/team/collaborate", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "collaboration_quality" in data["data"]
    assert "time_taken" in data["data"]


@pytest.mark.asyncio
async def test_team_vote(client):
    """测试团队投票"""
    request_data = {
        "proposal": "是否采用FastAPI框架",
        "agent_configs": [
            {
                "system_prompt": "你是后端工程师",
                "agent_role": "后端",
                "provider": "mock",
            },
            {
                "system_prompt": "你是前端工程师",
                "agent_role": "前端",
                "provider": "mock",
            },
            {
                "system_prompt": "你是架构师",
                "agent_role": "架构师",
                "provider": "mock",
            },
        ],
    }

    response = await client.post("/api/v1/team/vote", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "results" in data["data"]
    assert "agreed_count" in data["data"]
    assert "total_count" in data["data"]
    assert "consensus_reached" in data["data"]
    assert data["data"]["total_count"] == 3


@pytest.mark.asyncio
async def test_team_collaborate_single_agent(client):
    """测试单Agent协作（边缘情况）"""
    request_data = {
        "task": "独立完成任务",
        "agent_configs": [
            {
                "system_prompt": "你是全能助手",
                "agent_role": "助手",
                "provider": "mock",
            }
        ],
        "style": CollaborationStyle.DIRECT,
    }

    response = await client.post("/api/v1/team/collaborate", json=request_data)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert len(data["data"]["individual_results"]) >= 0


@pytest.mark.asyncio
async def test_team_vote_invalid_style(client):
    """测试无效的协作风格"""
    import httpx

    request_data = {
        "task": "测试",
        "agent_configs": [
            {"system_prompt": "测试", "agent_role": "测试", "provider": "mock"}
        ],
        "style": "invalid_style",  # 无效值
    }

    # Pydantic会拦截这个请求
    response = await client.post("/api/v1/team/collaborate", json=request_data)
    assert response.status_code == 422  # Unprocessable Entity

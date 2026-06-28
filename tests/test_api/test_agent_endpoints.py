"""
Agent端点测试
"""

import pytest


@pytest.mark.asyncio
async def test_create_agent(client, mock_agent_config):
    """测试创建Agent"""
    response = await client.post("/api/v1/agents", json=mock_agent_config)
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert isinstance(data["data"], str)  # session_id

    return data["data"]  # 返回session_id供后续测试使用


@pytest.mark.asyncio
async def test_think_without_session(client):
    """测试思考（无session）"""
    response = await client.post(
        "/api/v1/agent/think",
        json={"input": "什么是递归？"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "data" in data
    assert "content" in data["data"]
    assert "confidence" in data["data"]


@pytest.mark.asyncio
async def test_think_with_session(client, mock_agent_config):
    """测试思考（有session）"""
    # 先创建session
    create_resp = await client.post("/api/v1/agents", json=mock_agent_config)
    session_id = create_resp.json()["data"]

    # 使用session思考
    response = await client.post(
        "/api/v1/agent/think",
        json={"input": "分析Python的GIL问题", "session_id": session_id}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "content" in data["data"]


@pytest.mark.asyncio
async def test_plan(client):
    """测试规划"""
    response = await client.post(
        "/api/v1/agent/plan",
        json={"goal": "构建一个Web爬虫"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "goal" in data["data"]
    assert "steps" in data["data"]
    assert isinstance(data["data"]["steps"], list)


@pytest.mark.asyncio
async def test_execute(client):
    """测试执行"""
    response = await client.post(
        "/api/v1/agent/execute",
        json={"task": "数据分析任务"}
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "success" in data["data"]
    assert "steps" in data["data"]


@pytest.mark.asyncio
async def test_reflect(client):
    """测试反思"""
    response = await client.post(
        "/api/v1/agent/reflect",
        json={
            "task": "代码审查",
            "results": ["发现2个问题", "建议优化"],
        }
    )
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "insights" in data["data"]
    assert "improvements" in data["data"]
    assert "lessons_learned" in data["data"]


@pytest.mark.asyncio
async def test_get_agent(client, mock_agent_config):
    """测试获取Agent信息"""
    # 创建session
    create_resp = await client.post("/api/v1/agents", json=mock_agent_config)
    session_id = create_resp.json()["data"]

    # 获取信息
    response = await client.get(f"/api/v1/agents/{session_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "agent_id" in data["data"]
    assert "agent_role" in data["data"]


@pytest.mark.asyncio
async def test_delete_agent(client, mock_agent_config):
    """测试删除Agent"""
    # 创建session
    create_resp = await client.post("/api/v1/agents", json=mock_agent_config)
    session_id = create_resp.json()["data"]

    # 删除
    response = await client.delete(f"/api/v1/agents/{session_id}")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["data"] is True

    # 再次获取应该404
    get_resp = await client.get(f"/api/v1/agents/{session_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_invalid_session(client):
    """测试无效session"""
    response = await client.post(
        "/api/v1/agent/think",
        json={"input": "测试", "session_id": "invalid-session-id"}
    )
    assert response.status_code == 404

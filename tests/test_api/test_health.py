"""
健康检查测试
"""

import pytest


def get_test_client():
    """获取测试客户端"""
    from llm_agent.api.app import create_app
    from httpx import AsyncClient, ASGITransport

    app = create_app()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_health_check():
    """测试健康检查端点"""
    async with get_test_client() as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        # HealthResponse直接返回数据，不包装在BaseResponse中
        assert data["status"] == "healthy"
        assert "version" in data


@pytest.mark.asyncio
async def test_ping():
    """测试ping端点"""
    async with get_test_client() as client:
        response = await client.get("/api/v1/ping")
        assert response.status_code == 200
        assert response.text == "pong"


@pytest.mark.asyncio
async def test_root():
    """测试根路径"""
    async with get_test_client() as client:
        response = await client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "LLM Agent API"

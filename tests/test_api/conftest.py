"""
API测试配置和固具
"""

import pytest


@pytest.fixture
def mock_agent_config():
    """模拟Agent配置"""
    return {
        "system_prompt": "你是测试助手",
        "agent_role": "测试员",
        "provider": "mock",
    }


@pytest.fixture
async def client():
    """获取测试客户端"""
    from llm_agent.api.app import create_app
    from httpx import AsyncClient, ASGITransport

    app = create_app()
    transport = ASGITransport(app=app)

    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

"""
API Key 认证测试
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
async def test_auth_disabled_no_key_required():
    """测试：认证关闭时，不需要 key 也能访问业务端点"""
    # 认证关闭（默认 api_auth_enabled=False）
    async with get_test_client() as client:
        response = await client.post(
            "/api/v1/agent/think",
            json={"input": "测试问题"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


@pytest.mark.asyncio
async def test_auth_enabled_no_key_denied():
    """测试：认证开启但未提供 key → 401"""
    import os
    from llm_agent.config import reset_settings
    from llm_agent.api.app import create_app
    from httpx import AsyncClient, ASGITransport

    # 通过环境变量设置认证开启但未配置 key
    os.environ["LLM_AGENT_API_AUTH_ENABLED"] = "true"
    os.environ["LLM_AGENT_API_KEYS"] = "[]"
    reset_settings()

    app = create_app()
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")

    async with client:
        response = await client.post(
            "/api/v1/agent/think",
            json={"input": "测试问题"},
        )
        assert response.status_code == 401
        data = response.json()
        assert "detail" in data

    # 清理环境变量
    del os.environ["LLM_AGENT_API_AUTH_ENABLED"]
    del os.environ["LLM_AGENT_API_KEYS"]
    reset_settings()


@pytest.mark.asyncio
async def test_auth_enabled_with_valid_key():
    """测试：认证开启 + 提供有效 key → 200"""
    import os
    from llm_agent.config import reset_settings
    from llm_agent.api.app import create_app
    from httpx import AsyncClient, ASGITransport

    os.environ["LLM_AGENT_API_AUTH_ENABLED"] = "true"
    os.environ["LLM_AGENT_API_KEYS"] = '["sk-test123"]'
    reset_settings()

    app = create_app()
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")

    async with client:
        response = await client.post(
            "/api/v1/agent/think",
            json={"input": "测试问题"},
            headers={"X-API-Key": "sk-test123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    del os.environ["LLM_AGENT_API_AUTH_ENABLED"]
    del os.environ["LLM_AGENT_API_KEYS"]
    reset_settings()


@pytest.mark.asyncio
async def test_auth_enabled_with_invalid_key():
    """测试：认证开启 + 提供无效 key → 401"""
    import os
    from llm_agent.config import reset_settings
    from llm_agent.api.app import create_app
    from httpx import AsyncClient, ASGITransport

    os.environ["LLM_AGENT_API_AUTH_ENABLED"] = "true"
    os.environ["LLM_AGENT_API_KEYS"] = '["sk-correct"]'
    reset_settings()

    app = create_app()
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")

    async with client:
        response = await client.post(
            "/api/v1/agent/think",
            json={"input": "测试问题"},
            headers={"X-API-Key": "sk-wrong"},
        )
        assert response.status_code == 401

    del os.environ["LLM_AGENT_API_AUTH_ENABLED"]
    del os.environ["LLM_AGENT_API_KEYS"]
    reset_settings()


@pytest.mark.asyncio
async def test_health_endpoint_always_public():
    """测试：health 端点永远免鉴权（无论认证是否开启）"""
    import os
    from llm_agent.config import reset_settings
    from llm_agent.api.app import create_app
    from httpx import AsyncClient, ASGITransport

    os.environ["LLM_AGENT_API_AUTH_ENABLED"] = "true"
    os.environ["LLM_AGENT_API_KEYS"] = '["sk-test"]'
    reset_settings()

    app = create_app()
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")

    async with client:
        # 无 key 访问 health → 200
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    del os.environ["LLM_AGENT_API_AUTH_ENABLED"]
    del os.environ["LLM_AGENT_API_KEYS"]
    reset_settings()


@pytest.mark.asyncio
async def test_docs_endpoint_always_public():
    """测试：/docs 端点永远免鉴权"""
    import os
    from llm_agent.config import reset_settings
    from llm_agent.api.app import create_app
    from httpx import AsyncClient, ASGITransport

    os.environ["LLM_AGENT_API_AUTH_ENABLED"] = "true"
    os.environ["LLM_AGENT_API_KEYS"] = '["sk-test"]'
    reset_settings()

    app = create_app()
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")

    async with client:
        # 无 key 访问 docs → 200
        response = await client.get("/docs")
        assert response.status_code == 200

    del os.environ["LLM_AGENT_API_AUTH_ENABLED"]
    del os.environ["LLM_AGENT_API_KEYS"]
    reset_settings()

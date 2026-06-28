"""
FastAPI应用
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.responses import JSONResponse

from llm_agent.config import get_settings
from llm_agent.api.middleware import setup_cors, RequestLoggingMiddleware, ErrorHandlerMiddleware
from llm_agent.api.session import get_session_manager
from llm_agent.api.auth import verify_api_key

# 导入路由器
from llm_agent.api.routers import health, agents, agent, team

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # 启动
    settings = get_settings()
    logger.info(f"启动 LLM Agent API 服务: v{settings.api_host}:{settings.api_port}")

    # 检查 API 认证配置
    if settings.api_auth_enabled:
        if not settings.api_keys:
            logger.error(
                "API 认证已启用（api_auth_enabled=true）但未配置 api_keys，所有业务请求将被拒绝！"
            )
        else:
            logger.info(f"API 认证已启用，配置了 {len(settings.api_keys)} 个有效 API Key")
    else:
        logger.info("API 认证未启用（开发模式），所有请求免鉴权")

    # 启动会话管理器的后台清理任务
    session_mgr = get_session_manager()
    await session_mgr.start_background_cleanup()

    yield

    # 关闭
    logger.info("关闭 LLM Agent API 服务")
    await session_mgr.shutdown()


def create_app() -> FastAPI:
    """创建FastAPI应用工厂

    Returns:
        FastAPI应用实例
    """
    # 动态导入 __version__（避免硬编码）
    from llm_agent import __version__

    app = FastAPI(
        title="LLM Agent API",
        description="LLM驱动的智能Agent框架 - REST API",
        version=__version__,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # 配置CORS
    setup_cors(app)

    # 添加中间件
    app.add_middleware(ErrorHandlerMiddleware)
    app.add_middleware(RequestLoggingMiddleware)

    # 注册路由器
    # 认证依赖：业务路由需要 API Key，health/docs 等免鉴权
    auth_dependencies = [Depends(verify_api_key)]

    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    app.include_router(agents.router, prefix="/api/v1", tags=["Agents"], dependencies=auth_dependencies)
    app.include_router(agent.router, prefix="/api/v1", tags=["Agent"], dependencies=auth_dependencies)
    app.include_router(team.router, prefix="/api/v1", tags=["Team"], dependencies=auth_dependencies)

    # 根路径
    @app.get("/")
    async def root():
        """根路径"""
        return {
            "name": "LLM Agent API",
            "version": "0.1.0",
            "docs": "/docs",
        }

    return app


# 模块级应用实例（便于 uvicorn llm_agent.api:app）
app = create_app()

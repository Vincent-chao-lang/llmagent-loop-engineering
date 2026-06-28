"""
健康检查路由
"""

from fastapi import APIRouter, Response
from llm_agent import __version__
from llm_agent.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """健康检查"""
    return HealthResponse(
        status="healthy",
        version=__version__,
    )


@router.get("/ping")
async def ping():
    """简单ping"""
    return Response(content="pong", media_type="text/plain")

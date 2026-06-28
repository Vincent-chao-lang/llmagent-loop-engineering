"""
API中间件
"""

import logging
import time
import uuid
from typing import Callable, Awaitable

from fastapi import Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from llm_agent.config import get_settings
from llm_agent.schemas.common import ErrorResponse

logger = logging.getLogger(__name__)


def setup_cors(app):
    """配置CORS中间件"""
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )
    logger.info(f"CORS配置: origins={settings.cors_origins}")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录日志"""
        # 生成请求ID
        request_id = str(uuid.uuid4())[:8]
        request.state.request_id = request_id

        # 记录请求开始
        start_time = time.time()
        logger.info(f"[{request_id}] {request.method} {request.url.path}")

        # 处理请求
        try:
            response = await call_next(request)
            duration = time.time() - start_time
            logger.info(
                f"[{request_id}] {response.status_code} - {duration:.3f}s"
            )
            # 添加请求ID到响应头
            response.headers["X-Request-ID"] = request_id
            return response
        except Exception as e:
            duration = time.time() - start_time
            logger.error(f"[{request_id}] Exception: {e} - {duration:.3f}s")
            raise


class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    """全局异常处理中间件"""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理异常并返回统一格式"""
        try:
            return await call_next(request)
        except Exception as e:
            logger.exception(f"Unhandled exception: {e}")

            # 返回统一错误格式
            from fastapi.responses import JSONResponse

            error_response = ErrorResponse(
                error=str(e),
                detail=getattr(e, "detail", None),
            )
            return JSONResponse(
                content=error_response.model_dump(),
                status_code=getattr(e, "status_code", 500),
            )

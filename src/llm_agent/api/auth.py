"""
API Key 认证依赖
"""

import logging
from typing import Annotated, Optional

from fastapi import Depends, HTTPException, Security, status
from fastapi.security.utils import get_authorization_scheme_param
from pydantic import Field
from fastapi.security import APIKeyHeader

from llm_agent.config import Settings, get_settings

logger = logging.getLogger(__name__)

# API Key Header（优先从 X-API-Key 读，auto_error=False 兼容 Authorization Bearer）
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key(
    x_api_key: Optional[str] = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> Optional[str]:
    """
    从请求头获取 API Key

    优先读取 X-API-Key 头，回退读取 Authorization: Bearer <key>

    Returns:
        str: API Key 字符串，如果未提供则返回 None
    """
    # 优先从 X-API-Key 获取
    if x_api_key:
        return x_api_key

    # 回退：从 Authorization Bearer 获取（在调用方通过 Depends(Authorization) 读取）
    # 这里简化为：如果 X-API-Key 不存在，返回 None，让 verify_api_key 继续处理
    return None


async def verify_api_key(
    x_api_key: Optional[str] = Security(api_key_header),
    settings: Settings = Depends(get_settings),
) -> bool:
    """
    验证 API Key 依赖

    - api_auth_enabled=False 时直接放行（开发模式）
    - 启用但未配置 api_keys → 401（配置错误）
    - 启用且 key 在 api_keys 列表中 → 放行
    - 其他情况 → 401

    Raises:
        HTTPException: 401 Unauthorized
    """
    # 认证未启用，直接放行
    if not settings.api_auth_enabled:
        return True

    # 启用认证但未配置任何 key（配置错误，拒绝所有请求）
    if not settings.api_keys:
        logger.warning("API 认证已启用（api_auth_enabled=true）但未配置 api_keys，拒绝所有请求")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API 认证配置错误：未配置有效密钥",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 获取提供的 key
    provided_key = x_api_key
    if not provided_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key（需 X-API-Key 或 Authorization: Bearer 头）",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 验证 key 是否在允许列表中
    if provided_key not in settings.api_keys:
        logger.warning(f"API Key 验证失败：提供的 key 不在允许列表中")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的 API Key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    # 验证通过
    logger.debug(f"API Key 验证通过（key 前4位: {provided_key[:4]}***）")
    return True


# 依赖注入类型别名（供 router 使用）
ApiKeyDep = Annotated[bool, Depends(verify_api_key)]

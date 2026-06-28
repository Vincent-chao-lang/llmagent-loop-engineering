"""
通用Schema定义
"""

from typing import TypeVar, Generic, Optional, Any
from datetime import datetime
from pydantic import BaseModel, Field


T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    """统一响应格式"""

    success: bool = Field(description="请求是否成功")
    data: Optional[T] = Field(default=None, description="响应数据")
    error: Optional[str] = Field(default=None, description="错误信息")
    timestamp: datetime = Field(default_factory=datetime.now, description="响应时间戳")

    model_config = {"from_attributes": False}


class ErrorResponse(BaseModel):
    """错误响应"""

    success: bool = Field(default=False, description="固定为False")
    error: str = Field(description="错误消息")
    detail: Optional[str] = Field(default=None, description="详细错误信息")
    timestamp: datetime = Field(default_factory=datetime.now)

    model_config = {"from_attributes": False}


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field(description="服务状态: healthy/degraded")
    version: str = Field(description="框架版本")
    timestamp: datetime = Field(default_factory=datetime.now)

"""
依赖注入
"""

from fastapi import Depends
from typing import Annotated

from llm_agent.config import Settings, get_settings
from llm_agent.api.session import SessionManager, get_session_manager

# 依赖注入类型别名
SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionManagerDep = Annotated[SessionManager, Depends(get_session_manager)]

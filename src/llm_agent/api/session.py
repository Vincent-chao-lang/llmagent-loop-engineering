"""
会话管理器
管理LLMAgent实例的生命周期
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import uuid4

from llm_agent.agents.base import LLMAgent
from llm_agent.config import get_settings
from llm_agent.memory.memory import Memory, MemoryConfig

logger = logging.getLogger(__name__)


class SessionManager:
    """Agent会话管理器

    管理多个Agent实例的生命周期，支持会话创建、获取、销毁和过期清理。
    """

    def __init__(self, session_ttl: Optional[int] = None):
        """初始化会话管理器

        Args:
            session_ttl: 会话过期时间（秒），None则从配置读取
        """
        settings = get_settings()
        self.session_ttl = session_ttl or settings.session_ttl
        self.max_sessions = settings.max_sessions

        self._sessions: Dict[str, LLMAgent] = {}
        self._last_access: Dict[str, datetime] = {}
        self._lock = asyncio.Lock()
        self._cleanup_task: Optional[asyncio.Task] = None

        logger.info(
            f"SessionManager初始化: TTL={self.session_ttl}s, max={self.max_sessions}"
        )

    async def create_session(
        self,
        system_prompt: str,
        agent_role: str,
        provider: str = "mock",
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        memory_config: Optional[MemoryConfig] = None,
    ) -> str:
        """创建Agent会话

        Args:
            system_prompt: 系统提示词
            agent_role: Agent角色
            provider: LLM提供商
            model: 模型名称
            api_key: API密钥
            memory_config: 记忆配置

        Returns:
            session_id: 会话ID
        """
        async with self._lock:
            # 检查会话数量上限
            if len(self._sessions) >= self.max_sessions:
                # 先清理过期会话
                await self.cleanup_expired()
                # 如果还是满，删除最旧的会话
                if len(self._sessions) >= self.max_sessions:
                    oldest_id = min(self._last_access, key=self._last_access.get)
                    await self.destroy_session(oldest_id)
                    logger.warning(f"达到最大会话数，清理最旧会话: {oldest_id}")

            # 创建LLM客户端
            from llm_agent.llm.client import LLMClient

            llm_config = {}
            if api_key:
                llm_config["api_key"] = api_key

            llm_client = LLMClient(
                provider=provider,
                model_name=model or "llm-agent-model",
                config=llm_config if llm_config else None,
            )

            # 创建记忆系统
            if memory_config is None:
                settings = get_settings()
                memory_config = MemoryConfig(
                    short_term_capacity=settings.memory_short_term_capacity,
                    long_term_capacity=settings.memory_long_term_capacity,
                    working_memory_capacity=settings.memory_working_capacity,
                )

            memory = Memory(memory_config)

            # 创建Agent
            agent = LLMAgent(
                llm_client=llm_client,
                system_prompt=system_prompt,
                agent_role=agent_role,
                memory=memory,
            )

            session_id = agent.agent_id
            self._sessions[session_id] = agent
            self._last_access[session_id] = datetime.now()

            logger.info(f"创建会话: {session_id}, role={agent_role}")
            return session_id

    async def get_session(self, session_id: str) -> Optional[LLMAgent]:
        """获取Agent会话

        Args:
            session_id: 会话ID

        Returns:
            LLMAgent实例，不存在或过期返回None
        """
        async with self._lock:
            if session_id not in self._sessions:
                return None

            # 检查是否过期
            last_access = self._last_access[session_id]
            if datetime.now() - last_access > timedelta(seconds=self.session_ttl):
                await self.destroy_session(session_id)
                return None

            # 更新最后访问时间
            self._last_access[session_id] = datetime.now()
            return self._sessions[session_id]

    async def destroy_session(self, session_id: str) -> bool:
        """销毁Agent会话

        Args:
            session_id: 会话ID

        Returns:
            是否成功销毁
        """
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                del self._last_access[session_id]
                logger.info(f"销毁会话: {session_id}")
                return True
            return False

    async def cleanup_expired(self) -> int:
        """清理过期会话

        Returns:
            清理的会话数
        """
        async with self._lock:
            now = datetime.now()
            expired_ids = [
                sid
                for sid, last_access in self._last_access.items()
                if now - last_access > timedelta(seconds=self.session_ttl)
            ]

            for sid in expired_ids:
                del self._sessions[sid]
                del self._last_access[sid]

            if expired_ids:
                logger.info(f"清理过期会话: {len(expired_ids)}个")

            return len(expired_ids)

    def get_session_info(self) -> Dict:
        """获取会话统计信息

        Returns:
            会话统计信息
        """
        return {
            "total_sessions": len(self._sessions),
            "max_sessions": self.max_sessions,
            "session_ttl": self.session_ttl,
            "active_sessions": list(self._sessions.keys()),
        }

    async def start_background_cleanup(self, interval: int = 300):
        """启动后台清理任务

        Args:
            interval: 清理间隔（秒），默认5分钟
        """

        async def cleanup_loop():
            while True:
                try:
                    await asyncio.sleep(interval)
                    await self.cleanup_expired()
                except asyncio.CancelledError:
                    logger.info("后台清理任务已取消")
                    break
                except Exception as e:
                    logger.error(f"后台清理异常: {e}")

        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(f"启动后台清理任务，间隔: {interval}s")

    async def stop_background_cleanup(self):
        """停止后台清理任务"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            self._cleanup_task = None
            logger.info("后台清理任务已停止")

    async def shutdown(self):
        """关闭会话管理器"""
        await self.stop_background_cleanup()
        async with self._lock:
            self._sessions.clear()
            self._last_access.clear()
        logger.info("SessionManager已关闭")


# 全局会话管理器实例
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """获取全局会话管理器单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager


def reset_session_manager():
    """重置会话管理器（主要用于测试）"""
    global _session_manager
    _session_manager = None

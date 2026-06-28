"""
配置管理
"""

from typing import List, Optional
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from llm_agent.llm.client import LLMClient
from llm_agent.memory.memory import Memory, MemoryConfig


class Settings(BaseSettings):
    """LLM Agent框架配置"""

    # LLM配置
    llm_provider: str = Field(default="mock", description="LLM提供商: mock/anthropic/openai")
    llm_model: str = Field(default="llm-agent-model", description="模型名称")
    llm_api_key: Optional[str] = Field(default=None, description="API密钥")

    # API服务配置
    api_host: str = Field(default="0.0.0.0", description="API服务地址")
    api_port: int = Field(default=8000, description="API服务端口")
    api_workers: int = Field(default=1, description="API服务进程数")

    # 会话管理
    session_ttl: int = Field(default=3600, description="会话过期时间（秒）")
    max_sessions: int = Field(default=100, description="最大并发会话数")

    # 记忆配置
    memory_short_term_capacity: int = Field(default=100, description="短期记忆容量")
    memory_long_term_capacity: int = Field(default=1000, description="长期记忆容量")
    memory_working_capacity: int = Field(default=10, description="工作记忆容量")

    # 循环终止配置
    max_execution_retries: int = Field(default=3, description="执行失败时最大重试次数")
    max_execution_time: int = Field(default=300, description="执行任务的最大时间（秒）")
    max_think_calls: int = Field(default=50, description="最大思考次数限制（防无限循环）")
    allow_plan_regression: bool = Field(default=False, description="是否允许计划退化（新计划步骤更多）")

    # API认证配置
    api_auth_enabled: bool = Field(default=False, description="是否启用API Key认证")
    api_keys: List[str] = Field(default_factory=list, description="有效的API Key列表")

    # CORS配置
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        description="CORS允许的来源"
    )
    cors_allow_methods: List[str] = Field(default=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    cors_allow_headers: List[str] = Field(
        default=["Authorization", "Content-Type", "X-API-Key", "X-Request-ID"],
        description="CORS允许的请求头（allow_credentials=True时浏览器不接受*）"
    )

    # 环境变量前缀
    model_config = SettingsConfigDict(
        env_prefix="LLM_AGENT_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    def get_llm_client(self) -> LLMClient:
        """创建LLM客户端实例"""
        config = {}
        if self.llm_api_key:
            config["api_key"] = self.llm_api_key

        return LLMClient(
            provider=self.llm_provider,
            model_name=self.llm_model,
            config=config if config else None
        )

    def get_memory(self) -> Memory:
        """创建记忆系统实例"""
        memory_config = MemoryConfig(
            short_term_capacity=self.memory_short_term_capacity,
            long_term_capacity=self.memory_long_term_capacity,
            working_memory_capacity=self.memory_working_capacity,
        )
        return Memory(memory_config)


# 全局配置实例
_settings: Optional[Settings] = None


def get_settings(config_file: Optional[Path] = None) -> Settings:
    """获取配置单例"""
    global _settings
    if _settings is None:
        if config_file and config_file.exists():
            # 从YAML文件加载（需要yaml支持）
            import yaml
            with open(config_file) as f:
                config_data = yaml.safe_load(f)
            _settings = Settings(**config_data)
        else:
            _settings = Settings()
    return _settings


def reset_settings():
    """重置配置（主要用于测试）"""
    global _settings
    _settings = None

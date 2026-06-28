"""
LLM Agent Framework - LLM组件

提供专门为LLM Agent设计的LLM客户端和提示词管理。
"""

from llm_agent.llm.client import LLMClient, LLMResponse
from llm_agent.llm.prompts import PromptManager, PromptTemplate, get_prompt_manager
from llm_agent.llm.adapters import (
    BaseAdapter,
    MockAdapter,
    AnthropicAdapter,
    OpenAIAdapter,
    AdapterFactory
)

__all__ = [
    "LLMClient",
    "LLMResponse",
    "PromptManager",
    "PromptTemplate",
    "get_prompt_manager",
    "BaseAdapter",
    "MockAdapter",
    "AnthropicAdapter",
    "OpenAIAdapter",
    "AdapterFactory"
]

"""
LLM Agent Framework - 适配器

连接不同的LLM提供商
"""

from typing import Dict, List, Any, Optional
import asyncio


class BaseAdapter:
    """LLM提供商适配器基类"""

    def __init__(self, config: Dict[str, Any]):
        """初始化适配器

        Args:
            config: 提供商配置
        """
        self.config = config
        self.client = None

    async def initialize(self):
        """初始化客户端"""
        raise NotImplementedError

    async def chat(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """聊天接口

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            **kwargs: 额外参数

        Returns:
            响应字典
        """
        raise NotImplementedError

    async def stream_chat(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ):
        """流式聊天接口

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            **kwargs: 额外参数

        Yields:
            流式响应片段
        """
        raise NotImplementedError


class MockAdapter(BaseAdapter):
    """模拟适配器 - 用于测试"""

    async def initialize(self):
        """初始化模拟客户端"""
        self.client = "mock_client"

    async def chat(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """模拟聊天"""
        await asyncio.sleep(0.1)

        return {
            "content": f"模拟响应: {prompt[:50]}...",
            "reasoning": "模拟推理过程",
            "confidence": 0.85,
            "success": True
        }

    async def stream_chat(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ):
        """模拟流式聊天"""
        response = f"流式响应: {prompt[:30]}..."
        for char in response:
            await asyncio.sleep(0.01)
            yield {"content": char, "done": False}
        yield {"content": "", "done": True}


class AnthropicAdapter(BaseAdapter):
    """Anthropic Claude适配器"""

    async def initialize(self):
        """初始化Anthropic客户端"""
        try:
            from anthropic import AsyncAnthropic
            api_key = self.config.get("api_key")
            if not api_key:
                raise ValueError("缺少api_key配置")

            self.client = AsyncAnthropic(api_key=api_key)

        except ImportError:
            raise ImportError("需要安装 anthropic 包: pip install anthropic")

    async def chat(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """使用Claude聊天"""
        try:
            response = await self.client.messages.create(
                model=self.config.get("model", "claude-opus-4-6"),
                max_tokens=self.config.get("max_tokens", 4096),
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            )

            return {
                "content": response.content[0].text,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                "success": True
            }

        except Exception as e:
            return {
                "content": "",
                "error": str(e),
                "success": False
            }

    async def stream_chat(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ):
        """Claude流式聊天"""
        try:
            async with self.client.messages.stream(
                model=self.config.get("model", "claude-opus-4-6"),
                max_tokens=self.config.get("max_tokens", 4096),
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}],
                **kwargs
            ) as stream:
                async for text in stream.text_stream:
                    yield {"content": text, "done": False}
                yield {"content": "", "done": True}

        except Exception as e:
            yield {"content": f"错误: {str(e)}", "done": True}


class OpenAIAdapter(BaseAdapter):
    """OpenAI GPT适配器"""

    async def initialize(self):
        """初始化OpenAI客户端"""
        try:
            from openai import AsyncOpenAI
            api_key = self.config.get("api_key")
            if not api_key:
                raise ValueError("缺少api_key配置")

            self.client = AsyncOpenAI(api_key=api_key)

        except ImportError:
            raise ImportError("需要安装 openai 包: pip install openai")

    async def chat(
        self,
        prompt: str,
        system_prompt: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """使用GPT聊天"""
        try:
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            response = await self.client.chat.completions.create(
                model=self.config.get("model", "gpt-4"),
                messages=messages,
                **kwargs
            )

            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.prompt_tokens,
                    "output_tokens": response.usage.completion_tokens
                },
                "success": True
            }

        except Exception as e:
            return {
                "content": "",
                "error": str(e),
                "success": False
            }


class AdapterFactory:
    """适配器工厂"""

    @staticmethod
    def create_adapter(provider: str, config: Dict[str, Any]) -> BaseAdapter:
        """创建适配器

        Args:
            provider: 提供商名称
            config: 配置字典

        Returns:
            适配器实例
        """
        adapters = {
            "mock": MockAdapter,
            "anthropic": AnthropicAdapter,
            "openai": OpenAIAdapter,
        }

        adapter_class = adapters.get(provider.lower())
        if not adapter_class:
            raise ValueError(f"不支持的提供商: {provider}")

        return adapter_class(config)


__all__ = [
    "BaseAdapter",
    "MockAdapter",
    "AnthropicAdapter",
    "OpenAIAdapter",
    "AdapterFactory"
]

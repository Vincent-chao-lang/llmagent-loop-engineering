"""
LLM Agent工具系统

提供工具注册和执行功能。
"""

from typing import Dict, List, Any, Callable, Optional


class Tool:
    """工具定义"""

    def __init__(
        self,
        name: str,
        description: str,
        function: Callable,
        parameters: Dict[str, Any] = None
    ):
        """初始化工具

        Args:
            name: 工具名称
            description: 工具描述
            function: 执行函数
            parameters: 参数定义
        """
        self.name = name
        self.description = description
        self.function = function
        self.parameters = parameters or {}

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具

        Args:
            **kwargs: 工具参数

        Returns:
            执行结果
        """
        try:
            if asyncio.iscoroutinefunction(self.function):
                result = await self.function(**kwargs)
            else:
                result = self.function(**kwargs)

            return {
                "success": True,
                "result": result,
                "tool": self.name
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "tool": self.name
            }


class ToolRegistry:
    """工具注册表"""

    def __init__(self, tools: List[Tool] = None):
        """初始化工具注册表

        Args:
            tools: 初始工具列表
        """
        self.tools = {tool.name: tool for tool in (tools or [])}
        self.usage_history = {}

    def register(self, tool: Tool):
        """注册新工具

        Args:
            tool: 工具对象
        """
        self.tools[tool.name] = tool

    def get_tool(self, name: str) -> Optional[Tool]:
        """获取工具

        Args:
            name: 工具名称

        Returns:
            工具对象或None
        """
        return self.tools.get(name)

    async def execute_tool(self, name: str, params: Dict) -> Dict[str, Any]:
        """执行工具

        Args:
            name: 工具名称
            params: 参数字典

        Returns:
            执行结果
        """
        tool = self.get_tool(name)
        if not tool:
            return {
                "success": False,
                "error": f"工具 '{name}' 不存在"
            }

        # 记录使用历史
        if name not in self.usage_history:
            self.usage_history[name] = []

        result = await tool.execute(**params)

        self.usage_history[name].append({
            "params": params,
            "result": result,
            "timestamp": __import__("datetime").datetime.now()
        })

        return result

    def list_available(self) -> List[str]:
        """列出可用工具

        Returns:
            工具名称列表
        """
        return list(self.tools.keys())

    def get_tool_info(self, name: str) -> Optional[Dict]:
        """获取工具信息

        Args:
            name: 工具名称

        Returns:
            工具信息字典
        """
        tool = self.get_tool(name)
        if not tool:
            return None

        return {
            "name": tool.name,
            "description": tool.description,
            "parameters": tool.parameters,
            "usage_count": len(self.usage_history.get(name, []))
        }


__all__ = ["Tool", "ToolRegistry"]

"""
增强的工具注册表 - 集成所有工具系统深度功能
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from .registry import Tool, ToolRegistry as BaseToolRegistry
from .tool_chain import ToolChainOrchestrator, ToolChain, ChainExecutionResult
from .tool_cache import ToolCache, create_tool_cache, CacheStrategy


class ToolCategory(Enum):
    """工具分类"""
    DATA_PROCESSING = "data_processing"      # 数据处理
    FILE_OPERATIONS = "file_operations"        # 文件操作
    NETWORK = "network"                       # 网络操作
    ANALYSIS = "analysis"                       # 分析工具
    AUTOMATION = "automation"                   # 自动化工具
    INTEGRATION = "integration"                 # 集成工具


@dataclass
class EnhancedTool(Tool):
    """增强的工具定义"""
    category: ToolCategory = ToolCategory.INTEGRATION
    version: str = "1.0"
    author: str = ""
    dependencies: List[str] = field(default_factory=list)
    performance_score: float = 0.8  # 性能评分
    reliability_score: float = 0.8   # 可靠性评分
    execution_cost: float = 0.5       # 执行成本（token数）

    # 增强的元数据
    timeout: int = 30                    # 超时时间（秒）
    retry_count: int = 3                # 重试次数
    rate_limit: Optional[int] = None    # 速率限制（次/分钟）
    required_permissions: List[str] = field(default_factory=list)


class EnhancedToolRegistry(BaseToolRegistry):
    """
    增强的工具注册表

    集成工具链编排、智能缓存、性能监控等深度功能。
    """

    def __init__(self, tools: List[Tool] = None):
        """初始化增强工具注册表

        Args:
            tools: 初始工具列表
        """
        super().__init__(tools)

        # 深度功能组件
        self.chain_orchestrator = ToolChainOrchestrator(self)
        self.cache = create_tool_cache(strategy=CacheStrategy.ADAPTIVE)

        # 增强的使用追踪
        self.detailed_history = {}
        self.performance_metrics = {}

    async def register_enhanced_tool(self, tool: EnhancedTool) -> str:
        """注册增强工具

        Args:
            tool: 增强的工具对象

        Returns:
            str: 工具ID
        """
        # 检查依赖
        for dep in tool.dependencies:
            if not self.get_tool(dep):
                raise ValueError(f"依赖工具 {dep} 不存在")

        # 注册工具
        tool_id = await self.register(tool)

        # 初始化性能指标
        self.performance_metrics[tool.name] = {
            "total_executions": 0,
            "successful_executions": 0,
            "average_execution_time": 0.0,
            "average_cost": tool.execution_cost,
            "error_rate": 0.0
        }

        return tool_id

    async def execute_tool_enhanced(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        use_cache: bool = True,
        timeout: int = None,
        retry_count: int = None
    ) -> Dict[str, Any]:
        """增强的工具执行

        Args:
            tool_name: 工具名称
            parameters: 工具参数
            use_cache: 是否使用缓存
            timeout: 超时时间
            retry_count: 重试次数

        Returns:
            Dict: 执行结果
        """
        start_time = datetime.now()
        execution_id = f"{tool_name}_{start_time.timestamp()}"

        try:
            # 检查缓存
            cached_result = None
            if use_cache:
                cached_result = await self.cache.get(tool_name, parameters)

            if cached_result is not None:
                # 缓存命中
                self._update_performance_metrics(tool_name, True, 0.001, cached_result)
                return {
                    "success": True,
                    "result": cached_result,
                    "tool": tool_name,
                    "cached": True,
                    "execution_time": 0.001,
                    "metadata": {"execution_id": execution_id}
                }

            # 执行工具
            tool = self.get_tool(tool_name)
            if not tool:
                return {
                    "success": False,
                    "error": f"工具 {tool_name} 不存在",
                    "tool": tool_name
                }

            # 应用重试逻辑
            result = await self._execute_with_retry(
                tool, parameters, retry_count or 3
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            # 更新性能指标
            self._update_performance_metrics(tool_name, result["success"], execution_time, result)

            # 缓存成功结果
            if result["success"] and use_cache:
                await self.cache.set(tool_name, parameters, result)

            return {
                **result,
                "tool": tool_name,
                "execution_time": execution_time,
                "cached": False,
                "metadata": {"execution_id": execution_id}
            }

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return {
                "success": False,
                "error": str(e),
                "tool": tool_name,
                "execution_time": execution_time,
                "cached": False
            }

    async def _execute_with_retry(
        self,
        tool: Tool,
        parameters: Dict[str, Any],
        max_retries: int
    ) -> Dict[str, Any]:
        """带重试的工具执行

        Args:
            tool: 工具对象
            parameters: 参数字典
            max_retries: 最大重试次数

        Returns:
            Dict: 执行结果
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                result = await tool.execute(**parameters)
                return result
            except Exception as e:
                last_error = e
                if attempt < max_retries - 1:
                    await asyncio.sleep(1)  # 重试前等待
                    continue

        # 所有重试都失败
        return {
            "success": False,
            "error": f"重试 {max_retries} 次后仍失败: {last_error}"
        }

    def _update_performance_metrics(
        self,
        tool_name: str,
        success: bool,
        execution_time: float,
        result: Dict[str, Any]
    ):
        """更新性能指标

        Args:
            tool_name: 工具名称
            success: 是否成功
            execution_time: 执行时间
            result: 执行结果
        """
        if tool_name not in self.performance_metrics:
            self.performance_metrics[tool_name] = {
                "total_executions": 0,
                "successful_executions": 0,
                "average_execution_time": 0.0,
                "average_cost": 0.0,
                "error_rate": 0.0
            }

        metrics = self.performance_metrics[tool_name]
        metrics["total_executions"] += 1

        if success:
            metrics["successful_executions"] += 1

        # 更新平均执行时间
        total_executions = metrics["total_executions"]
        current_avg = metrics["average_execution_time"]
        metrics["average_execution_time"] = (
            (current_avg * (total_executions - 1) + execution_time) / total_executions
        )

        # 更新错误率
        metrics["error_rate"] = 1.0 - (
            metrics["successful_executions"] / total_executions
        )

    async def create_tool_chain(
        self,
        name: str,
        description: str = "",
        strategy: str = "sequential"
    ) -> ToolChain:
        """创建工具链

        Args:
            name: 工具链名称
            description: 描述
            strategy: 执行策略

        Returns:
            ToolChain: 工具链对象
        """
        chain = await self.chain_orchestrator.create_chain(name, description)

        if strategy == "parallel":
            chain.execution_strategy = ExecutionStrategy.PARALLEL
        elif strategy == "pipeline":
            chain.execution_strategy = ExecutionStrategy.PIPELINE

        return chain

    async def execute_tool_chain(
        self,
        chain: ToolChain,
        input_data: Any = None
    ) -> ChainExecutionResult:
        """执行工具链

        Args:
            chain: 工具链
            input_data: 输入数据

        Returns:
            ChainExecutionResult: 执行结果
        """
        return await self.chain_orchestrator.execute_chain(chain, input_data)

    def get_performance_report(self, tool_name: str = None) -> Dict[str, Any]:
        """获取性能报告

        Args:
            tool_name: 工具名称（可选）

        Returns:
            Dict: 性能报告
        """
        if tool_name:
            if tool_name in self.performance_metrics:
                return self.performance_metrics[tool_name]
            else:
                return {"error": f"工具 {tool_name} 没有性能数据"}
        else:
            return self.performance_metrics

    async def optimize_registry(self):
        """优化工具注册表"""
        # 1. 清理未使用的工具缓存
        await self.cache.optimize_cache()

        # 2. 分析工具性能，移除低性能工具
        tools_to_remove = []
        for tool_name, metrics in self.performance_metrics.items():
            if metrics["error_rate"] > 0.5:  # 错误率超过50%
                tools_to_remove.append(tool_name)

        # 3. 重新排序工具列表（按性能）
        # （这里可以添加更多优化逻辑）

    async def get_comprehensive_stats(self) -> Dict[str, Any]:
        """获取综合统计信息

        Returns:
            Dict: 综合统计
        """
        cache_stats = await self.cache.get_cache_stats()
        orch_stats = self.chain_orchestrator.get_execution_statistics()

        return {
            "total_tools": len(self.tools),
            "performance_metrics": self.performance_metrics,
            "cache_statistics": cache_stats,
            "chain_statistics": orch_stats,
            "detailed_usage_history": len(self.detailed_history)
        }


# 工厂函数
def create_enhanced_tool_registry(tools: List[Tool] = None) -> EnhancedToolRegistry:
    """创建增强工具注册表

    Args:
        tools: 初始工具列表

    Returns:
        EnhancedToolRegistry: 增强注册表实例
    """
    return EnhancedToolRegistry(tools)
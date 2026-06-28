"""
工具链编排系统 - 支持复杂工具组合和智能执行
"""

import asyncio
from typing import Dict, List, Any, Optional, Callable, Union
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid
import hashlib


class ExecutionStrategy(Enum):
    """执行策略"""
    SEQUENTIAL = "sequential"           # 顺序执行
    PARALLEL = "parallel"               # 并行执行
    CONDITIONAL = "conditional"         # 条件执行
    PIPELINE = "pipeline"               # 管道式执行
    BRANCHING = "branching"             # 分支执行


@dataclass
class ToolResult:
    """工具执行结果"""
    tool_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "execution_time": self.execution_time,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ChainStep:
    """工具链步骤"""
    step_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    tool_name: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None  # 执行条件
    next_steps: List[str] = field(default_factory=list)  # 下一步骤
    parallel_group: Optional[str] = None  # 并行组标识
    strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL

    def with_result(self, result: ToolResult) -> 'ChainStepWithResult':
        """创建带结果的步骤"""
        return ChainStepWithResult(
            step_id=self.step_id,
            tool_name=self.tool_name,
            parameters=self.parameters,
            condition=self.condition,
            next_steps=self.next_steps,
            parallel_group=self.parallel_group,
            strategy=self.strategy,
            result=result
        )


@dataclass
class ChainStepWithResult(ChainStep):
    """带执行结果的步骤"""
    result: Optional[ToolResult] = None


@dataclass
class ToolChain:
    """工具链"""
    chain_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: List[ChainStep] = field(default_factory=list)
    execution_strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_step(self, tool_name: str, parameters: Dict[str, Any] = None,
                strategy: ExecutionStrategy = ExecutionStrategy.SEQUENTIAL,
                condition: str = None) -> ChainStep:
        """添加步骤到工具链"""
        step = ChainStep(
            tool_name=tool_name,
            parameters=parameters or {},
            strategy=strategy,
            condition=condition
        )
        self.steps.append(step)
        return step

    def connect(self, from_step: str, to_step: str):
        """连接两个步骤"""
        for step in self.steps:
            if step.step_id == from_step:
                step.next_steps.append(to_step)
                break


@dataclass
class ChainExecutionResult:
    """工具链执行结果"""
    chain_id: str
    chain_name: str
    success: bool
    executed_steps: List[ChainStepWithResult] = field(default_factory=list)
    total_execution_time: float = 0.0
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class ToolChainOrchestrator:
    """
    工具链编排器

    支持复杂的工具组合和智能执行策略。
    """

    def __init__(self, tool_registry):
        """初始化工具链编排器

        Args:
            tool_registry: 工具注册表
        """
        self.tool_registry = tool_registry
        self.execution_cache = {}
        self.execution_history = []

    async def create_chain(self, name: str, description: str = "") -> ToolChain:
        """创建工具链

        Args:
            name: 工具链名称
            description: 工具链描述

        Returns:
            ToolChain: 工具链对象
        """
        return ToolChain(
            name=name,
            description=description,
            execution_strategy=ExecutionStrategy.SEQUENTIAL
        )

    async def execute_chain(
        self,
        chain: ToolChain,
        input_data: Any = None,
        strategy: ExecutionStrategy = None
    ) -> ChainExecutionResult:
        """执行工具链

        Args:
            chain: 工具链
            input_data: 输入数据
            strategy: 执行策略（可选，默认使用工具链的策略）

        Returns:
            ChainExecutionResult: 执行结果
        """
        start_time = datetime.now()
        executed_steps = []
        execution_strategy = strategy or chain.execution_strategy

        try:
            if execution_strategy == ExecutionStrategy.SEQUENTIAL:
                result = await self._execute_sequential(chain, input_data, executed_steps)
            elif execution_strategy == ExecutionStrategy.PARALLEL:
                result = await self._execute_parallel(chain, input_data, executed_steps)
            elif execution_strategy == ExecutionStrategy.PIPELINE:
                result = await self._execute_pipeline(chain, input_data, executed_steps)
            elif execution_strategy == ExecutionStrategy.CONDITIONAL:
                result = await self._execute_conditional(chain, input_data, executed_steps)
            else:
                result = await self._execute_sequential(chain, input_data, executed_steps)

            execution_time = (datetime.now() - start_time).total_seconds()

            return ChainExecutionResult(
                chain_id=chain.chain_id,
                chain_name=chain.name,
                success=result.success,
                executed_steps=executed_steps,
                total_execution_time=execution_time,
                error=result.error,
                metadata={
                    "strategy": execution_strategy.value,
                    "input_type": type(input_data).__name__
                }
            )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ChainExecutionResult(
                chain_id=chain.chain_id,
                chain_name=chain.name,
                success=False,
                executed_steps=executed_steps,
                total_execution_time=execution_time,
                error=str(e)
            )

    async def _execute_sequential(
        self,
        chain: ToolChain,
        input_data: Any,
        executed_steps: List[ChainStepWithResult]
    ) -> ChainExecutionResult:
        """顺序执行工具链

        Args:
            chain: 工具链
            input_data: 输入数据
            executed_steps: 已执行步骤列表

        Returns:
            ChainExecutionResult: 执行结果
        """
        current_data = input_data

        for step in chain.steps:
            step_result = await self._execute_step(step, current_data)
            executed_steps.append(step.with_result(step_result))

            if not step_result.success:
                return ChainExecutionResult(
                    chain_id=chain.chain_id,
                    chain_name=chain.name,
                    success=False,
                    executed_steps=executed_steps,
                    error=f"步骤 {step.tool_name} 执行失败: {step_result.error}"
                )

            # 将结果传递给下一步
            current_data = step_result.result

        return ChainExecutionResult(
            chain_id=chain.chain_id,
            chain_name=chain.name,
            success=True,
            executed_steps=executed_steps
        )

    async def _execute_parallel(
        self,
        chain: ToolChain,
        input_data: Any,
        executed_steps: List[ChainStepWithResult]
    ) -> ChainExecutionResult:
        """并行执行工具链

        Args:
            chain: 工具链
            input_data: 输入数据
            executed_steps: 已执行步骤列表

        Returns:
            ChainExecutionResult: 执行结果
        """
        # 按并行组分组
        parallel_groups = {}
        for step in chain.steps:
            group_id = step.parallel_group or "default"
            if group_id not in parallel_groups:
                parallel_groups[group_id] = []
            parallel_groups[group_id].append(step)

        # 并行执行每个组
        group_results = {}
        for group_id, steps in parallel_groups.items():
            group_tasks = [
                self._execute_step(step, input_data)
                for step in steps
            ]
            group_results[group_id] = await asyncio.gather(*group_tasks)

        # 收集结果
        all_successful = True
        for group_id, results in group_results.items():
            for step, result in zip(parallel_groups[group_id], results):
                executed_steps.append(step.with_result(result))
                if not result.success:
                    all_successful = False

        return ChainExecutionResult(
            chain_id=chain.chain_id,
            chain_name=chain.name,
            success=all_successful,
            executed_steps=executed_steps
        )

    async def _execute_pipeline(
        self,
        chain: ToolChain,
        input_data: Any,
        executed_steps: List[ChainStepWithResult]
    ) -> ChainExecutionResult:
        """管道式执行工具链

        Args:
            chain: 工具链
            input_data: 输入数据
            executed_steps: 已执行步骤列表

        Returns:
            ChainExecutionResult: 执行结果
        """
        current_data = input_data

        for step in chain.steps:
            # 管道式执行：每个工具的输出成为下一个的输入
            step_result = await self._execute_step(step, current_data)
            executed_steps.append(step.with_result(step_result))

            if not step_result.success:
                return ChainExecutionResult(
                    chain_id=chain.chain_id,
                    chain_name=chain.name,
                    success=False,
                    executed_steps=executed_steps,
                    error=f"管道步骤 {step.tool_name} 执行失败: {step_result.error}"
                )

            # 管道式传递数据
            current_data = self._transform_for_next_step(step_result.result, step.tool_name)

        return ChainExecutionResult(
            chain_id=chain.chain_id,
            chain_name=chain.name,
            success=True,
            executed_steps=executed_steps
        )

    async def _execute_conditional(
        self,
        chain: ToolChain,
        input_data: Any,
        executed_steps: List[ChainStepWithResult]
    ) -> ChainExecutionResult:
        """条件执行工具链

        Args:
            chain: 工具链
            input_data: 输入数据
            executed_steps: 已执行步骤列表

        Returns:
            ChainExecutionResult: 执行结果
        """
        current_data = input_data

        for step in chain.steps:
            # 检查执行条件
            if step.condition and not self._evaluate_condition(step.condition, current_data):
                continue

            step_result = await self._execute_step(step, current_data)
            executed_steps.append(step.with_result(step_result))

            if not step_result.success:
                # 条件执行失败不影响整体成功
                continue

            current_data = step_result.result

        return ChainExecutionResult(
            chain_id=chain.chain_id,
            chain_name=chain.name,
            success=True,
            executed_steps=executed_steps
        )

    async def _execute_step(self, step: ChainStep, input_data: Any) -> ToolResult:
        """执行单个工具步骤

        Args:
            step: 工具步骤
            input_data: 输入数据

        Returns:
            ToolResult: 执行结果
        """
        start_time = datetime.now()

        try:
            # 从工具注册表获取工具
            tool = self.tool_registry.get_tool(step.tool_name)
            if not tool:
                return ToolResult(
                    tool_name=step.tool_name,
                    success=False,
                    error=f"工具 {step.tool_name} 不存在"
                )

            # 检查缓存
            cache_key = self._generate_cache_key(step.tool_name, step.parameters)
            if cache_key in self.execution_cache:
                cached_result = self.execution_cache[cache_key]
                return ToolResult(
                    tool_name=step.tool_name,
                    success=True,
                    result=cached_result,
                    execution_time=0.001,  # 缓存命中，时间极短
                    metadata={"cached": True, "from_cache": True}
                )

            # 执行工具
            result = await self.tool_registry.execute_tool(
                step.tool_name,
                {**step.parameters, "input_data": input_data}
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            if result["success"]:
                # 缓存成功的结果
                self.execution_cache[cache_key] = result["result"]
                return ToolResult(
                    tool_name=step.tool_name,
                    success=True,
                    result=result["result"],
                    execution_time=execution_time,
                    metadata={"cached": False}
                )
            else:
                return ToolResult(
                    tool_name=step.tool_name,
                    success=False,
                    error=result.get("error", "执行失败"),
                    execution_time=execution_time
                )

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            return ToolResult(
                tool_name=step.tool_name,
                success=False,
                error=str(e),
                execution_time=execution_time
            )

    def _generate_cache_key(self, tool_name: str, parameters: Dict[str, Any]) -> str:
        """生成缓存键

        Args:
            tool_name: 工具名称
            parameters: 参数字典

        Returns:
            str: 缓存键
        """
        # 创建一个确定性的字符串表示
        params_str = str(sorted(parameters.items()))
        cache_string = f"{tool_name}:{params_str}"
        return hashlib.md5(cache_string.encode()).hexdigest()

    def _evaluate_condition(self, condition: str, data: Any) -> bool:
        """评估执行条件

        Args:
            condition: 条件表达式
            data: 上下文数据

        Returns:
            bool: 条件是否满足
        """
        try:
            # 简化实现：支持基本条件
            if "=" in condition:
                var, value = condition.split("=", 1)
                return str(data.get(var.strip())) == value.strip()
            elif ">" in condition:
                var, value = condition.split(">", 1)
                return float(data.get(var.strip(), 0)) > float(value.strip())
            elif "<" in condition:
                var, value = condition.split("<", 1)
                return float(data.get(var.strip(), 0)) < float(value.strip())
            else:
                return bool(data.get(condition.strip()))
        except:
            return False

    def _transform_for_next_step(self, result: Any, tool_name: str) -> Any:
        """为下一步骤转换数据

        Args:
            result: 当前步骤结果
            tool_name: 工具名称

        Returns:
            Any: 转换后的数据
        """
        # 大多数情况直接传递结果
        if isinstance(result, dict):
            return result.get("output", result)
        return result

    async def optimize_chain(self, chain: ToolChain) -> ToolChain:
        """优化工具链

        Args:
            chain: 原始工具链

        Returns:
            ToolChain: 优化后的工具链
        """
        # 1. 移除重复步骤
        seen_tools = set()
        optimized_steps = []
        for step in chain.steps:
            if step.tool_name not in seen_tools:
                optimized_steps.append(step)
                seen_tools.add(step.tool_name)

        # 2. 识别可并行执行的步骤
        for i, step in enumerate(optimized_steps):
            if i > 0 and not step.next_steps:
                # 检查是否可以与前一步骤并行
                prev_step = optimized_steps[i-1]
                if self._can_execute_in_parallel(step, prev_step):
                    step.strategy = ExecutionStrategy.PARALLEL
                    step.parallel_group = f"group_{i-1}_{i}"

        # 3. 优化参数
        for step in optimized_steps:
            step.parameters = await self._optimize_parameters(step.tool_name, step.parameters)

        return ToolChain(
            chain_id=chain.chain_id,
            name=chain.name,
            description=chain.description,
            steps=optimized_steps,
            execution_strategy=chain.execution_strategy
        )

    def _can_execute_in_parallel(self, step1: ChainStep, step2: ChainStep) -> bool:
        """判断两个步骤是否可以并行执行

        Args:
            step1: 第一个步骤
            step2: 第二个步骤

        Returns:
            bool: 是否可以并行
        """
        # 简化实现：如果没有数据依赖，可以并行
        return (
            step1.tool_name != step2.tool_name and
            not any(step2.tool_name in dep for dep in step1.next_steps)
        )

    async def _optimize_parameters(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """优化工具参数

        Args:
            tool_name: 工具名称
            parameters: 原始参数

        Returns:
            Dict: 优化后的参数
        """
        # 简化实现：移除None值和空字符串
        return {
            k: v for k, v in parameters.items()
            if v is not None and v != ""
        }

    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计信息

        Returns:
            Dict: 统计信息
        """
        if not self.execution_history:
            return {}

        total_executions = len(self.execution_history)
        successful_executions = len([r for r in self.execution_history if r.success])

        return {
            "total_executions": total_executions,
            "successful_executions": successful_executions,
            "success_rate": successful_executions / total_executions if total_executions > 0 else 0,
            "cache_hit_rate": len(self.execution_cache) / max(total_executions, 1),
            "average_execution_time": sum(r.total_execution_time for r in self.execution_history) / total_executions if total_executions > 0 else 0
        }


# 工厂函数
def create_tool_chain_orchestrator(tool_registry) -> ToolChainOrchestrator:
    """创建工具链编排器

    Args:
        tool_registry: 工具注册表

    Returns:
        ToolChainOrchestrator: 编排器实例
    """
    return ToolChainOrchestrator(tool_registry)
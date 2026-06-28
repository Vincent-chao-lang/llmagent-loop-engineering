"""
LLM Agent基类

专门的LLM Agent实现，以LLM为核心，
具备记忆、规划、反思等AI能力。
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import uuid


@dataclass
class AgentResponse:
    """Agent响应"""
    content: str
    tool_calls: List[Dict] = field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPlan:
    """执行计划"""
    goal: str
    steps: List[Dict] = field(default_factory=list)
    estimated_time: int = 0
    required_tools: List[str] = field(default_factory=list)
    
    # 执行进度追踪
    executed_steps: List[Dict] = field(default_factory=list)
    current_step_index: int = 0

    def remaining_steps(self) -> List[Dict]:
        """获取剩余未执行的步骤"""
        if self.current_step_index >= len(self.steps):
            return []
        return self.steps[self.current_step_index:]
    
    def total_steps(self) -> int:
        """获取总步骤数"""
        return len(self.steps)
    
    def completed_steps_count(self) -> int:
        """获取已完成步骤数"""
        return self.current_step_index
    
    def mark_step_completed(self, step_result: Dict = None) -> None:
        """标记当前步骤为已完成
        
        Args:
            step_result: 步骤执行结果（可选）
        """
        if self.current_step_index < len(self.steps):
            step = self.steps[self.current_step_index].copy()
            if step_result:
                step.update(step_result)
            self.executed_steps.append(step)
            self.current_step_index += 1
    
    def get_progress(self) -> float:
        """获取执行进度百分比
        
        Returns:
            float: 0.0 到 1.0
        """
        if not self.steps:
            return 1.0
        return self.current_step_index / len(self.steps)

    def update(self, new_plan_content: str) -> None:
        """更新执行计划

        根据新的计划内容更新当前步骤。
        用于动态重规划场景。

        Args:
            new_plan_content: 新的计划内容（LLM生成的文本）
        """
        # 简化实现：解析新内容并更新步骤
        # 实际应该有更复杂的解析逻辑，保持已完成的步骤
        import re
        # 尝试提取步骤（简单实现）
        step_patterns = re.findall(r'(?:步骤|step)\s*\d+[:\.]\s*([^\n]+)', new_plan_content, re.IGNORECASE)
        if step_patterns:
            self.steps = [{"description": s.strip(), "step_type": "thinking"} for s in step_patterns]
            self.estimated_time = len(self.steps) * 60  # 重新估算时间
        # 如果解析失败，保持原计划不变


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    steps: List[Any] = field(default_factory=list)
    reflection: Optional[str] = None
    error: Optional[str] = None


@dataclass
class Reflection:
    """反思结果"""
    insights: str
    improvements: str
    lessons_learned: str


@dataclass
class MemoryContext:
    """记忆上下文"""
    long_term: List[Any] = field(default_factory=list)
    short_term: List[Any] = field(default_factory=list)
    working: Dict[str, Any] = field(default_factory=dict)


class LLMAgent:
    """专门的LLM Agent

    特点：
    - LLM为核心，不是外挂组件
    - 具备完整的记忆系统
    - 能够自主规划和执行
    - 支持工具的智能调用
    - 具备反思和改进能力
    """

    def __init__(
        self,
        llm_client,                    # 必需：LLM客户端
        system_prompt: str,            # 必需：系统提示词
        agent_role: str,               # 必需：Agent角色
        memory,                        # 必需：记忆系统
        tools=None,                    # 可选：工具列表
        planning_strategy: str = "auto" # 可选：规划策略
    ):
        """初始化LLM Agent

        Args:
            llm_client: LLM客户端（必需）
            system_prompt: 系统提示词（必需）
            agent_role: Agent角色（必需）
            memory: 记忆系统（必需）
            tools: 工具列表（可选）
            planning_strategy: 规划策略（可选）
        """
        # 核心组件（必需）
        self.llm = llm_client
        self.system_prompt = system_prompt
        self.agent_role = agent_role
        self.memory = memory

        # 增强组件（可选）
        self.tools = tools
        self.planning_strategy = planning_strategy

        # Agent状态
        self.agent_id = str(uuid.uuid4())
        self.created_at = datetime.now()
        self.execution_count = 0
        self.last_activity = None
        
        # 循环终止状态
        self.think_call_count = 0
        
        # 获取循环终止配置
        from llm_agent.config import get_settings
        try:
            settings = get_settings()
            self.max_think_calls = settings.max_think_calls
        except:
            self.max_think_calls = 50  # 默认值

    async def think(self, input: str) -> AgentResponse:
        """核心思考能力

        这是LLM Agent的核心方法，所有智能行为都从这里开始。

        Args:
            input: 输入信息

        Returns:
            AgentResponse: Agent的思考结果
        """
        # 0. 检查思考次数限制
        self.think_call_count += 1
        if self.think_call_count > self.max_think_calls:
            raise Exception(
                f"已达到最大思考次数限制 ({self.max_think_calls})，"
                f"可能陷入无限循环。当前任务: {input[:100]}"
            )
        
        # 1. 检索相关记忆
        context = await self._retrieve_context(input)

        # 2. 构建完整提示
        full_prompt = self._build_prompt(input, context)

        # 3. LLM推理
        try:
            response = await self.llm.chat(
                prompt=full_prompt,
                system_prompt=self.system_prompt
            )

            # 4. 存储新记忆
            await self._store_memory(input, response)

            # 5. 更新状态
            self.execution_count += 1
            self.last_activity = datetime.now()

            return AgentResponse(
                content=response.content,
                reasoning=response.reasoning,
                confidence=response.confidence,
                metadata={
                    "agent_id": self.agent_id,
                    "agent_role": self.agent_role,
                    "timestamp": datetime.now().isoformat()
                }
            )

        except Exception as e:
            # 错误时的响应
            return AgentResponse(
                content=f"思考过程出错: {str(e)}",
                confidence=0.0,
                metadata={"error": str(e)}
            )

    async def plan(self, goal: str) -> ExecutionPlan:
        """任务规划能力

        使用LLM自主制定执行计划

        Args:
            goal: 目标描述

        Returns:
            ExecutionPlan: 执行计划
        """
        planning_prompt = f"""
作为{self.agent_role}，请为以下目标制定详细的执行计划：

目标: {goal}

请制定计划，包括：
1. 任务分解 - 将大任务分解为小步骤
2. 执行顺序 - 确定步骤的执行顺序
3. 工具选择 - 确定每步需要的工具
4. 验证标准 - 确定如何验证每步的成功

请严格按照以下JSON格式输出计划（不要添加任何其他文字）：
{{
    "steps": [
        {{"description": "步骤1描述", "type": "thinking|tool_use", "tool": "工具名（可选）", "estimated_time": 60}},
        {{"description": "步骤2描述", "type": "thinking|tool_use", "tool": "工具名（可选）", "estimated_time": 90}}
    ],
    "total_estimated_time": 150,
    "required_tools": ["tool1", "tool2"]
}}
"""

        response = await self.think(planning_prompt)

        # 解析LLM返回的计划
        try:
            plan_data = self._parse_json_plan(response.content)
            steps = self._parse_plan_steps_from_dict(plan_data)
            tools = plan_data.get("required_tools", [])
            total_time = plan_data.get("total_estimated_time", len(steps) * 60)
        except Exception as e:
            # JSON 解析失败，回退到文本解析
            print(f"JSON 解析失败，尝试文本解析: {e}")
            steps = self._parse_plan_steps_text_fallback(response.content)
            tools = self._extract_required_tools(response.content)
            total_time = len(steps) * 60

        plan = ExecutionPlan(
            goal=goal,
            steps=steps,
            required_tools=tools,
            estimated_time=total_time
        )

        return plan

    async def execute(self, task: str, max_retries: Optional[int] = None, timeout: Optional[int] = None) -> ExecutionResult:
        """任务执行能力

        自主执行任务的完整流程：
        1. 规划执行步骤
        2. 执行每个步骤
        3. 动态调整计划
        4. 反思总结

        Args:
            task: 任务描述

        Returns:
            ExecutionResult: 执行结果
        """
        try:
            # 获取配置
            from llm_agent.config import get_settings
            import asyncio
            
            # 设置超时
            settings = get_settings()
            if timeout is None:
                timeout = settings.max_execution_time
            
            # 定义执行逻辑（内部函数）
            async def _execute_with_retry():
                # 获取重试配置
                nonlocal max_retries
                if max_retries is None:
                    max_retries = settings.max_execution_retries
            settings = get_settings()
            if max_retries is None:
                max_retries = settings.max_execution_retries
            
            # 1. 规划执行步骤
            plan = await self.plan(task)

            # 2. 执行每个步骤（带重试机制）
            results = []
            retry_count = 0
            
            while plan.remaining_steps():
                step = plan.steps[plan.current_step_index]
                print(f"执行步骤 {plan.current_step_index + 1}/{len(plan.steps)}: {step.get('description', '')}")
                print(f"进度: {plan.get_progress()*100:.1f}%")

                # 执行步骤
                step_result = await self._execute_step(step)
                results.append(step_result)
                
                # 标记步骤完成
                plan.mark_step_completed(step_result)

                # 根据结果调整后续步骤
                if not step_result.get("success", True):
                    # 检查重试次数
                    retry_count += 1
                    print(f"步骤失败，重试次数: {retry_count}/{max_retries}")
                    
                    if retry_count >= max_retries:
                        error_msg = f"达到最大重试次数 ({max_retries})，终止执行"
                        print(f"❌ {error_msg}")
                        
                        # 生成最终反思
                        reflection = await self._reflect_on_execution(task, results)
                        
                        return ExecutionResult(
                            success=False,
                            steps=results,
                            reflection=reflection,
                            error=error_msg
                        )
                    
                    # 步骤失败，重新规划
                    print(f"尝试重新规划...")
                    adjustment = await self.think(
                        f"步骤 '{step.get('description', '')}' 失败（第{retry_count}次），"
                        f"请调整剩余计划: {plan.remaining_steps()}"
                    )
                    plan.update(adjustment.content)
                    break  # 跳出当前循环，重新开始执行新计划

            # 3. 反思总结
            reflection = await self._reflect_on_execution(task, results)

            return ExecutionResult(
                success=all(r.get("success", True) for r in results),
                steps=results,
                reflection=reflection
            )

        except Exception as e:
            return ExecutionResult(
                success=False,
                error=str(e)
            )

    async def reflect(self, task: str, results: List) -> Reflection:
        """反思能力

        对执行过程进行反思，总结经验教训

        Args:
            task: 执行的任务
            results: 执行结果列表

        Returns:
            Reflection: 反思结果
        """
        reflection_prompt = f"""
作为{self.agent_role}，请对以下任务执行过程进行反思：

任务: {task}
执行结果: {results}

请反思并提供结构化的反馈，严格按照以下JSON格式输出（不要添加任何其他文字）：
{{
    "insights": "做得好的方面",
    "improvements": "可以改进的方面",
    "lessons_learned": "学到的经验教训"
}}
"""

        response = await self.think(reflection_prompt)

        # 尝试解析JSON格式的反思
        try:
            reflection_data = self._parse_json_plan(response.content)
            insights = reflection_data.get("insights", response.content[:200])
            improvements = reflection_data.get("improvements", "待改进")
            lessons_learned = reflection_data.get("lessons_learned", "已记录")
        except Exception as e:
            # JSON 解析失败，使用整个响应作为 insights
            insights = response.content
            improvements = "需要进一步分析"
            lessons_learned = "已记录到记忆"

        return Reflection(
            insights=insights,
            improvements=improvements,
            lessons_learned=lessons_learned
        )

    # === 私有辅助方法 ===

    async def _retrieve_context(self, input: str) -> MemoryContext:
        """检索相关上下文"""
        if self.memory:
            return await self.memory.retrieve(input)
        return MemoryContext()

    def _build_prompt(self, input: str, context: Dict) -> str:
        """构建完整提示"""
        parts = [f"任务: {input}"]

        # 处理短期记忆
        short_term = context.get("short_term", [])
        if short_term:
            parts.append(f"最近上下文: {short_term}")

        # 处理长期记忆
        long_term = context.get("long_term", [])
        if long_term:
            parts.append(f"相关经验: {long_term}")

        # 处理工作记忆
        working = context.get("working", {})
        if working:
            parts.append(f"工作记忆: {working}")

        return "\n\n".join(parts)

    async def _store_memory(self, input: str, response: Dict):
        """存储新记忆"""
        if self.memory:
            await self.memory.store({
                "input": input,
                "response": response,
                "timestamp": datetime.now().isoformat()
            })

    async def _execute_step(self, step: Dict) -> Dict:
        """执行单个步骤"""
        step_type = step.get("type", "thinking")

        if step_type == "thinking":
            # 思考型步骤，使用LLM
            response = await self.think(step.get("description", ""))
            return {
                "success": True,
                "result": response.content,
                "step": step,
                "type": "thinking"
            }
        elif step_type == "tool_use" and self.tools:
            # 工具使用步骤
            tool_name = step.get("tool")
            params = step.get("parameters", {})
            
            try:
                # 从工具注册表获取工具
                tool_func = self.tools.get_tool(tool_name)
                if tool_func:
                    # 执行工具函数（假设是异步函数）
                    if hasattr(tool_func, '__call__'):
                        result = tool_func(**params) if params else tool_func()
                        if hasattr(result, '__aiter__'):
                            result = await result
                    return {
                        "success": True,
                        "result": str(result),
                        "step": step,
                        "type": "tool_use",
                        "tool": tool_name
                    }
                else:
                    # 工具不存在，返回错误
                    return {
                        "success": False,
                        "error": f"工具 {tool_name} 未注册",
                        "step": step,
                        "type": "tool_use"
                    }
            except Exception as e:
                return {
                    "success": False,
                    "error": str(e),
                    "step": step,
                    "type": "tool_use"
                }
        else:
            # 默认处理
            return {
                "success": True,
                "result": "步骤完成（默认处理）",
                "step": step,
                "type": "unknown"
            }

    async def _reflect_on_execution(self, task: str, results: List) -> str:
        """对执行过程进行反思"""
        if not results:
            return "没有执行结果可反思"

        reflection_prompt = f"任务: {task}\n结果: {results}\n请总结经验教训"
        response = await self.think(reflection_prompt)
        return response.content


    def _parse_json_plan(self, plan_text: str) -> dict:
        """解析JSON格式的计划"""
        import json
        # 尝试提取JSON（处理可能的前后文字）
        json_start = plan_text.find('{')
        json_end = plan_text.rfind('}') + 1
        
        if json_start >= 0 and json_end > json_start:
            json_str = plan_text[json_start:json_end]
            return json.loads(json_str)
        else:
            raise ValueError("无法找到JSON格式的计划")
    
    def _parse_plan_steps_from_dict(self, plan_data: dict) -> List[Dict]:
        """从字典数据解析步骤"""
        steps_data = plan_data.get("steps", [])
        steps = []
        
        for step_data in steps_data:
            step = {
                "description": step_data.get("description", "未命名步骤"),
                "type": step_data.get("type", "thinking"),
                "tool": step_data.get("tool", ""),
                "estimated_time": step_data.get("estimated_time", 60)
            }
            steps.append(step)
        
        return steps
    
    def _parse_plan_steps_text_fallback(self, plan_text: str) -> List[Dict]:
        """文本格式回退解析（当JSON解析失败时使用）"""
        import re
        steps = []
        
        # 尝试识别列表项（1. 2. 3. 或 -）
        patterns = [
            r'(?:^|\n)\s*(\d+\.[-·])\s*\n?\s*([^\n]+)',  # 数字列表
            r'(?:^|\n)\s*([-*])\s*([^\n]+)',  # 符号列表
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, plan_text, re.MULTILINE)
            if matches:
                for match in matches:
                    if isinstance(match, tuple):
                        desc = match[-1]  # 取最后一个捕获组
                    else:
                        desc = match
                    steps.append({
                        "description": desc.strip(),
                        "type": "thinking",
                        "tool": "",
                        "estimated_time": 60
                    })
                break
        
        # 如果还是没找到，默认返回一个步骤
        if not steps:
            return [{
                "description": "执行任务",
                "type": "thinking",
                "tool": "",
                "estimated_time": 60
            }]
        
        return steps

    def _parse_plan_steps(self, plan_text: str) -> List[Dict]:
        """解析计划步骤"""
        # 简化实现，实际需要更复杂的解析逻辑
        return [
            {"description": f"步骤{i+1}", "type": "thinking"}
            for i in range(3)  # 假设总是3个步骤
        ]

    def _extract_required_tools(self, plan_text: str) -> List[str]:
        """从计划文本中提取所需工具"""
        import re
        
        # 如果已经从JSON解析过，优先使用
        if hasattr(self, '_last_plan_data'):
            return self._last_plan_data.get("required_tools", [])
        
        tools = set()
        
        # 常见工具关键词 - 每个键映射到一个工具名称
        tool_keywords = {
            'http': 'http_request',
            'curl': 'http_request',
            'fetch': 'http_request',
            'request': 'http_request',
            'code': 'code_generation',
            'write': 'code_generation',
            'edit': 'code_generation',
            'refactor': 'code_generation',
            'file': 'file_operation',
            'read': 'file_operation',
            'delete': 'file_operation',
            'database': 'db_query',
            'sql': 'db_query',
            'analysis': 'data_analysis',
            'analyze': 'data_analysis',
            'calculate': 'data_analysis',
            'search': 'search',
            'find': 'search',
            'grep': 'search'
        }
        
        # 从文本中提取可能涉及的工具
        text_lower = plan_text.lower()
        for keyword, tool_name in tool_keywords.items():
            if keyword in text_lower:
                tools.add(tool_name)
        
        # 显式工具名称（可能有 "使用xxx工具" 的表述）
        tool_mentions = re.findall(r'(?:使用|调用|apply|using)\s*([a-zA-Z_]\w*)\s*(?:工具|tool)', plan_text, re.IGNORECASE)
        for mention in tool_mentions:
            tools.add(mention[1])
        
        return list(tools)

    def get_info(self) -> Dict[str, Any]:
        """获取Agent信息"""
        return {
            "agent_id": self.agent_id,
            "agent_role": self.agent_role,
            "created_at": self.created_at.isoformat(),
            "execution_count": self.execution_count,
            "last_activity": self.last_activity.isoformat() if self.last_activity else None,
            "has_tools": self.tools is not None,
            "has_memory": self.memory is not None
        }

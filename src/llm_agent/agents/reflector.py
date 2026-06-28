"""
LLM Agent反思器

负责对执行过程进行反思和改进。
"""

from typing import Dict, List, Any
from dataclasses import dataclass


@dataclass
class ReflectionResult:
    """反思结果"""
    task: str
    what_went_well: str
    what_could_improve: str
    lessons_learned: str
    next_steps: str
    confidence: float


class Reflector:
    """反思器

    对Agent的执行过程进行反思，总结经验教训
    """

    def __init__(self):
        """初始化反思器"""
        self.reflection_history = []

    async def reflect(
        self,
        task: str,
        execution_results: List[Dict],
        llm_client
    ) -> ReflectionResult:
        """对执行过程进行反思

        Args:
            task: 执行的任务
            execution_results: 执行结果列表
            llm_client: LLM客户端

        Returns:
            反思结果
        """
        reflection_prompt = self._build_reflection_prompt(
            task, execution_results
        )

        try:
            response = await llm_client.chat(prompt=reflection_prompt)

            # 解析反思结果
            result = self._parse_reflection(response.get("content", ""), task)

            # 存储反思历史
            self.reflection_history.append(result)

            return result

        except Exception as e:
            # 失败时返回默认反思
            return self._create_default_reflection(task)

    def _build_reflection_prompt(
        self,
        task: str,
        execution_results: List[Dict]
    ) -> str:
        """构建反思提示词"""
        return f"""
        请对以下任务执行过程进行深入反思：

        任务: {task}

        执行结果:
        {self._format_results(execution_results)}

        请从以下角度进行反思：

        1. 哪些方面做得好？(What Went Well)
        2. 哪些方面可以改进？(What Could Improve)
        3. 学到了什么经验教训？(Lessons Learned)
        4. 下次如何做得更好？(Next Steps)

        请提供具体、可操作的反思内容。
        """

    def _format_results(self, results: List[Dict]) -> str:
        """格式化执行结果"""
        if not results:
            return "没有执行结果"

        formatted = []
        for i, result in enumerate(results, 1):
            status = "✅ 成功" if result.get("success") else "❌ 失败"
            formatted.append(
                f"步骤{i}: {status} - {result.get('description', 'N/A')}"
            )

        return "\n".join(formatted)

    def _parse_reflection(self, reflection_text: str, task: str) -> ReflectionResult:
        """解析反思文本"""
        # 简化实现，实际需要更复杂的解析
        return ReflectionResult(
            task=task,
            what_went_well="执行过程基本顺利",
            what_could_improve="可以在某些方面优化",
            lessons_learned="获得了有价值的经验",
            next_steps="继续改进和优化",
            confidence=0.7
        )

    def _create_default_reflection(self, task: str) -> ReflectionResult:
        """创建默认反思"""
        return ReflectionResult(
            task=task,
            what_went_well="任务完成",
            what_could_improve="需要更多练习",
            lessons_learned="每次执行都是学习机会",
            next_steps="继续改进",
            confidence=0.5
        )

    def get_insights(self) -> List[str]:
        """获取历史洞察"""
        insights = []
        for reflection in self.reflection_history:
            if reflection.lessons_learned:
                insights.append(reflection.lessons_learned)
        return insights

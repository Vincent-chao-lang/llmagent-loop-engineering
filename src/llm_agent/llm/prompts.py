"""
LLM Agent提示词管理

提供专业的提示词模板和管理功能。
"""

from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json
import uuid


@dataclass
class PromptTemplate:
    """提示词模板"""
    id: str
    name: str
    description: str
    template: str
    variables: List[str] = field(default_factory=list)
    category: str = "general"
    version: str = "1.0"
    created_at: str = ""
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()

    def format(self, **kwargs) -> str:
        """格式化提示词

        Args:
            **kwargs: 变量值

        Returns:
            格式化后的提示词
        """
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            missing_var = str(e).strip("'")
            raise ValueError(f"缺少必需的变量: {missing_var}")

    def validate(self) -> bool:
        """验证模板"""
        try:
            # 检查必需变量
            import re
            vars_found = re.findall(r'\{(\w+)\}', self.template)
            return all(var in self.variables for var in vars_found)
        except Exception:
            return False


class PromptManager:
    """提示词管理器

    管理LLM Agent的提示词模板
    """

    def __init__(self):
        """初始化提示词管理器"""
        self.templates: Dict[str, PromptTemplate] = {}
        self._load_builtin_templates()

    def register_template(self, template: PromptTemplate):
        """注册提示词模板

        Args:
            template: 提示词模板
        """
        if not template.validate():
            raise ValueError(f"模板验证失败: {template.name}")

        self.templates[template.id] = template

    def get_template(self, template_id: str) -> Optional[PromptTemplate]:
        """获取提示词模板

        Args:
            template_id: 模板ID

        Returns:
            提示词模板或None
        """
        return self.templates.get(template_id)

    def list_templates(
        self,
        category: str = None,
        tag: str = None
    ) -> List[PromptTemplate]:
        """列出提示词模板

        Args:
            category: 分类筛选
            tag: 标签筛选

        Returns:
            提示词模板列表
        """
        templates = list(self.templates.values())

        if category:
            templates = [t for t in templates if t.category == category]

        if tag:
            templates = [t for t in templates if tag in t.tags]

        return templates

    def format_prompt(
        self,
        template_id: str,
        **kwargs
    ) -> str:
        """格式化提示词

        Args:
            template_id: 模板ID
            **kwargs: 变量值

        Returns:
            格式化后的提示词
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"模板不存在: {template_id}")

        return template.format(**kwargs)

    def create_system_prompt(
        self,
        agent_role: str,
        capabilities: List[str] = None,
        constraints: List[str] = None
    ) -> str:
        """创建系统提示词

        Args:
            agent_role: Agent角色
            capabilities: 能力列表
            constraints: 约束条件

        Returns:
            系统提示词
        """
        prompt_parts = [
            f"你是一个{agent_role}。",
        ]

        if capabilities:
            prompt_parts.append(
                f"\n你的能力包括：\n" +
                "\n".join([f"- {cap}" for cap in capabilities])
            )

        if constraints:
            prompt_parts.append(
                f"\n请遵守以下约束：\n" +
                "\n".join([f"- {constraint}" for constraint in constraints])
            )

        return "\n".join(prompt_parts)

    def _load_builtin_templates(self):
        """加载内置模板"""

        # 推理模板
        self.register_template(PromptTemplate(
            id="reasoning_basic",
            name="基础推理模板",
            description="用于基础推理任务",
            category="reasoning",
            template="""请对以下问题进行推理分析：

问题: {problem}
上下文: {context}

请提供：
1. 问题理解
2. 推理过程
3. 结论
4. 置信度""",
            variables=["problem", "context"],
            tags=["reasoning", "basic"]
        ))

        # 规划模板
        self.register_template(PromptTemplate(
            id="planning_basic",
            name="基础规划模板",
            description="用于任务规划",
            category="planning",
            template="""请为以下目标制定执行计划：

目标: {goal}
约束: {constraints}
资源: {resources}

请制定：
1. 任务分解
2. 执行步骤
3. 时间估算
4. 验证标准""",
            variables=["goal", "constraints", "resources"],
            tags=["planning", "basic"]
        ))

        # 反思模板
        self.register_template(PromptTemplate(
            id="reflection_basic",
            name="基础反思模板",
            description="用于经验反思",
            category="reflection",
            template="""请对以下经验进行反思：

经验: {experience}
结果: {results}

请反思：
1. 哪些做得好？
2. 哪些可以改进？
3. 学到了什么？
4. 下次如何做得更好？""",
            variables=["experience", "results"],
            tags=["reflection", "basic"]
        ))

        # 工具使用模板
        self.register_template(PromptTemplate(
            id="tool_use_basic",
            name="基础工具使用模板",
            description="用于工具使用决策",
            category="tool_use",
            template="""任务: {task}

可用工具:
{tools}

请决定：
1. 是否需要使用工具
2. 使用哪个工具
3. 如何调用工具""",
            variables=["task", "tools"],
            tags=["tool", "basic"]
        ))

        # 代码分析模板
        self.register_template(PromptTemplate(
            id="code_analysis",
            name="代码分析模板",
            description="专门用于代码分析",
            category="code",
            template="""请分析以下代码：

代码:
```{language}
{code}
```

任务: {task}

请提供：
1. 代码结构分析
2. 潜在问题识别
3. 改进建议
4. 最佳实践建议""",
            variables=["language", "code", "task"],
            tags=["code", "analysis"]
        ))

        # 数据分析模板
        self.register_template(PromptTemplate(
            id="data_analysis",
            name="数据分析模板",
            description="专门用于数据分析",
            category="data",
            template="""请分析以下数据：

数据:
{data}

分析目标: {goal}

请提供：
1. 数据概述
2. 关键发现
3. 趋势分析
4. 建议和洞察""",
            variables=["data", "goal"],
            tags=["data", "analysis"]
        ))

    def export_templates(self, file_path: str):
        """导出模板到文件

        Args:
            file_path: 文件路径
        """
        templates_data = [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "template": t.template,
                "variables": t.variables,
                "category": t.category,
                "version": t.version,
                "tags": t.tags
            }
            for t in self.templates.values()
        ]

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(templates_data, f, ensure_ascii=False, indent=2)

    def import_templates(self, file_path: str):
        """从文件导入模板

        Args:
            file_path: 文件路径
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            templates_data = json.load(f)

        for data in templates_data:
            template = PromptTemplate(**data)
            self.register_template(template)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        categories = {}
        for template in self.templates.values():
            if template.category not in categories:
                categories[template.category] = 0
            categories[template.category] += 1

        return {
            "total_templates": len(self.templates),
            "categories": categories
        }


# 全局提示词管理器实例
_global_manager = None


def get_prompt_manager() -> PromptManager:
    """获取全局提示词管理器

    Returns:
        PromptManager: 全局管理器实例
    """
    global _global_manager
    if _global_manager is None:
        _global_manager = PromptManager()
    return _global_manager


__all__ = [
    "PromptTemplate",
    "PromptManager",
    "get_prompt_manager"
]

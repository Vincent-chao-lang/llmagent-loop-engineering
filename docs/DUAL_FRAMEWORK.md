# AI Agent System - 双框架架构

## 🎯 项目定位

本项目提供**两个Agent框架**，分别适应不同的应用场景：

### 1. 通用Agent框架 (`src/`)
**定位**: 自动化基础设施
- **核心**: MessageBus + 规则逻辑
- **适用**: 传统自动化、工作流、固定流程
- **特点**: 无API费用、快速响应、确定性输出

### 2. LLM Agent框架 (`llm_agent/`)
**定位**: AI驱动的智能系统
- **核心**: LLM + 记忆 + 规划
- **适用**: AI应用、智能决策、复杂推理
- **特点**: 理解能力强、适应性强、持续学习

## 🚀 快速开始

### 通用Agent框架
```bash
# 运行通用框架Demo
python demo/demo_framework_pubsub.py
python demo/demo_framework_pipeline.py
```

### LLM Agent框架
```bash
# 运行LLM框架Demo
python demo/demo_llm_agent_framework.py
```

## 📊 如何选择

| 需求 | 推荐框架 |
|------|----------|
| 流程自动化 | 通用框架 |
| 数据处理 | 通用框架 |
| 智能客服 | LLM框架 |
| 代码助手 | LLM框架 |

详细选择指南: [docs/FRAMEWORK_CHOICE.md](docs/FRAMEWORK_CHOICE.md)

## 📚 文档导航

- **LLM Agent分析**: [LLM_AGENT_ANALYSIS.md](LLM_AGENT_ANALYSIS.md)
- **LLM框架设计**: [LLM_AGENT_FRAMEWORK.md](LLM_AGENT_FRAMEWORK.md)
- **方案C总结**: [SOLUTION_C_SUMMARY.md](SOLUTION_C_SUMMARY.md)
- **框架选择**: [docs/FRAMEWORK_CHOICE.md](docs/FRAMEWORK_CHOICE.md)

## 🎓 示例对比

### 通用框架示例 (规则驱动)
```python
from src.agents.base import Agent, AgentConfig

config = AgentConfig(
    agent_id="agent_1",
    name="DataProcessor",
    role=AgentRole.EXECUTOR
)

agent = Agent(config)
result = await agent.process({"task": "process_data"}, context)
```

### LLM框架示例 (AI驱动)
```python
from llm_agent import LLMAgent, Memory

agent = LLMAgent(
    llm_client=llm_client,
    system_prompt="你是专业的数据分析师",
    agent_role="分析师",
    memory=Memory(...)
)

response = await agent.think("分析这个数据")
plan = await agent.plan("制定分析策略")
result = await agent.execute("执行数据分析")
```

## 💡 核心价值

通过提供两个框架，我们实现了：
- ✅ **场景覆盖** - 从自动化到AI应用的完整覆盖
- ✅ **灵活选择** - 根据需求选择最合适的框架
- ✅ **互相补充** - 两个框架可以协同工作
- ✅ **降低成本** - 简单任务无需使用昂贵的LLM

---

*双框架架构 - 适配不同场景的Agent解决方案*

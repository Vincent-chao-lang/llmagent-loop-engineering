# LLM Agent 框架快速开始指南

> **5分钟上手 llmagent 框架** - 专业的LLM Agent框架，具备思考、规划、执行、反思四大核心能力

## 🚀 快速安装

### 方式1: PyPI 安装（推荐）
```bash
pip install llmagent
```

### 方式2: 本地开发安装
```bash
cd /path/to/autoAgent/llm_agent
pip install -e .
```

## 📝 基础使用

### 1. 创建你的第一个 Agent

```python
import asyncio
from llm_agent import LLMAgent, Memory, MemoryConfig
from llm_agent.llm.client import LLMClient

async def main():
    # 创建 LLM 客户端
    llm_client = LLMClient(provider="anthropic")  # 或 "openai", "mock"
    
    # 创建记忆系统
    memory = Memory(MemoryConfig())
    
    # 创建 Agent
    agent = LLMAgent(
        llm_client=llm_client,
        system_prompt="你是一个AI助手，擅长回答问题",
        agent_role="助手",
        memory=memory
    )
    
    # 使用 Agent 思考
    response = await agent.think("什么是递归？")
    print(f"回答: {response.content}")

asyncio.run(main())
```

### 2. 使用四大核心能力

#### 🧠 think（思考）- 核心推理能力
```python
response = await agent.think("分析这个问题")
print(f"思考结果: {response.content}")
print(f"推理过程: {response.reasoning}")
print(f"置信度: {response.confidence}")
```

#### 📋 plan（规划）- 任务分解能力
```python
plan = await agent.plan("构建一个Web爬虫")
print(f"总步骤: {len(plan.steps)}")
print(f"预估时间: {plan.estimated_time}秒")

for i, step in enumerate(plan.steps, 1):
    print(f"{i}. {step['description']}")
```

#### ⚙️ execute（执行）- 自主执行能力
```python
result = await agent.execute(
    "分析用户数据",
    max_retries=3,    # 失败重试次数
    timeout=300       # 超时时间（秒）
)

print(f"执行状态: {'成功' if result.success else '失败'}")
print(f"执行步骤: {len(result.steps)}")
print(f"反思总结: {result.reflection}")
```

#### 🤔 reflect（反思）- 经验学习能力
```python
reflection = await agent.reflect("代码审查", result)
print(f"优点: {reflection.insights}")
print(f"改进: {reflection.improvements}")
print(f"经验: {reflection.lessons_learned}")
```

## 🔧 配置说明

### 环境变量配置
```bash
# LLM 配置
export LLM_AGENT_LLM_PROVIDER="anthropic"
export LLM_AGENT_LLM_API_KEY="your-api-key"

# 循环终止配置（生产环境推荐）
export LLM_AGENT_MAX_EXECUTION_RETRIES=5
export LLM_AGENT_MAX_EXECUTION_TIME=600
export LLM_AGENT_MAX_THINK_CALLS=100
export LLM_AGENT_ALLOW_PLAN_REGRESSION=false
```

### 代码配置
```python
from llm_agent.config import get_settings

settings = get_settings()

# 自定义配置
settings.max_execution_retries = 5
settings.max_execution_time = 600
settings.max_think_calls = 100
```

## 📚 完整示例

### 示例1: 智能代码审查 Agent

```python
import asyncio
from llm_agent import LLMAgent, Memory, MemoryConfig
from llm_agent.llm.client import LLMClient

async def code_review_agent():
    # 创建代码审查 Agent
    llm_client = LLMClient(provider="anthropic")
    memory = Memory(MemoryConfig())
    
    agent = LLMAgent(
        llm_client=llm_client,
        system_prompt="你是一个资深代码审查专家",
        agent_role="代码审查员",
        memory=memory
    )
    
    # 1. 分析代码质量
    analysis = await agent.think("分析以下代码的潜在问题")
    
    # 2. 制定审查计划
    plan = await agent.plan("执行完整的代码审查流程")
    
    # 3. 执行审查（包含安全检查、性能分析等）
    result = await agent.execute("执行代码审查", max_retries=3)
    
    # 4. 反思总结（经验教训）
    print(f"审查完成: {result.success}")
    print(f"发现的问题: {len(result.steps)}个")
    print(f"改进建议: {result.reflection}")

asyncio.run(code_review_agent())
```

### 示例2: 数据分析 Agent

```python
async def data_analysis_agent():
    # 创建数据分析 Agent
    agent = LLMAgent(
        llm_client=LLMClient(provider="openai"),
        system_prompt="你是一个数据科学家",
        agent_role="数据分析师",
        memory=Memory(MemoryConfig(
            short_term_capacity=100,    # 保留最近100条
            long_term_capacity=1000,    # 保留最相关1000条
            working_capacity=10         # 临时工作记忆
        ))
    )
    
    # 完整的数据分析流程
    result = await agent.execute(
        "分析用户行为数据并生成报告",
        max_retries=3,
        timeout=600  # 10分钟超时
    )
    
    print(f"分析成功: {result.success}")
    print(f"分析步骤: {len(result.steps)}")
    print(f"数据洞察: {result.reflection}")

asyncio.run(data_analysis_agent())
```

## 🎯 不同场景的配置

### 开发环境（快速失败）
```bash
export LLM_AGENT_MAX_EXECUTION_RETRIES=1
export LLM_AGENT_MAX_EXECUTION_TIME=60
export LLM_AGENT_MAX_THINK_CALLS=20
```

### 生产环境（稳定可靠）
```bash
export LLM_AGENT_MAX_EXECUTION_RETRIES=5
export LLM_AGENT_MAX_EXECUTION_TIME=600
export LLM_AGENT_MAX_THINK_CALLS=100
```

### 复杂任务（更多容错）
```bash
export LLM_AGENT_MAX_EXECUTION_RETRIES=10
export LLM_AGENT_MAX_EXECUTION_TIME=1800
export LLM_AGENT_MAX_THINK_CALLS=200
```

## 🐛 调试技巧

### 查看执行进度
```python
plan = await agent.plan("复杂任务")
print(f"当前进度: {plan.get_progress()*100:.1f}%")
```

### 监控思考次数
```python
print(f"当前思考次数: {agent.think_call_count}")
print(f"最大思考次数: {agent.max_think_calls}")

if agent.think_call_count > agent.max_think_calls * 0.9:
    print("⚠️ 思考次数接近上限")
```

### 获取 Agent 信息
```python
info = agent.get_info()
print(f"Agent ID: {info['agent_id']}")
print(f"角色: {info['agent_role']}")
print(f"执行次数: {info['execution_count']}")
```

## 📖 更多资源

- **[完整文档](README.md)** - 详细的框架说明
- **[能力详解](CAPABILITIES.md)** - 四大核心能力深度解析
- **[循环终止](LOOP_TERMINATION.md)** - 运行时安全保障
- **[改进总结](IMPROVEMENTS_SUMMARY.md)** - 最新改进内容

## 🎉 开始使用

现在你已经准备好了！选择一个场景开始：

1. **快速体验**: 复制上面的基础使用代码
2. **完整示例**: 运行代码审查或数据分析示例
3. **深入学习**: 阅读四大能力文档
4. **生产部署**: 配置环境变量和参数

**框架已就绪，开始构建你的 AI Agent 吧！** 🚀
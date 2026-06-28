# 🤖 LLM Agent 框架

> **以LLM为核心的智能Agent框架** - 具备思考、规划、执行、反思四大能力

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.0-orange.svg)](https://github.com/Vincent-chao-lang/AutoAgent)

## 🎯 框架定位

**LLM Agent是一个专门的LLM驱动智能Agent框架**，具备以下特点：

- **LLM即核心**：所有智能行为由LLM驱动（不是外挂插件）
- **四大核心能力**：think（思考）、plan（规划）、execute（执行）、reflect（反思）
- **三层记忆系统**：短期、长期、工作记忆，支持持续学习
- **智能协作**：支持多Agent团队协作、协商、投票
- **多提供商支持**：Anthropic Claude、OpenAI GPT、Mock测试

适用于构建AI驱动的智能应用，如代码审查、数据分析、智能运维等。

## 🚀 三种使用方式

### 1️⃣ Python库导入

```bash
pip install -e .
```

```python
from llm_agent import LLMAgent, Memory, MemoryConfig
from llm_agent.llm import LLMClient

# 创建LLM客户端
llm_client = LLMClient(provider="anthropic", model_name="claude-opus-4-6")

# 创建记忆系统
memory = Memory(MemoryConfig(
    short_term_capacity=100,
    long_term_capacity=1000
))

# 创建Agent
agent = LLMAgent(
    llm_client=llm_client,
    system_prompt="你是一个专业的代码审查专家",
    agent_role="代码审查员",
    memory=memory
)

# 使用Agent四大能力
response = await agent.think("审查以下代码的安全性")
plan = await agent.plan("制定代码审查计划")
result = await agent.execute("执行代码审查任务")
reflection = await agent.reflect("审查结果", [result])
```

### 2️⃣ 命令行工具（CLI）

```bash
# 安装后直接使用
llm-agent think "什么是递归？"
llm-agent plan "构建一个Web爬虫"
llm-agent execute "分析用户行为数据"

# 启动API服务
llm-agent server --host 0.0.0.0 --port 8000
```

### 3️⃣ HTTP REST API

```bash
# 启动服务
llm-agent server

# 创建Agent会话
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{"system_prompt":"你是助手","agent_role":"助手"}'

# 使用session_id进行思考
curl -X POST http://localhost:8000/api/v1/agent/think \
  -H "Content-Type: application/json" \
  -d '{"input":"分析问题","session_id":"<session_id>"}'

# 规划
curl -X POST http://localhost:8000/api/v1/agent/plan \
  -H "Content-Type: application/json" \
  -d '{"goal":"制定计划"}'

# 执行
curl -X POST http://localhost:8000/api/v1/agent/execute \
  -H "Content-Type: application/json" \
  -d '{"task":"执行任务"}'
```

## 🏗️ 核心架构

```
llm_agent/
├── agents/              # Agent核心
│   ├── base.py          # LLMAgent（think/plan/execute/reflect）
│   ├── planner.py       # 规划器
│   └── reflector.py     # 反思器
├── llm/                 # LLM层
│   ├── client.py        # LLMClient（chat/reason/plan/reflect/use_tool）
│   ├── prompts.py       # 提示词管理（6个内置模板）
│   └── adapters.py     # 多提供商适配器
├── memory/              # 记忆系统
│   └── memory.py        # 三层记忆（短期/长期/工作）
├── collaboration/       # 协作层
│   ├── protocol.py      # 通信协议
│   ├── team.py          # 团队管理
│   └── negotiation.py   # 协商机制
├── tools/               # 工具系统
│   └── registry.py      # 工具注册表
├── api/                 # HTTP API层
│   ├── app.py           # FastAPI应用
│   ├── session.py       # 会话管理器
│   ├── routers/         # API路由
│   └── middleware.py    # 中间件
├── cli/                 # 命令行工具
│   └── main.py          # click CLI
└── schemas/             # Pydantic Schema
    ├── common.py        # 通用响应格式
    ├── agent.py         # Agent相关Schema
    └── team.py          # 团队相关Schema
```

## 📖 核心能力

### 1. 四大核心能力

```python
# 思考 - 理解和分析问题
response = await agent.think("如何优化Python代码性能？")
print(response.content)        # 思考结果
print(response.reasoning)      # 推理过程
print(response.confidence)     # 置信度

# 规划 - 制定执行计划
plan = await agent.plan("构建Web爬虫")
print(plan.steps)              # 执行步骤列表
print(plan.estimated_time)     # 预估时间

# 执行 - 自主执行任务
result = await agent.execute("数据分析任务")
print(result.success)          # 是否成功
print(result.steps)            # 执行步骤
print(result.reflection)       # 反思总结

# 反思 - 总结经验教训
reflection = await agent.reflect("任务执行情况", [result])
print(reflection.insights)      # 关键洞察
print(reflection.improvements)  # 改进建议
print(reflection.lessons_learned) # 学到的经验
```

### 2. 三层记忆系统

```python
from llm_agent.memory import Memory, MemoryConfig

memory = Memory(MemoryConfig(
    short_term_capacity=100,    # 短期记忆（FIFO）
    long_term_capacity=1000,     # 长期记忆（重要性排序）
    working_memory_capacity=10   # 工作记忆（手动管理）
))

# 存储记忆（自动评估重要性）
await memory.store({
    "type": "code_review",
    "content": "发现3个安全问题",
    "importance": 0.8  # 可选，不传则自动评估
})

# 检索记忆
context = await memory.retrieve("安全问题")
print(context["long_term"])    # 长期记忆
print(context["short_term"])   # 短期记忆
print(context["working"])      # 工作记忆
```

### 3. 多Agent协作

```python
from llm_agent.collaboration import LLMAgentTeam, TeamConfig, TeamRole
from llm_agent import LLMAgent, Memory, MemoryConfig
from llm_agent.llm import LLMClient

# 创建团队
team_config = TeamConfig(
    team_name="代码审查团队",
    goal="审查代码质量和安全"
)
team = LLMAgentTeam(team_config)

# 创建多个Agent
llm_client = LLMClient(provider="mock")
memory = Memory(MemoryConfig())

agents = {}
for role_name, team_role in [("架构师", TeamRole.LEADER), ("安全专家", TeamRole.SPECIALIST)]:
    agent = LLMAgent(llm_client, f"你是{role_name}", role_name, memory)
    agents[role_name] = agent
    team.add_member(role_name, team_role)

# 团队协作
result = await team.collaborate("审查认证模块代码", agents, style="peer_to_peer")
print(result.consensus)         # 达成的共识
print(result.individual_results) # 各Agent的结果
```

### 4. 多LLM提供商

```python
from llm_agent.llm import LLMClient

# Anthropic Claude
claude_client = LLMClient(
    provider="anthropic",
    model_name="claude-opus-4-6",
    config={"api_key": "your-api-key"}
)

# OpenAI GPT
openai_client = LLMClient(
    provider="openai",
    model_name="gpt-4",
    config={"api_key": "your-api-key"}
)

# Mock（测试/开发）
mock_client = LLMClient(provider="mock")

```
### 5. 循环终止配置

框架内置多层防护机制，防止 Agent 执行过程中陷入无限循环：

```bash
export LLM_AGENT_MAX_EXECUTION_RETRIES=3    # 执行失败最大重试次数
export LLM_AGENT_MAX_EXECUTION_TIME=300      # 单次执行最大时间（秒）
export LLM_AGENT_MAX_THINK_CALLS=50          # 最大思考次数限制
export LLM_AGENT_ALLOW_PLAN_REGRESSION=false  # 是否允许计划退化
```

**生产环境推荐**：
- 最大重试次数：5（允许一定容错）
- 最大执行时间：600秒（10分钟）
- 最大思考次数：100（复杂任务）

**开发/测试环境**（快速失败）：
- 最大重试次数：1
- 最大执行时间：60秒
- 最大思考次数：20

**代码中配置**：
```python
from llm_agent.config import Settings, get_settings

settings = Settings(
    max_execution_retries=5,
    max_execution_time=600,
    max_think_calls=100,
    allow_plan_regression=False
)
```

**执行时指定**：
```python
# 覆盖配置
result = await agent.execute(
    "处理大数据集",
    max_retries=5,      # 覆盖配置
    timeout=600         # 覆盖配置
)
```

详见 [循环终止条件完整文档](LOOP_TERMINATION.md)。

---
## 📡 API端点

| Method | Path | 说明 |
|--------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/agents` | 创建Agent会话 |
| GET | `/api/v1/agents/{id}` | 获取Agent信息 |
| DELETE | `/api/v1/agents/{id}` | 销毁Agent会话 |
| POST | `/api/v1/agent/think` | 思考能力 |
| POST | `/api/v1/agent/plan` | 规划能力 |
| POST | `/api/v1/agent/execute` | 执行能力 |
| POST | `/api/v1/agent/reflect` | 反思能力 |
| POST | `/api/v1/team/collaborate` | 团队协作 |
| POST | `/api/v1/team/vote` | 团队投票 |

**Swagger文档**：启动服务后访问 `http://localhost:8000/docs`

## 🔧 配置方式

### 环境变量

```bash
export LLM_AGENT_PROVIDER=anthropic
export LLM_AGENT_MODEL=claude-opus-4-6
export LLM_AGENT_API_KEY=your-api-key
export LLM_AGENT_API_PORT=8000
```

### 配置文件

```python
from llm_agent.config import Settings, get_settings

# 使用默认配置
settings = get_settings()

# 从YAML加载
settings = get_settings(Path("config.yaml"))

# 自定义配置
from llm_agent.config import Settings
settings = Settings(
    llm_provider="anthropic",
    llm_model="claude-opus-4-6",
    api_port=9000
)
```




## 📦 安装

```bash

# 从 PyPI 安装（推荐生产环境）
pip install llmagent

# 或从源码本地安装（开发模式）# 方式1：从 llm_agent/ 目录安装
cd /path/to/autoAgent/llm_agent
pip install -e ".[all]"

# 方式2：从项目根目录安装（使用绝对路径）
pip install -e /path/to/autoAgent/llm_agent ".[all]"

# 安装选项
pip install -e ".[all]"     # 完整功能（API + CLI + LLM提供商）
pip install -e ".[api]"     # 仅API服务
pip install -e ".[cli]"     # 仅CLI工具
pip install -e ".[anthropic]"  # 添加Claude支持
pip install -e ".[dev]"     # 开发依赖
```

## 🧪 测试

```bash
# 单元测试
pytest tests/test_api/ -v

# CLI测试
llm-agent think "测试问题"

# API测试
llm-agent server
curl http://localhost:8000/api/v1/health
```


## 🎯 适用场景

✅ **AI驱动应用**：
- 智能代码审查
- 自动数据分析
- 智能运维监控
- 客户服务自动化

✅ **跨语言集成**：
- 通过HTTP API从任何语言调用
- Python应用直接导入使用
- 命令行快速调用

## 🚀 快速开始

```bash
# 1. 安装
git clone https://github.com/Vincent-chao-lang/AutoAgent.git
cd llm-agent
pip install -e ".[all]"

# 2. 配置（可选）
export LLM_AGENT_API_KEY=your-key

# 3. 使用
llm-agent think "什么是递归？"

# 4. 启动API服务
llm-agent server

# 5. 访问文档
# http://localhost:8000/docs
```

---

**以LLM为核心，构建下一代智能应用！** 🚀

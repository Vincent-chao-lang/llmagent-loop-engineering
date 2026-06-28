# LLM Agent 框架 - 5分钟快速上手

## 🚀 三种使用方式

### 1️⃣ Python库（推荐开发者）

```bash
# 必须在 llm_agent/ 目录下执行
cd /path/to/autoAgent/llm_agent
pip install -e ".[all]"

# 或从项目根目录安装（使用绝对路径）
pip install -e /path/to/autoAgent/llm_agent ".[all]"
```

```python
import asyncio
from llm_agent import LLMAgent, Memory, MemoryConfig
from llm_agent.llm import LLMClient

async def main():
    # 创建Agent（3步）
    llm_client = LLMClient(provider="mock")  # 或 anthropic/openai
    memory = Memory(MemoryConfig())
    agent = LLMAgent(
        llm_client=llm_client,
        system_prompt="你是代码审查专家",
        agent_role="审查员",
        memory=memory
    )

    # 使用四大能力
    response = await agent.think("这个代码有什么问题？")
    print(response.content)

asyncio.run(main())
```

### 2️⃣ 命令行工具（推荐快速测试）

```bash
# 安装
pip install -e ".[cli]"

# 直接使用
llm-agent think "什么是递归？"
llm-agent plan "构建Web爬虫"
llm-agent execute "数据分析任务"

# 启动API服务
llm-agent server --port 8000
```

### 3️⃣ HTTP API（推荐跨语言集成）

```bash
# 启动服务
llm-agent server

# 创建Agent
curl -X POST http://localhost:8000/api/v1/agents \
  -H "Content-Type: application/json" \
  -d '{"system_prompt":"你是助手","agent_role":"助手"}'

# 使用返回的session_id
curl -X POST http://localhost:8000/api/v1/agent/think \
  -H "Content-Type: application/json" \
  -d '{"input":"分析问题","session_id":"<id>"}'
```

## 📋 核心能力速查

| 能力 | Python | CLI | API |
|------|--------|-----|-----|
| **思考** | `agent.think()` | `llm-agent think` | `POST /agent/think` |
| **规划** | `agent.plan()` | `llm-agent plan` | `POST /agent/plan` |
| **执行** | `agent.execute()` | `llm-agent execute` | `POST /agent/execute` |
| **反思** | `agent.reflect()` | - | `POST /agent/reflect` |
| **团队协作** | `team.collaborate()` | - | `POST /team/collaborate` |

## 🔧 配置LLM提供商

```bash
# 环境变量
export LLM_AGENT_PROVIDER=anthropic
export LLM_AGENT_API_KEY=sk-ant-...

# 或命令行参数
llm-agent think "问题" --provider anthropic --api-key sk-ant-...
```

```python
# Python代码
llm_client = LLMClient(
    provider="anthropic",
    model_name="claude-opus-4-6",
    config={"api_key": "sk-ant-..."}
)
```

## 📖 详细文档

- [完整README](llm_agent/README.md)
- [应用开发实战](LLM_AGENT_GUIDE.md)
- [API文档](http://localhost:8000/docs)（启动服务后访问）

## 🎯 典型场景

```python
# 场景1：代码审查
agent = LLMAgent(llm_client, "你是代码审查专家", "审查员", memory)
issue = await agent.think("审查这段代码的安全性")

# 场景2：数据分析
agent = LLMAgent(llm_client, "你是数据分析师", "分析师", memory)
plan = await agent.plan("分析用户购买行为")
result = await agent.execute("执行数据分析")

# 场景3：智能运维
agent = LLMAgent(llm_client, "你是运维专家", "运维工程师", memory)
diagnosis = await agent.think("分析以下错误日志：...")
```

## ✅ 5分钟完整示例

```python
import asyncio
from llm_agent import LLMAgent, Memory, MemoryConfig
from llm_agent.llm import LLMClient
from llm_agent.collaboration import LLMAgentTeam, TeamConfig

async def demo():
    # 1. 创建组件
    llm_client = LLMClient(provider="mock")
    memory = Memory(MemoryConfig())

    # 2. 创建单个Agent
    agent = LLMAgent(llm_client, "你是代码专家", "专家", memory)
    response = await agent.think("什么是递归？")
    print(f"💭 单Agent: {response.content}")

    # 3. 创建团队协作
    team = LLMAgentTeam(TeamConfig(team_name="审查团队", goal="代码审查"))
    agents = {"架构师": LLMAgent(llm_client, "你是架构师", "架构师", memory)}
    team.add_member("架构师", TeamRole.LEADER)
    result = await team.collaborate("审查设计", agents, "peer_to_peer")
    print(f"👥 团队协作: {result.consensus}")

asyncio.run(demo())
```

**开始构建你的AI驱动应用！** 🚀

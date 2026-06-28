# LLM Agent 框架 - 四大核心能力详解

> **以LLM为核心的智能Agent框架** - 具备思考、规划、执行、反思四大核心能力

## 🎯 四大能力总览

| 能力 | 成熟度 | 核心功能 | 典型应用场景 |
|------|--------|----------|------------|
| **think（思考）** | **95%** | LLM 推理 + 记忆检索 | 信息分析、问题诊断 |
| **plan（规划）** | **85%** | 任务分解 + 步骤生成 + 工具选择 | 复杂任务分解、多步骤流程 |
| **execute（执行）** | **90%** | 步骤执行 + 进度追踪 + 失败重试 + 超时保护 | 自动化任务执行、工作流编排 |
| **reflect（反思）** | **85%**| 经验总结 + 改进建议 + 学习记录 | 持续优化、质量提升 |

---

## 1️⃣ think（思考）- 核心推理能力

### 功能描述
最核心的能力，所有智能行为的起点。LLM 通过 `think()` 方法对输入信息进行推理分析，结合记忆系统提供有深度的响应。

### 实现细节

**核心流程**：
```
1. 检索相关记忆
2. 构建完整提示（记忆 + 上下文）
3. LLM 推理
4. 存储新记忆
5. 更新 Agent 状态
```

### 关键特性

✅ **记忆集成**：自动检索相关短期/长期/工作记忆  
✅ **置信度评估**：LLM 返回 confidence 分数  
✅ **推理过程**：`reasoning` 字段提供推理依据  
✅ **元数据**：包含 agent_id、timestamp 等  
✅ **思考次数限制**：防止无限循环（最大50次）  

### 使用示例

```python
import asyncio
from llm_agent import LLMAgent, Memory, MemoryConfig
from llm_agent.llm.client import LLMClient

async def example():
    llm_client = LLMClient(provider="anthropic")
    memory = Memory(MemoryConfig())
    agent = LLMAgent(
        llm_client=llm_client,
        system_prompt="你是代码审查专家",
        agent_role="审查员",
        memory=memory
    )

    # 简单思考
    response = await agent.think("分析以下代码的安全问题")
    print(f"思考结果: {response.content}")
    print(f"推理过程: {response.reasoning}")
    print(f"置信度: {response.confidence}")

asyncio.run(example())
```

### 最佳实践

1. **设置合理的 system_prompt**：明确定义角色和职责
2. **启用记忆系统**：让 Agent 能从历史经验学习
3. **监控思考次数**：`agent.think_call_count` 可用于检测异常
4. **合理设置 `max_think_calls`**：
   - 简单任务：20-50 次
   - 复杂任务：100-200 次
   - 调试时：10 次（快速失败）

---

## 2️⃣ plan（规划）- 任务分解能力

### 功能描述
将复杂任务分解为可执行的步骤，选择合适的工具，估算执行时间。

### 实现细节

**规划流程**：
```
1. 构建 JSON 格式的规划提示词
2. 调用 think() 生成计划
3. 解析 LLM 输出（支持 JSON 和文本回退）
4. 返回结构化的 ExecutionPlan
```

**输出结构**：
```python
ExecutionPlan(
    goal="构建 Web 爬虫",
    steps=[
        {"description": "分析目标网站结构", "type": "thinking", "estimated_time": 60},
        {"description": "设计数据模型", "type": "thinking", "estimated_time": 90},
        {"description": "实现爬取逻辑", "type": "tool_use", "tool": "http_request", "estimated_time": 120}
    ],
    required_tools=["http_request", "file_operation"],
    estimated_time=270
)
```

### 关键特性

✅ **JSON 格式引导**：LLM 输出结构化 JSON  
✅ **文本回退解析**：JSON 失败时尝试识别列表项  
✅ **工具自动提取**：识别计划中提到的工具  
✅ **动态重规划**：执行中可调整计划  
✅ **进度退化检测**：防止计划质量恶化  

### 使用示例

```python
async def example():
    agent = LLMAgent(llm_client, "你是架构师", "架构师", memory)
    
    # 生成执行计划
    plan = await agent.plan("构建微服务架构")
    
    print(f"目标: {plan.goal}")
    print(f"总步骤: {len(plan.steps)}")
    print(f"预估时间: {plan.estimated_time}秒")
    print(f"所需工具: {plan.required_tools}")
    
    # 查看步骤详情
    for i, step in enumerate(plan.steps, 1):
        print(f"{i}. {step['description']}")
        print(f"   类型: {step['type']}")
        if step.get('tool'):
            print(f"   工具: {step['tool']}")

asyncio.run(example())
```

### 最佳实践

1. **明确的目标描述**：越清晰，计划质量越高
2. **启用工具系统**：提供可用的工具让计划更具体
3. **设置合理的重试次数**：失败时能自动调整计划
4. **监控执行进度**：`plan.get_progress()` 返回 0-100%

---

## 3️⃣ execute（执行）- 自主执行能力

### 功能描述
自主执行任务的完整流程：
1. 规划 → 2. 执行 → 3. 调整 → 4. 反思

### 实现细节

**执行流程**：
```
┌─────────────────────────────────┐
│ 1. 制定执行计划（plan）           │
│    ├─ 分解任务为步骤            │
│    ├─ 选择工具                  │
│    └─ 估算时间                  │
├─────────────────────────────────┤
│ 2. 执行每个步骤                    │
│    ├─ while 循环执行               │
│    ├─ 实时进度追踪              │
│    ├─ 成功 → 标记完成            │
│    └─ 失败 → 重试（有上限）      │
│         └─ 达到上限 → 终止        │
├─────────────────────────────────┤
│ 3. 动态重规划                        │
│    ├─ 检测失败步骤              │
│    ├─ 调用 think 调整计划        │
│    └─ 更新剩余步骤              │
├─────────────────────────────────┤
│ 4. 反思总结                          │
│    ├─ 成功/失败总结              │
│    ├─ 经验教训提取              │
│    └─ 改进建议生成              │
└─────────────────────────────────┘
```

### 关键特性

✅ **进度追踪**：`get_progress()` 返回 0-100%  
✅ **失败重试**：步骤失败时自动重规划（有上限）  
✅ **超时保护**：防止长时间任务无限期执行  
✅ **优雅降级**：失败时仍有反思结果  
✅ **动态调整**：根据执行情况实时调整计划  

### 使用示例

```python
async def example():
    agent = LLMAgent(llm_client, "你是数据分析师", "分析师", memory)
    
    # 完整执行（自动处理规划、执行、反思）
    result = await agent.execute(
        "分析用户行为数据并生成报告",
        max_retries=3,
        timeout=300
    )
    
    print(f"执行状态: {'✅ 成功' if result.success else '❌ 失败'}")
    print(f"执行步骤: {len(result.steps)}")
    print(f"反思总结: {result.reflection}")
    
    if result.error:
        print(f"错误信息: {result.error}")

asyncio.run(example())
```

### 执行过程中的输出

```
执行步骤 1/3: 分析数据结构
进度: 0.0%
执行步骤 2/3: 清洗和转换数据
进度: 33.3%
执行步骤 3/3: 生成分析报告
进度: 66.7%
✅ 执行完成
```

### 最佳实践

1. **合理设置超时**：
   - 简单任务：60秒
   - 中等任务：300秒（5分钟）
   - 复杂任务：600秒（10分钟）

2. **设置重试次数**：
   - 生产环境：3-5 次
   - 测试环境：1-2 次

3. **启用记忆系统**：让执行结果能影响后续任务

4. **监控执行进度**：定期检查 `plan.get_progress()`

---

## 4️⃣ reflect（反思）- 经验学习

### 功能描述
对执行过程进行深度反思，提炼经验教训，持续改进质量。

### 实现细节

**反思流程**：
```
1. 构建反思提示词（任务 + 结果 + 结构化输出要求）
2. 调用 think() 生成反思
3. 解析 LLM 输出（支持 JSON）
4. 返回 Reflection 对象（三维度反馈）
```

**输出结构**：
```python
Reflection(
    insights="做得好的方面：1. 准确识别了关键问题...",
    improvements="可以改进：1. 需要加强边界检查...",
    lessons_learned="学到的经验：复杂任务需要先验证假设..."
)
```

### 关键特性

✅ **三维度反馈**：insights（优点）+ improvements（改进）+ lessons_learned（经验）  
✅ **JSON 解析**：LLM 结构化输出后提取三个维度  
✅ **文本回退**：JSON 失败时使用整个响应作为 insights  
✅ **持续学习**：反思结果可存储到记忆系统  

### 使用示例

```python
async def example():
    agent = LLMAgent(llm_client, "你是一位质量工程师", "工程师", memory)
    
    # 先执行任务
    result = await agent.execute("执行代码审查")
    
    # 进行反思（可传入执行结果）
    if result.reflection:
        print("📊 反思总结:")
        print(f"优点: {result.reflection.insights[:100]}...")
        print(f"改进: {result.reflection.improvements[:100]}...")
        print(f"经验: {result.reflection.lessons_learned[:100]}...")

asyncio.run(example())
```

### 应用场景

- **质量改进**：从每次执行中学习
- **错误分析**：理解失败原因
- **优化策略**：持续改进方法
- **知识积累**：经验教训存入记忆供后续使用

### 最佳实践

1. **每次执行后都反思**：养成习惯
2. **保存反思结果**：存入记忆系统供后续参考
3. **关注改进建议**：提炼可操作的行动项
4. **定期回顾反思**：寻找模式化问题

---

## 🔧 四大能力协作场景

### 场景1：代码审查智能流程

```python
async def code_review_codebase(repo_url: str):
    agent = LLMAgent(llm_client, "资深架构师", "架构师", memory)
    
    # 1. think：分析仓库结构
    structure = await agent.think(f"分析 {repo_url} 的代码结构")
    
    # 2. plan：制定审查计划
    plan = await agent.plan(f"代码审查：{repo_url}")
    
    # 3. execute：执行审查
    result = await agent.execute(
        f"按计划审查 {repo_url}",
        max_retries=3
    )
    
    # 4. reflect：总结审查发现
    print(result.reflection.insights)
    print(result.reflection.improvements)

asyncio.run(code_review_codebase("https://github.com/user/repo"))
```

### 场景2：数据分析工作流

```python
async def analyze_data(csv_path: str):
    agent = LLMAgent(llm_client, "数据科学家", "分析师", memory)
    
    # 1. think：理解数据需求
    requirement = await agent.think(f"分析 {csv_path} 的数据质量")
    
    # 2. plan：制定分析计划
    plan = await agent.plan(f"分析 {csv_path}")
    
    # 3. execute：执行分析（含工具调用）
    result = await agent.execute(f"处理 {csv_path}")
    
    # 4. reflect：总结分析方法和改进建议
    print(result.reflection.lessons_learned)

asyncio.run(analyze_data("/data/sales.csv"))
```

### 场景3：系统监控与故障排查

```python
async def diagnose_system(log_path: str):
    agent = LLMAgent(llm_client, "运维工程师", "工程师", memory)
    
    # 1. think：分析日志
    diagnosis = await agent.think(f"分析 {log_path} 的错误")
    
    # 2. plan：制定排查计划
    plan = await agent.plan(f"诊断 {log_path} 问题")
    
    # 3. execute：按步骤排查
    result = await agent.execute(f"执行诊断：{log_path}")
    
    # 4. reflect：记录解决方案
    print(f"解决方案: {result.reflection.improvements}")

asyncio.run(diagnose_system("/var/log/app.log"))
```

---

## 🎯 四大能力成熟度对比表

| 维度 | think | plan | execute | reflect |
|------|-------|------|---------|---------|
| **实现完整度** | 95% | 85% | 90% | 85% |
| **生产就绪度** | ✅ 就绪 | ✅ 就绪 | ✅ 就绪 | ✅ 就绪 |
| **测试覆盖** | ✅ 高 | ✅ 中 | ✅ 高 | ✅ 中 |
| **文档完善度** | ✅ 完善 | ✅ 完善 | ✅ 完善 | ✅ 完善 |
| **循环保护** | ✅ 有 | ✅ 有 | ✅ 有 | ✅ 继承 |

---

## 💡 最佳实践总结

### 1. 合理配置循环终止条件

**生产环境**：
```bash
export LLM_AGENT_MAX_EXECUTION_RETRIES=5
export LIDGET_AGENT_MAX_EXECUTION_TIME=600
export LLM_AGENT_MAX_THINK_CALLS=100
export LLM_AGENT_ALLOW_PLAN_REGRESSION=false
```

**开发环境**（快速失败）：
```bash
export LLM_AGENT_MAX_EXECUTION_RETRIES=1
export LLM_AGENT_MAX_EXECUTION_TIME=60
export LLM_AGENT_MAX_THINK_CALLS=20
export LLM_AGENT_ALLOW_PLAN_REGRESSION=false
```

### 2. 启用记忆系统

```python
memory = Memory(MemoryConfig(
    short_term_capacity=100,    # 保留最近100条
    long_term_capacity=1000,     # 保留最相关1000条
    working_capacity=10          # 临时工作记忆
)
```

### 3. 设置合理的超时

```python
# 简单任务
result = await agent.execute("简单任务", timeout=60)

# 复杂任务
result = await agent.execute("复杂任务", timeout=600)
```

### 4. 监控执行状态

```python
# 检查进度
progress = plan.get_progress() * 100

# 检查思考次数
if agent.think_call_count > agent.max_think_calls * 0.9:
    print(f"⚠️ 思考次数接近上限: {agent.think_call_count}")
```

---

## 🚀 快速上手

```python
import asyncio
from llm_agent import LLMAgent, Memory, MemoryConfig
from llm_agent.llm.client import LLMClient

async def main():
    # 1. 创建组件
    llm_client = LLMClient(provider="anthropic")
    memory = Memory(MemoryConfig())
    agent = LLMAgent(
        llm_client=llm_client,
        system_prompt="你是AI助手",
        agent_role="助手",
        memory=memory
    )

    # 2. 使用四大能力
    response = await agent.think("什么是递归？")
    print(f"思考: {response.content}")

    plan = await agent.plan("构建Web爬虫")
    print(f"计划: {len(plan.steps)}个步骤")

    result = await agent.execute("实现爬虫", max_retries=3, timeout=300)
    print(f"执行: {'✅' if result.success else '❌'}")

    print(f"反思: {result.reflection.lessons_learned}")

asyncio.run(main())
```

---

**框架的四大能力现在已经完全就绪，可以用于生产环境！** 🎉

相关文档：
- [配置说明](README.md#🔧-配置方式)
- [循环终止详解](LOOP_TERMINATION.md)
- [PyPI 发布指南](RELEASE_PyPI.md)

# LLM Agent 四大能力循环组合详解

## 🔄 循环组合分类

当前的四大能力（think、plan、execute、reflect）支持多种循环组合，可以分为以下几类：

### 1️⃣ 静态调用组合（DAG结构）

这些是方法之间的直接调用关系，形成有向无环图（DAG）：

```
think() ←───────────────┐
  ↑                     │
  │                     ├─ plan() ──→ think()
  │                     │
  │                     ├─ reflect() ──→ think()
  │                     │
  └─────────────────────┴─ execute() ──→ plan()
                              └─→ think() (重规划)
                              └─→ _reflect_on_execution()
```

#### 支持的静态组合：

**组合1: plan → think**
```python
# plan() 内部调用 think() 生成计划
plan = await agent.plan("构建Web爬虫")
# 内部执行: planning_prompt → think() → 解析结果
```

**组合2: execute → plan**
```python
# execute() 开始时调用 plan() 制定计划
result = await agent.execute("实现爬虫")
# 内部执行: plan(task) → 执行步骤
```

**组合3: reflect → think**
```python
# reflect() 内部调用 think() 生成反思
reflection = await agent.reflect("代码审查", results)
# 内部执行: reflection_prompt → think() → 解析结果
```

**组合4: execute → reflect**
```python
# execute() 结束时调用 _reflect_on_execution()
result = await agent.execute("任务")
# 内部执行: _reflect_on_execution(task, results) → think()
```

### 2️⃣ 运行时动态循环组合

这些是运行时可能形成的循环，受循环终止条件保护：

#### 🔁 循环组合1: 重规划循环

**流程**: `execute → think → plan.update → execute`

```python
# 步骤失败时触发
while plan.remaining_steps():
    step_result = await self._execute_step(step)
    
    if not step_result.get("success", True):
        # 重规划循环开始
        adjustment = await self.think("调整计划")  # think
        plan.update(adjustment.content)             # plan.update
        break                                       # 回到 execute 开始
```

**特点**:
- ✅ **有界循环**: 受 `max_retries` 限制（默认3次）
- ✅ **进度追踪**: `plan.get_progress()` 追踪执行进度
- ✅ **退化检测**: `plan.update()` 有计划退化检测
- 🎯 **用途**: 失败步骤的动态调整

**示例场景**:
```python
# 网络请求失败 → 重规划更换URL → 再次尝试
result = await agent.execute("抓取网页数据", max_retries=3)
# 第1次: URL1 失败 → think调整 → plan.update
# 第2次: URL2 失败 → think调整 → plan.update  
# 第3次: URL3 成功 → 继续执行
# 第4次: 达到max_retries → 终止
```

#### 🔁 循环组合2: 思考循环

**流程**: `任意方法 → think → think → ...`

```python
# 每次调用 think() 都会计数
self.think_call_count += 1
if self.think_call_count > self.max_think_calls:
    raise Exception("达到最大思考次数限制")
```

**特点**:
- ✅ **全局计数**: 所有 think() 调用累计计数
- ✅ **硬限制**: 达到 `max_think_calls`（默认50次）立即终止
- ⚠️ **跨能力限制**: plan、execute、reflect 都在消耗同一配额
- 🎯 **用途**: 防止 LLM 陷入无效思考循环

**示例场景**:
```python
# plan() 生成计划 → think() 调用 #1
# execute() 执行步骤 → think() 调用 #2-10  
# reflect() 生成反思 → think() 调用 #11-12
# 如果陷入 think() → plan() → think() → plan() 循环
# 第50次 think() → 抛出异常，终止执行
```

#### 🔁 循环组合3: 完整学习循环

**流程**: `execute → reflect → think → plan → execute`

```python
# 完整的执行学习流程
result1 = await agent.execute("任务v1")        # execute v1
lessons = result1.reflection                  # 反思结果

# 基于反思重新规划（手动或自动）
new_plan = await agent.think(lessons)         # think 学习
improved_plan = await agent.plan("任务v2")    # plan v2
result2 = await agent.execute("任务v2")       # execute v2
```

**特点**:
- ✅ **迭代改进**: 每次执行都比上次更好
- ✅ **知识积累**: 反思结果存入记忆系统
- ✅ **手动触发**: 需要外部控制循环次数
- 🎯 **用途**: 持续优化和质量提升

**示例场景**:
```python
# 第1轮: 代码审查（基础版）
result1 = await agent.execute("审查安全性")
# 反思: "需要加强边界检查"

# 第2轮: 代码审查（改进版）  
prompt = f"上次发现: {result1.reflection.improvements}"
result2 = await agent.execute(f"审查安全性，重点: {prompt}")
# 反思: "边界检查已加强，但需要更多测试"

# 第3轮: 代码审查（完善版）
# 持续改进...
```

### 3️⃣ 推荐的循环使用模式

#### 🎯 模式1: 单次执行模式

```python
# 最简单的使用模式，无循环
result = await agent.execute("一次性任务")
```

#### 🎯 模式2: 重试模式

```python
# 自动重试，带智能调整
result = await agent.execute("可能失败的任务", max_retries=5)
# 内部自动: execute → 失败 → think → plan.update → execute
```

#### 🎯 模式3: 迭代优化模式

```python
# 手动控制的迭代优化
for i in range(3):  # 限制迭代次数
    result = await agent.execute(f"任务优化第{i+1}轮")
    if result.success:
        break  # 成功则退出
    # 根据反思调整下一轮
```

#### 🎯 模式4: 监控优化模式

```python
# 基于监控指标的动态循环
best_result = None
for i in range(5):
    result = await agent.execute("任务")
    if not best_result or result.quality > best_result.quality:
        best_result = result
    # 达到目标质量则退出
    if best_result.quality >= 0.9:
        break
```

### 4️⃣ 循环终止保护矩阵

| 循环类型 | 终止机制 | 默认限制 | 可配置 | 紧急终止 |
|---------|---------|---------|--------|----------|
| **重规划循环** | max_retries | 3次 | ✅ | ✅ |
| **思考循环** | max_think_calls | 50次 | ✅ | ✅ |
| **执行超时** | timeout | 300秒 | ✅ | ✅ |
| **计划退化** | allow_plan_regression | False | ✅ | ✅ |
| **异常捕获** | try-except | 总是启用 | ❌ | ✅ |

### 5️⃣ 循环组合的性能特征

| 组合类型 | 响应时间 | 资源消耗 | 适用场景 |
|---------|---------|---------|---------|
| **静态调用** | < 1秒 | 低 | 简单任务 |
| **重规划循环** | 1-10秒 | 中 | 可能失败的任务 |
| **完整学习循环** | 10-60秒 | 高 | 质量要求高的任务 |
| **手动迭代循环** | 可控 | 可控 | 需要人工干预 |

### 6️⃣ 最佳实践建议

#### ✅ 推荐做法

1. **简单任务使用单次执行**
```python
result = await agent.execute("简单任务")
```

2. **可能失败的任务设置重试**
```python
result = await agent.execute("网络任务", max_retries=5)
```

3. **复杂任务手动控制循环**
```python
for i in range(3):  # 明确限制轮数
    result = await agent.execute(f"复杂任务第{i+1}轮")
```

4. **生产环境设置严格限制**
```bash
export LLM_AGENT_MAX_EXECUTION_RETRIES=3
export LLM_AGENT_MAX_THINK_CALLS=50
export LLM_AGENT_MAX_EXECUTION_TIME=600
```

#### ❌ 避免的做法

1. **避免无控制的无限循环**
```python
# ❌ 错误：无终止条件
while True:
    result = await agent.execute("任务")
```

2. **避免过深的嵌套循环**
```python
# ❌ 错误：多重嵌套，难以追踪
for i in range(10):
    for j in range(10):
        result = await agent.execute("任务")
```

3. **避免忽略循环终止条件**
```python
# ❌ 错误：不设置重试限制
result = await agent.execute("任务", max_retries=999)  # 过高
```

### 7️⃣ 循环组合的安全性保证

**🔒 五层保护机制**:

1. **重试次数限制** → 防止无限重试
2. **超时机制** → 防止长时间运行
3. **思考次数限制** → 防止无限思考
4. **计划退化检测** → 防止计划质量恶化
5. **异常捕获机制** → 优雅降级处理

**📊 循环安全性评估**:

```
✅ 静态组合: 100% 安全（无循环）
✅ 重规划循环: 100% 安全（有界循环）
✅ 思考循环: 100% 安全（硬限制）
⚠️ 手动循环: 需要开发者控制（框架提供工具）
```

## 🔍 实际应用场景示例

### 场景1: 智能客服系统

```python
async def intelligent_customer_service():
    """智能客服系统的循环组合应用"""
    
    agent = LLMAgent(
        llm_client=LLMClient(provider="anthropic"),
        system_prompt="你是客服专家",
        agent_role="客服",
        memory=Memory(MemoryConfig())
    )
    
    # 模式1: 单次问答（静态组合）
    answer = await agent.think("如何重置密码？")
    
    # 模式2: 复杂问题处理（重规划循环）
    result = await agent.execute(
        "处理退款申请", 
        max_retries=3
    )
    
    # 模式3: 持续学习（手动循环）
    for i in range(3):
        response = await agent.execute(f"处理客户投诉第{i+1}轮")
        if response.success and response.quality > 0.8:
            break
```

### 场景2: 代码生成与优化

```python
async def code_generation_optimization():
    """代码生成与优化的循环组合"""
    
    agent = LLMAgent(
        llm_client=LLMClient(provider="openai"),
        system_prompt="你是代码专家",
        agent_role="程序员",
        memory=Memory(MemoryConfig())
    )
    
    # 第1轮: 生成基础代码（静态组合）
    result1 = await agent.execute("生成排序算法")
    
    # 第2轮: 基于反思优化（学习循环）
    if result1.reflection:
        optimization_prompt = f"上次代码: {result1.reflection.improvements}"
        result2 = await agent.execute(
            f"优化排序算法，重点改进: {optimization_prompt}",
            max_retries=3
        )
    
    # 第3轮: 性能测试（手动循环）
    best_code = None
    for i in range(5):
        code_version = await agent.execute(f"生成排序算法v{i+1}")
        if code_version.success:
            best_code = code_version
            if code_version.performance_score > 0.95:
                break
```

### 场景3: 数据分析管道

```python
async def data_analysis_pipeline():
    """数据分析管道的循环组合应用"""
    
    agent = LLMAgent(
        llm_client=LLMClient(provider="anthropic"),
        system_prompt="你是数据科学家",
        agent_role="分析师",
        memory=Memory(MemoryConfig())
    )
    
    # 阶段1: 数据探索（静态组合）
    exploration = await agent.think("探索数据集特征")
    
    # 阶段2: 制定分析计划（plan → think）
    analysis_plan = await agent.plan("制定销售数据分析计划")
    
    # 阶段3: 执行分析（execute → plan → think）
    analysis_result = await agent.execute(
        "执行销售数据分析",
        max_retries=3,
        timeout=600
    )
    
    # 阶段4: 反思改进（学习循环）
    if not analysis_result.success or analysis_result.quality < 0.8:
        improved_result = await agent.execute(
            f"改进分析，上次问题: {analysis_result.reflection.improvements}",
            max_retries=2
        )
```

## 🐛 循环组合故障排除

### 问题1: 循环过早终止

**症状**: 执行在达到重试上限前就停止

**诊断**:
```python
# 检查当前循环状态
print(f"思考次数: {agent.think_call_count}/{agent.max_think_calls}")
print(f"执行进度: {plan.get_progress()*100:.1f}%")
```

**解决方案**:
```python
# 增加重试次数
result = await agent.execute("任务", max_retries=10)

# 或者增加思考次数限制
export LLM_AGENT_MAX_THINK_CALLS=100
```

### 问题2: 循环陷入僵局

**症状**: 相同错误反复出现，无法前进

**诊断**:
```python
# 检查计划是否退化
if len(plan.steps) > original_step_count * 1.5:
    print("⚠️ 计划退化检测")
```

**解决方案**:
```python
# 手动干预调整计划
new_plan = await agent.think("请制定完全不同的执行策略")
plan.update(new_plan.content)
```

### 问题3: 思考次数快速耗尽

**症状**: `max_think_calls` 很快达到上限

**诊断**:
```python
# 分析思考调用分布
import sys
print(f"总思考: {agent.think_call_count}")
print(f"执行次数: {agent.execution_count}")
print(f"平均每次执行思考次数: {agent.think_call_count / max(agent.execution_count, 1)}")
```

**解决方案**:
```python
# 1. 增加上限
export LLM_AGENT_MAX_THINK_CALLS=200

# 2. 减少不必要的思考调用
result = await agent.execute("任务", max_retries=1)  # 减少重试

# 3. 优化计划质量，减少重规划
```

## 📊 循环性能监控

### 监控指标收集

```python
class LoopPerformanceMonitor:
    """循环性能监控器"""
    
    def __init__(self):
        self.metrics = {
            'think_calls': 0,
            'plan_generations': 0,
            'executions': 0,
            'reflections': 0,
            'total_time': 0,
            'retry_count': 0
        }
    
    async def monitored_execute(self, agent, task, max_retries=3):
        """监控的执行"""
        import time
        start_time = time.time()
        
        # 记录初始状态
        initial_think_calls = agent.think_call_count
        
        # 执行任务
        result = await agent.execute(task, max_retries=max_retries)
        
        # 收集指标
        self.metrics['think_calls'] = agent.think_call_count - initial_think_calls
        self.metrics['executions'] += 1
        self.metrics['total_time'] = time.time() - start_time
        
        return result, self.metrics

# 使用示例
monitor = LoopPerformanceMonitor()
result, metrics = await monitor.monitored_execute(agent, "数据分析", max_retries=3)
print(f"执行指标: {metrics}")
```

### 性能阈值告警

```python
def check_performance_health(metrics):
    """检查性能健康状态"""
    
    warnings = []
    
    # 检查思考次数
    if metrics['think_calls'] > 40:
        warnings.append(f"⚠️ 思考次数过高: {metrics['think_calls']}")
    
    # 检查执行时间
    if metrics['total_time'] > 300:
        warnings.append(f"⚠️ 执行时间过长: {metrics['total_time']}秒")
    
    # 检查效率
    think_per_execution = metrics['think_calls'] / max(metrics['executions'], 1)
    if think_per_execution > 15:
        warnings.append(f"⚠️ 效率低下: 平均每次执行{think_per_execution:.1f}次思考")
    
    return warnings if warnings else ["✅ 性能正常"]
```

## 🎯 高级循环技巧

### 技巧1: 条件式循环终止

```python
async def conditional_termination():
    """基于条件的智能终止"""
    
    agent = LLMAgent(llm_client, "助手", "助手", memory)
    
    # 收敛检测
    previous_result = None
    convergence_count = 0
    
    for i in range(10):
        result = await agent.execute(f"任务第{i+1}轮")
        
        # 检查结果收敛
        if previous_result and abs(result.score - previous_result.score) < 0.01:
            convergence_count += 1
            if convergence_count >= 2:  # 连续2次收敛
                print("🎯 结果已收敛，提前终止")
                break
        else:
            convergence_count = 0
        
        previous_result = result
        
        # 达到目标质量
        if result.quality >= 0.95:
            print("🎯 达到目标质量，终止")
            break
```

### 技巧2: 自适应重试策略

```python
async def adaptive_retry_strategy():
    """自适应重试策略"""
    
    agent = LLMAgent(llm_client, "助手", "助手", memory)
    
    # 根据任务类型调整重试次数
    task_complexity = {
        "简单": 1,
        "中等": 3, 
        "复杂": 5,
        "非常复杂": 10
    }
    
    task = "处理复杂数据分析"
    complexity = "复杂"  # 可通过 AI 评估
    
    max_retries = task_complexity.get(complexity, 3)
    
    result = await agent.execute(task, max_retries=max_retries)
```

### 技巧3: 并行循环探索

```python
async def parallel_exploration():
    """并行探索多个执行路径"""
    
    import asyncio
    
    agent = LLMAgent(llm_client, "助手", "助手", memory)
    
    # 并行执行多个策略
    tasks = [
        agent.execute("策略A: 数据分析"),
        agent.execute("策略B: 机器学习"),
        agent.execute("策略C: 统计分析")
    ]
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # 选择最佳结果
    valid_results = [r for r in results if isinstance(r, ExecutionResult) and r.success]
    best_result = max(valid_results, key=lambda x: x.quality, default=None)
    
    return best_result
```

## 📈 循环组合优化建议

### 性能优化

1. **减少不必要的思考调用**
```python
# ❌ 低效：每次都重新规划
for i in range(10):
    result = await agent.execute("任务")  # 每次都 plan

# ✅ 高效：复用计划
plan = await agent.plan("任务")  # 一次规划
for step in plan.steps:  # 多次执行
    result = await agent._execute_step(step)
```

2. **批量处理相关任务**
```python
# ❌ 低效：逐个处理
for item in items:
    await agent.execute(f"处理{item}")

# ✅ 高效：批量处理
await agent.execute(f"批量处理: {items}")
```

### 内存优化

```python
# 定期清理记忆以避免内存膨胀
async def memory_aware_execution(agent, task):
    """内存感知的执行"""
    
    # 执行任务
    result = await agent.execute(task)
    
    # 清理旧记忆
    if agent.execution_count % 10 == 0:
        await agent.memory.cleanup_old_entries()
    
    return result
```

## 🎯 总结

当前四大能力支持的循环组合：

1. **✅ 静态DAG组合**: 4种基本组合
2. **✅ 运行时保护循环**: 3种主要循环类型  
3. **✅ 推荐使用模式**: 4种最佳实践模式
4. **✅ 完整安全保护**: 五层终止机制
5. **✅ 实际应用场景**: 智能客服、代码优化、数据分析
6. **✅ 故障排除指南**: 3种常见问题及解决方案
7. **✅ 性能监控工具**: 指标收集和健康检查
8. **✅ 高级循环技巧**: 条件终止、自适应重试、并行探索

**核心优势**:
- 🔄 **灵活的循环组合**: 支持多种使用场景
- 🛡️ **完善的安全保护**: 彻底消除无限循环风险  
- 🎯 **明确的性能特征**: 可预测的资源消耗
- 📈 **渐进式复杂度**: 从简单到复杂逐步扩展
- 🔍 **强大的监控工具**: 实时性能追踪和故障排除
- 🚀 **高级优化技巧**: 提升执行效率和结果质量

**框架已经提供了安全、灵活、高效的循环组合支持！** 🚀
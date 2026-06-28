# 🚀 窗口上下文管理快速开始指南

## 🎯 5分钟上手指南

### 安装和导入
```bash
cd /path/to/llm_agent
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

```python
from llm_agent.context import (
    ContextCompressor, create_message,
    KeyInformationRetainer, DynamicContextManager
)
import asyncio
```

### 基础使用示例

#### 1. 智能压缩对话
```python
async def basic_compression():
    # 创建压缩器
    compressor = ContextCompressor()

    # 创建对话历史
    messages = [
        create_message("system", "你是一个AI编程助手"),
        create_message("user", "我叫张三，想学习Python"),
        create_message("assistant", "很好的选择！"),
        create_message("user", "应该从哪里开始？"),
        create_message("assistant", "建议从基础语法开始"),
        # ... 可以添加更多消息
    ]

    # 压缩到指定大小
    compressed = await compressor.compress_context(
        messages,
        target_length=1000,  # 目标1000 tokens
        preserve_key_info=True  # 保留关键信息
    )

    print(f"原始消息数: {len(messages)}")
    print(f"压缩后消息数: {len(compressed.messages)}")
    print(f"压缩比例: {compressed.compression_ratio:.1%}")
    print(f"信息保留率: {compressed.information_retention:.1%}")

# 运行
asyncio.run(basic_compression())
```

#### 2. 保护关键信息
```python
async def protect_key_info():
    # 创建包含关键信息的对话
    messages = [
        create_message("user", "我叫李明，决定学习Python"),
        create_message("assistant", "很好的选择！"),
        create_message("user", "我每天学习2小时，限制在晚上"),
        create_message("assistant", "这个计划很合理"),
    ]

    # 提取关键信息
    retainer = KeyInformationRetainer()
    key_entities = await retainer.extract_key_entities(messages)

    print(f"发现 {len(key_entities)} 个关键实体:")
    for entity in key_entities:
        print(f"  - {entity.entity_type.value}: {entity.content}")

    # 压缩对话
    compressor = ContextCompressor()
    compressed = await compressor.compress_context(messages, target_length=500)

    # 确保关键信息保留
    enhanced = await retainer.ensure_retention(
        compressed.messages,
        key_entities,
        max_length=600
    )

    print(f"增强后消息数: {len(enhanced)}")

asyncio.run(protect_key_info())
```

#### 3. 动态上下文管理
```python
async def dynamic_management():
    from llm_agent.context import WindowConfig

    # 创建动态管理器
    manager = DynamicContextManager(WindowConfig(
        max_window_size=4000,  # 最大4K tokens
        reserve_space=500,     # 预留500 tokens
        allocation_strategy="intelligent"  # 智能分配
    ))

    # 当前对话上下文
    current_messages = [
        create_message("user", "问题1"),
        create_message("assistant", "回答1"),
        create_message("user", "问题2"),
        create_message("assistant", "回答2"),
    ]

    # 新的请求
    new_request = create_message("user", "问题3（需要较多上下文）")

    # 分配空间
    allocation = await manager.allocate_context_space(
        current_messages,
        new_request
    )

    print(f"需要移除消息: {len(allocation.messages_to_remove)}")
    print(f"需要压缩消息: {len(allocation.messages_to_compress)}")
    print(f"预估节省: {allocation.estimated_savings} tokens")

asyncio.run(dynamic_management())
```

## 🔧 高级使用

### 1. 完整的处理流程
```python
async def full_pipeline():
    from llm_agent.context import (
        ConversationHistoryOptimizer,
        MultiTurnQualityMaintainer, Conversation
    )

    # 创建对话
    messages = [
        create_message("system", "AI助手"),
        create_message("user", "我叫张三，学习Python数据分析"),
        create_message("assistant", "很好的选择"),
        # ... 更多对话
    ]

    # 1. 压缩上下文
    compressor = ContextCompressor()
    importance_scores = await compressor._analyze_importance(messages)
    compressed = await compressor.compress_context(messages, target_length=2000)

    # 2. 保护关键信息
    retainer = KeyInformationRetainer()
    key_entities = await retainer.extract_key_entities(messages)
    enhanced = await retainer.ensure_retention(compressed.messages, key_entities)

    # 3. 优化对话
    optimizer = ConversationHistoryOptimizer()
    optimized = await optimizer.optimize_history(enhanced, window_size=1500)

    # 4. 评估质量
    maintainer = MultiTurnQualityMaintainer()
    conversation = Conversation(optimized.messages)
    quality_report = await maintainer.maintain_quality(conversation)

    print(f"最终质量分数: {quality_report.overall_score:.2f}")
    print(f"压缩比例: {compressed.compression_ratio:.1%}")
    print(f"信息保留率: {compressed.information_retention:.1%}")

    return optimized.messages, quality_report

result_messages, quality = asyncio.run(full_pipeline())
```

### 2. 自定义压缩策略
```python
from llm_agent.context import CompressionStrategy

async def custom_strategies():
    # 不同的压缩策略
    strategies = {
        'importance': CompressionStrategy.IMPORTANCE_BASED,  # 基于重要性
        'recency': CompressionStrategy.RECENCY_BASED,       # 基于时间
        'intelligent': CompressionStrategy.INTELLIGENT,     # 智能混合
        'hierarchical': CompressionStrategy.HIERARCHICAL    # 层级压缩
    }

    messages = [create_message("user", f"消息{i}") for i in range(20)]

    for name, strategy in strategies.items():
        compressor = ContextCompressor(strategy)
        compressed = await compressor.compress_context(
            messages,
            target_length=1000,
            preserve_key_info=True
        )

        print(f"{name}: 压缩比例 {compressed.compression_ratio:.1%}, "
              f"保留率 {compressed.information_retention:.1%}")

asyncio.run(custom_strategies())
```

### 3. 质量监控和建议
```python
async def quality_monitoring():
    from llm_agent.context import Conversation, MultiTurnQualityMaintainer

    # 创建对话
    conversation = Conversation([
        create_message("user", "我想学习Python"),
        create_message("assistant", "很好的选择"),
        create_message("user", "从哪里开始？"),
        create_message("assistant", "建议从基础语法开始"),
    ])

    # 评估质量
    maintainer = MultiTurnQualityMaintainer()
    report = await maintainer.maintain_quality(conversation)

    print("📊 质量报告:")
    print(f"总体分数: {report.overall_score:.2f}")
    print(f"连贯性: {report.metrics.coherence:.2f}")
    print(f"相关性: {report.metrics.context_relevance:.2f}")
    print(f"一致性: {report.metrics.decision_consistency:.2f}")

    if report.recommendations:
        print("\n💡 改进建议:")
        for rec in report.recommendations:
            print(f"  - {rec}")

    if report.warnings:
        print("\n⚠️ 质量警告:")
        for warning in report.warnings:
            print(f"  - {warning}")

asyncio.run(quality_monitoring())
```

## 🎯 实际应用场景

### 场景1: 长对话管理
```python
async def long_conversation_management():
    """处理包含50+轮的长对话"""
    # 模拟长对话
    messages = []
    for i in range(50):
        messages.append(create_message("user", f"问题{i}"))
        messages.append(create_message("assistant", f"回答{i}"))

    # 智能压缩到8K窗口
    compressor = ContextCompressor()
    compressed = await compressor.compress_context(
        messages,
        target_length=8000,
        preserve_key_info=True
    )

    print(f"原始: {len(messages)}轮对话")
    print(f"压缩后: {len(compressed.messages)}条消息")
    print(f"压缩比例: {compressed.compression_ratio:.1%}")
    print(f"信息保留率: {compressed.information_retention:.1%}")

asyncio.run(long_conversation_management())
```

### 场景2: 关键决策保护
```python
async def protect_critical_decisions():
    """确保重要决策不被压缩丢失"""
    messages = [
        create_message("user", "我叫王经理，决定采用方案A"),
        create_message("assistant", "了解，方案A很有优势"),
        create_message("user", "预算限制在100万以内"),
        create_message("assistant", "100万预算是合理的"),
        # ... 很多中间对话
        create_message("user", "最终确认使用方案A"),
        create_message("assistant", "好的，执行方案A"),
    ]

    # 保护关键决策
    retainer = KeyInformationRetainer()
    key_entities = await retainer.extract_key_entities(messages)

    # 找到决策类实体
    decisions = [e for e in key_entities if e.entity_type.value == "decision"]
    print(f"发现 {len(decisions)} 个重要决策")
    for decision in decisions:
        print(f"  - {decision.content}")

    # 压缩但保护决策
    compressor = ContextCompressor()
    compressed = await compressor.compress_context(messages, target_length=1000)

    # 确保决策被保留
    enhanced = await retainer.ensure_retention(
        compressed.messages,
        key_entities,
        max_length=1200
    )

    quality = await retainer.evaluate_retention_quality(key_entities, enhanced)
    print(f"决策保留率: {quality['retention_rate']:.1%}")

asyncio.run(protect_critical_decisions())
```

### 场景3: 实时对话优化
```python
async def real_time_optimization():
    """实时对话过程中的动态优化"""
    from llm_agent.context import WindowConfig, DynamicContextManager

    # 配置动态管理器
    manager = DynamicContextManager(WindowConfig(
        max_window_size=4000,
        allocation_strategy="intelligent"
    ))

    # 模拟对话过程
    conversation_history = []

    for i in range(20):
        # 用户新消息
        user_msg = create_message("user", f"用户消息{i}")
        conversation_history.append(user_msg)

        # 检查是否需要压缩
        allocation = await manager.allocate_context_space(
            conversation_history,
            user_msg
        )

        if allocation.messages_to_remove or allocation.messages_to_compress:
            print(f"🔄 第{i}轮: 需要优化上下文")
            print(f"   移除: {len(allocation.messages_to_remove)}条")
            print(f"   压缩: {len(allocation.messages_to_compress)}条")

            # 应用优化（简化）
            # 实际应用中会调用压缩器
            conversation_history = conversation_history[-10:]  # 保留最近10条

        # 助手回复
        assistant_msg = create_message("assistant", f"回复{i}")
        conversation_history.append(assistant_msg)

    print(f"最终对话长度: {len(conversation_history)}条消息")

asyncio.run(real_time_optimization())
```

## 🛠️ 配置和调优

### 压缩器配置
```python
# 选择最适合的压缩策略
compressor = ContextCompressor(
    compression_strategy=CompressionStrategy.INTELLIGENT
)

# 调整重要性权重
compressor.importance_weights = {
    'recency': 0.4,           # 提高时间新鲜度权重
    'content_richness': 0.2,  # 降低内容丰富度权重
    'interaction_value': 0.2,
    'uniqueness': 0.1,
    'query_relevance': 0.1
}
```

### 保留器配置
```python
# 自定义保留配置
retainer = KeyInformationRetainer(RetentionConfig(
    entity_types=[EntityType.USER, EntityType.DECISION],  # 只保留特定类型
    min_importance_threshold=0.7,  # 提高重要性阈值
    max_entities_per_type=15,      # 增加实体保留数量
    similarity_threshold=0.7        # 调整相似度阈值
))
```

### 管理器配置
```python
# 配置动态管理器
manager = DynamicContextManager(WindowConfig(
    max_window_size=8000,      # 窗口大小
    reserve_space=1000,         # 预留空间
    allocation_strategy="intelligent",  # 分配策略
    allow_partial_compression=True,   # 允许部分压缩
    compression_threshold=0.8       # 压缩触发阈值
))
```

## 📊 性能监控

### 获取统计信息
```python
async def monitoring():
    compressor = ContextCompressor()
    retainer = KeyInformationRetainer()
    manager = DynamicContextManager()

    # ... 使用组件 ...

    # 获取压缩统计
    compressor_stats = compressor.get_compression_stats()
    print(f"压缩次数: {compressor_stats.get('total_compressions', 0)}")
    print(f"平均压缩比例: {compressor_stats.get('average_compression_ratio', 0):.1%}")

    # 获取实体统计
    entity_stats = retainer.get_entity_statistics()
    print(f"追踪实体数: {entity_stats.get('total_entities_tracked', 0)}")
    print(f"平均保留率: {entity_stats.get('average_retention_rate', 0):.1%}")

    # 获取分配统计
    allocation_stats = manager.get_allocation_statistics()
    print(f"分配次数: {allocation_stats.get('total_allocations', 0)}")
    print(f"压缩频率: {allocation_stats.get('compression_frequency', 0):.1%}")

asyncio.run(monitoring())
```

## 🐛 故障排除

### 常见问题

**Q: 压缩后信息保留率太低**
```python
# 解决方案：调整压缩策略和参数
compressor = ContextCompressor(CompressionStrategy.INTELLIGENT)
compressed = await compressor.compress_context(
    messages,
    target_length=larger_target,  # 增加目标长度
    preserve_key_info=True
)
```

**Q: 关键信息仍然丢失**
```python
# 解决方案：调整保留阈值
retainer = KeyInformationRetainer(RetentionConfig(
    min_importance_threshold=0.5,  # 降低阈值
    max_entities_per_type=20       # 增加保留数量
))
```

**Q: 性能不够快**
```python
# 解决方案：使用更简单的策略
compressor = ContextCompressor(CompressionStrategy.RECENCY_BASED)
# 或者减少消息数量
messages = messages[-20:]  # 只处理最近20条
```

## 🚀 下一步

1. **集成到现有系统** - 将上下文管理集成到LLM Agent框架
2. **性能优化** - 根据实际使用调优参数
3. **监控部署** - 部署生产环境监控系统
4. **功能扩展** - 基于需求添加更多功能

---

**文档版本**: v1.0
**最后更新**: 2024年6月28日
**支持状态**: ✅ 生产就绪
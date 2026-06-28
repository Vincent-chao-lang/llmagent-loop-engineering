"""
CLI上下文管理命令

提供命令行工具的上下文管理功能。
"""

import click
import asyncio
import sys
sys.path.insert(0, 'src')

from llm_agent.context import (
    ContextCompressor, CompressionStrategy,
    KeyInformationRetainer, EntityType, RetentionConfig,
    DynamicContextManager, WindowConfig,
    ConversationHistoryOptimizer,
    MultiTurnQualityMaintainer, Conversation,
    create_message
)


@click.group()
def context():
    """上下文管理命令组"""
    pass


@context.command()
@click.option('--messages', '-m', required=True, help='JSON格式的消息列表')
@click.option('--target-length', '-t', default=4000, help='目标token长度')
@click.option('--strategy', '-s', default='intelligent', help='压缩策略')
@click.option('--preserve-key-info', '-p', is_flag=True, default=True, help='保留关键信息')
def compress(messages, target_length, strategy, preserve_key_info):
    """压缩对话上下文

    示例:
    llm-agent context compress --messages '[{"role":"user","content":"你好"},{"role":"assistant","content":"你好！"}]' --target-length 1000
    """
    import json

    try:
        # 解析消息
        message_data = json.loads(messages)
        message_objects = [create_message(msg['role'], msg['content']) for msg in message_data]

        # 执行压缩
        async def do_compress():
            compressor = ContextCompressor(CompressionStrategy(strategy))
            compressed = await compressor.compress_context(
                message_objects,
                target_length=target_length,
                preserve_key_info=preserve_key_info
            )

            return compressed

        compressed = asyncio.run(do_compress())

        # 输出结果
        click.echo(click.style("📊 压缩结果:", bold=True))
        click.echo(f"原始消息数: {len(message_data)}")
        click.echo(f"压缩后消息数: {len(compressed.messages)}")
        click.echo(f"压缩比例: {compressed.compression_ratio:.1%}")
        click.echo(f"信息保留率: {compressed.information_retention:.1%}")

        click.echo(click.style("\n💬 压缩后的对话:", bold=True))
        for msg in compressed.messages:
            role_color = "green" if msg.role == "user" else "blue"
            click.echo(click.style(f"{msg.role}: ", fg=role_color, bold=True), nl=False)
            click.echo(msg.content[:100] + "..." if len(msg.content) > 100 else msg.content)

    except Exception as e:
        click.echo(click.style(f"❌ 压缩失败: {e}", fg="red"), err=True)


@context.command()
@click.option('--conversation', '-c', required=True, help='JSON格式的对话列表')
def extract_entities(conversation):
    """提取对话中的关键实体

    示例:
    llm-agent context extract-entities --conversation '[{"role":"user","content":"我叫张三"}]'
    """
    import json

    try:
        # 解析对话
        message_data = json.loads(conversation)
        message_objects = [create_message(msg['role'], msg['content']) for msg in message_data]

        # 提取实体
        async def do_extract():
            retainer = KeyInformationRetainer()
            entities = await retainer.extract_key_entities(message_objects)
            return entities

        entities = asyncio.run(do_extract())

        # 输出结果
        click.echo(click.style(f"🔍 发现 {len(entities)} 个关键实体:", bold=True))

        for entity in entities:
            click.echo(f"  • {entity.entity_type.value}: {entity.content} "
                     f"(重要性: {entity.importance:.2f}, 置信度: {entity.confidence:.2f})")

    except Exception as e:
        click.echo(click.style(f"❌ 提取失败: {e}", fg="red"), err=True)


@context.command()
@click.option('--conversation', '-c', required=True, help='JSON格式的对话列表')
@click.option('--window-size', '-w', default=8000, help='窗口大小')
def analyze_usage(conversation, window_size):
    """分析对话上下文使用情况

    示例:
    llm-agent context analyze-usage --conversation '[{"role":"user","content":"你好"}]'
    """
    import json

    try:
        # 解析对话
        message_data = json.loads(conversation)
        message_objects = [create_message(msg['role'], msg['content']) for msg in message_data]

        # 分析使用情况
        async def do_analyze():
            manager = DynamicContextManager(WindowConfig(max_window_size=window_size))
            usage = await manager.analyzer.analyze_usage(message_objects)
            return usage

        usage = asyncio.run(do_analyze())

        # 输出结果
        click.echo(click.style("📊 上下文使用分析:", bold=True))
        click.echo(f"消息总数: {usage['total_messages']}")
        click.echo(f"Token总数: {usage['total_tokens']}")
        click.echo(f"平均消息长度: {usage['average_message_length']:.1f} tokens")

        # 角色分布
        click.echo(click.style("\n👥 角色分布:", bold=True))
        for role, count in usage['role_distribution'].items():
            click.echo(f"  {role}: {count}")

        # 使用模式
        click.echo(click.style("\n🔍 使用模式:", bold=True))
        click.echo(f"  模式: {usage['usage_pattern']}")
        click.echo(f"  内存强度: {usage['memory_intensity']:.2f}")

        # 窗口利用率
        utilization = usage['total_tokens'] / window_size
        click.echo(click.style(f"\n📏 窗口利用率:", bold=True))
        click.echo(f"  {utilization:.1%} ", nl=False)
        if utilization < 0.7:
            click.echo(click.style("✅ 良好", fg="green"))
        elif utilization < 0.9:
            click.echo(click.style("⚠️  需注意", fg="yellow"))
        else:
            click.echo(click.style("❌ 需要压缩", fg="red"))

    except Exception as e:
        click.echo(click.style(f"❌ 分析失败: {e}", fg="red"), err=True)


@context.command()
@click.option('--conversation', '-c', required=True, help='JSON格式的对话列表')
def quality_report(conversation):
    """生成对话质量报告

    示例:
    llm-agent context quality-report --conversation '[{"role":"user","content":"你好"}]'
    """
    import json

    try:
        # 解析对话
        message_data = json.loads(conversation)
        message_objects = [create_message(msg['role'], msg['content']) for msg in message_data]

        # 生成质量报告
        async def do_quality():
            maintainer = MultiTurnQualityMaintainer()
            conv = Conversation(message_objects)
            report = await maintainer.maintain_quality(conv)
            return report

        report = asyncio.run(do_quality())

        # 输出结果
        click.echo(click.style("📊 对话质量报告:", bold=True))
        click.echo(f"总体质量分数: {report.overall_score:.2f} ", nl=False)
        if report.overall_score >= 0.8:
            click.echo(click.style("✅ 优秀", fg="green"))
        elif report.overall_score >= 0.6:
            click.echo(click.style("⚠️  良好", fg="yellow"))
        else:
            click.echo(click.style("❌ 需要改进", fg="red"))

        # 详细指标
        click.echo(click.style("\n📈 详细指标:", bold=True))
        metrics = [
            ("连贯性", report.metrics.coherence),
            ("上下文相关性", report.metrics.context_relevance),
            ("决策一致性", report.metrics.decision_consistency),
            ("用户满意度", report.metrics.user_satisfaction),
            ("完整性", report.metrics.completeness)
        ]

        for name, value in metrics:
            status = "✅" if value >= 0.7 else "⚠️"
            click.echo(f"  {name}: {value:.2f} {status}")

        # 建议
        if report.recommendations:
            click.echo(click.style("\n💡 改进建议:", bold=True))
            for i, rec in enumerate(report.recommendations, 1):
                click.echo(f"  {i}. {rec}")

        # 警告
        if report.warnings:
            click.echo(click.style("\n⚠️ 质量警告:", bold=True))
            for warning in report.warnings:
                click.echo(click.style(f"  • {warning}", fg="yellow"))

    except Exception as e:
        click.echo(click.style(f"❌ 质量评估失败: {e}", fg="red"), err=True)


@context.command()
def list_strategies():
    """列出可用的压缩策略"""
    strategies = {
        "intelligent": "智能混合策略，综合考虑重要性和时间",
        "importance_based": "基于内容重要性的压缩",
        "recency_based": "基于时间的新鲜度压缩",
        "hierarchical": "层级压缩，平衡各类信息"
    }

    click.echo(click.style("📋 可用的压缩策略:", bold=True))
    for name, description in strategies.items():
        click.echo(f"  • {click.style(name, bold=True)}: {description}")


@context.command()
def list_entity_types():
    """列出可保护的实体类型"""
    entity_types = {
        "user": "用户信息和身份",
        "decision": "决策和选择信息",
        "constraint": "约束条件和限制",
        "preference": "用户偏好和倾向",
        "domain": "专业术语和领域知识",
        "metadata": "元数据和配置信息"
    }

    click.echo(click.style("🏷️ 可保护的实体类型:", bold=True))
    for name, description in entity_types.items():
        click.echo(f"  • {click.style(name, bold=True)}: {description}")


# 快速测试命令
@context.command()
@click.option('--rounds', '-r', default=20, help='对话轮数')
def demo_long_conversation(rounds):
    """演示长对话场景

    生成一个指定轮数的对话，展示上下文管理效果。
    """
    import random

    click.echo(click.style(f"🚀 生成 {rounds} 轮对话演示...", bold=True))

    # 生成对话
    messages = []
    user_questions = [
        "我想学习编程",
        "应该从哪个语言开始？",
        "Python有什么优点？",
        "需要什么基础？",
        "学习周期多长？",
        "有什么好的学习资源？",
        "如何实践？",
        "遇到问题怎么办？",
        "能找到工作吗？",
        "薪资水平如何？"
    ]

    for i in range(rounds):
        # 用户消息
        user_msg = create_message("user", f"{user_questions[i % len(user_questions)]} (问题{i+1})")
        messages.append(user_msg)

        # 助手消息
        responses = [
            "很好的选择！",
            "需要坚持学习",
            "建议从基础开始",
            "多实践很重要",
            "可以参考在线教程"
        ]
        assistant_msg = create_message("assistant", f"{random.choice(responses)} (回答{i+1})")
        messages.append(assistant_msg)

    # 分析原始对话
    total_tokens = sum(msg.token_count for msg in messages)
    click.echo(f"原始对话: {len(messages)} 条消息, {total_tokens} tokens")

    # 压缩演示
    async def do_compress():
        compressor = ContextCompressor(CompressionStrategy.INTELLIGENT)
        compressed = await compressor.compress_context(
            messages,
            target_length=2000,  # 压缩到2000 tokens
            preserve_key_info=True
        )

        return compressed

    compressed = asyncio.run(do_compress())

    click.echo(f"压缩后对话: {len(compressed.messages)} 条消息")
    click.echo(f"压缩比例: {compressed.compression_ratio:.1%}")
    click.echo(f"信息保留率: {compressed.information_retention:.1%}")

    # 显示压缩前后对比
    click.echo(click.style("\n📊 效果对比:", bold=True))
    click.echo(f"对话轮次扩展: {rounds / len(compressed.messages):.1f}x")
    click.echo(f"Token效率提升: {total_tokens / sum(msg.token_count for msg in compressed.messages):.1f}x")

    # 质量评估
    async def do_quality():
        maintainer = MultiTurnQualityMaintainer()
        conv = Conversation(compressed.messages)
        report = await maintainer.maintain_quality(conv)
        return report

    quality = asyncio.run(do_quality())

    click.echo(f"对话质量: {quality.overall_score:.2f}")
    click.echo(click.style("\n✨ 上下文管理让长对话成为可能！", bold=True))


# 为现有的CLI添加集成
def add_context_commands_to_cli(cli_group):
    """将上下文管理命令添加到现有CLI组"""
    cli_group.add_command(context, name="context")
    return cli_group


# 如果直接运行此文件
if __name__ == "__main__":
    context()
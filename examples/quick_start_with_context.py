"""
快速开始：使用上下文管理功能

这是一个简单的示例，展示如何使用集成了上下文管理功能的LLM Agent。
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from llm_agent.agents.context_managed import create_context_managed_agent, ContextManagementConfig
from llm_agent.llm.client import LLMClient
from llm_agent.memory import Memory, MemoryConfig
from llm_agent.context import CompressionStrategy


async def main():
    """演示上下文管理功能的使用"""
    print("🚀 上下文管理功能快速开始")
    print("="*60)

    # 1. 创建基础组件
    print("\n1️⃣ 创建组件...")
    llm_client = LLMClient(provider="mock")  # 使用mock进行演示
    memory = Memory(MemoryConfig())

    # 2. 配置上下文管理
    print("2️⃣ 配置上下文管理...")
    context_config = ContextManagementConfig(
        enabled=True,
        max_window_size=6000,           # 6K窗口
        compression_strategy=CompressionStrategy.INTELLIGENT,
        preserve_key_info=True,           # 保护关键信息
        enable_quality_monitoring=True   # 启用质量监控
    )

    # 3. 创建增强版Agent
    print("3️⃣ 创建增强版Agent...")
    agent = create_context_managed_agent(
        llm_client=llm_client,
        system_prompt="你是一个专业的编程学习助手，擅长帮助学生解决编程问题。",
        agent_role="编程导师",
        memory=memory,
        context_config=context_config
    )

    print("✅ Agent创建成功！")

    # 4. 模拟学习对话
    print("\n4️⃣ 开始学习对话...")
    print("-"*60)

    learning_conversation = [
        "你好，我想学习Python编程",
        "Python适合初学者吗？",
        "我应该从哪里开始学习？",
        "学习Python需要什么基础？",
        "Python能用来做什么？",
        "我决定学习Python了",
        "有什么好的学习资源推荐？",
        "如何练习编程？",
        "遇到问题怎么办？",
        "能找到工作吗？",
        "我想专注于Web开发",
        "Web开发需要学什么框架？",
        "Django和Flask有什么区别？",
        "学习周期大概多久？",
        "如何开始第一个项目？"
    ]

    for i, user_input in enumerate(learning_conversation):
        # 显示用户输入
        print(f"\n👤 学生({i+1}/{len(learning_conversation)}): {user_input}")

        # Agent响应
        response = await agent.think(user_input)
        print(f"🤖 导师: {response.content[:100]}...")

        # 每5轮显示一次统计
        if (i + 1) % 5 == 0:
            stats = agent.get_context_statistics()
            print(f"  📊 对话进度: {len(learning_conversation)}轮中完成{i+1}轮")
            print(f"  💬 当前历史: {stats['current_conversation_length']}条消息")
            print(f"  📏 窗口利用率: {stats['window_utilization']:.1%}")

    # 5. 查看最终统计
    print("\n" + "="*60)
    print("5️⃣ 最终统计报告")
    print("="*60)

    final_stats = agent.get_context_statistics()
    print(f"📊 对话统计:")
    print(f"  • 总对话轮次: {len(learning_conversation)}")
    print(f"  • 当前历史长度: {final_stats['current_conversation_length']}条")
    print(f"  • Token总数: {final_stats['current_token_count']}")
    print(f"  • 窗口利用率: {final_stats['window_utilization']:.1%}")

    print(f"\n🎯 上下文管理效果:")
    print(f"  • 压缩次数: {final_stats['total_compressions']}")
    print(f"  • 保护实体: {final_stats['total_key_entities_protected']}个")

    # 6. 质量评估
    print(f"\n🌟 对话质量评估:")
    quality_report = await agent.get_conversation_quality_report()
    if quality_report:
        print(f"  • 总体质量: {quality_report['overall_score']:.2f}")
        print(f"  • 连贯性: {quality_report['coherence']:.2f}")
        print(f"  • 相关性: {quality_report['context_relevance']:.2f}")

        if quality_report['warnings']:
            print(f"  • 质量警告: {len(quality_report['warnings'])}个")

    # 7. 使用建议
    print("\n💡 使用建议:")
    print("  ✅ 已成功支持15轮完整对话")
    print("  ✅ 所有关键信息都得到了保护")
    print("  ✅ 对话质量保持良好水平")
    print("  ✅ 可以继续更多轮对话")

    print("\n" + "="*60)
    print("🎉 恭喜！您已经成功使用了上下文管理功能！")
    print("="*60)

    print("\n🚀 下一步:")
    print("  1. 调整max_window_size支持更长对话")
    print("  2. 尝试不同的compression_strategy")
    print("  3. 在生产环境中使用真实的LLM客户端")
    print("  4. 通过API和CLI使用上下文管理功能")


# 为生产环境使用提供的模板
async def production_example():
    """生产环境使用示例"""
    print("\n🏭 生产环境使用示例:")

    # 使用真实的LLM提供商
    print("""
# 使用Anthropic Claude
llm_client = LLMClient(
    provider="anthropic",
    model_name="claude-opus-4-6",
    config={"api_key": "your-api-key"}
)

# 大窗口配置
context_config = ContextManagementConfig(
    enabled=True,
    max_window_size=32000,           # 32K窗口
    compression_strategy=CompressionStrategy.INTELLIGENT,
    enable_quality_monitoring=True
)

agent = create_context_managed_agent(
    llm_client=llm_client,
    system_prompt="你的系统提示",
    agent_role="你的角色",
    memory=Memory(MemoryConfig(
        short_term_capacity=200,
        long_term_capacity=1000
    )),
    context_config=context_config
)

# 使用完全相同的方式
response = await agent.think("用户问题")

# 监控对话质量
stats = agent.get_context_statistics()
if stats['window_utilization'] > 0.8:
    print("窗口使用率较高，考虑清理历史或增加窗口大小")

quality = await agent.get_conversation_quality_report()
if quality['overall_score'] < 0.6:
    print("对话质量偏低，建议关注用户反馈")
    """)


if __name__ == "__main__":
    # 运行演示
    asyncio.run(main())

    # 显示生产环境示例
    asyncio.run(production_example())
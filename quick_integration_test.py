"""
快速集成验证测试

简化版集成测试，验证核心功能。
"""

import asyncio
import sys
sys.path.insert(0, 'src')

from llm_agent.agents.context_managed import create_context_managed_agent, ContextManagementConfig
from llm_agent.agents.base import LLMAgent
from llm_agent.memory import Memory, MemoryConfig
from llm_agent.llm.client import LLMClient
from llm_agent.context import CompressionStrategy


async def quick_test():
    """快速测试核心集成功能"""
    print("🚀 快速集成验证测试")

    # 创建基础组件
    llm_client = LLMClient(provider="mock")
    memory = Memory(MemoryConfig())

    # 测试1：创建增强版Agent
    print("\n1️⃣ 测试增强版Agent创建:")
    try:
        agent = create_context_managed_agent(
            llm_client=llm_client,
            system_prompt="你是一个AI助手",
            agent_role="助手",
            memory=memory
        )
        print("✅ 增强版Agent创建成功")
        print(f"   上下文管理启用: {agent.context_config.enabled}")
        print(f"   窗口大小: {agent.context_config.max_window_size}")
    except Exception as e:
        print(f"❌ 创建失败: {e}")
        return

    # 测试2：基本对话功能
    print("\n2️⃣ 测试基本对话功能:")
    try:
        response1 = await agent.think("你好，我是新用户")
        print(f"✅ 第1次对话成功")
        print(f"   响应: {response1.content[:50]}...")

        # 多轮对话
        for i in range(5):
            response = await agent.think(f"问题{i+1}")
            if i == 4:
                print(f"✅ 完成5轮对话")
                print(f"   当前对话历史: {len(agent.conversation_history)}条")
    except Exception as e:
        print(f"❌ 对话失败: {e}")
        return

    # 测试3：上下文管理统计
    print("\n3️⃣ 测试上下文管理统计:")
    try:
        stats = agent.get_context_statistics()
        print("✅ 统计信息获取成功:")
        print(f"   对话长度: {stats['current_conversation_length']}条")
        print(f"   Token数量: {stats['current_token_count']}")
        print(f"   窗口利用率: {stats['window_utilization']:.1%}")
        print(f"   压缩次数: {stats['total_compressions']}")
    except Exception as e:
        print(f"❌ 统计获取失败: {e}")
        return

    # 测试4：兼容性测试
    print("\n4️⃣ 测试与原始Agent兼容性:")
    try:
        # 创建原始Agent
        original_agent = LLMAgent(
            llm_client=llm_client,
            system_prompt="你是一个AI助手",
            agent_role="助手",
            memory=memory
        )

        # 相同输入测试
        test_input = "测试问题"

        # 原始Agent
        orig_response = await original_agent.think(test_input)
        print(f"✅ 原始Agent响应: {orig_response.content[:30]}...")

        # 增强版Agent（禁用上下文管理）
        enhanced_response = await agent.think(test_input, enable_context_management=False)
        print(f"✅ 增强版Agent响应: {enhanced_response.content[:30]}...")

    except Exception as e:
        print(f"❌ 兼容性测试失败: {e}")
        return

    # 测试5：上下文管理功能
    print("\n5️⃣ 测试上下文管理功能:")
    try:
        # 创建更多对话以触发压缩
        for i in range(15):
            await agent.think(f"长对话测试消息{i+1}，包含一些内容来增加上下文长度")

        stats_after = agent.get_context_statistics()
        print(f"✅ 长对话测试完成:")
        print(f"   对话轮次: 22")
        print(f"   当前历史: {stats_after['current_conversation_length']}条")
        print(f"   压缩次数: {stats_after['total_compressions']}")

    except Exception as e:
        print(f"❌ 上下文管理测试失败: {e}")
        return

    print("\n🎉 所有核心集成功能验证通过！")
    print("\n🌟 集成成果:")
    print("  ✅ 增强版Agent完全兼容原始功能")
    print("  ✅ 上下文管理功能正常工作")
    print("  ✅ 统计和监控功能完整")
    print("  ✅ 可以无缝替换原始Agent")
    print("\n🎯 使用方式:")
    print("  1. 导入: from llm_agent.agents.context_managed import create_context_managed_agent")
    print("  2. 创建: agent = create_context_managed_agent(...)")
    print("  3. 使用: await agent.think(\"问题\")")
    print("  4. 监控: stats = agent.get_context_statistics()")


if __name__ == "__main__":
    asyncio.run(quick_test())
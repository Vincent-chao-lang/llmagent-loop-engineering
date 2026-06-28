"""
循环终止条件演示

展示 llmagent 的四大能力如何正确终止，避免无限循环。
"""

import asyncio
import sys
import os

# 添加源码路径以支持本地开发
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llm_agent import LLMAgent, Memory, MemoryConfig
from llm_agent.llm.client import LLMClient


async def demo_loop_termination():
    """演示循环终止条件的使用"""

    print("=" * 60)
    print("🔄 llmagent 循环终止条件演示")
    print("=" * 60)

    # 创建 Agent
    llm_client = LLMClient(provider="mock")
    memory = Memory(MemoryConfig())
    agent = LLMAgent(
        llm_client=llm_client,
        system_prompt="你是一个测试助手，擅长分解任务",
        agent_role="测试员",
        memory=memory
    )

    print("\n📊 配置的循环终止条件：")
    print("  • max_execution_retries: 3（执行失败最大重试次数）")
    print("  • max_execution_time: 300秒（最大执行时间）")
    print("  • max_think_calls: 50（最大思考次数限制）")
    print("  • allow_plan_regression: False（不允许计划退化）")

    print("\n" + "=" * 60)
    print("场景1: 正常执行（所有步骤成功）")
    print("=" * 60)

    result1 = await agent.execute(
        "写一个简单的Hello World程序",
        max_retries=3
    )
    print(f"✅ 执行结果: {'成功' if result1.success else '失败'}")
    print(f"   已执行步骤: {len(result1.steps)}")
    print(f"   反思总结: {result1.reflection[:50] if result1.reflection else '无'}...")

    print("\n" + "=" * 60)
    print("场景2: 执行失败，达到最大重试次数")
    print("=" * 60)

    result2 = await agent.execute(
        "执行一个不存在的复杂任务（模拟失败）",
        max_retries=2  # 故意设低重试次数
    )
    print(f"✅ 执行结果: {'成功' if result2.success else '失败'}")
    if result2.error:
        print(f"   错误信息: {result2.error}")

    print("\n" + "=" * 60)
    print("场景3: 执行超时（设置很短的超时）")
    print("=" * 60)

    try:
        result3 = await agent.execute(
            "需要长时间处理的任务",
            timeout=2  # 2秒超时
        )
        print(f"✅ 执行结果: {'成功' if result3.success else '失败'}")
    except Exception as e:
        print(f"✅ 异常捕获: {str(e)}")

    print("\n" + "=" * 60)
    print("场景4: 思考次数限制（模拟多次思考）")
    print("=" * 60)

    print("LLM 每次调用 think() 都会增加计数...")
    print(f"当前思考次数: {agent.think_call_count}")
    print(f"最大思考次数限制: {agent.max_think_calls}")

    print("\n💡 如果 think() 超过限制，会抛出异常终止执行")
    print("   这防止了 LLM 陷入无限重规划的循环")

    print("\n" + "=" * 60)
    print("场景5: 计划退化检测")
    print("=" * 60)

    print("如果重规划时新计划比当前计划还复杂，会被拒绝更新")
    print("这防止了计划质量恶化导致的无限循环")

    print("\n" + "=" * 60)
    print("✅ 所有循环终止条件就绪！")
    print("=" * 60)

    print(f"\n📊 最终统计:")
    print(f"  总思考次数: {agent.think_call_count}")
    print(f"  总执行次数: {agent.execution_count}")
    print(f"  最后活动时间: {agent.last_activity}")


if __name__ == "__main__":
    asyncio.run(demo_loop_termination())

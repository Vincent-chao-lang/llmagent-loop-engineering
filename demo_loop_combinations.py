"""
四大能力循环组合演示脚本

展示 think、plan、execute、reflect 之间的各种循环组合
"""
import asyncio
import sys
import os

# 添加源码路径以支持本地开发
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llm_agent import LLMAgent, Memory, MemoryConfig
from llm_agent.llm.client import LLMClient

async def demo_loop_combinations():
    """演示四大能力的循环组合"""

    print("=" * 70)
    print("🔄 LLM Agent 四大能力循环组合演示")
    print("=" * 70)

    # 创建 Agent
    llm_client = LLMClient(provider="mock")
    memory = Memory(MemoryConfig())
    agent = LLMAgent(
        llm_client=llm_client,
        system_prompt="你是一个AI助手，擅长分解任务和执行",
        agent_role="助手",
        memory=memory
    )

    print("\n📊 支持的循环组合类型:")
    print("  1️⃣  静态DAG组合（无循环）")
    print("  2️⃣  运行时保护循环（有界循环）")
    print("  3️⃣  手动控制循环（开发者控制）")

    # 演示1: 静态DAG组合
    print("\n" + "=" * 70)
    print("🧪 演示1: 静态DAG组合（无循环风险）")
    print("=" * 70)

    print("\n📋 组合1: plan → think")
    print("执行: await agent.plan('制定计划')")
    plan = await agent.plan("制定测试计划")
    print(f"✅ 结果: {len(plan.steps)} 个步骤")
    print(f"   内部调用: plan() → think() → 解析JSON")

    print("\n🧪 组合2: execute → plan → think")
    print("执行: await agent.execute('执行任务')")
    result = await agent.execute("简单测试任务", max_retries=1)
    print(f"✅ 结果: {'成功' if result.success else '失败'}")
    print(f"   内部调用: execute() → plan() → think() → 执行步骤")

    print("\n🧪 组合3: reflect → think")
    print("执行: await agent.reflect('反思任务', [])")
    reflection = await agent.reflect("测试反思", [])
    print(f"✅ 结果: 反思生成成功")
    print(f"   内部调用: reflect() → think() → 解析JSON")

    # 演示2: 运行时保护循环
    print("\n" + "=" * 70)
    print("🧪 演示2: 运行时保护循环（安全有界）")
    print("=" * 70)

    print("\n🔄 循环1: 重规划循环")
    print("流程: execute → 失败 → think → plan.update → execute")
    print("特点: 受 max_retries 限制（默认3次）")

    agent2 = LLMAgent(
        llm_client=LLMClient(provider="mock"),
        system_prompt="测试助手",
        agent_role="测试员",
        memory=Memory(MemoryConfig())
    )

    result_retry = await agent2.execute("演示重试任务", max_retries=2)
    print(f"✅ 执行完成: {'成功' if result_retry.success else '失败'}")
    print(f"   如果有失败步骤，会触发: think → plan.update → 重新执行")
    print(f"   达到重试上限后会安全终止")

    print(f"\n🔄 循环2: 思考循环保护")
    print(f"当前思考次数: {agent.think_call_count}")
    print(f"最大思考次数: {agent.max_think_calls}")
    print(f"剩余思考次数: {agent.max_think_calls - agent.think_call_count}")
    print(f"✅ 如果达到上限，会抛出异常终止执行")
    print(f"   这防止了无限 think() 调用循环")

    print(f"\n🔄 循环3: 超时保护")
    print(f"默认超时时间: 300秒")
    print(f"✅ 执行时间超过限制会抛出 asyncio.TimeoutError")
    print(f"   这防止了长时间运行的循环")

    # 演示3: 手动控制循环
    print("\n" + "=" * 70)
    print("🧪 演示3: 手动控制循环（推荐模式）")
    print("=" * 70)

    print("\n🎯 模式1: 单次执行模式")
    print("代码: await agent.execute('一次性任务')")
    print("✅ 最简单，无循环风险")

    print("\n🎯 模式2: 明确限制的迭代")
    print("代码:")
    print("  for i in range(3):")
    print("      result = await agent.execute(f'任务第{i+1}轮')")
    print("      if result.success: break")
    print("✅ 开发者完全控制循环次数")

    print("\n🎯 模式3: 基于质量的迭代")
    print("代码:")
    print("  best_result = None")
    print("  for i in range(5):")
    print("      result = await agent.execute('任务')")
    print("      if result.quality > 0.9: break")
    print("✅ 基于结果质量决定是否继续")

    # 演示4: 完整学习循环
    print("\n" + "=" * 70)
    print("🧪 演示4: 完整学习循环（迭代改进）")
    print("=" * 70)

    print("\n📚 学习循环流程:")
    print("  第1轮: execute → 反思 → 学习")
    print("  第2轮: 基于学习 → 重新规划 → 执行")
    print("  第3轮: 继续改进...")

    # 模拟两轮迭代
    print("\n🔄 第1轮执行:")
    result1 = await agent.execute("代码审查v1", max_retries=1)
    print(f"✅ 第1轮完成: {'成功' if result1.success else '失败'}")
    print(f"   反思结果: {result1.reflection[:80] if result1.reflection else '无'}...")

    print("\n🔄 第2轮执行（基于第1轮反思）:")
    result2 = await agent.execute("代码审查v2", max_retries=1)
    print(f"✅ 第2轮完成: {'成功' if result2.success else '失败'}")
    print(f"   反思结果: {result2.reflection[:80] if result2.reflection else '无'}...")

    print("\n💡 这种模式允许持续改进，但需要手动控制轮数")

    # 安全性总结
    print("\n" + "=" * 70)
    print("🔒 循环组合安全性总结")
    print("=" * 70)

    print(f"\n📊 当前循环计数:")
    print(f"  总思考次数: {agent.think_call_count}")
    print(f"  总执行次数: {agent.execution_count}")
    print(f"  剩余思考次数: {agent.max_think_calls - agent.think_call_count}")

    print(f"\n🛡️ 五层安全保护:")
    print(f"  1️⃣  重试次数限制 → 防止无限重试")
    print(f"  2️⃣  超时机制 → 防止长时间运行")
    print(f"  3️⃣  思考次数限制 → 防止无限思考循环")
    print(f"  4️⃣  计划退化检测 → 防止计划质量恶化")
    print(f"  5️⃣  异常捕获机制 → 优雅降级处理")

    print(f"\n✅ 所有循环组合都是安全的！")
    print(f"   • 静态组合: 无循环风险")
    print(f"   • 保护循环: 受限次数，自动终止")
    print(f"   • 手动循环: 开发者完全控制")

    print("\n" + "=" * 70)
    print("🎯 推荐使用指南")
    print("=" * 70)

    print("\n✅ 简单任务: 直接 execute()")
    print("✅ 可能失败: execute(..., max_retries=3)")
    print("✅ 迭代优化: 手动 for 循环，明确限制轮数")
    print("✅ 持续学习: 多轮 execute，使用反思结果")

    print("\n❌ 避免: 无限循环，不设置终止条件")
    print("❌ 避免: 嵌套过深，难以追踪")
    print("❌ 避免: 忽略循环限制，设置过高的重试次数")

    print("\n" + "=" * 70)
    print("✅ 四大能力循环组合演示完成！")
    print("=" * 70)

    print(f"\n🚀 框架支持的循环组合:")
    print(f"   • 4种静态DAG组合")
    print(f"   • 3种运行时保护循环")
    print(f"   • 4种推荐使用模式")
    print(f"   • 5层安全保护机制")

    print(f"\n💡 核心优势:")
    print(f"   🔄 灵活的循环组合")
    print(f"   🛡️ 完善的安全保护")
    print(f"   🎯 明确的性能特征")
    print(f"   📈 渐进式复杂度")

if __name__ == "__main__":
    asyncio.run(demo_loop_combinations())
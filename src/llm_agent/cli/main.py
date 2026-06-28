"""
LLM Agent CLI 命令行工具
"""

import asyncio
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console

from llm_agent.agents.base import LLMAgent
from llm_agent.llm.client import LLMClient
from llm_agent.memory.memory import Memory, MemoryConfig

console = Console()


@click.group()
@click.version_option(version=lambda: __import__("llm_agent").__version__)
@click.option("--provider", default="mock", help="LLM提供商 (mock/anthropic/openai)")
@click.option("--model", default=None, help="模型名称")
@click.option("--api-key", default=None, help="API密钥")
@click.pass_context
def cli(ctx, provider: str, model: Optional[str], api_key: Optional[str]):
    """LLM Agent框架 - 命令行工具

    智能Agent框架，具备思考、规划、执行、反思等AI能力。
    """
    ctx.ensure_object(dict)
    ctx.obj["provider"] = provider
    ctx.obj["model"] = model
    ctx.obj["api_key"] = api_key


def create_agent(ctx) -> LLMAgent:
    """创建Agent实例"""
    provider = ctx.obj.get("provider", "mock")
    model = ctx.obj.get("model")
    api_key = ctx.obj.get("api_key")

    config = {}
    if api_key:
        config["api_key"] = api_key

    llm_client = LLMClient(
        provider=provider,
        model_name=model or "llm-agent-model",
        config=config if config else None,
    )

    memory = Memory(MemoryConfig())

    agent = LLMAgent(
        llm_client=llm_client,
        system_prompt="你是一个智能助手，擅长分析问题和执行任务。",
        agent_role="助手",
        memory=memory,
    )

    return agent


@cli.command()
@click.argument("question")
@click.pass_context
def think(ctx, question: str):
    """思考问题

    示例: llm-agent think "什么是递归？"
    """
    agent = create_agent(ctx)

    async def _think():
        with console.status("[bold green]Agent思考中...", spinner="dots"):
            response = await agent.think(question)

        console.print(f"\n[bold cyan]思考结果:[/bold cyan]")
        console.print(f"{response.content}\n")
        console.print(f"[dim]置信度: {response.confidence:.2f}[/dim]")

    asyncio.run(_think())


@cli.command()
@click.argument("goal")
@click.pass_context
def plan(ctx, goal: str):
    """制定计划

    示例: llm-agent plan "构建一个Web爬虫"
    """
    agent = create_agent(ctx)

    async def _plan():
        with console.status("[bold green]Agent规划中...", spinner="dots"):
            plan_result = await agent.plan(goal)

        console.print(f"\n[bold cyan]执行计划:[/bold cyan]")
        console.print(f"目标: {plan_result.goal}\n")
        console.print(f"[bold]步骤:[/bold]")
        for i, step in enumerate(plan_result.steps, 1):
            step_desc = step.get("description", str(step))
            console.print(f"  {i}. {step_desc}")
        console.print(f"\n[dim]预估时间: {plan_result.estimated_time}秒[/dim]")

    asyncio.run(_plan())


@cli.command()
@click.argument("task")
@click.pass_context
def execute(ctx, task: str):
    """执行任务

    示例: llm-agent execute "分析用户行为数据"
    """
    agent = create_agent(ctx)

    async def _execute():
        with console.status("[bold green]Agent执行中...", spinner="dots"):
            result = await agent.execute(task)

        status = "[bold green]✓[/bold green]" if result.success else "[bold red]✗[/bold red]"
        console.print(f"\n{status} 执行状态: {'成功' if result.success else '失败'}\n")

        if result.steps:
            console.print("[bold cyan]执行步骤:[/bold cyan]")
            for i, step in enumerate(result.steps, 1):
                console.print(f"  步骤 {i}: {step}")

        if result.reflection:
            console.print(f"\n[bold cyan]反思总结:[/bold cyan]")
            console.print(f"{result.reflection}")

        if result.error:
            console.print(f"\n[bold red]错误:[/bold red] {result.error}")

    asyncio.run(_execute())


@cli.command()
@click.option("--host", default="0.0.0.0", help="服务地址")
@click.option("--port", default=8000, type=int, help="服务端口")
@click.option("--reload", is_flag=True, help="自动重载")
def server(host: str, port: int, reload: bool):
    """启动API服务

    示例: llm-agent server --host 0.0.0.0 --port 8000
    """
    import uvicorn

    console.print(
        f"[bold green]启动 LLM Agent API 服务[/bold green]"
        f" - http://{host}:{port}"
    )
    console.print("[dim]按 Ctrl+C 停止服务[/dim]\n")

    try:
        uvicorn.run(
            "llm_agent.api.app:app",
            host=host,
            port=port,
            reload=reload,
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]服务已停止[/yellow]")


if __name__ == "__main__":
    cli(obj={})

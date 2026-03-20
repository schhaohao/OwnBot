from __future__ import annotations

import asyncio
import signal
import sys
from pathlib import Path

import typer
from loguru import logger

# Import and setup logging first
from ownbot.utils.logger import console, setup_logging

setup_logging()

from ownbot.agent import AgentLoop
from ownbot.bus import MessageBus
from ownbot.channels import ChannelManager
from ownbot.config import AppConfig, get_config_path, load_config, save_config, set_config_path

app = typer.Typer(no_args_is_help=True)


@app.command()
def onboard() -> None:
    """初始化配置文件（~/.ownbot/config.json）。-"""
    path = save_config(AppConfig())
    console.print(f"[green]已生成配置：{path}[/green]")
    console.print(
        "[yellow]下一步：编辑 telegram.token / telegram.allowFrom / llm.apiKey 等字段，然后运行：ownbot gateway[/yellow]"
    )


@app.command()
def gateway(
    config: str | None = typer.Option(
        None, "--config", "-c", help="配置文件路径（默认 ~/.ownbot/config.json）"
    ),
) -> None:
    """启动 gateway（Telegram + AgentLoop）。"""
    if config:
        set_config_path(Path(config).expanduser().resolve())

    cfg = load_config()
    bus = MessageBus()
    agent = AgentLoop(cfg=cfg, bus=bus)
    channel_manager = ChannelManager(cfg, bus)
    channel_manager.setup_channels()

    async def _run() -> None:
        logger.info("Config: {}", get_config_path())
        try:
            await asyncio.gather(
                agent.run(),
                channel_manager.start_all(),
            )
        finally:
            # Cleanup MCP connections
            await agent.cleanup()

    asyncio.run(_run())


@app.command()
def channels(
    action: str = typer.Argument(..., help="操作：login / status"),
    channel: str = typer.Option(None, "--channel", "-c", help="通道名称，如 whatsapp"),
    config: str | None = typer.Option(
        None, "--config", "-f", help="配置文件路径（默认 ~/.ownbot/config.json）"
    ),
) -> None:
    """管理通道，如登录 WhatsApp。"""
    if config:
        set_config_path(Path(config).expanduser().resolve())

    cfg = load_config()
    bus = MessageBus()

    if action == "login":
        if channel == "whatsapp":
            from ownbot.channels.whatsapp import WhatsAppChannel

            whatsapp = WhatsAppChannel(cfg.whatsapp, bus)

            console.print("[yellow]正在启动 WhatsApp 登录流程...[/yellow]")
            console.print("[yellow]请确保已安装 Node.js 和 npm[/yellow]")
            console.print()

            # Setup signal handler for graceful shutdown
            def signal_handler(sig, frame):
                console.print("\n[yellow]正在停止...[/yellow]")
                asyncio.create_task(whatsapp.stop())
                sys.exit(0)

            signal.signal(signal.SIGINT, signal_handler)

            try:
                asyncio.run(whatsapp.start())
            except KeyboardInterrupt:
                console.print("\n[yellow]登录流程已取消[/yellow]")
        else:
            console.print("[red]错误：请指定 --channel whatsapp[/red]")
    elif action == "status":
        console.print(
            "[green]Telegram: {}[/green]".format("enabled" if cfg.telegram.enabled else "disabled")
        )
        console.print(
            "[green]WhatsApp: {}[/green]".format("enabled" if cfg.whatsapp.enabled else "disabled")
        )
    else:
        console.print(f"[red]错误：未知操作 {action}[/red]")


@app.command()
def index_skills(
    force: bool = typer.Option(False, "--force", "-f", help="强制重建索引"),
    config: str | None = typer.Option(
        None, "--config", "-c", help="配置文件路径（默认 ~/.ownbot/config.json）"
    ),
) -> None:
    """构建 Skill 向量索引（用于 RAG 检索）。"""
    if config:
        set_config_path(Path(config).expanduser().resolve())

    cfg = load_config()

    if not cfg.retrieval.enabled:
        console.print(
            "[yellow]警告：RAG 检索未启用，请在配置中设置 retrieval.enabled = true[/yellow]"
        )
        return

    from ownbot.agent.context import ContextBuilder

    try:
        context = ContextBuilder(
            workspace=cfg.workspace_path,
            enable_rag=True,
            use_milvus_lite=cfg.retrieval.use_milvus_lite,
            milvus_host=cfg.retrieval.milvus_host,
            milvus_port=cfg.retrieval.milvus_port,
            milvus_db_path=cfg.retrieval.milvus_db_path,
            embedding_model=cfg.retrieval.embedding_model,
        )

        console.print("[green]正在构建 Skill 索引...[/green]")
        count = context.build_index(force_rebuild=force)
        console.print(f"[green]成功索引 {count} 个 Skills[/green]")

    except Exception as e:
        console.print(f"[red]错误：{e}[/red]")
        logger.exception("Failed to build skill index")

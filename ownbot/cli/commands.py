from __future__ import annotations

import asyncio
import signal
import sys
from pathlib import Path

import typer
from loguru import logger

# Import and setup logging first
from ownbot.utils.logger import setup_logging, console
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
    console.print('[yellow]下一步：编辑 telegram.token / telegram.allowFrom / llm.apiKey 等字段，然后运行：ownbot gateway[/yellow]')


@app.command()
def gateway(
    config: str | None = typer.Option(None, "--config", "-c", help="配置文件路径（默认 ~/.ownbot/config.json）"),
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
        await asyncio.gather(
            agent.run(),
            channel_manager.start_all(),
        )

    asyncio.run(_run())


@app.command()
def channels(
    action: str = typer.Argument(..., help="操作：login / status"),
    channel: str = typer.Option(None, "--channel", "-c", help="通道名称，如 whatsapp"),
    config: str | None = typer.Option(None, "--config", "-f", help="配置文件路径（默认 ~/.ownbot/config.json）"),
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
        console.print("[green]Telegram: {}[/green]".format("enabled" if cfg.telegram.enabled else "disabled"))
        console.print("[green]WhatsApp: {}[/green]".format("enabled" if cfg.whatsapp.enabled else "disabled"))
    else:
        console.print("[red]错误：未知操作 {}[/red]".format(action))

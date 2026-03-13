from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from loguru import logger

from ownbot.agent import AgentLoop
from ownbot.bus import MessageBus
from ownbot.channels import ChannelManager
from ownbot.config import AppConfig, get_config_path, load_config, save_config, set_config_path

app = typer.Typer(no_args_is_help=True)


@app.command()
def onboard() -> None:
    """初始化配置文件（~/.ownbot/config.json）。"""
    path = save_config(AppConfig())
    typer.echo(f"已生成配置：{path}")
    typer.echo('下一步：编辑 telegram.token / telegram.allowFrom / llm.apiKey 等字段，然后运行：ownbot gateway')


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


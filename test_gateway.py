#!/usr/bin/env python3

import asyncio
from ownbot.agent import AgentLoop
from ownbot.bus import MessageBus
from ownbot.channels import ChannelManager
from ownbot.config import AppConfig

async def test_gateway():
    """Test the gateway functionality."""
    # Create a minimal config
    cfg = AppConfig()
    cfg.telegram.enabled = True
    # You would normally set these values in the config file
    # cfg.telegram.token = "YOUR_TELEGRAM_BOT_TOKEN"
    # cfg.telegram.allow_from = ["*"]
    # cfg.llm.api_key = "YOUR_OPENAI_API_KEY"
    
    bus = MessageBus()
    agent = AgentLoop(cfg=cfg, bus=bus)
    channel_manager = ChannelManager(cfg, bus)
    channel_manager.setup_channels()
    
    print("Gateway test initialized successfully!")
    print("To use this with Telegram, please:")
    print("1. Edit ~/.ownbot/config.json and set your Telegram bot token")
    print("2. Set your OpenAI API key in the config")
    print("3. Run: ownbot gateway")

if __name__ == "__main__":
    asyncio.run(test_gateway())

from __future__ import annotations

import asyncio
from typing import Dict, List, Optional

from loguru import logger

from ownbot.bus.events import OutboundMessage
from ownbot.bus.queue import MessageBus
from ownbot.channels.base import BaseChannel
from ownbot.channels.telegram import TelegramChannel
from ownbot.channels.whatsapp import WhatsAppChannel
from ownbot.config.schema import AppConfig


class ChannelManager:
    """
    Manages all chat channels and dispatches outbound messages.
    """

    def __init__(self, config: AppConfig, bus: MessageBus):
        """
        Initialize the channel manager.

        Args:
            config: The application configuration.
            bus: The message bus for communication.
        """
        self.config = config
        self.bus = bus
        self.channels: Dict[str, BaseChannel] = {}
        self._tasks: List[asyncio.Task] = []

    def setup_channels(self) -> None:
        """Set up all enabled channels."""
        # Telegram channel
        if self.config.telegram.enabled:
            telegram_channel = TelegramChannel(self.config.telegram, self.bus)
            self.channels[telegram_channel.name] = telegram_channel
            logger.info("Telegram channel enabled")

        # WhatsApp channel
        if self.config.whatsapp.enabled:
            whatsapp_channel = WhatsAppChannel(self.config.whatsapp, self.bus)
            self.channels[whatsapp_channel.name] = whatsapp_channel
            logger.info("WhatsApp channel enabled")

        # Add other channels here as needed

    async def start_all(self) -> None:
        """Start all enabled channels."""
        for channel in self.channels.values():
            task = asyncio.create_task(channel.start())
            self._tasks.append(task)
            logger.info(f"Started {channel.display_name} channel")
        
        # Start message bus consumer
        consumer_task = asyncio.create_task(self._consume_outbound_messages())
        self._tasks.append(consumer_task)
        logger.info("Started message bus consumer")
    
    async def _consume_outbound_messages(self) -> None:
        """Consume outbound messages from the message bus and dispatch them to channels."""
        while True:
            try:
                msg = await self.bus.consume_outbound()
                await self.dispatch(msg)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error consuming outbound message: {e}")
                await asyncio.sleep(1)

    async def stop_all(self) -> None:
        """Stop all channels."""
        for channel in self.channels.values():
            await channel.stop()
            logger.info(f"Stopped {channel.display_name} channel")

        # Cancel all tasks
        for task in self._tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    async def dispatch(self, msg: OutboundMessage) -> None:
        """
        Dispatch an outbound message to the appropriate channel.

        Args:
            msg: The message to dispatch.
        """
        if msg.channel in self.channels:
            try:
                await self.channels[msg.channel].send(msg)
            except Exception as e:
                logger.error(f"Error sending message to {msg.channel}: {e}")
        else:
            logger.warning(f"Unknown channel: {msg.channel}")

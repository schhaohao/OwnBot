from __future__ import annotations

import asyncio

from loguru import logger

from ownbot.bus import InboundMessage, MessageBus, OutboundMessage
from ownbot.config import AppConfig
from ownbot.llm import OpenAICompatibleClient


class AgentLoop:
    """MVP: inbound -> LLM -> outbound."""

    def __init__(self, *, cfg: AppConfig, bus: MessageBus):
        self.cfg = cfg
        self.bus = bus
        self._running = False
        self._lock = asyncio.Lock()
        self._llm = OpenAICompatibleClient(cfg.llm)

    def stop(self) -> None:
        self._running = False

    async def run(self) -> None:
        self._running = True
        logger.info("Agent loop started")
        while self._running:
            try:
                msg = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            asyncio.create_task(self._dispatch(msg))

    async def _dispatch(self, msg: InboundMessage) -> None:
        async with self._lock:
            text = msg.content.strip()
            if not text:
                return
            logger.info(
                "Processing inbound chat_id={}, sender_id={}, len={}",
                msg.chat_id,
                msg.sender_id,
                len(text),
            )
            reply = await self._llm.chat(text)
            await self.bus.publish_outbound(OutboundMessage(chat_id=msg.chat_id, content=reply))


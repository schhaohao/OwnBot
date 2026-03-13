 from __future__ import annotations
 
 import asyncio
 from dataclasses import dataclass, field
 
 
 @dataclass(frozen=True)
 class InboundMessage:
     chat_id: str
     sender_id: str
     content: str
     is_group: bool = False
     metadata: dict = field(default_factory=dict)
 
 
 @dataclass(frozen=True)
 class OutboundMessage:
     chat_id: str
     content: str
     metadata: dict = field(default_factory=dict)
 
 
 class MessageBus:
     def __init__(self) -> None:
         self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
         self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()
 
     async def publish_inbound(self, msg: InboundMessage) -> None:
         await self.inbound.put(msg)
 
     async def consume_inbound(self) -> InboundMessage:
         return await self.inbound.get()
 
     async def publish_outbound(self, msg: OutboundMessage) -> None:
         await self.outbound.put(msg)
 
     async def consume_outbound(self) -> OutboundMessage:
         return await self.outbound.get()
 

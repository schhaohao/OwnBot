"""Message bus implementation for OwnBot.

Provides asynchronous message queues for decoupling message reception
from processing and response generation from delivery.
"""

from __future__ import annotations

import asyncio

from ownbot.bus.events import InboundMessage, OutboundMessage


class MessageBus:
    """Async message bus for decoupling channels from the agent core.

    The message bus provides two queues:
    - inbound: Messages from channels to the agent
    - outbound: Responses from the agent to channels

    This decoupling allows channels and the agent to operate at different
    speeds and handle backpressure gracefully.

    Example:
        bus = MessageBus()

        # In a channel handler
        await bus.publish_inbound(InboundMessage(...))

        # In the agent
        msg = await bus.consume_inbound()
        response = process(msg)
        await bus.publish_outbound(OutboundMessage(...))

        # In channel sender
        response = await bus.consume_outbound()
        await channel.send(response)
    """

    def __init__(self, maxsize: int = 0) -> None:
        """Initialize the message bus.

        Args:
            maxsize: Maximum queue size (0 = unlimited)
        """
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue(maxsize=maxsize)
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue(maxsize=maxsize)

    async def publish_inbound(self, message: InboundMessage) -> None:
        """Publish a message from a channel to the inbound queue.

        Args:
            message: The inbound message to queue.

        Raises:
            asyncio.QueueFull: If the queue is full and has a maxsize.
        """
        await self.inbound.put(message)

    async def consume_inbound(self) -> InboundMessage:
        """Consume the next inbound message.

        Blocks until a message is available.

        Returns:
            The next inbound message from the queue.

        Raises:
            asyncio.CancelledError: If the operation is cancelled.
        """
        return await self.inbound.get()

    def try_consume_inbound(self) -> InboundMessage | None:
        """Try to consume an inbound message without blocking.

        Returns:
            The next message if available, None otherwise.
        """
        try:
            return self.inbound.get_nowait()
        except asyncio.QueueEmpty:
            return None

    async def publish_outbound(self, message: OutboundMessage) -> None:
        """Publish a response from the agent to the outbound queue.

        Args:
            message: The outbound message to queue.

        Raises:
            asyncio.QueueFull: If the queue is full and has a maxsize.
        """
        await self.outbound.put(message)

    async def consume_outbound(self) -> OutboundMessage:
        """Consume the next outbound message.

        Blocks until a message is available.

        Returns:
            The next outbound message from the queue.

        Raises:
            asyncio.CancelledError: If the operation is cancelled.
        """
        return await self.outbound.get()

    def try_consume_outbound(self) -> OutboundMessage | None:
        """Try to consume an outbound message without blocking.

        Returns:
            The next message if available, None otherwise.
        """
        try:
            return self.outbound.get_nowait()
        except asyncio.QueueEmpty:
            return None

    @property
    def inbound_size(self) -> int:
        """Get the number of pending inbound messages.

        Returns:
            Current size of the inbound queue.
        """
        return self.inbound.qsize()

    @property
    def outbound_size(self) -> int:
        """Get the number of pending outbound messages.

        Returns:
            Current size of the outbound queue.
        """
        return self.outbound.qsize()

    @property
    def is_empty(self) -> bool:
        """Check if both queues are empty.

        Returns:
            True if both inbound and outbound queues are empty.
        """
        return self.inbound.empty() and self.outbound.empty()

    def task_done(self, queue: str = "inbound") -> None:
        """Mark a task as done for a queue.

        Args:
            queue: Which queue ('inbound' or 'outbound').
        """
        if queue == "inbound":
            self.inbound.task_done()
        elif queue == "outbound":
            self.outbound.task_done()

"""Message bus for OwnBot.

Provides asynchronous message passing between channels and the agent core.
"""

from ownbot.bus.events import InboundMessage, OutboundMessage
from ownbot.bus.queue import MessageBus

__all__ = [
    "MessageBus",
    "InboundMessage",
    "OutboundMessage",
]

"""Message event definitions for the OwnBot message bus.

Defines the data structures for inbound and outbound messages
flowing through the system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime

from ownbot.types import ChannelName, ChatId, JsonDict, MediaUrl, SenderId


@dataclass(frozen=True)
class InboundMessage:
    """Message received from a chat channel.

    Represents a single message from a user, including metadata
    about the sender, channel, and optional media attachments.

    Attributes:
        channel: Channel identifier (e.g., 'telegram', 'whatsapp')
        sender_id: Unique identifier for the sender
        chat_id: Unique identifier for the chat/conversation
        content: Text content of the message
        timestamp: When the message was received
        media: List of media file paths or URLs
        metadata: Channel-specific additional data
        session_key_override: Optional override for session grouping
    """

    channel: ChannelName
    sender_id: SenderId
    chat_id: ChatId
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    media: list[MediaUrl] = field(default_factory=list)
    metadata: JsonDict = field(default_factory=dict)
    session_key_override: str | None = None

    @property
    def session_key(self) -> str:
        """Generate a unique session key for this message.

        Used to group related messages into a single conversation session.
        Can be overridden by session_key_override for advanced use cases
        like thread-scoped sessions.

        Returns:
            Session key in format "{channel}:{chat_id}" or the override value.
        """
        return self.session_key_override or f"{self.channel}:{self.chat_id}"

    def is_command(self, command: str) -> bool:
        """Check if the message content is a specific command.

        Args:
            command: The command to check (e.g., "/help")

        Returns:
            True if the message content matches the command (case-insensitive).
        """
        return self.content.strip().lower() == command.lower()

    def has_command_prefix(self) -> bool:
        """Check if the message starts with a command prefix.

        Returns:
            True if the message starts with '/'.
        """
        return self.content.strip().startswith("/")


@dataclass(frozen=True)
class OutboundMessage:
    """Message to be sent to a chat channel.

    Represents a response from the agent to be delivered
    to the user through the appropriate channel.

    Attributes:
        channel: Target channel identifier
        chat_id: Target chat identifier
        content: Text content of the response
        reply_to: Optional message ID to reply to
        media: Optional list of media file paths to send
        metadata: Channel-specific additional data
    """

    channel: ChannelName
    chat_id: ChatId
    content: str
    reply_to: str | None = None
    media: list[MediaUrl] = field(default_factory=list)
    metadata: JsonDict = field(default_factory=dict)

    def is_empty(self) -> bool:
        """Check if the message has no content and no media.

        Returns:
            True if both content and media are empty.
        """
        return not self.content and not self.media

    def truncate_content(self, max_length: int, suffix: str = "...") -> str:
        """Truncate content to a maximum length.

        Args:
            max_length: Maximum length for the content
            suffix: Suffix to add if truncated

        Returns:
            Truncated content string.
        """
        if len(self.content) <= max_length:
            return self.content
        return self.content[: max_length - len(suffix)] + suffix

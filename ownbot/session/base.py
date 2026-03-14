from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class Session:
    """
    A conversation session.

    Stores messages for conversation history and context.
    """

    key: str
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def get_history(self, max_messages: int = 0) -> list[dict[str, Any]]:
        """
        Get message history.

        Args:
            max_messages: Maximum number of messages to return (0 = all)

        Returns:
            List of messages
        """
        if max_messages > 0:
            return self.messages[-max_messages:]
        return self.messages

    def add_message(self, role: str, content: str, metadata: dict[str, Any] | None = None) -> None:
        """
        Add a message to the session.

        Args:
            role: Message role (e.g., "user", "assistant")
            content: Message content
            metadata: Optional metadata
        """
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        }
        if metadata:
            message["metadata"] = metadata

        self.messages.append(message)
        self.updated_at = datetime.now()

    def clear(self) -> None:
        """Clear all messages from the session."""
        self.messages = []
        self.updated_at = datetime.now()

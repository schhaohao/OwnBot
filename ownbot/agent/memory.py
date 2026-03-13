from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List, Optional

from loguru import logger

from ownbot.providers.base import LLMProvider


@dataclass
class MemoryEntry:
    """A single memory entry."""
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    tags: List[str] = field(default_factory=list)


class MemoryStore:
    """
    Stores and manages memory entries.
    """

    def __init__(self, path: Path):
        self.path = path
        self.entries: List[MemoryEntry] = []
        self._load()

    def _load(self) -> None:
        """Load memories from disk."""
        if not self.path.exists():
            return
        try:
            with self.path.open("r", encoding="utf-8") as f:
                data = json.load(f)
                for entry in data:
                    self.entries.append(
                        MemoryEntry(
                            content=entry["content"],
                            timestamp=datetime.fromisoformat(entry["timestamp"]),
                            tags=entry.get("tags", []),
                        )
                    )
        except Exception as e:
            logger.error(f"Failed to load memories: {e}")

    def save(self) -> None:
        """Save memories to disk."""
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("w", encoding="utf-8") as f:
                data = [
                    {
                        "content": entry.content,
                        "timestamp": entry.timestamp.isoformat(),
                        "tags": entry.tags,
                    }
                    for entry in self.entries
                ]
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")

    def add(self, content: str, tags: List[str] = None) -> None:
        """Add a new memory entry."""
        entry = MemoryEntry(content=content, tags=tags or [])
        self.entries.append(entry)
        self.save()

    def get_recent(self, limit: int = 10) -> List[MemoryEntry]:
        """Get recent memory entries."""
        return sorted(self.entries, key=lambda x: x.timestamp, reverse=True)[:limit]


class MemoryConsolidator:
    """
    Consolidates session history into memories.
    """

    def __init__(
        self,
        workspace: Path,
        provider: LLMProvider,
        model: str,
        sessions: Any,
        context_window_tokens: int,
        build_messages: Callable,
        get_tool_definitions: Callable,
    ):
        self.workspace = workspace
        self.provider = provider
        self.model = model
        self.sessions = sessions
        self.context_window_tokens = context_window_tokens
        self.build_messages = build_messages
        self.get_tool_definitions = get_tool_definitions
        self.memory_store = MemoryStore(workspace / "memories.json")

    async def maybe_consolidate_by_tokens(self, session: Any) -> bool:
        """Check if consolidation is needed and perform it if so."""
        # For MVP, we'll skip token counting and just do simple consolidation
        if len(session.messages) > 50:
            await self.consolidate(session)
            return True
        return False

    async def consolidate(self, session: Any) -> None:
        """Consolidate session history into memories."""
        # For MVP, we'll just save the last few messages as a memory
        if len(session.messages) > 10:
            recent_messages = session.messages[-10:]
            content = "\n".join(
                f"{msg['role']}: {msg.get('content', '')}" for msg in recent_messages
            )
            self.memory_store.add(content, tags=["session_summary"])
            # Keep only the last 20 messages
            session.messages = session.messages[-20:]

    async def archive_unconsolidated(self, session: Any) -> bool:
        """Archive unconsolidated memories."""
        try:
            if session.messages:
                content = "\n".join(
                    f"{msg['role']}: {msg.get('content', '')}" for msg in session.messages
                )
                self.memory_store.add(content, tags=["archived_session"])
            return True
        except Exception as e:
            logger.error(f"Failed to archive memories: {e}")
            return False

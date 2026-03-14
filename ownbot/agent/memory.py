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

    def _get_session_dir(self, session: Any) -> Path:
        """Get session-specific directory."""
        # Create session directory based on session key
        safe_key = session.key.replace("/", "_").replace("\\", "_")
        session_dir = self.workspace / "sessions" / safe_key
        session_dir.mkdir(parents=True, exist_ok=True)
        return session_dir

    def _get_memory_store(self, session: Any) -> MemoryStore:
        """Get session-specific memory store."""
        session_dir = self._get_session_dir(session)
        return MemoryStore(session_dir / "memories.json")

    async def maybe_consolidate_by_tokens(self, session: Any) -> bool:
        """Check if consolidation is needed and perform it if so."""
        # For MVP, we'll skip token counting and just do simple consolidation
        if len(session.messages) > 50:
            await self.consolidate(session)
            return True
        return False

    async def generate_summary(self, messages: list[dict]) -> str:
        """Generate a summary of the conversation using LLM."""
        # Build summary prompt
        prompt = "请总结以下对话，提取关键信息和主要内容：\n\n"
        for msg in messages:
            role = msg.get('role', 'unknown')
            content = msg.get('content', '')
            if content:
                prompt += f"{role}: {content}\n"
        
        # Call LLM to generate summary
        try:
            response = await self.provider.chat_with_retry(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
            )
            return response.content
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            # Fallback to simple concatenation if LLM fails
            return "\n".join(
                f"{msg.get('role', 'unknown')}: {msg.get('content', '')}"
                for msg in messages[-10:]
            )

    def save_memory_files(self, session: Any, summary: str) -> None:
        """Save memory to files."""
        try:
            session_dir = self._get_session_dir(session)
            
            # Save to MEMORY.md
            memory_file = session_dir / "MEMORY.md"
            memory_file.write_text(f"# Memory Summary\n\n{summary}", encoding="utf-8")
            
            # Save to HISTORY.md
            history = "# Conversation History\n\n"
            for msg in session.messages:
                role = msg.get('role', 'unknown')
                content = msg.get('content', '')
                timestamp = msg.get('timestamp', datetime.now().isoformat())
                history += f"## {role} ({timestamp})\n\n{content}\n\n"
            
            history_file = session_dir / "HISTORY.md"
            history_file.write_text(history, encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save memory files: {e}")

    async def consolidate(self, session: Any) -> None:
        """Consolidate session history into memories."""
        if len(session.messages) > 10:
            # Generate summary using LLM
            summary = await self.generate_summary(session.messages)
            
            # Save summary as memory
            memory_store = self._get_memory_store(session)
            memory_store.add(summary, tags=["session_summary"])
            
            # Save to memory files
            self.save_memory_files(session, summary)
            
            # Keep only the last 20 messages
            session.messages = session.messages[-20:]
            logger.info(f"Session history consolidated for {session.key}")

    async def archive_unconsolidated(self, session: Any) -> bool:
        """Archive unconsolidated memories."""
        try:
            if session.messages:
                # Generate summary of the entire session
                summary = await self.generate_summary(session.messages)
                
                # Save to memory
                memory_store = self._get_memory_store(session)
                memory_store.add(summary, tags=["archived_session"])
                
                # Save to archive file
                session_dir = self._get_session_dir(session)
                archive_file = session_dir / f"archive_{datetime.now().isoformat()}.md"
                archive_content = f"# Archived Session\n\n{summary}\n\n"
                archive_content += "## Full History\n\n"
                for msg in session.messages:
                    role = msg.get('role', 'unknown')
                    content = msg.get('content', '')
                    archive_content += f"{role}: {content}\n\n"
                archive_file.write_text(archive_content, encoding="utf-8")
            return True
        except Exception as e:
            logger.error(f"Failed to archive memories: {e}")
            return False

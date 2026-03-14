from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from loguru import logger

from ownbot.config.paths import get_workspace_dir
from ownbot.session.base import Session


class SessionManager:
    """
    Manages conversation sessions.

    Sessions are stored as JSONL files in the sessions directory.
    """

    def __init__(self, workspace: Path | None = None):
        if workspace is None:
            workspace = get_workspace_dir()

        self.workspace = workspace
        self.sessions_dir = workspace / "sessions"
        self._cache: dict[str, Session] = {}

        self._ensure_sessions_dir()

    def _ensure_sessions_dir(self) -> None:
        """Ensure sessions directory exists."""
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, key: str) -> Path:
        """
        Get the file path for a session.

        Args:
            key: Session key

        Returns:
            Path to session file
        """
        safe_key = key.replace("/", "_").replace("\\", "_")
        return self.sessions_dir / f"{safe_key}.jsonl"

    def _load(self, key: str) -> Session | None:
        """
        Load a session from disk.

        Args:
            key: Session key

        Returns:
            Session or None if not found
        """
        path = self._get_session_path(key)
        if not path.exists():
            return None

        try:
            messages = []
            metadata = {}
            created_at = None
            updated_at = None

            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    data = json.loads(line)
                    if data.get("_type") == "metadata":
                        metadata = {
                            "key": data.get("key"),
                            "created_at": data.get("created_at"),
                            "updated_at": data.get("updated_at"),
                            "metadata": data.get("metadata", {})
                        }
                        if data.get("created_at"):
                            created_at = datetime.fromisoformat(data["created_at"])
                        if data.get("updated_at"):
                            updated_at = datetime.fromisoformat(data["updated_at"])
                    else:
                        messages.append(data)

            if created_at and updated_at:
                return Session(
                    key=key,
                    messages=messages,
                    created_at=created_at,
                    updated_at=updated_at,
                    metadata=metadata
                )
        except Exception as e:
            logger.error("Error loading session {}: {}", key, e)

        return None

    def get_or_create(self, key: str) -> Session:
        """
        Get an existing session or create a new one.

        Args:
            key: Session key (usually channel:chat_id)

        Returns:
            The session
        """
        if key in self._cache:
            return self._cache[key]

        session = self._load(key)
        if session is None:
            session = Session(key=key)

        self._cache[key] = session
        return session

    def save(self, session: Session) -> None:
        """
        Save a session to disk.

        Args:
            session: Session to save
        """
        path = self._get_session_path(session.key)

        with open(path, "w", encoding="utf-8") as f:
            metadata_line = {
                "_type": "metadata",
                "key": session.key,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata
            }
            f.write(json.dumps(metadata_line, ensure_ascii=False) + "\n")
            for msg in session.messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

        self._cache[session.key] = session

    def invalidate(self, key: str) -> None:
        """
        Invalidate a session from cache.

        Args:
            key: Session key to invalidate
        """
        if key in self._cache:
            del self._cache[key]

    def list_sessions(self) -> list[str]:
        """
        List all session keys.

        Returns:
            List of session keys
        """
        if not self.sessions_dir.exists():
            return []

        session_keys = []
        for path in self.sessions_dir.glob("*.jsonl"):
            session_keys.append(path.stem)

        return session_keys

    def delete_session(self, key: str) -> bool:
        """
        Delete a session.

        Args:
            key: Session key to delete

        Returns:
            True if deleted, False otherwise
        """
        path = self._get_session_path(key)
        if not path.exists():
            return False

        try:
            path.unlink()
            if key in self._cache:
                del self._cache[key]
            return True
        except Exception as e:
            logger.error("Error deleting session {}: {}", key, e)
            return False

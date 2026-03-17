from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from loguru import logger

from ownbot.agent.tools.base import Tool


class ListFilesTool(Tool):
    """List files in a directory."""

    name = "list_files"
    description = "List files in a directory"

    def __init__(
        self,
        workspace: Path | None = None,
        skills_dir: Path | None = None,
        builtin_skills_dir: Path | None = None,
    ):
        self.workspace = Path(workspace).resolve() if workspace is not None else Path.cwd()
        self.skills_dir = Path(skills_dir).resolve() if skills_dir is not None else None
        self.builtin_skills_dir = Path(builtin_skills_dir).resolve() if builtin_skills_dir is not None else None
        self.repo_root = self.builtin_skills_dir.parent.parent if self.builtin_skills_dir is not None else None

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(os.path.expanduser(raw_path))
        if path.is_absolute():
            if self.skills_dir is not None and raw_path.startswith("/skills/"):
                relative = raw_path.removeprefix("/skills/").strip("/")
                return (self.skills_dir / relative).resolve()
            return path
        if raw_path.startswith("ownbot/skills/") and self.repo_root is not None:
            return (self.repo_root / raw_path).resolve()
        return (self.workspace / path).resolve()

    async def execute(self, arguments: dict[str, Any]) -> str:
        raw_path = arguments.get("path", ".")
        try:
            path = self._resolve_path(raw_path)
            files = os.listdir(path)
            return "\n".join(files)
        except Exception as e:
            logger.error("Error listing files in {}: {}", raw_path, e)
            return f"Error listing files: {str(e)}"

    def _get_parameters_schema(self) -> dict[str, Any]:
        return {
            "path": {
                "type": "string",
                "description": "Directory path (default: current directory)",
            }
        }


class ReadFileTool(Tool):
    """Read file contents."""

    name = "read_file"
    description = "Read file contents"

    def __init__(
        self,
        workspace: Path | None = None,
        skills_dir: Path | None = None,
        builtin_skills_dir: Path | None = None,
    ):
        self.workspace = Path(workspace).resolve() if workspace is not None else Path.cwd()
        self.skills_dir = Path(skills_dir).resolve() if skills_dir is not None else None
        self.builtin_skills_dir = Path(builtin_skills_dir).resolve() if builtin_skills_dir is not None else None
        self.repo_root = self.builtin_skills_dir.parent.parent if self.builtin_skills_dir is not None else None

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(os.path.expanduser(raw_path))
        if path.is_absolute():
            if self.skills_dir is not None and raw_path.startswith("/skills/"):
                relative = raw_path.removeprefix("/skills/").strip("/")
                return (self.skills_dir / relative).resolve()
            return path
        if raw_path.startswith("ownbot/skills/") and self.repo_root is not None:
            return (self.repo_root / raw_path).resolve()
        return (self.workspace / path).resolve()

    async def execute(self, arguments: dict[str, Any]) -> str:
        raw_path = arguments.get("path")
        if not raw_path:
            return "Error: path is required"

        try:
            path = self._resolve_path(raw_path)
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error("Error reading file {}: {}", raw_path, e)
            return f"Error reading file: {str(e)}"

    def _get_parameters_schema(self) -> dict[str, Any]:
        return {
            "path": {
                "type": "string",
                "description": "File path",
            }
        }


class WriteFileTool(Tool):
    """Write content to a file."""

    name = "write_file"
    description = "Write content to a file"

    def __init__(
        self,
        workspace: Path | None = None,
        skills_dir: Path | None = None,
        builtin_skills_dir: Path | None = None,
    ):
        self.workspace = Path(workspace).resolve() if workspace is not None else Path.cwd()
        self.skills_dir = Path(skills_dir).resolve() if skills_dir is not None else None
        self.builtin_skills_dir = Path(builtin_skills_dir).resolve() if builtin_skills_dir is not None else None
        self.repo_root = self.builtin_skills_dir.parent.parent if self.builtin_skills_dir is not None else None

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(os.path.expanduser(raw_path))
        if path.is_absolute():
            if self.skills_dir is not None and raw_path.startswith("/skills/"):
                relative = raw_path.removeprefix("/skills/").strip("/")
                return (self.skills_dir / relative).resolve()
            return path
        if raw_path.startswith("ownbot/skills/") and self.repo_root is not None:
            return (self.repo_root / raw_path).resolve()
        return (self.workspace / path).resolve()

    async def execute(self, arguments: dict[str, Any]) -> str:
        raw_path = arguments.get("path")
        content = arguments.get("content", "")
        if not raw_path:
            return "Error: path is required"

        try:
            path = self._resolve_path(raw_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        except Exception as e:
            logger.error("Error writing to file {}: {}", raw_path, e)
            return f"Error writing to file: {str(e)}"

    def _get_parameters_schema(self) -> dict[str, Any]:
        return {
            "path": {
                "type": "string",
                "description": "File path",
            },
            "content": {
                "type": "string",
                "description": "Content to write",
            }
        }

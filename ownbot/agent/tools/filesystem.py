"""Filesystem tools for the agent.

Provides secure file operations with path validation to prevent directory traversal.
"""

from __future__ import annotations

import os
from abc import ABC
from pathlib import Path
from typing import Any

from loguru import logger

from ownbot.agent.tools.base import Tool
from ownbot.constants import MAX_FILE_READ_SIZE
from ownbot.exceptions import FileNotFoundError, FileSystemError, PathNotAllowedError


class BaseFileSystemTool(Tool, ABC):
    """Base class for filesystem tools with path validation."""

    # Skill path prefixes that trigger special handling
    SKILLS_PREFIX: str = "/skills/"
    REPO_SKILLS_PREFIX: str = "ownbot/skills/"

    def __init__(
        self,
        workspace: Path | None = None,
        skills_dir: Path | None = None,
        builtin_skills_dir: Path | None = None,
    ) -> None:
        self.workspace = Path(workspace).resolve() if workspace else Path.cwd()
        self.skills_dir = Path(skills_dir).resolve() if skills_dir else None
        self.builtin_skills_dir = Path(builtin_skills_dir).resolve() if builtin_skills_dir else None
        self.repo_root = self.builtin_skills_dir.parent.parent if self.builtin_skills_dir else None

    def _resolve_path(self, raw_path: str) -> Path:
        """Resolve a path, handling special skill directory prefixes.

        Args:
            raw_path: The raw path string from user input.

        Returns:
            Resolved Path object.

        Raises:
            PathNotAllowedError: If path is outside allowed directories.
        """
        path = Path(os.path.expanduser(raw_path))

        # Handle absolute paths with special prefixes
        if path.is_absolute():
            if self.skills_dir and raw_path.startswith(self.SKILLS_PREFIX):
                return self._resolve_skills_path(raw_path)

            fallback = self._maybe_resolve_builtin_skill_fallback(path)
            if fallback:
                return fallback

            # Validate the path is within workspace
            resolved = path.resolve()
            if not self._is_path_allowed(resolved):
                raise PathNotAllowedError(f"Path '{raw_path}' is outside allowed directories")
            return resolved

        # Handle repo-relative skill paths
        if raw_path.startswith(self.REPO_SKILLS_PREFIX) and self.repo_root:
            return (self.repo_root / raw_path).resolve()

        # Relative path from workspace
        return (self.workspace / path).resolve()

    def _resolve_skills_path(self, raw_path: str) -> Path:
        """Resolve a path starting with /skills/ prefix."""
        relative = raw_path.removeprefix(self.SKILLS_PREFIX).strip("/")
        return (self.skills_dir / relative).resolve()

    def _maybe_resolve_builtin_skill_fallback(self, path: Path) -> Path | None:
        """Fall back to built-in skill if workspace skill doesn't exist.

        This allows skills to be read from the package directory
        even if the user references them via workspace path.
        """
        if not self.skills_dir or not self.builtin_skills_dir:
            return None
        if path.exists() or path.name != "SKILL.md":
            return None

        try:
            path.relative_to(self.skills_dir)
        except ValueError:
            return None

        skill_name = path.parent.name
        builtin_path = (self.builtin_skills_dir / skill_name / "SKILL.md").resolve()
        if builtin_path.exists():
            logger.debug(
                "Workspace skill path {} missing; falling back to built-in {}",
                path,
                builtin_path,
            )
            return builtin_path
        return None

    def _is_path_allowed(self, path: Path) -> bool:
        """Check if a path is within allowed directories."""
        try:
            path.relative_to(self.workspace)
            return True
        except ValueError:
            pass

        if self.skills_dir:
            try:
                path.relative_to(self.skills_dir)
                return True
            except ValueError:
                pass

        if self.builtin_skills_dir:
            try:
                path.relative_to(self.builtin_skills_dir)
                return True
            except ValueError:
                pass

        return False


class ListFilesTool(BaseFileSystemTool):
    """List files in a directory."""

    name = "list_files"
    description = "List files and directories in a specified path"

    async def execute(self, arguments: dict[str, Any]) -> str:
        """List files in a directory.

        Args:
            arguments: Must contain 'path' key with directory path.

        Returns:
            Newline-separated list of files and directories.

        Raises:
            FileSystemError: If directory cannot be read.
        """
        raw_path = arguments.get("path", ".")

        try:
            path = self._resolve_path(raw_path)

            if not path.exists():
                raise FileNotFoundError(f"Directory not found: {raw_path}")

            if not path.is_dir():
                raise FileSystemError(f"Path is not a directory: {raw_path}")

            files = os.listdir(path)
            return "\n".join(files) if files else "(empty directory)"

        except PathNotAllowedError:
            raise
        except FileNotFoundError:
            raise
        except Exception as e:
            logger.error("Error listing files in {}: {}", raw_path, e)
            raise FileSystemError(f"Failed to list files: {e}") from e

    def _get_parameters_schema(self) -> dict[str, Any]:
        return {
            "path": {
                "type": "string",
                "description": "Directory path (default: current directory)",
            }
        }


class ReadFileTool(BaseFileSystemTool):
    """Read file contents."""

    name = "read_file"
    description = "Read the contents of a file"

    async def execute(self, arguments: dict[str, Any]) -> str:
        """Read file contents.

        Args:
            arguments: Must contain 'path' key with file path.

        Returns:
            File contents as string.

        Raises:
            FileNotFoundError: If file doesn't exist.
            FileSystemError: If file cannot be read.
            PathNotAllowedError: If path is outside allowed directories.
        """
        raw_path = arguments.get("path")
        if not raw_path:
            raise ToolValidationError("Path is required")

        try:
            path = self._resolve_path(raw_path)

            if not path.exists():
                raise FileNotFoundError(f"File not found: {raw_path}")

            if not path.is_file():
                raise FileSystemError(f"Path is not a file: {raw_path}")

            # Check file size
            file_size = path.stat().st_size
            if file_size > MAX_FILE_READ_SIZE:
                raise FileSystemError(
                    f"File too large ({file_size} bytes). Max size: {MAX_FILE_READ_SIZE} bytes"
                )

            with open(path, encoding="utf-8") as f:
                content = f.read()
            return content

        except PathNotAllowedError:
            raise
        except FileNotFoundError:
            raise
        except UnicodeDecodeError as e:
            raise FileSystemError(f"File is not valid UTF-8 text: {e}") from e
        except Exception as e:
            logger.error("Error reading file {}: {}", raw_path, e)
            raise FileSystemError(f"Failed to read file: {e}") from e

    def _get_parameters_schema(self) -> dict[str, Any]:
        return {
            "path": {
                "type": "string",
                "description": "File path to read",
            }
        }


class WriteFileTool(BaseFileSystemTool):
    """Write content to a file."""

    name = "write_file"
    description = "Write content to a file (creates directories if needed)"

    async def execute(self, arguments: dict[str, Any]) -> str:
        """Write content to a file.

        Args:
            arguments: Must contain 'path' and 'content' keys.

        Returns:
            Success message with resolved path.

        Raises:
            FileSystemError: If file cannot be written.
            PathNotAllowedError: If path is outside allowed directories.
        """
        raw_path = arguments.get("path")
        content = arguments.get("content", "")

        if not raw_path:
            raise ToolValidationError("Path is required")

        try:
            path = self._resolve_path(raw_path)

            # Ensure parent directory exists
            path.parent.mkdir(parents=True, exist_ok=True)

            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

            return f"Successfully wrote {len(content)} characters to {path}"

        except PathNotAllowedError:
            raise
        except Exception as e:
            logger.error("Error writing to file {}: {}", raw_path, e)
            raise FileSystemError(f"Failed to write file: {e}") from e

    def _get_parameters_schema(self) -> dict[str, Any]:
        return {
            "path": {
                "type": "string",
                "description": "File path to write",
            },
            "content": {
                "type": "string",
                "description": "Content to write",
                "default": "",
            },
        }


# Import needed for type checking
from ownbot.exceptions import ToolValidationError

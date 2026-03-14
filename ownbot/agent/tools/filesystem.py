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

    async def execute(self, arguments: dict[str, Any]) -> str:
        path = arguments.get("path", ".")
        try:
            files = os.listdir(path)
            return "\n".join(files)
        except Exception as e:
            logger.error("Error listing files in {}: {}", path, e)
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

    async def execute(self, arguments: dict[str, Any]) -> str:
        path = arguments.get("path")
        if not path:
            return "Error: path is required"

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return content
        except Exception as e:
            logger.error("Error reading file {}: {}", path, e)
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

    async def execute(self, arguments: dict[str, Any]) -> str:
        path = arguments.get("path")
        content = arguments.get("content", "")
        if not path:
            return "Error: path is required"

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            return f"Successfully wrote to {path}"
        except Exception as e:
            logger.error("Error writing to file {}: {}", path, e)
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

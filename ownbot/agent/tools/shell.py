from __future__ import annotations

import asyncio
import shlex
from typing import Any

from loguru import logger

from ownbot.agent.tools.base import Tool


class ShellTool(Tool):
    """Execute shell commands."""

    name = "shell"
    description = "Execute a shell command"

    async def execute(self, arguments: dict[str, Any]) -> str:
        command = arguments.get("command")
        if not command:
            return "Error: command is required"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                shell=True
            )

            stdout, stderr = await process.communicate()

            output = ""
            if stdout:
                output += stdout.decode("utf-8", errors="replace")
            if stderr:
                output += stderr.decode("utf-8", errors="replace")

            return output or f"Command executed with exit code {process.returncode}"
        except Exception as e:
            logger.error("Error executing command {}: {}", command, e)
            return f"Error executing command: {str(e)}"

    def _get_parameters_schema(self) -> dict[str, Any]:
        return {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            }
        }

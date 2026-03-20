"""Shell execution tool for the agent.

Provides controlled shell command execution with security restrictions.
"""

from __future__ import annotations

import asyncio
import shlex
from typing import Any

from loguru import logger

from ownbot.agent.tools.base import Tool
from ownbot.exceptions import ShellCommandBlockedError, ShellCommandError, ToolValidationError


class ShellTool(Tool):
    """Execute shell commands with security restrictions.

    WARNING: This tool executes shell commands directly. Use with caution
    and ensure proper input validation and access controls are in place.
    """

    name = "shell"
    description = "Execute a shell command with security restrictions"

    # Maximum output size to prevent memory issues
    MAX_OUTPUT_SIZE: int = 100_000
    # Default timeout for commands
    DEFAULT_TIMEOUT: float = 60.0
    # Commands that are completely blocked
    BLOCKED_PATTERNS: tuple[str, ...] = (
        "rm -rf /",
        "rm -rf ~",
        "rm -rf /*",
        ":(){ :|:& };:",  # fork bomb
        "dd if=/dev/zero",
        "> /dev/sda",
        "mkfs",
    )

    def __init__(self, allowed_commands: list[str] | None = None) -> None:
        """Initialize ShellTool.

        Args:
            allowed_commands: Optional whitelist of allowed commands.
                            If None, all commands are allowed (except blocked ones).
        """
        self.allowed_commands = set(allowed_commands) if allowed_commands else None

    def _is_command_blocked(self, command: str) -> bool:
        """Check if a command matches blocked patterns."""
        command_lower = command.lower().strip()

        # Check against blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in command_lower:
                return True

        # Check for dangerous patterns
        dangerous_patterns = (
            "; rm ",
            "&& rm ",
            "|| rm ",
            "`rm ",
            "$(rm ",
            "| bash",
            "| sh ",
            "curl *| *sh",
            "wget *| *sh",
        )

        for pattern in dangerous_patterns:
            if pattern in command_lower:
                return True

        return False

    def _validate_command(self, command: str) -> None:
        """Validate a command before execution.

        Args:
            command: The command to validate.

        Raises:
            ToolValidationError: If command is empty.
            ShellCommandBlockedError: If command is blocked.
        """
        if not command or not command.strip():
            raise ToolValidationError("Command cannot be empty")

        if self._is_command_blocked(command):
            raise ShellCommandBlockedError(
                f"Command blocked for security reasons: {command[:50]}..."
            )

        # Check whitelist if configured
        if self.allowed_commands:
            # Extract base command
            try:
                base_cmd = shlex.split(command)[0]
            except ValueError:
                base_cmd = command.split()[0] if command.split() else ""

            if base_cmd not in self.allowed_commands:
                raise ShellCommandBlockedError(
                    f"Command '{base_cmd}' is not in the allowed commands list"
                )

    async def execute(self, arguments: dict[str, Any]) -> str:
        """Execute a shell command.

        Args:
            arguments: Must contain 'command' key with the command to execute.
                      Optional 'timeout' key for command timeout in seconds.
                      Optional 'cwd' key for working directory.

        Returns:
            Command output (stdout + stderr).

        Raises:
            ToolValidationError: If command is invalid.
            ShellCommandBlockedError: If command is blocked.
            ShellCommandError: If command execution fails.
        """
        command = arguments.get("command", "").strip()
        timeout = arguments.get("timeout", self.DEFAULT_TIMEOUT)
        cwd = arguments.get("cwd")

        # Validate the command
        self._validate_command(command)

        logger.debug("Executing shell command: {}", command[:100])

        try:
            process = await asyncio.create_subprocess_shell(  # nosec B604
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
                shell=True,
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except TimeoutError:
                process.kill()
                await process.wait()
                raise ShellCommandError(f"Command timed out after {timeout} seconds")

            # Decode output
            output_parts: list[str] = []
            if stdout:
                stdout_str = stdout.decode("utf-8", errors="replace")
                output_parts.append(stdout_str)
            if stderr:
                stderr_str = stderr.decode("utf-8", errors="replace")
                output_parts.append(f"[stderr] {stderr_str}")

            output = "\n".join(output_parts)

            # Truncate if too large
            if len(output) > self.MAX_OUTPUT_SIZE:
                output = output[: self.MAX_OUTPUT_SIZE] + "\n... (output truncated)"

            if process.returncode != 0:
                status = f"\n[Exit code: {process.returncode}]"
                if output:
                    return output + status
                return status

            return output or "Command executed successfully (exit code 0)"

        except ShellCommandError:
            raise
        except Exception as e:
            logger.error("Error executing command '{}': {}", command[:100], e)
            raise ShellCommandError(f"Failed to execute command: {e}") from e

    def _get_parameters_schema(self) -> dict[str, Any]:
        return {
            "command": {
                "type": "string",
                "description": "Shell command to execute",
            },
            "timeout": {
                "type": "number",
                "description": f"Command timeout in seconds (default: {self.DEFAULT_TIMEOUT})",
                "default": self.DEFAULT_TIMEOUT,
            },
            "cwd": {
                "type": "string",
                "description": "Working directory for command execution",
            },
        }

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolCall:
    """
    Represents a tool call request.
    """

    name: str
    arguments: dict[str, Any]


class Tool(ABC):
    """
    Base class for agent tools.

    Tools are callable functions that can be used by the agent
    to perform actions like file operations, shell commands, etc.
    """

    name: str
    description: str

    @abstractmethod
    async def execute(self, arguments: dict[str, Any]) -> str:
        """
        Execute the tool with given arguments.

        Args:
            arguments: Tool arguments

        Returns:
            Tool execution result as string
        """
        pass

    def to_openai_tool_call(self) -> dict[str, Any]:
        """
        Convert tool to OpenAI tool call format.

        Returns:
            Tool call dictionary
        """
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": self._get_parameters_schema(),
                }
            }
        }

    def _get_parameters_schema(self) -> dict[str, Any]:
        """
        Get parameters schema for the tool.

        Returns:
            Parameters schema dictionary
        """
        return {}

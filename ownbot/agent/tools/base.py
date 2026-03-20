"""Base classes for agent tools.

Provides the abstract base class that all tools must implement,
along with supporting data structures.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ownbot.types import ToolParameters, ToolResult


@dataclass(frozen=True)
class ToolCall:
    """Represents a tool call request from the LLM.

    Attributes:
        name: The name of the tool to call.
        arguments: Dictionary of arguments to pass to the tool.
    """

    name: str
    arguments: ToolParameters


class Tool(ABC):
    """Abstract base class for all agent tools.

    Tools are callable functions that extend the agent's capabilities,
    allowing it to perform actions like file operations, shell commands,
    web requests, etc.

    To create a new tool:
    1. Inherit from this class
    2. Define `name` and `description` class attributes
    3. Implement the `execute` method
    4. Optionally override `_get_parameters_schema` to define parameters
    """

    # Tool metadata - must be overridden by subclasses
    name: str
    description: str

    @abstractmethod
    async def execute(self, arguments: ToolParameters) -> ToolResult:
        """Execute the tool with the given arguments.

        Args:
            arguments: Tool arguments as a dictionary. The specific keys
                      depend on the tool's parameter schema.

        Returns:
            Tool execution result as a string.

        Raises:
            OwnBotError: If tool execution fails. Specific subclasses should
                        be raised for different error types.
        """
        raise NotImplementedError

    def to_openai_tool_call(self) -> dict[str, Any]:
        """Convert tool to OpenAI-compatible function definition format.

        This format is used by OpenAI's function calling API and compatible
        providers.

        Returns:
            Dictionary with 'type' and 'function' keys following OpenAI's schema.
        """
        schema = self._get_parameters_schema()
        parameters: dict[str, Any] = {
            "type": "object",
            "properties": schema,
        }

        # Determine required parameters
        required = [
            name for name, spec in schema.items() if isinstance(spec, dict) and spec.get("required")
        ]
        if required:
            parameters["required"] = required

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }

    def _get_parameters_schema(self) -> dict[str, Any]:
        """Get the JSON Schema for tool parameters.

        Override this method to define the expected parameters.
        Each parameter should be a dictionary with:
        - type: JSON Schema type (string, number, boolean, object, array)
        - description: Human-readable description
        - optional: default, enum, required, etc.

        Returns:
            Dictionary mapping parameter names to their schema definitions.
        """
        return {}

    def validate_arguments(self, arguments: ToolParameters) -> None:
        """Validate arguments against the parameter schema.

        Args:
            arguments: Arguments to validate.

        Raises:
            ToolValidationError: If validation fails.
        """
        schema = self._get_parameters_schema()

        # Check for unknown parameters
        for key in arguments:
            if key not in schema:
                raise ToolValidationError(f"Unknown parameter '{key}' for tool '{self.name}'")

        # Check required parameters
        for key, spec in schema.items():
            if isinstance(spec, dict) and spec.get("required", False):
                if key not in arguments:
                    raise ToolValidationError(
                        f"Missing required parameter '{key}' for tool '{self.name}'"
                    )


# Import at end to avoid circular imports

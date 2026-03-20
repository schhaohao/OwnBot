"""Tool registry for managing and executing agent tools.

Provides a central registry for tool registration, lookup, and execution
with proper error handling and logging.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from ownbot.agent.tools.base import Tool
from ownbot.exceptions import ToolExecutionError, ToolNotFoundError
from ownbot.types import ToolParameters, ToolResult


class ToolRegistry:
    """Registry for agent tools.

    Manages tool registration and provides a unified interface for tool execution.
    Tools are registered by name and can be looked up and executed dynamically.

    Example:
        registry = ToolRegistry()
        registry.register(MyTool())
        result = await registry.execute("my_tool", {"arg": "value"})
    """

    def __init__(self) -> None:
        """Initialize an empty tool registry."""
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool in the registry.

        Args:
            tool: The tool instance to register.

        Raises:
            ValueError: If a tool with the same name is already registered.
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")

        self._tools[tool.name] = tool
        logger.info("Registered tool: {}", tool.name)

    def unregister(self, name: str) -> bool:
        """Unregister a tool by name.

        Args:
            name: The name of the tool to unregister.

        Returns:
            True if the tool was found and removed, False otherwise.
        """
        if name in self._tools:
            del self._tools[name]
            logger.info("Unregistered tool: {}", name)
            return True
        return False

    def get(self, name: str) -> Tool | None:
        """Get a tool by name.

        Args:
            name: The name of the tool to retrieve.

        Returns:
            The tool instance if found, None otherwise.
        """
        return self._tools.get(name)

    def has_tool(self, name: str) -> bool:
        """Check if a tool is registered.

        Args:
            name: The name of the tool to check.

        Returns:
            True if the tool is registered, False otherwise.
        """
        return name in self._tools

    def list_tools(self) -> list[str]:
        """Get a list of all registered tool names.

        Returns:
            Sorted list of tool names.
        """
        return sorted(self._tools.keys())

    def get_definitions(self) -> list[dict[str, Any]]:
        """Get all tool definitions in OpenAI-compatible format.

        Returns:
            List of tool definition dictionaries.
        """
        return [tool.to_openai_tool_call() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: ToolParameters) -> ToolResult:
        """Execute a tool by name with the given arguments.

        Args:
            name: The name of the tool to execute.
            arguments: Arguments to pass to the tool.

        Returns:
            The tool's result as a string.

        Raises:
            ToolNotFoundError: If the tool is not registered.
            ToolExecutionError: If tool execution fails.
        """
        tool = self.get(name)
        if tool is None:
            raise ToolNotFoundError(f"Tool '{name}' not found")

        logger.debug("Executing tool '{}' with arguments: {}", name, arguments)

        try:
            # Validate arguments before execution
            tool.validate_arguments(arguments)

            # Execute the tool
            result = await tool.execute(arguments)
            return result

        except ToolNotFoundError:
            raise
        except Exception as e:
            logger.exception("Error executing tool '{}': {}", name, e)
            raise ToolExecutionError(f"Error executing tool '{name}': {e}") from e

    def __len__(self) -> int:
        """Return the number of registered tools."""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """Check if a tool name is registered."""
        return name in self._tools

    def __iter__(self):
        """Iterate over registered tools."""
        return iter(self._tools.values())

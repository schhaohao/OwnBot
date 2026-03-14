from __future__ import annotations

from typing import Any

from loguru import logger

from ownbot.agent.tools.base import Tool


class ToolRegistry:
    """
    Registry for agent tools.

    Allows dynamic registration and execution of tools.
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self._tools[tool.name] = tool
        logger.info("Registered tool: {}", tool.name)

    def unregister(self, name: str) -> bool:
        """Unregister a tool."""
        if name in self._tools:
            del self._tools[name]
            logger.info("Unregistered tool: {}", name)
            return True
        return False

    def get(self, name: str) -> Tool | None:
        """Get a tool by name."""
        return self._tools.get(name)

    def get_definitions(self) -> list[dict[str, Any]]:
        """Get all tool definitions in OpenAI format."""
        return [tool.to_openai_tool_call() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        """Execute a tool by name."""
        tool = self.get(name)
        if tool is None:
            return f"Tool {name} not found"

        try:
            return await tool.execute(arguments)
        except Exception as e:
            logger.exception("Error executing tool {}: {}", name, e)
            return f"Error executing tool {name}: {str(e)}"

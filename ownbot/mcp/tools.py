"""MCP Tool Adapter for OwnBot.

Adapts MCP tools to OwnBot's Tool interface, allowing seamless
integration of MCP servers into the OwnBot agent.
"""

from __future__ import annotations

from typing import Any

from loguru import logger
from mcp.types import Tool as MCPTool

from ownbot.agent.tools.base import Tool
from ownbot.mcp.client import MCPClientManager
from ownbot.types import ToolParameters, ToolResult


class MCPToolAdapter(Tool):
    """Adapter that wraps an MCP tool for use in OwnBot.

    This adapter converts MCP tool definitions to OwnBot's Tool interface,
    allowing MCP tools to be used seamlessly within the agent's tool loop.

    Attributes:
        name: The tool name (prefixed with server name)
        description: Tool description from MCP
        server_name: Name of the MCP server providing this tool
        mcp_tool_name: Original MCP tool name
        client_manager: MCP client manager for executing tool calls
    """

    def __init__(
        self,
        server_name: str,
        mcp_tool: MCPTool,
        client_manager: MCPClientManager,
    ) -> None:
        """Initialize the MCP tool adapter.

        Args:
            server_name: Name of the MCP server
            mcp_tool: MCP tool definition
            client_manager: Client manager for executing calls
        """
        self.server_name = server_name
        self.mcp_tool_name = mcp_tool.name
        self.client_manager = client_manager
        self._mcp_tool = mcp_tool

        # Create prefixed name to avoid conflicts
        # e.g., "filesystem_read_file" for "filesystem" server's "read_file" tool
        self.name = f"mcp_{server_name}_{mcp_tool.name}"
        self.description = self._build_description(mcp_tool)

        logger.debug("Created MCP tool adapter: {} -> {}", self.name, mcp_tool.name)

    def _build_description(self, mcp_tool: MCPTool) -> str:
        """Build a comprehensive description for the tool.

        Args:
            mcp_tool: MCP tool definition

        Returns:
            Tool description with server info
        """
        base_desc = mcp_tool.description or f"Execute {mcp_tool.name} via MCP"
        return f"[{self.server_name}] {base_desc}"

    def _get_parameters_schema(self) -> dict[str, Any]:
        """Get the JSON Schema for tool parameters.

        Returns:
            Parameter schema from MCP tool definition
        """
        if self._mcp_tool.inputSchema:
            # Extract properties from the schema
            schema = self._mcp_tool.inputSchema
            if schema.get("type") == "object" and "properties" in schema:
                return schema["properties"]
            return schema
        return {}

    async def execute(self, arguments: ToolParameters) -> ToolResult:
        """Execute the MCP tool.

        Args:
            arguments: Tool arguments

        Returns:
            Tool execution result as string
        """
        logger.info(
            "Executing MCP tool: {}.{} (as {})", self.server_name, self.mcp_tool_name, self.name
        )

        # Call the tool through the client manager
        result = await self.client_manager.call_tool(
            server_name=self.server_name,
            tool_name=self.mcp_tool_name,
            arguments=arguments,
        )

        # Format result
        return self.client_manager.format_tool_result(result)

    def to_openai_tool_call(self) -> dict[str, Any]:
        """Convert tool to OpenAI-compatible function definition.

        Override to preserve the original MCP schema structure.

        Returns:
            Dictionary with 'type' and 'function' keys
        """
        # Get the base schema
        schema = self._mcp_tool.inputSchema or {"type": "object", "properties": {}}

        # Ensure it's a valid OpenAI function definition
        parameters: dict[str, Any] = {
            "type": "object",
            "properties": schema.get("properties", {}),
        }

        # Add required fields if specified in schema
        if "required" in schema:
            parameters["required"] = schema["required"]

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": parameters,
            },
        }


class MCPRegistry:
    """Registry for managing MCP tool adapters.

    Creates and manages tool adapters for all connected MCP servers,
    providing a unified interface for tool registration.

    Example:
        registry = MCPRegistry(client_manager)
        await registry.load_tools()
        for tool in registry.get_tools():
            tool_registry.register(tool)
    """

    def __init__(self, client_manager: MCPClientManager) -> None:
        """Initialize the MCP registry.

        Args:
            client_manager: MCP client manager with active connections
        """
        self.client_manager = client_manager
        self._adapters: list[MCPToolAdapter] = []

    async def load_tools(self) -> list[MCPToolAdapter]:
        """Load all tools from connected MCP servers.

        Returns:
            List of tool adapters
        """
        self._adapters = []

        all_tools = self.client_manager.get_all_tools()
        for server_name, mcp_tool in all_tools:
            adapter = MCPToolAdapter(
                server_name=server_name,
                mcp_tool=mcp_tool,
                client_manager=self.client_manager,
            )
            self._adapters.append(adapter)

        logger.info(
            "Loaded {} MCP tools from {} servers",
            len(self._adapters),
            len(self.client_manager._connections),
        )
        return self._adapters

    def get_tools(self) -> list[MCPToolAdapter]:
        """Get all loaded tool adapters.

        Returns:
            List of tool adapters
        """
        return self._adapters

    def get_tool_names(self) -> list[str]:
        """Get names of all loaded tools.

        Returns:
            List of tool names
        """
        return [adapter.name for adapter in self._adapters]

    def get_tools_for_server(self, server_name: str) -> list[MCPToolAdapter]:
        """Get tools for a specific server.

        Args:
            server_name: Name of the MCP server

        Returns:
            List of tool adapters for that server
        """
        return [adapter for adapter in self._adapters if adapter.server_name == server_name]

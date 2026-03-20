"""MCP client manager for connecting to MCP servers.

Provides functionality to connect to MCP servers via different transports
(stdio, SSE, HTTP) and manage tool discovery/execution.
"""

from __future__ import annotations

import os
from contextlib import AsyncExitStack
from dataclasses import dataclass
from typing import Any

from loguru import logger
from mcp import ClientSession, StdioServerParameters
from mcp.client.sse import sse_client
from mcp.client.stdio import stdio_client
from mcp.types import CallToolResult, TextContent, Tool

from ownbot.config.schema import MCPServerConfig
from ownbot.exceptions import (
    MCPConnectionError,
    MCPServerNotFoundError,
    MCPToolError,
)


@dataclass
class MCPConnection:
    """Represents an active MCP server connection."""

    server_name: str
    session: ClientSession
    tools: list[Tool]
    exit_stack: AsyncExitStack


class MCPClientManager:
    """Manager for MCP client connections.

    Handles connection lifecycle, tool discovery, and tool execution
    for multiple MCP servers.

    Example:
        manager = MCPClientManager()
        await manager.connect_all(servers)
        tools = manager.get_all_tools()
        result = await manager.call_tool(server_name, tool_name, args)
        await manager.disconnect_all()
    """

    def __init__(self) -> None:
        """Initialize the MCP client manager."""
        self._connections: dict[str, MCPConnection] = {}
        self._exit_stack = AsyncExitStack()

    async def connect_server(self, config: MCPServerConfig) -> MCPConnection:
        """Connect to a single MCP server.

        Args:
            config: MCP server configuration

        Returns:
            MCPConnection object

        Raises:
            MCPConnectionError: If connection fails
        """
        if not config.enabled:
            raise MCPConnectionError(f"Server '{config.name}' is disabled")

        logger.info("Connecting to MCP server: {} (transport: {})", config.name, config.transport)

        try:
            if config.transport == "stdio":
                session = await self._connect_stdio(config)
            elif config.transport == "sse":
                session = await self._connect_sse(config)
            elif config.transport == "http":
                # HTTP transport uses SSE client for now
                session = await self._connect_sse(config)
            else:
                raise MCPConnectionError(f"Unknown transport: {config.transport}")

            # List available tools
            tools_result = await session.list_tools()
            tools = tools_result.tools

            logger.info("Connected to MCP server: {} with {} tools", config.name, len(tools))
            for tool in tools:
                logger.debug("  - Tool: {}", tool.name)

            # Create connection (exit_stack managed by _connections)
            conn = MCPConnection(
                server_name=config.name,
                session=session,
                tools=tools,
                exit_stack=self._exit_stack,
            )
            self._connections[config.name] = conn
            return conn

        except Exception as e:
            logger.exception("Failed to connect to MCP server: {}", config.name)
            raise MCPConnectionError(f"Failed to connect to '{config.name}': {e}") from e

    async def _connect_stdio(self, config: MCPServerConfig) -> ClientSession:
        """Connect via stdio transport."""
        if not config.command:
            raise MCPConnectionError(f"Command required for stdio transport: {config.name}")

        # Prepare environment variables
        env = os.environ.copy()
        env.update(config.env)

        server_params = StdioServerParameters(
            command=config.command,
            args=config.args,
            env=env,
        )

        # Connect to the server
        stdio_transport = await self._exit_stack.enter_async_context(stdio_client(server_params))
        read_stream, write_stream = stdio_transport

        # Create session
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        # Initialize
        await session.initialize()
        return session

    async def _connect_sse(self, config: MCPServerConfig) -> ClientSession:
        """Connect via SSE transport."""
        if not config.url:
            raise MCPConnectionError(f"URL required for SSE transport: {config.name}")

        # Connect to the server
        sse_transport = await self._exit_stack.enter_async_context(sse_client(config.url))
        read_stream, write_stream = sse_transport

        # Create session
        session = await self._exit_stack.enter_async_context(
            ClientSession(read_stream, write_stream)
        )

        # Initialize
        await session.initialize()
        return session

    async def connect_all(self, configs: list[MCPServerConfig]) -> list[MCPConnection]:
        """Connect to all enabled MCP servers.

        Args:
            configs: List of MCP server configurations

        Returns:
            List of successful connections
        """
        connections = []
        for config in configs:
            if not config.enabled:
                continue
            try:
                conn = await self.connect_server(config)
                connections.append(conn)
            except MCPConnectionError as e:
                logger.warning("Skipping MCP server {}: {}", config.name, e)
        return connections

    def get_connection(self, server_name: str) -> MCPConnection | None:
        """Get a connection by server name.

        Args:
            server_name: Name of the MCP server

        Returns:
            MCPConnection if found, None otherwise
        """
        return self._connections.get(server_name)

    def get_all_tools(self) -> list[tuple[str, Tool]]:
        """Get all tools from all connected servers.

        Returns:
            List of (server_name, tool) tuples
        """
        return [
            (conn.server_name, tool) for conn in self._connections.values() for tool in conn.tools
        ]

    def get_tools_for_server(self, server_name: str) -> list[Tool]:
        """Get tools for a specific server.

        Args:
            server_name: Name of the MCP server

        Returns:
            List of tools

        Raises:
            MCPServerNotFoundError: If server not found
        """
        conn = self._connections.get(server_name)
        if not conn:
            raise MCPServerNotFoundError(f"MCP server not found: {server_name}")
        return conn.tools

    async def call_tool(
        self,
        server_name: str,
        tool_name: str,
        arguments: dict[str, Any],
    ) -> CallToolResult:
        """Call a tool on an MCP server.

        Args:
            server_name: Name of the MCP server
            tool_name: Name of the tool to call
            arguments: Tool arguments

        Returns:
            Tool execution result

        Raises:
            MCPServerNotFoundError: If server not found
            MCPToolError: If tool execution fails
        """
        conn = self._connections.get(server_name)
        if not conn:
            raise MCPServerNotFoundError(f"MCP server not found: {server_name}")

        logger.debug("Calling MCP tool: {}.{} with args: {}", server_name, tool_name, arguments)

        try:
            result = await conn.session.call_tool(tool_name, arguments)
            return result
        except Exception as e:
            logger.exception("MCP tool call failed: {}.{}", server_name, tool_name)
            raise MCPToolError(f"Tool '{tool_name}' failed: {e}") from e

    def format_tool_result(self, result: CallToolResult) -> str:
        """Format CallToolResult to a string.

        Args:
            result: Tool execution result

        Returns:
            Formatted string
        """
        if not result.content:
            return ""

        parts = []
        for content in result.content:
            if isinstance(content, TextContent):
                parts.append(content.text)
            else:
                # Handle other content types (images, etc.)
                parts.append(f"[{content.type} content]")

        return "\n".join(parts)

    async def disconnect_all(self) -> None:
        """Disconnect all MCP servers and cleanup resources."""
        logger.info("Disconnecting from all MCP servers")
        self._connections.clear()
        await self._exit_stack.aclose()
        # Create new exit stack for potential reconnection
        self._exit_stack = AsyncExitStack()

    async def __aenter__(self) -> MCPClientManager:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect_all()

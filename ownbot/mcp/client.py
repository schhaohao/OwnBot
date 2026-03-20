"""MCP client manager for connecting to MCP servers.

Provides functionality to connect to MCP servers via different transports
(stdio, SSE, HTTP) and manage tool discovery/execution.
"""

from __future__ import annotations

import json
import os
import uuid
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from typing import Any

from loguru import logger
import asyncio

import httpx
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
    session: Any  # ClientSession or SimpleHTTPMCPClient
    tools: list[Tool]
    exit_stack: AsyncExitStack


class SimpleHTTPMCPClient:
    """Simple HTTP-only MCP client for servers without SSE support.

    This client uses direct HTTP POST requests instead of streaming connections.
    Suitable for simple MCP servers that only support request/response pattern.
    """

    def __init__(self, url: str, timeout: float = 30.0) -> None:
        """Initialize the HTTP MCP client.

        Args:
            url: MCP server endpoint URL
            timeout: Request timeout in seconds
        """
        self.url = url.rstrip("/")
        self.timeout = timeout
        # Disable env proxy for localhost to avoid connection issues
        client_kwargs: dict[str, Any] = {"timeout": timeout}
        if "localhost" in self.url or "127.0.0.1" in self.url:
            client_kwargs["trust_env"] = False
        self._client = httpx.AsyncClient(**client_kwargs)
        self._request_id = 0
        self._initialized = False
        self._session_id: str | None = None
        self.server_info: dict[str, Any] = {}
        self.server_capabilities: dict[str, Any] = {}

    async def initialize(self) -> None:
        """Initialize the MCP session."""
        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {"listChanged": True},
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "ownbot-mcp-client",
                    "version": "1.0.0"
                }
            }
        }

        response_data = await self._send_request(request)
        if "error" in response_data:
            raise MCPConnectionError(f"Initialize failed: {response_data['error']}")

        result = response_data.get("result", {})
        self.server_info = result.get("serverInfo", {})
        self.server_capabilities = result.get("capabilities", {})
        self._initialized = True

        logger.debug("MCP server info: {}", self.server_info)
        logger.debug("MCP session ID: {}", self._session_id)

        # Send initialized notification (MCP protocol requires this)
        await self._send_notification("notifications/initialized", {})

        # Wait for server to process the state change
        await asyncio.sleep(0.5)

    async def _send_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """Send a JSON-RPC request to the server."""
        try:
            headers = {"Content-Type": "application/json"}
            # Include session ID if available (for session-aware servers)
            if self._session_id:
                headers["mcp-session-id"] = self._session_id

            resp = await self._client.post(
                self.url,
                json=request,
                headers=headers
            )
            resp.raise_for_status()

            # Extract session ID from response headers if present
            session_id = resp.headers.get("mcp-session-id")
            if session_id:
                self._session_id = session_id
                logger.debug("Received MCP session ID: {}", session_id)

            return resp.json()
        except httpx.HTTPError as e:
            raise MCPConnectionError(f"HTTP request failed: {e}") from e
        except json.JSONDecodeError as e:
            raise MCPConnectionError(f"Invalid JSON response: {e}") from e

    async def _send_notification(self, method: str, params: dict[str, Any]) -> None:
        """Send a JSON-RPC notification (no response expected)."""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        try:
            headers = {"Content-Type": "application/json"}
            if self._session_id:
                headers["mcp-session-id"] = self._session_id

            resp = await self._client.post(
                self.url,
                json=notification,
                headers=headers
            )
            # Extract session ID from response headers if present
            session_id = resp.headers.get("mcp-session-id")
            if session_id:
                self._session_id = session_id
        except Exception:
            # Notifications are best-effort
            pass

    async def list_tools(self) -> Any:
        """List available tools from the server."""
        if not self._initialized:
            raise MCPConnectionError("Client not initialized")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/list",
            "params": {}
        }

        response = await self._send_request(request)
        if "error" in response:
            raise MCPConnectionError(f"List tools failed: {response['error']}")

        # Create a simple object with .tools attribute
        result = response.get("result", {})
        tools_data = result.get("tools", [])

        # Convert to Tool objects
        tools = []
        for tool_data in tools_data:
            tool = Tool(
                name=tool_data.get("name", ""),
                description=tool_data.get("description", ""),
                inputSchema=tool_data.get("inputSchema", {})
            )
            tools.append(tool)

        return type('ToolsResult', (), {'tools': tools})()

    async def call_tool(self, tool_name: str, arguments: dict[str, Any]) -> CallToolResult:
        """Call a tool on the server."""
        if not self._initialized:
            raise MCPConnectionError("Client not initialized")

        self._request_id += 1
        request = {
            "jsonrpc": "2.0",
            "id": self._request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

        response = await self._send_request(request)
        if "error" in response:
            raise MCPToolError(f"Tool call failed: {response['error']}")

        result = response.get("result", {})
        content = result.get("content", [])
        is_error = result.get("isError", False)

        # Convert content to TextContent objects
        text_contents = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text_contents.append(TextContent(type="text", text=item.get("text", "")))
            elif isinstance(item, str):
                text_contents.append(TextContent(type="text", text=item))

        return CallToolResult(content=text_contents, isError=is_error)

    async def aclose(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()

    async def __aenter__(self) -> SimpleHTTPMCPClient:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.aclose()


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
                session = await self._connect_http(config)
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

    async def _connect_http(self, config: MCPServerConfig) -> SimpleHTTPMCPClient:
        """Connect via simple HTTP transport (POST-only, no SSE)."""
        if not config.url:
            raise MCPConnectionError(f"URL required for HTTP transport: {config.name}")

        logger.debug("Creating simple HTTP MCP client for {}", config.url)

        # Create simple HTTP client
        client = SimpleHTTPMCPClient(config.url, timeout=config.timeout)

        # Register with exit stack for cleanup
        await self._exit_stack.enter_async_context(client)

        # Initialize
        await client.initialize()
        logger.debug("Simple HTTP MCP client initialized for {}", config.name)
        return client

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

        # Close each session gracefully first (only for SimpleHTTPMCPClient)
        for name, conn in list(self._connections.items()):
            try:
                if hasattr(conn.session, 'aclose'):
                    await conn.session.aclose()
                    logger.debug("Closed MCP session: {}", name)
            except Exception as e:
                logger.debug("Error closing session {}: {}", name, e)

        self._connections.clear()

        # Small delay to let stdio servers process shutdown
        await asyncio.sleep(0.2)

        # Close exit stack (may raise exceptions for some transports)
        try:
            await self._exit_stack.aclose()
        except Exception as e:
            logger.debug("Exit stack cleanup error (expected for some transports): {}", e)

        # Create new exit stack for potential reconnection
        self._exit_stack = AsyncExitStack()

    async def __aenter__(self) -> MCPClientManager:
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """Async context manager exit."""
        await self.disconnect_all()

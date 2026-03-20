"""MCP (Model Context Protocol) integration for OwnBot.

Provides support for connecting to MCP servers and using their tools
within the OwnBot agent framework.
"""

from ownbot.mcp.client import MCPClientManager
from ownbot.mcp.tools import MCPToolAdapter

__all__ = ["MCPClientManager", "MCPToolAdapter"]

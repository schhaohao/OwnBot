"""Tools package for the OwnBot agent.

Provides tools that extend the agent's capabilities including filesystem
operations, shell execution, and web requests.
"""

from ownbot.agent.tools.base import Tool, ToolCall
from ownbot.agent.tools.filesystem import ListFilesTool, ReadFileTool, WriteFileTool
from ownbot.agent.tools.registry import ToolRegistry
from ownbot.agent.tools.shell import ShellTool
from ownbot.agent.tools.web import WebRequestTool

__all__ = [
    "Tool",
    "ToolCall",
    "ToolRegistry",
    "ListFilesTool",
    "ReadFileTool",
    "WriteFileTool",
    "ShellTool",
    "WebRequestTool",
]

# MCP tools are imported separately to avoid dependency issues
try:
    from ownbot.mcp.tools import MCPRegistry, MCPToolAdapter

    __all__.extend(["MCPToolAdapter", "MCPRegistry"])
except ImportError:
    pass

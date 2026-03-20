"""Type definitions for OwnBot.

Centralizes complex type definitions to improve code clarity and maintainability.
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import TYPE_CHECKING, Any, TypeAlias, TypeVar

if TYPE_CHECKING:
    pass

# =============================================================================
# Primitive Type Aliases
# =============================================================================

JsonDict: TypeAlias = dict[str, Any]
JsonList: TypeAlias = list[Any]
JsonValue: TypeAlias = str | int | float | bool | None | JsonDict | JsonList

# =============================================================================
# Message Types
# =============================================================================

MessageRole: TypeAlias = str  # "system" | "user" | "assistant" | "tool"
MessageContent: TypeAlias = str | list[dict[str, Any]] | None

# OpenAI-compatible message format
ChatMessage: TypeAlias = dict[str, Any]  # {"role": str, "content": str | list, ...}

# =============================================================================
# Tool Types
# =============================================================================

ToolParameters: TypeAlias = dict[str, Any]
ToolResult: TypeAlias = str
ToolExecutor: TypeAlias = Callable[[ToolParameters], Coroutine[Any, Any, ToolResult]]

# OpenAI tool definition format
ToolDefinition: TypeAlias = dict[str, Any]

# Tool call from LLM
ToolCallDict: TypeAlias = dict[str, Any]

# =============================================================================
# LLM Types
# =============================================================================

LLMModel: TypeAlias = str
LLMTemperature: TypeAlias = float
LLMMaxTokens: TypeAlias = int

# Usage statistics from LLM response
LLMUsage: TypeAlias = dict[str, int]

# =============================================================================
# Session Types
# =============================================================================

SessionKey: TypeAlias = str
SessionMetadata: TypeAlias = dict[str, Any]

# =============================================================================
# Channel Types
# =============================================================================

ChannelName: TypeAlias = str  # "telegram" | "whatsapp" | "cli"
ChatId: TypeAlias = str
SenderId: TypeAlias = str

# =============================================================================
# Skill Types
# =============================================================================

SkillName: TypeAlias = str
SkillDescription: TypeAlias = str
SkillPath: TypeAlias = str
SkillCategory: TypeAlias = str

# =============================================================================
# Configuration Types
# =============================================================================

ConfigValue: TypeAlias = str | int | float | bool | None | list | dict

# =============================================================================
# Progress Callback Types
# =============================================================================

ProgressCallback: TypeAlias = Callable[[str], Coroutine[Any, Any, None]] | None

# =============================================================================
# Generic Type Variables
# =============================================================================

T = TypeVar("T")
T_co = TypeVar("T_co", covariant=True)

# =============================================================================
# Agent Types
# =============================================================================

# ReAct parsing result
ReActResult: TypeAlias = dict[str, str | None]  # {"thought": ..., "action": ..., ...}

# Memory entry types
MemoryContent: TypeAlias = str
MemoryTags: TypeAlias = list[str]

# =============================================================================
# File System Types
# =============================================================================

FilePath: TypeAlias = str
FileContent: TypeAlias = str
DirectoryListing: TypeAlias = list[str]

# =============================================================================
# Media Types
# =============================================================================

MediaType: TypeAlias = str  # "image" | "voice" | "audio" | "file" | "video" | "animation"
MediaUrl: TypeAlias = str
MediaPath: TypeAlias = str

# =============================================================================
# Web Types
# =============================================================================

HttpMethod: TypeAlias = str  # "GET" | "POST" | "PUT" | "DELETE" | "PATCH"
HttpHeaders: TypeAlias = dict[str, str]
HttpParams: TypeAlias = dict[str, str | int | float | bool]

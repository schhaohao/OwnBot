"""OwnBot custom exceptions.

Provides a hierarchy of domain-specific exceptions for better error handling
and debugging.
"""

from __future__ import annotations


class OwnBotError(Exception):
    """Base exception for all OwnBot errors."""

    def __init__(self, message: str, *, details: dict | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}


# =============================================================================
# Configuration Errors
# =============================================================================


class ConfigurationError(OwnBotError):
    """Raised when there's an issue with configuration."""

    pass


class ConfigNotFoundError(ConfigurationError):
    """Raised when configuration file is not found."""

    pass


class ConfigValidationError(ConfigurationError):
    """Raised when configuration validation fails."""

    pass


# =============================================================================
# Channel Errors
# =============================================================================


class ChannelError(OwnBotError):
    """Base exception for channel-related errors."""

    pass


class ChannelNotConfiguredError(ChannelError):
    """Raised when a channel is not properly configured."""

    pass


class ChannelConnectionError(ChannelError):
    """Raised when channel connection fails."""

    pass


class ChannelSendError(ChannelError):
    """Raised when sending a message through channel fails."""

    pass


class TelegramError(ChannelError):
    """Raised for Telegram-specific errors."""

    pass


class WhatsAppError(ChannelError):
    """Raised for WhatsApp-specific errors."""

    pass


# =============================================================================
# LLM / Provider Errors
# =============================================================================


class LLMError(OwnBotError):
    """Base exception for LLM-related errors."""

    pass


class LLMConfigurationError(LLMError):
    """Raised when LLM is not properly configured (e.g., missing API key)."""

    pass


class LLMResponseError(LLMError):
    """Raised when LLM returns an error response."""

    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""

    pass


class LLMRateLimitError(LLMError):
    """Raised when LLM rate limit is exceeded."""

    pass


class ProviderNotFoundError(LLMError):
    """Raised when specified provider is not found."""

    pass


# =============================================================================
# Tool Errors
# =============================================================================


class ToolError(OwnBotError):
    """Base exception for tool execution errors."""

    pass


class ToolNotFoundError(ToolError):
    """Raised when a requested tool is not found."""

    pass


class ToolExecutionError(ToolError):
    """Raised when tool execution fails."""

    pass


class ToolValidationError(ToolError):
    """Raised when tool arguments validation fails."""

    pass


class ShellCommandError(ToolError):
    """Raised when shell command execution fails."""

    pass


class ShellCommandBlockedError(ShellCommandError):
    """Raised when a shell command is blocked for security reasons."""

    pass


class FileSystemError(ToolError):
    """Raised for filesystem operation errors."""

    pass


class PathNotAllowedError(FileSystemError):
    """Raised when attempting to access a path outside allowed directories."""

    pass


class FileNotFoundError(FileSystemError):
    """Raised when a file is not found."""

    pass


# =============================================================================
# Session Errors
# =============================================================================


class SessionError(OwnBotError):
    """Base exception for session-related errors."""

    pass


class SessionNotFoundError(SessionError):
    """Raised when a session is not found."""

    pass


class SessionSaveError(SessionError):
    """Raised when saving a session fails."""

    pass


class SessionLoadError(SessionError):
    """Raised when loading a session fails."""

    pass


# =============================================================================
# Skill Errors
# =============================================================================


class SkillError(OwnBotError):
    """Base exception for skill-related errors."""

    pass


class SkillNotFoundError(SkillError):
    """Raised when a skill is not found."""

    pass


class SkillParseError(SkillError):
    """Raised when parsing a skill file fails."""

    pass


class SkillValidationError(SkillError):
    """Raised when skill validation fails."""

    pass


# =============================================================================
# Retrieval / RAG Errors
# =============================================================================


class RetrievalError(OwnBotError):
    """Base exception for retrieval-related errors."""

    pass


class VectorDBError(RetrievalError):
    """Raised when vector database operation fails."""

    pass


class EmbeddingError(RetrievalError):
    """Raised when embedding generation fails."""

    pass


class IndexNotFoundError(RetrievalError):
    """Raised when vector index is not found."""

    pass


# =============================================================================
# Permission Errors
# =============================================================================


class PermissionError(OwnBotError):
    """Raised when a user doesn't have permission for an action."""

    pass


class AdminRequiredError(PermissionError):
    """Raised when admin privileges are required but not present."""

    pass


# =============================================================================
# Web / Network Errors
# =============================================================================


class WebError(OwnBotError):
    """Base exception for web-related errors."""

    pass


class WebRequestError(WebError):
    """Raised when a web request fails."""

    pass


class WebTimeoutError(WebError):
    """Raised when a web request times out."""

    pass


# =============================================================================
# MCP Errors
# =============================================================================


class MCPError(OwnBotError):
    """Base exception for MCP-related errors."""

    pass


class MCPConnectionError(MCPError):
    """Raised when MCP server connection fails."""

    pass


class MCPToolError(MCPError):
    """Raised when MCP tool execution fails."""

    pass


class MCPServerNotFoundError(MCPError):
    """Raised when an MCP server is not found."""

    pass

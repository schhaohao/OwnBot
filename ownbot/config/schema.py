"""Pydantic models for OwnBot configuration.

Defines the configuration schema with validation using Pydantic.
Supports both camelCase (JSON) and snake_case (Python) naming.
"""

from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel
from pydantic_settings import BaseSettings

from ownbot import constants


class BaseConfigModel(BaseModel):
    """Base model with camelCase alias support for JSON compatibility."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",  # Allow extra fields for forward compatibility
    )


class TelegramConfig(BaseConfigModel):
    """Telegram channel configuration."""

    enabled: bool = False
    token: str = Field(default="", description="Bot token from @BotFather")
    allow_from: list[str] = Field(
        default_factory=list,
        description="Allowed user IDs or usernames. Use ['*'] to allow all.",
    )
    proxy: str | None = Field(
        default=None,
        description='HTTP/SOCKS5 proxy URL, e.g., "http://127.0.0.1:7890"',
    )
    reply_to_message: bool = Field(
        default=False,
        description="If true, bot replies quote the original message",
    )
    group_policy: Literal["open", "mention"] = Field(
        default=constants.TELEGRAM_DEFAULT_GROUP_POLICY,
        description='"mention" responds when @mentioned or replied to, "open" responds to all',
    )

    @field_validator("token")
    @classmethod
    def validate_token(cls, v: str) -> str:
        """Validate token format if provided."""
        if v and ":" not in v and len(v) < 30:
            # Basic sanity check - Telegram tokens usually contain a colon
            # and are reasonably long
            pass  # Don't raise error, just a warning would be logged
        return v


class WhatsAppConfig(BaseConfigModel):
    """WhatsApp channel configuration."""

    enabled: bool = False
    bridge_url: str = Field(
        default=constants.WHATSAPP_DEFAULT_BRIDGE_URL,
        description="URL of the WhatsApp bridge WebSocket server",
    )
    bridge_token: str = Field(
        default="",
        description="Shared token for bridge authentication (optional but recommended)",
    )
    allow_from: list[str] = Field(
        default_factory=list,
        description="Allowed phone numbers. Use ['*'] to allow all.",
    )


class LLMConfig(BaseConfigModel):
    """LLM provider configuration."""

    api_base: str = Field(
        default=constants.DEFAULT_LLM_API_BASE,
        description="Base URL for the LLM API",
    )
    api_key: str = Field(
        default="",
        description="API key for authentication",
    )
    model: str = Field(
        default=constants.DEFAULT_LLM_MODEL,
        description="Model identifier to use",
    )
    temperature: float = Field(
        default=constants.DEFAULT_LLM_TEMPERATURE,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 to 2.0)",
    )
    max_tokens: int = Field(
        default=constants.DEFAULT_LLM_MAX_TOKENS,
        gt=0,
        description="Maximum tokens in response",
    )
    reasoning_effort: str | None = Field(
        default=constants.DEFAULT_LLM_REASONING_EFFORT,
        description="Reasoning effort for supported models (e.g., 'low', 'medium', 'high')",
    )
    timeout_s: float = Field(
        default=constants.DEFAULT_LLM_TIMEOUT_SECONDS,
        gt=0,
        description="Request timeout in seconds",
    )


class RetrievalConfig(BaseConfigModel):
    """RAG-based skill retrieval configuration."""

    enabled: bool = Field(
        default=True,
        description="Enable RAG-based skill retrieval",
    )
    use_milvus_lite: bool = Field(
        default=True,
        description="Use Milvus Lite (embedded) instead of Milvus server",
    )
    milvus_host: str = Field(
        default=constants.DEFAULT_MILVUS_HOST,
        description="Milvus server host (only used if use_milvus_lite=false)",
    )
    milvus_port: int = Field(
        default=constants.DEFAULT_MILVUS_PORT,
        gt=0,
        lt=65536,
        description="Milvus server port",
    )
    milvus_db_path: str = Field(
        default=constants.DEFAULT_MILVUS_DB_PATH,
        description="Path to Milvus Lite database file",
    )
    top_k: int = Field(
        default=constants.DEFAULT_RETRIEVAL_TOP_K,
        gt=0,
        description="Number of skills to retrieve",
    )
    collection_name: str = Field(
        default=constants.DEFAULT_MILVUS_COLLECTION,
        description="Milvus collection name",
    )
    embedding_model: str = Field(
        default=constants.DEFAULT_EMBEDDING_MODEL,
        description="Embedding model name",
    )


class MCPServerConfig(BaseConfigModel):
    """Configuration for a single MCP server."""

    name: str = Field(
        description="Unique name for this MCP server",
    )
    enabled: bool = Field(
        default=True,
        description="Whether this MCP server is enabled",
    )
    transport: Literal["stdio", "sse", "http"] = Field(
        default="stdio",
        description="Transport type: stdio, sse, or http",
    )
    command: str | None = Field(
        default=None,
        description="Command to run for stdio transport (e.g., 'python', 'node')",
    )
    args: list[str] = Field(
        default_factory=list,
        description="Arguments for stdio transport command",
    )
    url: str | None = Field(
        default=None,
        description="URL for sse/http transport",
    )
    env: dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables for the MCP server",
    )
    timeout: float = Field(
        default=30.0,
        gt=0,
        description="Request timeout in seconds",
    )


class MCPConfig(BaseConfigModel):
    """MCP (Model Context Protocol) configuration."""

    enabled: bool = Field(
        default=False,
        description="Enable MCP tool integration",
    )
    servers: list[MCPServerConfig] = Field(
        default_factory=list,
        description="List of MCP server configurations",
    )


class AppConfig(BaseSettings):
    """Root configuration for OwnBot."""

    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    admin_ids: list[str] = Field(
        default_factory=list,
        alias="adminIds",
        validation_alias="adminIds",
        description="Admin user IDs for sensitive commands like /restart",
    )

    @property
    def workspace_path(self) -> Path:
        """Get the expanded workspace path."""
        return Path(constants.DEFAULT_WORKSPACE_PATH).expanduser()

    model_config = ConfigDict(
        env_prefix=constants.ENV_PREFIX,
        env_nested_delimiter=constants.ENV_NESTED_DELIMITER,
        populate_by_name=True,
        extra="ignore",
    )

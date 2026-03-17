from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic_settings import BaseSettings


class Base(BaseModel):
    """Base model that accepts both camelCase and snake_case keys."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TelegramConfig(Base):
    """Telegram channel configuration."""

    enabled: bool = False
    token: str = ""  # Bot token from @BotFather
    allow_from: list[str] = Field(default_factory=list)  # Allowed user IDs or usernames
    proxy: str | None = (
        None  # HTTP/SOCKS5 proxy URL, e.g. "http://127.0.0.1:7890" or "socks5://127.0.0.1:1080"
    )
    reply_to_message: bool = False  # If true, bot replies quote the original message
    group_policy: Literal["open", "mention"] = "mention"  # "mention" responds when @mentioned or replied to, "open" responds to all


class WhatsAppConfig(Base):
    """WhatsApp channel configuration."""

    enabled: bool = False
    bridge_url: str = "ws://localhost:3001"  # URL of the WhatsApp bridge server
    bridge_token: str = ""  # Shared token for bridge auth (optional, recommended)
    allow_from: list[str] = Field(default_factory=list)  # Allowed phone numbers


class LLMConfig(Base):
    """LLM configuration."""

    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4.1-mini"
    temperature: float = 0.1
    max_tokens: int = 8192
    reasoning_effort: str | None = None


class RetrievalConfig(Base):
    """RAG-based skill retrieval configuration."""

    enabled: bool = True  # Enable RAG-based skill retrieval
    use_milvus_lite: bool = True  # Use Milvus Lite (embedded) instead of Milvus server
    milvus_host: str = "localhost"  # Milvus server host (only used if use_milvus_lite=false)
    milvus_port: int = 19530  # Milvus server port (only used if use_milvus_lite=false)
    milvus_db_path: str = "./milvus_data/ownbot.db"  # Milvus Lite database file path
    top_k: int = 50  # Number of skills to retrieve
    collection_name: str = "ownbot_skills"  # Milvus collection name
    embedding_model: str = "BAAI/bge-m3"  # Embedding model name (e.g., "BAAI/bge-m3", "all-MiniLM-L6-v2")
    # Note: embedding dimension is automatically detected from the model


class AppConfig(BaseSettings):
    """Root configuration for ownbot."""

    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    whatsapp: WhatsAppConfig = Field(default_factory=WhatsAppConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    retrieval: RetrievalConfig = Field(default_factory=RetrievalConfig)
    admin_ids: list[str] = Field(
        default_factory=list,
        alias="adminIds",  # Support both admin_ids and adminIds
        validation_alias="adminIds",
    )  # Admin user IDs for sensitive commands like /restart

    @property
    def workspace_path(self) -> Path:
        """Get expanded workspace path."""
        return Path("~/.ownbot/workspace").expanduser()

    model_config = ConfigDict(
        env_prefix="OWNBOT_",
        env_nested_delimiter="__",
        populate_by_name=True,
    )

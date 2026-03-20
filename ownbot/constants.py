"""OwnBot constants and configuration defaults.

This module contains all hardcoded values used across the application
to ensure consistency and easy maintenance.
"""

from __future__ import annotations

# =============================================================================
# Project Metadata
# =============================================================================

VERSION: str = "0.0.1"
PROJECT_NAME: str = "OwnBot"
DEFAULT_ENCODING: str = "utf-8"

# =============================================================================
# Path Constants
# =============================================================================

DEFAULT_CONFIG_PATH: str = "~/.ownbot/config.json"
DEFAULT_WORKSPACE_PATH: str = "~/.ownbot/workspace"
DEFAULT_DATA_PATH: str = "~/.ownbot"
DEFAULT_LOG_PATH: str = "~/.ownbot/logs"
DEFAULT_MEDIA_PATH: str = "~/.ownbot/media"
DEFAULT_CRON_PATH: str = "~/.ownbot/cron"
DEFAULT_SESSIONS_PATH: str = "~/.ownbot/workspace/sessions"

# =============================================================================
# LLM Defaults
# =============================================================================

DEFAULT_LLM_API_BASE: str = "https://api.openai.com/v1"
DEFAULT_LLM_MODEL: str = "gpt-4.1-mini"
DEFAULT_LLM_TEMPERATURE: float = 0.1
DEFAULT_LLM_MAX_TOKENS: int = 8192
DEFAULT_LLM_TIMEOUT_SECONDS: float = 60.0
DEFAULT_LLM_REASONING_EFFORT: str | None = None

# LLM Retry Configuration
LLM_RETRY_DELAYS: tuple[int, ...] = (1, 2, 4)
LLM_MAX_RETRIES: int = 3
LLM_TRANSIENT_ERROR_MARKERS: tuple[str, ...] = (
    "429",
    "rate limit",
    "500",
    "502",
    "503",
    "504",
    "overloaded",
    "timeout",
    "timed out",
    "connection",
    "server error",
    "temporarily unavailable",
)

# =============================================================================
# Agent Loop Configuration
# =============================================================================

AGENT_MAX_ITERATIONS: int = 40
AGENT_TOOL_RESULT_MAX_CHARS: int = 16_000
AGENT_SESSION_MESSAGE_LIMIT: int = 50

# =============================================================================
# Telegram Configuration
# =============================================================================

TELEGRAM_MAX_MESSAGE_LENGTH: int = 4000
TELEGRAM_REPLY_CONTEXT_MAX_LENGTH: int = 4000
TELEGRAM_DEFAULT_GROUP_POLICY: str = "mention"
TELEGRAM_CONNECTION_POOL_SIZE: int = 16
TELEGRAM_POOL_TIMEOUT: float = 5.0
TELEGRAM_CONNECT_TIMEOUT: float = 30.0
TELEGRAM_READ_TIMEOUT: float = 30.0
TELEGRAM_TYPING_INTERVAL: int = 4  # seconds
TELEGRAM_MEDIA_GROUP_WAIT: float = 0.6  # seconds

# =============================================================================
# WhatsApp Configuration
# =============================================================================

WHATSAPP_DEFAULT_BRIDGE_URL: str = "ws://localhost:3001"
WHATSAPP_DEFAULT_BRIDGE_PORT: str = "3001"
WHATSAPP_RECONNECT_DELAY: int = 5  # seconds
WHATSAPP_MAX_PROCESSED_IDS: int = 1000
WHATSAPP_BRIDGE_STARTUP_WAIT: int = 3  # seconds
WHATSAPP_BRIDGE_STOP_TIMEOUT: int = 5  # seconds

# =============================================================================
# Retrieval / RAG Configuration
# =============================================================================

DEFAULT_EMBEDDING_MODEL: str = "BAAI/bge-m3"
DEFAULT_MILVUS_COLLECTION: str = "ownbot_skills"
DEFAULT_MILVUS_HOST: str = "localhost"
DEFAULT_MILVUS_PORT: int = 19530
DEFAULT_MILVUS_DB_PATH: str = "./milvus_data/ownbot.db"
DEFAULT_RETRIEVAL_TOP_K: int = 50

# Embedding Model Dimensions
EMBEDDING_DIMENSIONS: dict[str, int] = {
    # sentence-transformers models
    "all-MiniLM-L6-v2": 384,
    "all-MiniLM-L12-v2": 384,
    "all-distilroberta-v1": 768,
    "all-mpnet-base-v2": 768,
    "paraphrase-MiniLM-L6-v2": 384,
    "paraphrase-multilingual-MiniLM-L12-v2": 384,
    "distiluse-base-multilingual-cased-v1": 512,
    "distiluse-base-multilingual-cased-v2": 512,
    # BAAI models (FlagEmbedding)
    "BAAI/bge-m3": 1024,
    "BAAI/bge-large-zh": 1024,
    "BAAI/bge-base-zh": 768,
    "BAAI/bge-small-zh": 512,
    "BAAI/bge-large-en": 1024,
    "BAAI/bge-base-en": 768,
}

# =============================================================================
# HTTP / Web Configuration
# =============================================================================

DEFAULT_HTTP_TIMEOUT: float = 30.0
DEFAULT_WEB_REQUEST_TIMEOUT: float = 30.0
MAX_WEB_RESPONSE_LENGTH: int = 10_000

# =============================================================================
# File System Configuration
# =============================================================================

MAX_FILE_READ_SIZE: int = 10_000_000  # 10MB
ALLOWED_SHELL_COMMANDS: frozenset[str] = frozenset()  # Empty = allow all (for now)
BLOCKED_SHELL_COMMANDS: frozenset[str] = frozenset(
    {
        "rm -rf /",
        "rm -rf ~",
        "rm -rf /*",
        ":(){ :|:& };:",  # fork bomb
        "dd if=/dev/zero",
    }
)

# =============================================================================
# Session Configuration
# =============================================================================

SESSION_FILE_NAME: str = "session.jsonl"
MAX_SESSION_CACHE_SIZE: int = 1000

# =============================================================================
# Logging Configuration
# =============================================================================

LOG_ROTATION_SIZE: str = "10 MB"
LOG_RETENTION_DAYS: str = "7 days"
LOG_LEVEL_CONSOLE: str = "INFO"
LOG_LEVEL_FILE: str = "DEBUG"

# =============================================================================
# Small Talk Patterns (for skill filtering)
# =============================================================================

SMALL_TALK_PATTERNS: tuple[str, ...] = (
    r"^(hi|hello|hey|yo)\b",
    r"^(你好|您好|嗨|哈喽|在吗|早上好|中午好|晚上好)$",
    r"^(thanks|thank you|谢谢|多谢|收到|好的|ok|okay|嗯|嗯嗯)$",
)

# =============================================================================
# Environment Variable Prefixes
# =============================================================================

ENV_PREFIX: str = "OWNBOT_"
ENV_NESTED_DELIMITER: str = "__"

# =============================================================================
# Message Content
# =============================================================================

EMPTY_MESSAGE_PLACEHOLDER: str = "[empty message]"
VOICE_MESSAGE_PLACEHOLDER: str = "[Voice Message: Transcription not available for WhatsApp yet]"

# =============================================================================
# Runtime Context Tag
# =============================================================================

RUNTIME_CONTEXT_TAG: str = "[runtime-context]"

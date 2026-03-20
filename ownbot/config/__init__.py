"""Configuration management for OwnBot.

Provides configuration loading, saving, and path utilities.
"""

from ownbot.config.loader import (
    config_exists,
    get_config_path,
    load_config,
    save_config,
    set_config_path,
)
from ownbot.config.paths import (
    get_cron_dir,
    get_data_dir,
    get_logs_dir,
    get_media_dir,
    get_sessions_dir,
    get_skills_dir,
    get_workspace_dir,
)
from ownbot.config.schema import (
    AppConfig,
    LLMConfig,
    RetrievalConfig,
    TelegramConfig,
    WhatsAppConfig,
)

__all__ = [
    # Schema classes
    "AppConfig",
    "TelegramConfig",
    "WhatsAppConfig",
    "LLMConfig",
    "RetrievalConfig",
    # Loader functions
    "load_config",
    "save_config",
    "get_config_path",
    "set_config_path",
    "config_exists",
    # Path functions
    "get_data_dir",
    "get_workspace_dir",
    "get_sessions_dir",
    "get_media_dir",
    "get_cron_dir",
    "get_logs_dir",
    "get_skills_dir",
]

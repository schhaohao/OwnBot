"""Configuration loading and saving utilities.

Provides functions to load configuration from JSON files and environment variables,
and save configuration back to files.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from ownbot.config.schema import AppConfig
from ownbot.constants import DEFAULT_CONFIG_PATH
from ownbot.exceptions import ConfigNotFoundError, ConfigValidationError

# Global configuration path override
_config_path: Path | None = None

# Default configuration path as a constant
DEFAULT_CONFIG: Final[Path] = Path(DEFAULT_CONFIG_PATH).expanduser()


def get_config_path() -> Path:
    """Get the current configuration file path.

    Returns:
        Path to the configuration file. Uses the override if set,
        otherwise returns the default path.
    """
    if _config_path is not None:
        return _config_path
    return DEFAULT_CONFIG


def set_config_path(path: Path) -> None:
    """Set a custom configuration file path.

    Args:
        path: The path to use for configuration loading/saving.
    """
    global _config_path
    _config_path = path.expanduser().resolve()


def load_config(path: Path | None = None) -> AppConfig:
    """Load configuration from a JSON file.

    Args:
        path: Optional path to the config file. If not provided,
              uses get_config_path().

    Returns:
        Loaded and validated AppConfig instance.

    Raises:
        ConfigValidationError: If the configuration file is invalid.
    """
    cfg_path = path or get_config_path()

    if not cfg_path.exists():
        # Return default config if file doesn't exist
        return AppConfig()

    try:
        with cfg_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise ConfigValidationError(f"Invalid JSON in configuration file {cfg_path}: {e}") from e
    except OSError as e:
        raise ConfigNotFoundError(f"Cannot read configuration file {cfg_path}: {e}") from e

    try:
        return AppConfig(**data)
    except Exception as e:
        raise ConfigValidationError(f"Invalid configuration in {cfg_path}: {e}") from e


def save_config(config: AppConfig, path: Path | None = None) -> Path:
    """Save configuration to a JSON file.

    Args:
        config: The configuration to save.
        path: Optional path to save to. If not provided,
              uses get_config_path().

    Returns:
        Path to the saved configuration file.

    Raises:
        OSError: If the file cannot be written.
    """
    cfg_path = path or get_config_path()

    # Ensure parent directory exists
    cfg_path.parent.mkdir(parents=True, exist_ok=True)

    # Convert to JSON-serializable dict
    data = config.model_dump(mode="json", by_alias=True)

    with cfg_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        f.write("\n")  # Trailing newline

    return cfg_path


def config_exists(path: Path | None = None) -> bool:
    """Check if a configuration file exists.

    Args:
        path: Optional path to check. If not provided,
              uses get_config_path().

    Returns:
        True if the configuration file exists, False otherwise.
    """
    cfg_path = path or get_config_path()
    return cfg_path.exists()

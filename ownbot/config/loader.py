from __future__ import annotations

import json
from pathlib import Path

from ownbot.config.schema import AppConfig


_config_path: Path | None = None


def get_config_path() -> Path:
    """Get the current config path."""
    if _config_path:
        return _config_path
    return Path("~/.ownbot/config.json").expanduser()


def set_config_path(path: Path) -> None:
    """Set the config path."""
    global _config_path
    _config_path = path


def load_config() -> AppConfig:
    """Load config from file."""
    path = get_config_path()
    if not path.exists():
        return AppConfig()
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return AppConfig(**data)


def save_config(config: AppConfig) -> Path:
    """Save config to file."""
    path = get_config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(config.model_dump(mode="json"), f, indent=2, ensure_ascii=False)
    return path

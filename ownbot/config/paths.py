from __future__ import annotations

from pathlib import Path


def get_data_dir() -> Path:
    """Get the data directory."""
    return Path("~/.ownbot").expanduser()


def get_media_dir(channel: str | None = None) -> Path:
    """Get the media directory."""
    path = get_data_dir() / "media"
    if channel:
        path /= channel
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cron_dir() -> Path:
    """Get the cron directory."""
    path = get_data_dir() / "cron"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    """Get the logs directory."""
    path = get_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_workspace_dir() -> Path:
    """Get the workspace directory."""
    path = get_data_dir() / "workspace"
    path.mkdir(parents=True, exist_ok=True)
    return path

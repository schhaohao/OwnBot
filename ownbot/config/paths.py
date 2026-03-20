"""Path utilities for OwnBot.

Provides standardized paths for data, media, logs, workspace, etc.
"""

from __future__ import annotations

from pathlib import Path

from ownbot import constants


def get_data_dir() -> Path:
    """Get the base data directory.

    Returns:
        Path to ~/.ownbot
    """
    path = Path(constants.DEFAULT_DATA_PATH).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_workspace_dir() -> Path:
    """Get the workspace directory.

    Returns:
        Path to ~/.ownbot/workspace
    """
    path = get_data_dir() / "workspace"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_sessions_dir() -> Path:
    """Get the sessions directory.

    Returns:
        Path to ~/.ownbot/workspace/sessions
    """
    path = get_workspace_dir() / "sessions"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_media_dir(channel: str | None = None) -> Path:
    """Get the media storage directory.

    Args:
        channel: Optional channel name for subdirectory (e.g., 'telegram', 'whatsapp')

    Returns:
        Path to media directory, optionally with channel subdirectory
    """
    path = get_data_dir() / "media"
    if channel:
        path /= channel
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_cron_dir() -> Path:
    """Get the cron jobs directory.

    Returns:
        Path to ~/.ownbot/cron
    """
    path = get_data_dir() / "cron"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_logs_dir() -> Path:
    """Get the logs directory.

    Returns:
        Path to ~/.ownbot/logs
    """
    path = get_data_dir() / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_skills_dir() -> Path:
    """Get the workspace skills directory.

    Returns:
        Path to ~/.ownbot/workspace/skills
    """
    path = get_workspace_dir() / "skills"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_whatsapp_auth_dir() -> Path:
    """Get the WhatsApp authentication directory.

    Returns:
        Path to ~/.ownbot/workspace/whatsapp-auth
    """
    path = get_workspace_dir() / "whatsapp-auth"
    path.mkdir(parents=True, exist_ok=True)
    return path

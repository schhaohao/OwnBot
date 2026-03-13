from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class _Base(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class TelegramConfig(_Base):
    enabled: bool = False
    token: str = ""
    allow_from: list[str] = Field(default_factory=list)
    proxy: str | None = None
    group_policy: Literal["open", "mention"] = "mention"


class LLMConfig(_Base):
    api_base: str = "https://api.openai.com/v1"
    api_key: str = ""
    model: str = "gpt-4.1-mini"
    timeout_s: float = 60.0


class AppConfig(_Base):
    telegram: TelegramConfig = Field(default_factory=TelegramConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)


_CURRENT_CONFIG_PATH: Path | None = None


def set_config_path(path: Path) -> None:
    global _CURRENT_CONFIG_PATH
    _CURRENT_CONFIG_PATH = path


def get_config_path() -> Path:
    if _CURRENT_CONFIG_PATH is not None:
        return _CURRENT_CONFIG_PATH
    return Path.home() / ".ownbot" / "config.json"


def load_config(path: Path | None = None) -> AppConfig:
    cfg_path = path or get_config_path()
    if cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            data = json.load(f)
        return AppConfig.model_validate(data)
    return AppConfig()


def save_config(cfg: AppConfig, path: Path | None = None) -> Path:
    cfg_path = path or get_config_path()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg.model_dump(by_alias=True), f, indent=2, ensure_ascii=False)
    return cfg_path


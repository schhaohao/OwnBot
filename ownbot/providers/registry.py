from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProviderSpec:
    """LLM provider specification."""

    name: str
    keywords: list[str]
    is_local: bool = False
    is_gateway: bool = False
    is_oauth: bool = False
    default_api_base: str | None = None
    detect_by_base_keyword: str | None = None


PROVIDERS: list[ProviderSpec] = [
    ProviderSpec(
        name="openai",
        keywords=["gpt", "openai"],
        default_api_base="https://api.openai.com/v1",
    ),
    ProviderSpec(
        name="litellm",
        keywords=["litellm"],
        is_gateway=True,
        default_api_base="https://api.openai.com/v1",
    ),
]


def find_by_name(name: str) -> ProviderSpec | None:
    """Find provider spec by name."""
    for spec in PROVIDERS:
        if spec.name == name:
            return spec
    return None


def get_provider_spec(name: str) -> ProviderSpec:
    """Get provider spec by name, raising if not found."""
    spec = find_by_name(name)
    if not spec:
        raise ValueError(f"Unknown provider: {name}")
    return spec

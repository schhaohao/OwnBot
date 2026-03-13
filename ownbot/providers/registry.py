from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass
class ProviderSpec:
    """LLM provider specification."""
    name: str
    keywords: List[str]
    is_local: bool = False
    is_gateway: bool = False
    is_oauth: bool = False
    default_api_base: Optional[str] = None
    detect_by_base_keyword: Optional[str] = None


PROVIDERS: List[ProviderSpec] = [
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


def find_by_name(name: str) -> Optional[ProviderSpec]:
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

"""Skill data models."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class SkillMetadata:
    """Skill metadata from YAML frontmatter."""
    
    emoji: str = "🔧"
    requires: dict[str, Any] = field(default_factory=dict)
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SkillMetadata:
        """Create metadata from dictionary."""
        return cls(
            emoji=data.get("emoji", "🔧"),
            requires=data.get("requires", {}),
        )


@dataclass
class Skill:
    """A skill definition loaded from SKILL.md."""
    
    name: str
    description: str
    content: str
    metadata: SkillMetadata
    path: Path | None = None
    
    @property
    def system_prompt_addition(self) -> str:
        """Generate system prompt addition for this skill."""
        lines = [
            f"\n## Skill: {self.name} {self.metadata.emoji}",
            f"\n{self.description}",
            "\n### Instructions:",
            self.content,
        ]
        return "\n".join(lines)
    
    def to_tool_description(self) -> dict[str, Any]:
        """Convert skill to a tool-like description for the LLM."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": f"The query for {self.name} skill",
                        }
                    },
                    "required": ["query"],
                },
            },
        }


@dataclass
class SkillSummary:
    """A lightweight skill summary used for progressive disclosure."""

    name: str
    description: str
    metadata: SkillMetadata
    path: Path | None = None

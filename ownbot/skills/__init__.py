"""Skills module for OwnBot.

Skills extend the bot's capabilities through markdown-based instructions.
Each skill is defined in a SKILL.md file with YAML frontmatter.
"""

from ownbot.skills.loader import SkillLoader
from ownbot.skills.models import Skill, SkillMetadata

__all__ = ["SkillLoader", "Skill", "SkillMetadata"]

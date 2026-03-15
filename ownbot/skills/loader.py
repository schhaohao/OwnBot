"""Skill loader for parsing SKILL.md files."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml
from loguru import logger

from ownbot.skills.models import Skill, SkillMetadata


class SkillLoader:
    """Load skills from SKILL.md files."""
    
    # YAML frontmatter pattern: ---\n...\n---
    FRONTMATTER_PATTERN = re.compile(
        r'^---\s*\n(.*?)\n---\s*\n(.*)$',
        re.DOTALL | re.MULTILINE
    )
    
    def __init__(self, skills_dir: Path | None = None):
        """Initialize skill loader.
        
        Args:
            skills_dir: Directory containing skill subdirectories.
                       Defaults to built-in skills directory.
        """
        if skills_dir is None:
            skills_dir = Path(__file__).parent
        self.skills_dir = skills_dir
        self._skills: dict[str, Skill] = {}
    
    def load_skill(self, skill_path: Path) -> Skill | None:
        """Load a single skill from a directory or file.
        
        Args:
            skill_path: Path to skill directory or SKILL.md file.
            
        Returns:
            Loaded Skill or None if loading failed.
        """
        if skill_path.is_dir():
            skill_file = skill_path / "SKILL.md"
        else:
            skill_file = skill_path
        
        if not skill_file.exists():
            logger.warning("Skill file not found: {}", skill_file)
            return None
        
        try:
            content = skill_file.read_text(encoding="utf-8")
            return self._parse_skill(content, skill_file)
        except Exception as e:
            logger.error("Failed to load skill from {}: {}", skill_file, e)
            return None
    
    def _parse_skill(self, content: str, path: Path | None = None) -> Skill | None:
        """Parse skill content with YAML frontmatter.
        
        Args:
            content: Raw SKILL.md content.
            path: Optional path for reference.
            
        Returns:
            Parsed Skill or None if parsing failed.
        """
        match = self.FRONTMATTER_PATTERN.match(content.strip())
        
        if not match:
            logger.warning("Invalid skill format: missing YAML frontmatter")
            return None
        
        yaml_content, markdown_content = match.groups()
        
        try:
            frontmatter = yaml.safe_load(yaml_content) or {}
        except yaml.YAMLError as e:
            logger.error("Failed to parse YAML frontmatter: {}", e)
            return None
        
        # Extract required fields
        name = frontmatter.get("name")
        description = frontmatter.get("description", "")
        
        if not name:
            logger.warning("Skill missing required 'name' field")
            return None
        
        # Parse metadata
        metadata_dict = frontmatter.get("metadata", {})
        if "ownbot" in metadata_dict:
            metadata_dict = metadata_dict["ownbot"]
        metadata = SkillMetadata.from_dict(metadata_dict)
        
        return Skill(
            name=name,
            description=description,
            content=markdown_content.strip(),
            metadata=metadata,
            path=path,
        )
    
    def load_all_skills(self) -> dict[str, Skill]:
        """Load all skills from the skills directory.
        
        Returns:
            Dictionary mapping skill names to Skill objects.
        """
        self._skills = {}
        
        if not self.skills_dir.exists():
            logger.warning("Skills directory not found: {}", self.skills_dir)
            return self._skills
        
        for item in self.skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith("_"):
                skill = self.load_skill(item)
                if skill:
                    self._skills[skill.name] = skill
                    logger.info("Loaded skill: {} {}", skill.name, skill.metadata.emoji)
        
        return self._skills
    
    def get_skill(self, name: str) -> Skill | None:
        """Get a loaded skill by name.
        
        Args:
            name: Skill name.
            
        Returns:
            Skill or None if not found.
        """
        return self._skills.get(name)
    
    def list_skills(self) -> list[Skill]:
        """List all loaded skills.
        
        Returns:
            List of Skill objects.
        """
        return list(self._skills.values())
    
    def get_system_prompt_additions(self) -> str:
        """Get system prompt additions for all loaded skills.
        
        Returns:
            Combined system prompt additions.
        """
        if not self._skills:
            return ""
        
        lines = ["\n\n# Available Skills\n"]
        for skill in self._skills.values():
            lines.append(skill.system_prompt_addition)
        
        return "\n".join(lines)

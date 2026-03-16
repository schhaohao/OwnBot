from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional

from loguru import logger

from ownbot.retrieval import SkillRetriever
from ownbot.skills import SkillLoader


class ContextBuilder:
    """
    Builds context for LLM calls by combining session history, system prompts, and current input.
    
    Implements ReAct (Reasoning + Acting) architecture for better complex task handling.
    
    Skill Loading Strategy (Progressive Disclosure):
    1. RAG Retrieval: Search for top 50 relevant skills by query
    2. Summary Loading: Load only skill names and descriptions (not full content)
    3. On-Demand Loading: Agent uses read_file tool to load full SKILL.md when needed
    """

    _RUNTIME_CONTEXT_TAG = "[runtime-context]"

    def __init__(
        self,
        workspace: Path,
        skills_dir: Optional[Path] = None,
        enable_rag: bool = True,
        use_milvus_lite: bool = True,
        milvus_host: str = "localhost",
        milvus_port: int = 19530,
        milvus_db_path: str = "./milvus_data/ownbot.db",
        embedding_model: str = "BAAI/bge-m3",
    ):
        """
        Initialize the context builder.
        
        Args:
            workspace: Workspace directory
            skills_dir: Directory containing skills (defaults to built-in skills)
            enable_rag: Whether to enable RAG-based skill retrieval
            use_milvus_lite: Use Milvus Lite (embedded) instead of Milvus server
            milvus_host: Milvus server host (only used if use_milvus_lite=false)
            milvus_port: Milvus server port (only used if use_milvus_lite=false)
            milvus_db_path: Path to Milvus Lite database file
            embedding_model: Embedding model name for RAG (e.g., "BAAI/bge-m3")
        """
        self.workspace = workspace
        
        # Skill directories
        if skills_dir is None:
            skills_dir = Path(__file__).parent.parent / "skills"
        self.skills_dir = skills_dir
        
        # Traditional skill loader (for on-demand loading)
        self.skill_loader = SkillLoader(skills_dir)
        
        # RAG retriever (for initial skill discovery)
        self.enable_rag = enable_rag
        self.skill_retriever: Optional[SkillRetriever] = None
        if enable_rag:
            try:
                self.skill_retriever = SkillRetriever(
                    skills_dir=skills_dir,
                    use_milvus_lite=use_milvus_lite,
                    milvus_host=milvus_host,
                    milvus_port=milvus_port,
                    milvus_db_path=milvus_db_path,
                    embedding_model=embedding_model,
                )
            except Exception as e:
                # Fall back to traditional loading if RAG fails
                self.enable_rag = False
                self.skill_retriever = None
        
        # Pre-build index on startup if RAG is enabled
        if self.enable_rag and self.skill_retriever:
            try:
                logger.info("Pre-building skill index on startup...")
                count = self.skill_retriever.build_index()
                logger.info("Successfully pre-built index with {} skills", count)
            except Exception as e:
                logger.warning("Failed to pre-build index on startup: {}", e)
                logger.warning("Index will be built on first search")
    
    def build_messages(
        self,
        history: List[dict[str, Any]],
        current_message: str,
        media: Optional[List[str]] = None,
        channel: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> List[dict[str, Any]]:
        """
        Build a list of messages for the LLM using ReAct architecture.
        
        Args:
            history: Previous messages in the session.
            current_message: The current user message.
            media: Optional list of media file paths.
            channel: The channel the message came from.
            chat_id: The chat ID.
        
        Returns:
            A list of message dicts for the LLM.
        """
        messages: List[dict[str, Any]] = []

        # ReAct System prompt
        system_prompt = self._build_system_prompt(current_message)
        messages.append({"role": "system", "content": system_prompt.strip()})

        # Add history
        messages.extend(history)

        # Add current message
        user_content: Any = current_message
        if media:
            user_content = []
            user_content.append({"type": "text", "text": current_message})
            for m in media:
                user_content.append({"type": "image_url", "image_url": {"url": m}})

        messages.append({"role": "user", "content": user_content})

        return messages
    
    def _build_system_prompt(self, current_message: str) -> str:
        """
        Build the system prompt with progressive skill disclosure.
        
        Strategy:
        1. If RAG enabled: Search top 50 skills, show only names+descriptions
        2. Agent decides which skill to use
        3. Agent loads full skill content with read_file tool
        """
        # Base ReAct instructions
        base_prompt = """You are OwnBot, a helpful AI assistant using ReAct (Reasoning + Acting) architecture.

Your goal is to provide accurate and useful responses to user queries by thinking step by step.

IMPORTANT: You must ALWAYS use the following exact format for your responses:

Thought: [Your thinking process here]

Then either:
1. If you need to use a tool:
   Action: [tool_name]
   Action Input: [JSON parameters]

2. If you have the final answer:
   Final Answer: [Your response to the user]

Rules:
- ALWAYS start with "Thought:"
- When giving final answer, ALWAYS use "Final Answer:" prefix
- Never output both Action and Final Answer in the same response
- Be concise and helpful in your Final Answer
- Do not include the thought process in the Final Answer

Example 1 (using tool):
Thought: The user wants to know the weather in Tokyo. I need to use the web_request tool to get this information.
Action: web_request
Action Input: {"url": "https://api.weather.com/tokyo", "method": "GET"}

Example 2 (final answer):
Thought: I have successfully retrieved the weather information for Tokyo.
Final Answer: The weather in Tokyo is 22°C and sunny today.

Guidelines:
- Always think before acting
- Be concise in your thoughts
- Only use tools when necessary
- If you're unsure, ask for clarification
- Respect user privacy
"""
        
        # Add skills section using progressive disclosure
        skills_prompt = self._build_skills_prompt(current_message)
        if skills_prompt:
            base_prompt += "\n\n" + skills_prompt
        
        return base_prompt
    
    def _build_skills_prompt(self, current_message: str) -> str:
        """
        Build the skills section of the system prompt.
        
        Uses RAG to find relevant skills, then shows only summaries.
        The agent must use read_file to load full skill content.
        """
        if not self.enable_rag or self.skill_retriever is None:
            # Fallback: list all skills without RAG
            return self._build_fallback_skills_prompt()
        
        try:
            # RAG search for top 50 relevant skills
            relevant_skills = self.skill_retriever.search(current_message, top_k=50)
            
            if not relevant_skills:
                return ""
            
            lines = ["## Available Skills\n"]
            lines.append(f"Based on your query, here are {len(relevant_skills)} relevant skills you can use:\n")
            
            for skill in relevant_skills:
                emoji = skill.metadata.get("emoji", "🔧")
                lines.append(f"{emoji} **{skill.name}**: {skill.description}")
            
            lines.append("\n### How to Use Skills")
            lines.append("1. Choose the most relevant skill from the list above")
            lines.append("2. Read its full documentation using the `read_file` tool:")
            lines.append(f"   Action: read_file")
            lines.append(f"   Action Input: {{\"path\": \"/skills/{{skill_name}}/SKILL.md\"}}")
            lines.append("3. Follow the instructions in the SKILL.md file")
            lines.append("4. Use appropriate tools to complete the task")
            
            return "\n".join(lines)
            
        except Exception as e:
            # Fallback if RAG fails
            return self._build_fallback_skills_prompt()
    
    def _build_fallback_skills_prompt(self) -> str:
        """Fallback: List all available skills without RAG."""
        try:
            self.skill_loader.load_all_skills()
            skills = self.skill_loader.list_skills()
            
            if not skills:
                return ""
            
            lines = ["## Available Skills\n"]
            lines.append("You have access to the following skills:\n")
            
            for skill in skills:
                emoji = skill.metadata.emoji if skill.metadata else "🔧"
                lines.append(f"{emoji} **{skill.name}**: {skill.description}")
            
            lines.append("\nTo use a skill, read its SKILL.md file with the `read_file` tool.")
            
            return "\n".join(lines)
            
        except Exception:
            return ""
    
    def build_index(self, force_rebuild: bool = False) -> int:
        """
        Build or rebuild the skill vector index.
        
        Args:
            force_rebuild: If True, rebuild even if index exists
            
        Returns:
            Number of skills indexed
        """
        if self.skill_retriever is None:
            raise RuntimeError("RAG retriever not initialized")
        
        return self.skill_retriever.build_index(force_rebuild=force_rebuild)

from __future__ import annotations

import re
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
        builtin_skills_dir: Optional[Path] = None,
        workspace_skills_dir: Optional[Path] = None,
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
            builtin_skills_dir: Directory containing built-in skills bundled with OwnBot
            workspace_skills_dir: Directory containing user-installed skills in the workspace
            enable_rag: Whether to enable RAG-based skill retrieval
            use_milvus_lite: Use Milvus Lite (embedded) instead of Milvus server
            milvus_host: Milvus server host (only used if use_milvus_lite=false)
            milvus_port: Milvus server port (only used if use_milvus_lite=false)
            milvus_db_path: Path to Milvus Lite database file
            embedding_model: Embedding model name for RAG (e.g., "BAAI/bge-m3")
        """
        self.workspace = workspace.resolve()

        if builtin_skills_dir is None:
            builtin_skills_dir = Path(__file__).parent.parent / "skills"
        if workspace_skills_dir is None:
            workspace_skills_dir = self.workspace / "skills"

        self.builtin_skills_dir = builtin_skills_dir.resolve()
        self.workspace_skills_dir = workspace_skills_dir.resolve()
        self.workspace_skills_dir.mkdir(parents=True, exist_ok=True)

        # Keep a compatibility alias for callers that expect a single skills dir.
        self.skills_dir = self.workspace_skills_dir

        self.builtin_skill_loader = SkillLoader(self.builtin_skills_dir)
        self.workspace_skill_loader = SkillLoader(self.workspace_skills_dir)
        try:
            self.builtin_skill_loader.load_all_skills()
            logger.info(
                "Loaded {} built-in skill(s) from {}",
                len(self.builtin_skill_loader.list_skills()),
                self.builtin_skills_dir,
            )
        except Exception as e:
            logger.warning("Failed to load built-in skills from {}: {}", self.builtin_skills_dir, e)
        
        # RAG retriever (for initial skill discovery)
        self.enable_rag = enable_rag
        self.skill_retriever: Optional[SkillRetriever] = None
        if enable_rag:
            try:
                self.skill_retriever = SkillRetriever(
                    skills_dir=self.workspace_skills_dir,
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
        logger.info("Final system prompt:\n{}", system_prompt.strip())
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

    def add_assistant_message(
        self,
        messages: List[dict[str, Any]],
        content: Optional[str],
        tool_calls: Optional[List[dict[str, Any]]] = None,
        reasoning_content: Optional[str] = None,
    ) -> List[dict[str, Any]]:
        """Append an assistant message in the format expected by the provider."""
        msg: dict[str, Any] = {"role": "assistant"}
        if content:
            msg["content"] = content
        if tool_calls:
            msg["tool_calls"] = tool_calls
        if reasoning_content:
            msg["reasoning_content"] = reasoning_content
        messages.append(msg)
        return messages

    def add_tool_result(
        self,
        messages: List[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str,
    ) -> List[dict[str, Any]]:
        """Append a tool result message so the next LLM turn can observe it."""
        messages.append({
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": f"Observation: {result}",
        })
        return messages

    def parse_react_response(self, content: str) -> dict[str, Any]:
        """Parse a ReAct-formatted assistant response."""
        result = {
            "thought": None,
            "action": None,
            "action_input": None,
            "final_answer": None,
        }

        if not content:
            return result

        result["thought"] = self._extract_thought(content)
        action = self._extract_section(content, "Action")
        action_input = self._extract_section(content, "Action Input")
        final_answer = self._extract_final_answer(content)

        if action:
            result["action"] = action.strip()
        if action_input:
            result["action_input"] = self._strip_code_fence(action_input.strip())
        if final_answer:
            result["final_answer"] = final_answer.strip()

        return result

    def _extract_thought(self, content: str) -> Optional[str]:
        """Extract the Thought section, falling back to a short preview."""
        normalized = content.strip()
        if not normalized:
            return None

        patterns = (
            r"(?:^|\n)\s*Thought:\s*(.*?)(?=\n\s*(?:Action:|Final Answer:|$))",
            r"Thought:\s*(.+?)(?=\n[A-Za-z_][A-Za-z_ ]*:|$)",
        )
        for pattern in patterns:
            match = re.search(pattern, normalized, re.DOTALL | re.IGNORECASE)
            if match:
                thought = match.group(1).strip()
                if thought:
                    return thought

        if all(marker not in normalized for marker in ("Thought:", "Action:", "Final Answer:")):
            first_line = normalized.splitlines()[0].strip()
            return first_line or None

        return None

    def _extract_final_answer(self, content: str) -> Optional[str]:
        """Extract the final answer, tolerating slightly off-format model output."""
        normalized = content.strip()
        if not normalized:
            return None

        patterns = (
            r"(?:^|\n)\s*Final Answer:\s*(.*?)(?=\n[A-Za-z_][A-Za-z_ ]*:|$)",
            r"\*\*Final Answer\*\*:\s*(.*?)(?=\n[A-Za-z_][A-Za-z_ ]*:|$)",
        )
        for pattern in patterns:
            match = re.search(pattern, normalized, re.DOTALL | re.IGNORECASE)
            if match:
                answer = match.group(1).strip()
                if answer:
                    return answer

        if "Thought:" in normalized and "Action:" not in normalized:
            last_thought_idx = normalized.rfind("Thought:")
            after_thought = normalized[last_thought_idx + len("Thought:"):].strip()
            if after_thought:
                return after_thought

        if all(marker not in normalized for marker in ("Thought:", "Action:", "Final Answer:")):
            return normalized

        return None

    def _extract_section(self, content: str, section_name: str) -> Optional[str]:
        """Extract a labeled ReAct section from the content."""
        if not content:
            return None

        pattern = rf"(?:^|\n)\s*{re.escape(section_name)}:\s*(.*?)(?=\n[A-Za-z_][A-Za-z_ ]*:|$)"
        match = re.search(pattern, content, re.DOTALL | re.IGNORECASE)
        if not match:
            return None

        value = match.group(1).strip()
        return value or None

    @staticmethod
    def _strip_code_fence(text: str) -> str:
        """Remove surrounding markdown fences from Action Input content."""
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
        if fenced:
            return fenced.group(1).strip()
        return text
    
    def _build_system_prompt(self, current_message: str) -> str:
        """
        Build the system prompt with progressive skill disclosure.
        
        Strategy:
        1. Built-in skills are always listed in the system prompt
        2. Workspace skills are retrieved via RAG and shown on demand
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

        builtin_prompt = self._build_builtin_skills_prompt()
        if builtin_prompt:
            base_prompt += "\n\n" + builtin_prompt

        workspace_prompt = self._build_workspace_skills_prompt(current_message)
        if workspace_prompt:
            base_prompt += "\n\n" + workspace_prompt
        
        return base_prompt
    
    def _build_builtin_skills_prompt(self) -> str:
        """Build the built-in skills section of the system prompt."""
        try:
            self.builtin_skill_loader.load_all_skills()
            skills = self.builtin_skill_loader.list_skills()

            if not skills:
                return ""

            lines = ["## Built-in Skills\n"]
            lines.append("These built-in skills are always available and do not use vector retrieval:\n")

            for skill in skills:
                emoji = skill.metadata.emoji if skill.metadata else "🔧"
                skill_doc_path = skill.path if skill.path else (self.builtin_skills_dir / skill.name / "SKILL.md")
                lines.append(f"{emoji} **{skill.name}**: {skill.description} (doc path: {skill_doc_path})")

            lines.append("\nIf you need a built-in skill, read the exact doc path shown above with the `read_file` tool.")
            return "\n".join(lines)
        except Exception as e:
            logger.warning("Failed to build built-in skills prompt: {}", e)
            return ""

    def _build_workspace_skills_prompt(self, current_message: str) -> str:
        """
        Build the workspace skills section of the system prompt.
        
        Uses RAG to find relevant user-installed skills, then shows only summaries.
        The agent must use read_file to load full skill content.
        """
        if not self.enable_rag or self.skill_retriever is None:
            return ""
        
        try:
            relevant_skills = self.skill_retriever.search(current_message, top_k=50)
            logger.info("Skill retrieval query: {}", current_message)
            
            if not relevant_skills:
                logger.info("Workspace skill retrieval returned no matches")
                return ""

            log_preview = [
                f"{skill.name} score={skill.score:.4f} path={skill.path}"
                for skill in relevant_skills[:10]
            ]
            logger.info(
                "Skill retrieval results (top {}): {}",
                min(len(log_preview), len(relevant_skills)),
                " | ".join(log_preview),
            )
            
            lines = ["## Workspace Skills\n"]
            lines.append(
                f"Based on your query, here are {len(relevant_skills)} relevant user-installed skills from ~/.ownbot/workspace/skills:\n"
            )
            
            for skill in relevant_skills:
                emoji = skill.metadata.get("emoji", "🔧")
                skill_doc_path = Path(skill.path) / "SKILL.md"
                lines.append(f"{emoji} **{skill.name}**: {skill.description} (doc path: {skill_doc_path})")
            
            lines.append("\n### How to Use Workspace Skills")
            lines.append("1. Choose the most relevant skill from the list above")
            lines.append("2. Read its full documentation using the exact doc path shown above with the `read_file` tool:")
            lines.append(f"   Action: read_file")
            lines.append(f"   Action Input: {{\"path\": \"/Users/example/.ownbot/workspace/skills/<skill_name>/SKILL.md\"}}")
            lines.append("3. Follow the instructions in the SKILL.md file")
            lines.append("4. Use appropriate tools to complete the task")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.warning("Failed to build workspace skills prompt: {}", e)
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

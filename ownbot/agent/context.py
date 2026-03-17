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
    _SMALL_TALK_PATTERNS = (
        r"^(hi|hello|hey|yo)\b",
        r"^(你好|您好|嗨|哈喽|在吗|早上好|中午好|晚上好)$",
        r"^(thanks|thank you|谢谢|多谢|收到|好的|ok|okay|嗯|嗯嗯)$",
    )

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
                if count > 0:
                    self.skill_retriever.warm_up_query_embedding()
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

        # Native tool-calling System prompt
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
        """Extract the explicit Thought section from a legacy ReAct response."""
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
        Build the system prompt with built-in skills plus progressive workspace retrieval.
        
        Strategy:
        1. Built-in skills are always listed in the system prompt
        2. Workspace skills are retrieved via RAG and shown on demand
        3. Agent uses native tool calling when tools are needed
        """
        base_prompt = """You are OwnBot, a helpful AI assistant.

Your job is to answer the user's request accurately, using tools only when they are actually needed.

Response rules:
- If you can answer directly, reply with a normal assistant message.
- If you need a tool, use the model's native tool calling. Do not write `Thought:`, `Action:`, or `Action Input:` in normal responses.
- Keep internal reasoning private. Do not expose chain-of-thought.
- For greetings, acknowledgements, and casual small talk, answer directly and do not read any skill file.
- Do not use a skill unless it is relevant to the user's request.
- When you use a skill, copy the exact `doc_path` shown below. Never invent or rewrite a skill path from the skill name.
- Built-in skills and workspace skills are different sources. Never assume a built-in skill also exists in workspace, and never assume a workspace skill also exists as a built-in skill.
- Only the skills listed under `Workspace Skills` exist in `~/.ownbot/workspace/skills/`.
- If a skill appears in both sections, use the exact path from the section you intentionally chose.
- Prefer answering from your existing knowledge for trivial conversation instead of opening a skill document.
- If you are unsure which skill source to use, prefer the exact built-in path unless a workspace skill is explicitly listed for this query.
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
            lines.append("These built-in skills are always available and do not use vector retrieval.\n")
            lines.append("Use them only when relevant, and copy the exact `doc_path`.\n")

            for skill in skills:
                emoji = skill.metadata.emoji if skill.metadata else "🔧"
                skill_doc_path = skill.path if skill.path else (self.builtin_skills_dir / skill.name / "SKILL.md")
                lines.append(
                    f"- source=builtin | name={skill.name} | emoji={emoji} | doc_path={skill_doc_path} | description={skill.description}"
                )

            lines.append("\nImportant: built-in skills do not live under `~/.ownbot/workspace/skills/` unless a matching workspace skill is separately listed below.")
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
        if self._is_small_talk_or_greeting(current_message):
            logger.info("Skipping workspace skill retrieval for small-talk query: {}", current_message)
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
                f"Based on your query, here are {len(relevant_skills)} relevant user-installed skills from ~/.ownbot/workspace/skills.\n"
            )
            lines.append("Only these listed skills may be read from workspace for this query.\n")
            
            for skill in relevant_skills:
                emoji = skill.metadata.get("emoji", "🔧")
                skill_doc_path = Path(skill.path) / "SKILL.md"
                lines.append(
                    f"- source=workspace | name={skill.name} | emoji={emoji} | doc_path={skill_doc_path} | description={skill.description}"
                )
            
            lines.append("\n### How to Use Workspace Skills")
            lines.append("1. Choose a skill only if it is relevant to the user's request.")
            lines.append("2. Read its full documentation only by copying the exact `doc_path` shown above with `read_file`.")
            lines.append("3. Never construct a workspace path from a skill name that is not listed in this section.")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.warning("Failed to build workspace skills prompt: {}", e)
            return ""

    @classmethod
    def _is_small_talk_or_greeting(cls, message: str) -> bool:
        """Heuristic to avoid retrieving skills for casual greetings."""
        text = (message or "").strip().lower()
        if not text:
            return True
        return any(re.match(pattern, text, re.IGNORECASE) for pattern in cls._SMALL_TALK_PATTERNS)
    
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

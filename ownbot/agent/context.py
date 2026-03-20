from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from loguru import logger

from ownbot.retrieval import SkillRetriever
from ownbot.skills import SkillLoader, SkillSummary


class ContextBuilder:
    """Builds context for LLM calls by combining session history, system prompts, and current input.

    Implements ReAct (Reasoning + Acting) architecture for better complex task handling.

    Skill Loading Strategy (Progressive Disclosure):
    1. Load all built-in and workspace skill metadata on startup
    2. Expose only metadata in the system prompt
    3. Let the agent read full SKILL.md files on demand via read_file
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
        builtin_skills_dir: Path | None = None,
        workspace_skills_dir: Path | None = None,
        enable_rag: bool = True,
        use_milvus_lite: bool = True,
        milvus_host: str = "localhost",
        milvus_port: int = 19530,
        milvus_db_path: str = "./milvus_data/ownbot.db",
        embedding_model: str = "BAAI/bge-m3",
    ):
        """Initialize the context builder.

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
        self.builtin_skill_summaries: list[SkillSummary] = []
        self.workspace_skill_summaries: list[SkillSummary] = []
        self._builtin_skill_catalog_fingerprint: tuple[tuple[Any, ...], ...] = ()
        self._workspace_skill_catalog_fingerprint: tuple[tuple[Any, ...], ...] = ()
        self._load_skill_catalogs()

        # Keep the vector retriever available for explicit indexing/search flows.
        self.enable_rag = enable_rag
        self.skill_retriever: SkillRetriever | None = None
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
                logger.warning("Failed to initialize skill retriever: {}", e)
                self.enable_rag = False
                self.skill_retriever = None

    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        media: list[str] | None = None,
        channel: str | None = None,
        chat_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """Build a list of messages for the LLM using ReAct architecture.

        Args:
            history: Previous messages in the session.
            current_message: The current user message.
            media: Optional list of media file paths.
            channel: The channel the message came from.
            chat_id: The chat ID.

        Returns:
            A list of message dicts for the LLM.
        """
        messages: list[dict[str, Any]] = []
        self._refresh_skill_catalogs_if_needed()

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
        messages: list[dict[str, Any]],
        content: str | None,
        tool_calls: list[dict[str, Any]] | None = None,
        reasoning_content: str | None = None,
    ) -> list[dict[str, Any]]:
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
        messages: list[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str,
    ) -> list[dict[str, Any]]:
        """Append a tool result message so the next LLM turn can observe it."""
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call_id,
                "name": tool_name,
                "content": f"Observation: {result}",
            }
        )
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

    def _extract_thought(self, content: str) -> str | None:
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

    def _extract_final_answer(self, content: str) -> str | None:
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
            after_thought = normalized[last_thought_idx + len("Thought:") :].strip()
            if after_thought:
                return after_thought

        if all(marker not in normalized for marker in ("Thought:", "Action:", "Final Answer:")):
            return normalized

        return None

    def _extract_section(self, content: str, section_name: str) -> str | None:
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
        """Build the system prompt with metadata-only skill catalogs."""
        base_prompt = """You are OwnBot, a helpful AI assistant.

Your job is to answer the user's request accurately, using tools only when they are actually needed.

Response rules:
- If you can answer directly, reply with a normal assistant message.
- If you need a tool, use the model's native tool calling. Do not write `Thought:`, `Action:`, or `Action Input:` in normal responses.
- Keep internal reasoning private. Do not expose chain-of-thought.
- For greetings, acknowledgements, and casual small talk, answer directly and do not read any skill file.
- Do not use a skill unless it is relevant to the user's request.
- Skills are progressively disclosed: only metadata is loaded into the prompt. Read the full `SKILL.md` with `read_file` only after you decide a skill is relevant.
- When you use a skill, copy the exact `doc_path` shown below. Never invent or rewrite a skill path from the skill name.
- Built-in skills and workspace skills are different sources with different paths. Never assume a built-in skill also exists in workspace, and never assume a workspace skill also exists as a built-in skill.
- If a skill appears in both sections, use the exact path from the section you intentionally chose.
- Prefer answering from your existing knowledge for trivial conversation instead of opening a skill document.
- If you are unsure which skill source to use, prefer the exact built-in path unless the user is clearly asking for a workspace-installed skill.
"""

        skills_prompt = self._build_skill_catalog_prompt()
        if skills_prompt:
            base_prompt += "\n\n" + skills_prompt

        return base_prompt

    def _load_skill_catalogs(self) -> None:
        """Load metadata-only skill catalogs for built-in and workspace skills."""
        try:
            self.builtin_skill_loader.load_all_skill_summaries()
            self.builtin_skill_summaries = sorted(
                self.builtin_skill_loader.list_skill_summaries(),
                key=lambda skill: skill.name.lower(),
            )
            logger.info(
                "Loaded {} built-in skill summary/summaries from {}",
                len(self.builtin_skill_summaries),
                self.builtin_skills_dir,
            )
        except Exception as e:
            logger.warning(
                "Failed to load built-in skill summaries from {}: {}", self.builtin_skills_dir, e
            )
            self.builtin_skill_summaries = []

        try:
            self.workspace_skill_loader.load_all_skill_summaries()
            self.workspace_skill_summaries = sorted(
                self.workspace_skill_loader.list_skill_summaries(),
                key=lambda skill: skill.name.lower(),
            )
            logger.info(
                "Loaded {} workspace skill summary/summaries from {}",
                len(self.workspace_skill_summaries),
                self.workspace_skills_dir,
            )
        except Exception as e:
            logger.warning(
                "Failed to load workspace skill summaries from {}: {}", self.workspace_skills_dir, e
            )
            self.workspace_skill_summaries = []

        self._builtin_skill_catalog_fingerprint = self._compute_skill_catalog_fingerprint(
            self.builtin_skills_dir
        )
        self._workspace_skill_catalog_fingerprint = self._compute_skill_catalog_fingerprint(
            self.workspace_skills_dir
        )

    def _refresh_skill_catalogs_if_needed(self) -> None:
        """Refresh skill catalogs only when the skill directories have changed."""
        builtin_fingerprint = self._compute_skill_catalog_fingerprint(self.builtin_skills_dir)
        workspace_fingerprint = self._compute_skill_catalog_fingerprint(self.workspace_skills_dir)

        if (
            builtin_fingerprint == self._builtin_skill_catalog_fingerprint
            and workspace_fingerprint == self._workspace_skill_catalog_fingerprint
        ):
            return

        logger.info(
            "Skill catalog change detected; refreshing summaries (builtin_changed={}, workspace_changed={})",
            builtin_fingerprint != self._builtin_skill_catalog_fingerprint,
            workspace_fingerprint != self._workspace_skill_catalog_fingerprint,
        )
        self._load_skill_catalogs()

    @staticmethod
    def _compute_skill_catalog_fingerprint(skills_dir: Path) -> tuple[tuple[Any, ...], ...]:
        """Return a lightweight fingerprint for a skills directory."""
        if not skills_dir.exists():
            return ()

        fingerprint: list[tuple[Any, ...]] = []
        for item in sorted(skills_dir.iterdir(), key=lambda path: path.name.lower()):
            if not item.is_dir() or item.name.startswith("_"):
                continue

            skill_file = item / "SKILL.md"
            if skill_file.exists():
                stat = skill_file.stat()
                fingerprint.append((item.name, True, stat.st_mtime_ns, stat.st_size))
            else:
                fingerprint.append((item.name, False))

        return tuple(fingerprint)

    def _build_skill_catalog_prompt(self) -> str:
        """Build the metadata-only skill catalog for the system prompt."""
        if not self.builtin_skill_summaries and not self.workspace_skill_summaries:
            return ""

        lines = ["## Skill Catalog\n"]
        lines.append(
            "The entries below are metadata only. Read the full `SKILL.md` only when a skill is relevant.\n"
        )

        lines.append("### Built-in Skills\n")
        if self.builtin_skill_summaries:
            lines.append(
                "These skills ship with OwnBot. Their files live in the repository, not in the workspace.\n"
            )
            lines.extend(
                self._format_skill_summary_lines(self.builtin_skill_summaries, source="builtin")
            )
        else:
            lines.append("No built-in skills found.\n")

        lines.append("\n### Workspace Skills\n")
        if self.workspace_skill_summaries:
            lines.append(
                "These skills are user-installed under `~/.ownbot/workspace/skills/`. Use the exact `doc_path` shown below.\n"
            )
            lines.extend(
                self._format_skill_summary_lines(self.workspace_skill_summaries, source="workspace")
            )
        else:
            lines.append("No workspace skills installed.\n")

        lines.append(
            "\nChoose skills yourself based on relevance; there is no query-time vector filtering in this prompt."
        )
        return "\n".join(lines)

    @staticmethod
    def _format_skill_summary_lines(skills: list[SkillSummary], source: str) -> list[str]:
        """Format skill summaries for prompt inclusion."""
        lines: list[str] = []
        for skill in skills:
            emoji = skill.metadata.emoji if skill.metadata else "🔧"
            if skill.path is None:
                continue
            lines.append(
                f"- source={source} | name={skill.name} | emoji={emoji} | doc_path={skill.path} | description={skill.description}"
            )
        return lines

    @classmethod
    def _is_small_talk_or_greeting(cls, message: str) -> bool:
        """Heuristic to avoid retrieving skills for casual greetings."""
        text = (message or "").strip().lower()
        if not text:
            return True
        return any(re.match(pattern, text, re.IGNORECASE) for pattern in cls._SMALL_TALK_PATTERNS)

    def build_index(self, force_rebuild: bool = False) -> int:
        """Build or rebuild the skill vector index.

        Args:
            force_rebuild: If True, rebuild even if index exists

        Returns:
            Number of skills indexed
        """
        if self.skill_retriever is None:
            raise RuntimeError("RAG retriever not initialized")

        return self.skill_retriever.build_index(force_rebuild=force_rebuild)

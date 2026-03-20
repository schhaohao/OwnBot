"""Agent Loop - Core processing engine for OwnBot.

Implements the ReAct (Reasoning + Acting) architecture with native
tool calling support and session management.
"""

from __future__ import annotations

import asyncio
import collections
import contextlib
import json
import re
from collections.abc import Callable
from datetime import datetime
from typing import Any

from loguru import logger

from ownbot.agent.context import ContextBuilder
from ownbot.agent.tools import (
    ListFilesTool,
    ReadFileTool,
    ShellTool,
    ToolRegistry,
    WebRequestTool,
    WriteFileTool,
)
from ownbot.bus import InboundMessage, MessageBus, OutboundMessage
from ownbot.config import AppConfig
from ownbot.constants import (
    AGENT_MAX_ITERATIONS,
    AGENT_SESSION_MESSAGE_LIMIT,
    AGENT_TOOL_RESULT_MAX_CHARS,
)
from ownbot.providers import LiteLLMProvider
from ownbot.providers.base import GenerationSettings, ToolCallRequest
from ownbot.session import SessionManager
from ownbot.types import JsonDict
from ownbot.utils import create_agent_logger

# Type alias for progress notification callback
StepCallback = Callable[[str], None] | None


class AgentLoop:
    """Core processing engine for the OwnBot agent.

    The agent loop:
    1. Receives messages from the bus
    2. Builds context with history, memory, and skills
    3. Calls the LLM with tool definitions
    4. Executes tool calls and collects results
    5. Sends responses back through the bus

    Attributes:
        bus: Message bus for communication
        cfg: Application configuration
        provider: LLM provider for completions
        model: Model identifier to use
        max_iterations: Maximum tool call iterations per request
    """

    def __init__(self, cfg: AppConfig, bus: MessageBus) -> None:
        """Initialize the agent loop.

        Args:
            cfg: Application configuration
            bus: Message bus for communication
        """
        self.cfg = cfg
        self.bus = bus

        # Initialize LLM provider
        self.provider = LiteLLMProvider(
            api_key=cfg.llm.api_key,
            api_base=cfg.llm.api_base,
        )
        self.provider.generation = GenerationSettings(
            temperature=cfg.llm.temperature,
            max_tokens=cfg.llm.max_tokens,
            reasoning_effort=cfg.llm.reasoning_effort,
        )
        self.model = cfg.llm.model

        # Paths and limits
        self.workspace = cfg.workspace_path
        self.max_iterations = AGENT_MAX_ITERATIONS
        self._tool_result_max_chars = AGENT_TOOL_RESULT_MAX_CHARS

        # Initialize components
        self.context = self._create_context_builder()
        self.sessions = self._create_session_manager()
        self.tools = self._create_tool_registry()

        # Session message limit for sliding window
        self._session_message_limit = AGENT_SESSION_MESSAGE_LIMIT

        # Initialize MCP client manager if enabled
        self.mcp_manager: Any | None = None
        self.mcp_registry: Any | None = None
        if self.cfg.mcp.enabled:
            from ownbot.mcp import MCPClientManager

            self.mcp_manager = MCPClientManager()

        # Runtime state
        self._running = False
        self._active_tasks: dict[str, list[asyncio.Task]] = collections.defaultdict(list)
        self._session_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)

    def _create_context_builder(self) -> ContextBuilder:
        """Create the context builder with configuration."""
        return ContextBuilder(
            workspace=self.workspace,
            enable_rag=self.cfg.retrieval.enabled,
            use_milvus_lite=self.cfg.retrieval.use_milvus_lite,
            milvus_host=self.cfg.retrieval.milvus_host,
            milvus_port=self.cfg.retrieval.milvus_port,
            milvus_db_path=self.cfg.retrieval.milvus_db_path,
            embedding_model=self.cfg.retrieval.embedding_model,
        )

    def _create_session_manager(self) -> SessionManager:
        """Create the session manager."""
        return SessionManager(workspace=self.workspace)

    def _create_tool_registry(self) -> ToolRegistry:
        """Create and populate the tool registry."""
        registry = ToolRegistry()

        # Register filesystem tools
        fs_kwargs = {
            "workspace": self.workspace,
            "skills_dir": self.context.workspace_skills_dir,
            "builtin_skills_dir": self.context.builtin_skills_dir,
        }
        registry.register(ListFilesTool(**fs_kwargs))
        registry.register(ReadFileTool(**fs_kwargs))
        registry.register(WriteFileTool(**fs_kwargs))

        # Register other tools
        registry.register(ShellTool())
        registry.register(WebRequestTool())

        return registry

    async def initialize_mcp(self) -> None:
        """Initialize MCP connections and register MCP tools.

        This method connects to all configured MCP servers and
        registers their tools with the tool registry.
        """
        if not self.cfg.mcp.enabled or not self.mcp_manager:
            return

        # Prevent duplicate initialization
        if self.mcp_registry and self.mcp_manager._connections:
            logger.debug("MCP already initialized, skipping")
            return

        # Delayed import to avoid circular imports
        from ownbot.mcp.tools import MCPRegistry

        logger.info("Initializing MCP connections...")

        try:
            # Connect to all configured servers
            await self.mcp_manager.connect_all(self.cfg.mcp.servers)

            if not self.mcp_manager._connections:
                logger.warning("No MCP servers connected")
                return

            # Create registry and load tools
            self.mcp_registry = MCPRegistry(self.mcp_manager)
            await self.mcp_registry.load_tools()

            # Register all MCP tools
            for tool in self.mcp_registry.get_tools():
                try:
                    self.tools.register(tool)
                except ValueError as e:
                    logger.warning("Failed to register MCP tool {}: {}", tool.name, e)

            logger.info(
                "MCP initialization complete. Registered {} tools from {} servers",
                len(self.mcp_registry.get_tools()),
                len(self.mcp_manager._connections),
            )

        except Exception as e:
            logger.exception("Failed to initialize MCP: {}", e)
            logger.warning("Continuing without MCP tools")

    @staticmethod
    def _strip_think(text: str | None) -> str | None:
        """Remove <think>...</think> blocks from content.

        Some models (like DeepSeek-R1) embed reasoning in these tags.
        """
        if not text:
            return None
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None

    @staticmethod
    def _extract_think(text: str | None) -> str | None:
        """Extract content from <think>...</think> blocks."""
        if not text:
            return None
        matches = re.findall(r"<think>([\s\S]*?)</think>", text)
        parts = [match.strip() for match in matches if match.strip()]
        return "\n\n".join(parts) if parts else None

    @staticmethod
    def _serialize_for_log(data: Any) -> str:
        """Serialize data to JSON for logging."""
        try:
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except (TypeError, ValueError):
            return str(data)

    async def _execute_tool(
        self,
        tool_call: ToolCallRequest,
    ) -> tuple[str, str]:
        """Execute a single tool call with error handling.

        Args:
            tool_call: The tool call request

        Returns:
            Tuple of (tool_name, result_or_error)
        """
        try:
            result = await self.tools.execute(tool_call.name, tool_call.arguments)
            # Truncate long results
            if len(result) > self._tool_result_max_chars:
                result = result[: self._tool_result_max_chars] + "\n... (truncated)"
            return tool_call.name, result
        except Exception as e:
            logger.warning("Tool {} failed: {}", tool_call.name, e)
            return tool_call.name, f"Error: {e}"

    async def _run_agent_loop(  # noqa: PLR0912
        self,
        messages: list[JsonDict],
        agent_logger: Any | None = None,
        step_callback: StepCallback = None,
    ) -> tuple[str | None, list[str], list[JsonDict]]:
        """Run the agent iteration loop.

        Args:
            messages: Initial message list
            agent_logger: Optional logger for agent observability
            step_callback: Optional callback to notify progress to user

        Returns:
            Tuple of (final_content, tools_used, final_messages)
        """
        iteration = 0
        final_content: str | None = None
        tools_used: list[str] = []

        while iteration < self.max_iterations:
            iteration += 1

            if agent_logger:
                agent_logger.start_iteration(iteration)

            # Notify user about thinking (with step info after first iteration)
            if step_callback:
                if iteration == 1:
                    await step_callback("🤔 正在思考问题...")
                else:
                    await step_callback(f"🔄 第 {iteration} 轮思考...")

            tool_defs = self.tools.get_definitions()

            if agent_logger:
                agent_logger.log_progress("Calling LLM...")

            # Call LLM
            response = await self.provider.chat_with_retry(
                messages=messages,
                tools=tool_defs,
                model=self.model,
            )

            # Extract and log reasoning
            reasoning = response.reasoning_content or self._extract_think(response.content)
            if agent_logger and reasoning:
                agent_logger.log_reasoning(reasoning)

            clean_content = self._strip_think(response.content) or ""

            # Handle tool calls
            if response.has_tool_calls:
                if agent_logger and clean_content:
                    agent_logger.log_thought(clean_content)

                # Add assistant message with tool calls
                tool_call_dicts = [tc.to_openai_tool_call() for tc in response.tool_calls]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts
                )

                # Log actions
                if agent_logger:
                    for tc in response.tool_calls:
                        agent_logger.log_action(tc.name, tc.arguments)

                # Notify user about tool calls
                if step_callback:
                    tool_names = [tc.name for tc in response.tool_calls]
                    if len(tool_names) == 1:
                        tool_name = tool_names[0]
                        # Format MCP tool names nicely (mcp_server_tool -> server:tool)
                        if tool_name.startswith("mcp_"):
                            parts = tool_name.split("_")
                            if len(parts) >= 3:
                                # parts[0] = 'mcp', parts[1] = server, parts[2:] = tool parts
                                server = parts[1]
                                tool = "_".join(parts[2:])
                                tool_name = f"{server}:{tool}"
                        await step_callback(f"🔧 步骤 {iteration}: 调用 {tool_name}...")
                    else:
                        display_names = []
                        for name in tool_names:
                            if name.startswith("mcp_"):
                                parts = name.split("_")
                                if len(parts) >= 3:
                                    server = parts[1]
                                    tool = "_".join(parts[2:])
                                    display_names.append(f"{server}:{tool}")
                                else:
                                    display_names.append(name)
                            else:
                                display_names.append(name)
                        tools_str = ", ".join(display_names)
                        await step_callback(
                            f"🔧 步骤 {iteration}: 调用 {len(tool_names)} 个工具 ({tools_str})..."
                        )

                # Execute tools concurrently
                tool_tasks = [self._execute_tool(tc) for tc in response.tool_calls]
                results = await asyncio.gather(*tool_tasks)

                # Process results
                for tc, (tool_name, result) in zip(response.tool_calls, results, strict=False):
                    tools_used.append(tool_name)
                    logger.debug("Tool {} result: {} chars", tool_name, len(result))

                    if agent_logger:
                        agent_logger.log_observation(result)

                    messages = self.context.add_tool_result(messages, tc.id, tool_name, result)

                # Notify user about completion with result summary
                if step_callback:
                    # Summarize results
                    success_count = sum(
                        1 for _, result in results if not result.startswith("Error:")
                    )
                    total_count = len(results)
                    if total_count == 1:
                        _, result = results[0]
                        status = "✅" if not result.startswith("Error:") else "❌"
                        await step_callback(f"{status} 工具执行完成，继续思考...")  # noqa: RUF001
                    else:
                        await step_callback(
                            f"✅ {success_count}/{total_count} 个工具执行成功，继续思考..."  # noqa: RUF001
                        )

            else:
                # No tool calls - final answer
                final_content = clean_content or response.content

                if agent_logger:
                    agent_logger.log_final_answer(final_content or "(no content)")

                messages = self.context.add_assistant_message(messages, response.content)
                break

        # Handle max iterations reached
        if final_content is None and iteration >= self.max_iterations:
            logger.warning("Max iterations ({}) reached", self.max_iterations)
            final_content = (
                f"I reached the maximum number of iterations ({self.max_iterations}) "
                "without completing the task. Please try breaking it into smaller steps."
            )

        return final_content, tools_used, messages

    async def run(self) -> None:
        """Run the main agent loop."""
        self._running = True
        logger.info("Agent loop started")

        # Initialize MCP connections
        await self.initialize_mcp()

        while self._running:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_inbound(),
                    timeout=1.0,
                )
            except TimeoutError:
                continue
            except asyncio.CancelledError:
                break

            cmd = msg.content.strip().lower()

            if cmd == "/stop":
                await self._handle_stop(msg)
            elif cmd == "/restart":
                if not self._is_admin(msg.sender_id):
                    await self.bus.publish_outbound(
                        OutboundMessage(
                            channel=msg.channel,
                            chat_id=msg.chat_id,
                            content="Permission denied. Only admins can restart.",
                        )
                    )
                    continue
                await self._handle_restart(msg)
            else:
                task = asyncio.create_task(self._dispatch(msg))
                self._active_tasks[msg.session_key].append(task)
                task.add_done_callback(lambda t, k=msg.session_key: self._cleanup_task(t, k))

        logger.info("Agent loop stopped")

    def _cleanup_task(self, task: asyncio.Task, session_key: str) -> None:
        """Remove completed task from tracking."""
        tasks = self._active_tasks.get(session_key, [])
        if task in tasks:
            tasks.remove(task)

    def _is_admin(self, sender_id: str) -> bool:
        """Check if sender is an admin."""
        admin_ids = getattr(self.cfg, "admin_ids", [])
        if not admin_ids:
            return True  # No admin restriction if not configured
        return sender_id in admin_ids

    async def _handle_stop(self, msg: InboundMessage) -> None:
        """Cancel active tasks for a session."""
        tasks = self._active_tasks.pop(msg.session_key, [])
        cancelled = 0

        for task in tasks:
            if not task.done():
                task.cancel()
                cancelled += 1

        # Wait for cancellation to complete
        for task in tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task

        content = f"Stopped {cancelled} task(s)." if cancelled else "No active tasks."
        await self.bus.publish_outbound(
            OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=content)
        )

    async def _handle_restart(self, msg: InboundMessage) -> None:
        """Restart the bot process."""
        await self.bus.publish_outbound(
            OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content="Restarting...",
            )
        )

        async def _do_restart() -> None:
            await asyncio.sleep(1)
            import os
            import sys

            os.execv(  # nosec: B606
                sys.executable,
                [sys.executable, "-m", "ownbot", *sys.argv[1:]],
            )

        _ = asyncio.create_task(_do_restart())  # noqa: RUF006

    async def _dispatch(self, msg: InboundMessage) -> None:
        """Dispatch a message to the appropriate handler."""
        session_lock = self._session_locks[msg.session_key]

        async with session_lock:
            try:
                response = await self._process_message(msg)
                if response is not None:
                    await self.bus.publish_outbound(response)
            except asyncio.CancelledError:
                logger.info("Task cancelled for session {}", msg.session_key)
                raise
            except Exception as e:
                logger.exception("Error processing message for session {}", msg.session_key)
                await self.bus.publish_outbound(
                    OutboundMessage(
                        channel=msg.channel,
                        chat_id=msg.chat_id,
                        content=f"Sorry, I encountered an error: {e}",
                    )
                )

    async def _process_message(
        self,
        msg: InboundMessage,
    ) -> OutboundMessage | None:
        """Process a single message and generate a response.

        Args:
            msg: The inbound message

        Returns:
            Response message or None
        """
        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info("Processing message from {}: {}", msg.channel, preview)

        session = self.sessions.get_or_create(msg.session_key)

        # Create agent logger for observability
        agent_logger = create_agent_logger(msg.session_key)

        # Handle slash commands
        cmd = msg.content.strip().lower()

        if cmd == "/new":
            session.clear()
            self.sessions.save(session)
            return OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content="New session started.",
            )

        if cmd == "/help":
            return OutboundMessage(
                channel=msg.channel,
                chat_id=msg.chat_id,
                content=self._get_help_text(),
            )

        # Build messages for LLM (use sliding window)
        history = session.get_history(max_messages=self._session_message_limit)
        initial_messages = self.context.build_messages(
            history=history,
            current_message=msg.content,
            media=msg.media or None,
            channel=msg.channel,
            chat_id=msg.chat_id,
        )

        # Create progress callback for streaming updates
        async def send_progress(message: str) -> None:
            """Send progress update to user."""
            await self.bus.publish_outbound(
                OutboundMessage(
                    channel=msg.channel,
                    chat_id=msg.chat_id,
                    content=message,
                )
            )

        # Run agent loop with progress callback
        final_content, _, _ = await self._run_agent_loop(
            initial_messages,
            agent_logger=agent_logger,
            step_callback=send_progress,
        )

        if final_content is None:
            final_content = "I've completed processing but have no response to give."

        # Save session (with sliding window applied)
        self._save_turn(session, msg.content, final_content)
        self._apply_sliding_window(session)
        self.sessions.save(session)

        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info("Response to {}: {}", msg.channel, preview)

        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content,
            metadata=msg.metadata or {},
        )

    def _save_turn(
        self,
        session: Any,
        user_content: str,
        assistant_content: str,
    ) -> None:
        """Save a conversation turn to the session."""
        session.messages.append(
            {
                "role": "user",
                "content": user_content,
                "timestamp": datetime.now().isoformat(),
            }
        )
        session.messages.append(
            {
                "role": "assistant",
                "content": assistant_content,
                "timestamp": datetime.now().isoformat(),
            }
        )
        session.updated_at = datetime.now()

    def _apply_sliding_window(self, session: Any) -> None:
        """Apply sliding window to session messages.

        Keeps only the most recent messages up to the limit.
        This is a simple way to manage context window size.

        Args:
            session: The session to apply sliding window to
        """
        if len(session.messages) > self._session_message_limit:
            # Keep only the last N messages
            removed_count = len(session.messages) - self._session_message_limit
            session.messages = session.messages[-self._session_message_limit :]
            logger.debug(
                "Applied sliding window to session {}: removed {} messages, kept {}",
                session.key,
                removed_count,
                len(session.messages),
            )

    @staticmethod
    def _get_help_text() -> str:
        """Get the help message text."""
        return (
            "🤖 OwnBot Commands:\n"
            "/new — Start a new conversation\n"
            "/stop — Stop the current task\n"
            "/restart — Restart the bot (admin only)\n"
            "/help — Show this help message"
        )

    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("Agent loop stopping...")

    async def cleanup(self) -> None:
        """Cleanup resources including MCP connections."""
        if self.mcp_manager:
            logger.info("Disconnecting from MCP servers...")
            await self.mcp_manager.disconnect_all()
            self.mcp_manager = None
            self.mcp_registry = None

    async def process_direct(
        self,
        content: str,
        _session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
    ) -> str:
        """Process a message directly (for CLI usage).

        Args:
            content: Message content
            session_key: Session identifier
            channel: Channel name
            chat_id: Chat identifier

        Returns:
            Response content as string
        """
        msg = InboundMessage(
            channel=channel,
            sender_id="user",
            chat_id=chat_id,
            content=content,
        )
        response = await self._process_message(msg)
        return response.content if response else ""

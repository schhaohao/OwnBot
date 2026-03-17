from __future__ import annotations

import asyncio
import collections
import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from loguru import logger

from ownbot.agent.context import ContextBuilder
from ownbot.agent.memory import MemoryConsolidator
from ownbot.agent.tools import (
    ToolRegistry,
    ListFilesTool,
    ReadFileTool,
    WriteFileTool,
    ShellTool,
    WebRequestTool,
)
from ownbot.bus.events import InboundMessage, OutboundMessage
from ownbot.bus.queue import MessageBus
from ownbot.config.schema import AppConfig
from ownbot.providers.litellm_provider import LiteLLMProvider
from ownbot.session import SessionManager
from ownbot.utils.logger import (
    create_agent_logger,
    log_session_start,
    log_session_end,
)


class AgentLoop:
    """
    The agent loop is the core processing engine.

    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """

    _TOOL_RESULT_MAX_CHARS = 16_000

    def __init__(self, cfg: AppConfig, bus: MessageBus):
        self.bus = bus
        self.cfg = cfg
        self.provider = LiteLLMProvider(
            api_key=cfg.llm.api_key,
            api_base=cfg.llm.api_base,
        )
        # Create a new GenerationSettings object since it's frozen
        from ownbot.providers.base import GenerationSettings
        self.provider.generation = GenerationSettings(
            temperature=cfg.llm.temperature,
            max_tokens=cfg.llm.max_tokens,
            reasoning_effort=None
        )
        self.model = cfg.llm.model
        self.workspace = cfg.workspace_path
        self.max_iterations = 40
        self.context_window_tokens = 65_536

        self.context = ContextBuilder(
            workspace=self.workspace,
            enable_rag=cfg.retrieval.enabled,
            use_milvus_lite=cfg.retrieval.use_milvus_lite,
            milvus_host=cfg.retrieval.milvus_host,
            milvus_port=cfg.retrieval.milvus_port,
            milvus_db_path=cfg.retrieval.milvus_db_path,
            embedding_model=cfg.retrieval.embedding_model,
        )
        self.sessions = self._create_session_manager()
        self.tools = self._create_tool_registry()

        self._running = False
        self._active_tasks: dict[str, list[asyncio.Task]] = {}  # session_key -> tasks
        # Use session-level locks instead of global lock for better concurrency
        self._session_locks: dict[str, asyncio.Lock] = collections.defaultdict(asyncio.Lock)
        self.memory_consolidator = MemoryConsolidator(
            workspace=self.workspace,
            provider=self.provider,
            model=self.model,
            sessions=self.sessions,
            context_window_tokens=self.context_window_tokens,
            build_messages=self.context.build_messages,
            get_tool_definitions=self.tools.get_definitions,
        )

    def _create_session_manager(self):
        """Create a session manager for conversation history."""
        return SessionManager(workspace=self.workspace)

    def _create_tool_registry(self):
        """Create a tool registry with available tools."""
        registry = ToolRegistry()

        registry.register(
            ListFilesTool(
                workspace=self.workspace,
                skills_dir=self.context.workspace_skills_dir,
                builtin_skills_dir=self.context.builtin_skills_dir,
            )
        )
        registry.register(
            ReadFileTool(
                workspace=self.workspace,
                skills_dir=self.context.workspace_skills_dir,
                builtin_skills_dir=self.context.builtin_skills_dir,
            )
        )
        registry.register(
            WriteFileTool(
                workspace=self.workspace,
                skills_dir=self.context.workspace_skills_dir,
                builtin_skills_dir=self.context.builtin_skills_dir,
            )
        )
        registry.register(ShellTool())
        registry.register(WebRequestTool())

        return registry

    @staticmethod
    def _strip_think(text: str | None) -> str | None:
        """Remove <think>…</think> blocks that some models embed in content."""
        if not text:
            return None
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None

    @staticmethod
    def _dump_for_log(data: Any) -> str:
        """Serialize request payloads for readable logging."""
        try:
            return json.dumps(data, ensure_ascii=False, indent=2, default=str)
        except TypeError:
            return str(data)

    def _log_llm_request(self, iteration: int, messages: list[dict], tool_defs: list[dict[str, Any]]) -> None:
        """Log the exact payload sent to the model for this iteration."""
        logger.info("LLM request messages for iteration {}:\n{}", iteration, self._dump_for_log(messages))
        logger.info("LLM tool definitions for iteration {}:\n{}", iteration, self._dump_for_log(tool_defs))

    async def _execute_tool_with_error_handling(self, tool_call) -> tuple[str, str]:
        """Execute a tool with error handling, returning (tool_name, result)."""
        try:
            result = await self.tools.execute(tool_call.name, tool_call.arguments)
            return tool_call.name, result
        except Exception as e:
            logger.warning("Tool {} failed: {}", tool_call.name, e)
            # Return error message to LLM for self-correction
            error_result = f"Error executing tool: {str(e)}. Please analyze the error and try again."
            return tool_call.name, error_result

    async def _run_agent_loop(
        self,
        initial_messages: list[dict],
        on_progress: Callable[..., asyncio.coroutine] | None = None,
        agent_logger: Optional[Any] = None,
    ) -> tuple[str | None, list[str], list[dict]]:
        """Run the agent iteration loop with ReAct architecture."""
        messages = initial_messages
        iteration = 0
        final_content = None
        tools_used: list[str] = []

        while iteration < self.max_iterations:
            iteration += 1

            if agent_logger:
                agent_logger.start_iteration(iteration)

            tool_defs = self.tools.get_definitions()

            if agent_logger:
                agent_logger.log_progress("正在调用 LLM...")

            self._log_llm_request(iteration, messages, tool_defs)

            response = await self.provider.chat_with_retry(
                messages=messages,
                tools=tool_defs,
                model=self.model,
            )

            # Check for tool calls (OpenAI format) or ReAct format
            clean_content = self._strip_think(response.content) or ""
            react_result = self.context.parse_react_response(clean_content)
            
            # Debug: Log the raw content to understand the format
            logger.debug("Raw LLM response: {}", response.content[:500] if response.content else "None")
            logger.debug("Clean content: {}", clean_content[:500] if clean_content else "None")
            logger.debug("Parsed react_result: {}", react_result)
            
            # Check if this is a ReAct format with Action (but no OpenAI tool_calls)
            has_react_action = react_result.get('action') and react_result.get('action_input')
            
            if response.has_tool_calls or has_react_action:
                # Log thought to console (developer only, not to user)
                if agent_logger:
                    if react_result.get('thought'):
                        agent_logger.log_thought(react_result['thought'])
                    else:
                        # If no thought parsed, log the raw content for debugging
                        logger.warning("No thought parsed from response. Raw content preview: {}", 
                                     clean_content[:200] if clean_content else "Empty")

                # Handle ReAct format (convert to tool_calls)
                if has_react_action and not response.has_tool_calls:
                    from ownbot.providers.base import ToolCallRequest
                    try:
                        action_input = json.loads(react_result['action_input'])
                    except json.JSONDecodeError:
                        action_input = {"text": react_result['action_input']}
                    
                    react_tool_call = ToolCallRequest(
                        id=f"react_{iteration}",
                        name=react_result['action'],
                        arguments=action_input
                    )
                    # Create a new response with the parsed tool call
                    response.tool_calls = [react_tool_call]
                    logger.info("Parsed ReAct action: {}({})", react_result['action'], react_result['action_input'])

                # Note: We no longer send thought to user via on_progress
                # Only log it to console for debugging

                tool_call_dicts = [
                    tc.to_openai_tool_call()
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                )

                # Log actions
                if agent_logger:
                    for tc in response.tool_calls:
                        agent_logger.log_action(tc.name, tc.arguments)

                # Execute tools concurrently for better performance
                tool_tasks = [
                    self._execute_tool_with_error_handling(tc)
                    for tc in response.tool_calls
                ]
                results = await asyncio.gather(*tool_tasks)

                # Update messages with tool results and log observations
                for tc, (tool_name, result) in zip(response.tool_calls, results):
                    tools_used.append(tool_name)
                    args_str = json.dumps(tc.arguments, ensure_ascii=False)
                    logger.info("Tool call: {}({})", tool_name, args_str[:200])
                    
                    # Log observation
                    if agent_logger:
                        agent_logger.log_observation(result)
                    
                    messages = self.context.add_tool_result(
                        messages, tc.id, tool_name, result
                    )
            else:
                clean = self._strip_think(response.content)
                # Handle LLM errors with self-correction
                if response.finish_reason == "error":
                    error_msg = clean or "Unknown error"
                    logger.error("LLM returned error: {}", error_msg[:200])
                    if agent_logger:
                        agent_logger.log_error(error_msg)
                    
                    # Self-correction: Add error as observation and retry
                    logger.info("Attempting self-correction for LLM error...")
                    correction_message = f"The previous LLM call failed with error: {error_msg}. Please try again with a valid response."
                    messages = self.context.add_assistant_message(
                        messages, f"Error: {error_msg}"
                    )
                    messages.append({
                        "role": "user",
                        "content": correction_message,
                    })
                    continue  # Retry instead of breaking
                
                # Parse ReAct response to extract final answer
                react_result = self.context.parse_react_response(clean)
                
                # Log thought to console (developer only, not to user)
                if agent_logger and react_result.get('thought'):
                    agent_logger.log_thought(react_result['thought'])
                
                # If there's a final answer, use it; otherwise use the full content
                if react_result.get('final_answer'):
                    final_content = react_result['final_answer']
                else:
                    final_content = clean
                
                # Log final answer
                if agent_logger:
                    agent_logger.log_final_answer(final_content)
                
                messages = self.context.add_assistant_message(
                    messages, clean, reasoning_content=response.reasoning_content,
                )
                break

        if final_content is None and iteration >= self.max_iterations:
            logger.warning("Max iterations ({}) reached", self.max_iterations)
            error_msg = (
                f"I reached the maximum number of tool call iterations ({self.max_iterations}) "
                "without completing the task. You can try breaking the task into smaller steps."
            )
            if agent_logger:
                agent_logger.log_error(error_msg)
            final_content = error_msg

        return final_content, tools_used, messages

    async def run(self) -> None:
        """Run the agent loop."""
        self._running = True
        logger.info("Agent loop started")

        while self._running:
            try:
                msg = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            cmd = msg.content.strip().lower()
            if cmd == "/stop":
                await self._handle_stop(msg)
            elif cmd == "/restart":
                # Check admin permission before restart
                if not self._is_admin(msg.sender_id):
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel, chat_id=msg.chat_id,
                        content="Permission denied. Only admins can restart the bot.",
                    ))
                    continue
                await self._handle_restart(msg)
            else:
                task = asyncio.create_task(self._dispatch(msg))
                self._active_tasks.setdefault(msg.session_key, []).append(task)
                task.add_done_callback(lambda t, k=msg.session_key: self._active_tasks.get(k, []) and self._active_tasks[k].remove(t) if t in self._active_tasks.get(k, []) else None)

    def _is_admin(self, sender_id: str) -> bool:
        """Check if sender is an admin."""
        # Get admin IDs from config, default to empty list
        admin_ids = getattr(self.cfg, 'admin_ids', [])
        if not admin_ids:
            # If no admin_ids configured, allow all (for backward compatibility)
            return True
        return sender_id in admin_ids

    async def _handle_stop(self, msg: InboundMessage) -> None:
        """Cancel all active tasks for the session."""
        tasks = self._active_tasks.pop(msg.session_key, [])
        cancelled = sum(1 for t in tasks if not t.done() and t.cancel())
        for t in tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        total = cancelled
        content = f"Stopped {total} task(s)." if total else "No active task to stop."
        await self.bus.publish_outbound(OutboundMessage(
            channel=msg.channel, chat_id=msg.chat_id, content=content,
        ))

    async def _handle_restart(self, msg: InboundMessage) -> None:
        """Restart the process."""
        await self.bus.publish_outbound(OutboundMessage(
            channel=msg.channel, chat_id=msg.chat_id, content="Restarting...",
        ))

        async def _do_restart():
            await asyncio.sleep(1)
            import os
            import sys
            os.execv(sys.executable, [sys.executable, "-m", "ownbot"] + sys.argv[1:])

        asyncio.create_task(_do_restart())

    async def _dispatch(self, msg: InboundMessage) -> None:
        """Process a message under the session-level lock."""
        # Use session-level lock instead of global lock for better concurrency
        session_lock = self._session_locks[msg.session_key]
        async with session_lock:
            try:
                response = await self._process_message(msg)
                if response is not None:
                    await self.bus.publish_outbound(response)
            except asyncio.CancelledError:
                logger.info("Task cancelled for session {}", msg.session_key)
                raise
            except Exception:
                logger.exception("Error processing message for session {}", msg.session_key)
                await self.bus.publish_outbound(OutboundMessage(
                    channel=msg.channel, chat_id=msg.chat_id,
                    content="Sorry, I encountered an error.",
                ))

    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("Agent loop stopping")

    async def _process_message(
        self,
        msg: InboundMessage,
        session_key: str | None = None,
        on_progress: Callable[[str], asyncio.coroutine] | None = None,
    ) -> OutboundMessage | None:
        """Process a single inbound message and return the response."""
        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info("Processing message from {}:{}: {}", msg.channel, msg.sender_id, preview)

        key = session_key or msg.session_key
        session = self.sessions.get_or_create(key)

        # Log session start with rich
        log_session_start(key, msg.content)
        
        # Create agent logger for this session
        agent_logger = create_agent_logger(key)

        # Slash commands
        cmd = msg.content.strip().lower()
        if cmd == "/new":
            session.clear()
            self.sessions.save(session)
            self.sessions.invalidate(session.key)
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="New session started.")
        if cmd == "/help":
            lines = [
                "🐈 OwnBot commands:",
                "/new — Start a new conversation",
                "/stop — Stop the current task",
                "/restart — Restart the bot (admin only)",
                "/help — Show available commands",
            ]
            return OutboundMessage(
                channel=msg.channel, chat_id=msg.chat_id, content="\n".join(lines),
            )

        await self.memory_consolidator.maybe_consolidate_by_tokens(session)

        history = session.get_history(max_messages=0)
        initial_messages = self.context.build_messages(
            history=history,
            current_message=msg.content,
            media=msg.media if msg.media else None,
            channel=msg.channel, chat_id=msg.chat_id,
        )

        # Note: We no longer use on_progress to send intermediate thoughts to user
        # All intermediate steps are only logged to console for debugging
        final_content, _, all_msgs = await self._run_agent_loop(
            initial_messages, 
            on_progress=None,  # Disable progress updates to user
            agent_logger=agent_logger,
        )

        if final_content is None:
            final_content = "I've completed processing but have no response to give."

        # Save only essential messages (user input and final assistant response)
        # Skip intermediate tool calls and results to avoid memory pollution
        self._save_essential_turn(session, msg.content, final_content)
        self.sessions.save(session)
        await self.memory_consolidator.maybe_consolidate_by_tokens(session)

        # Log session end
        log_session_end(key)

        preview = final_content[:120] + "..." if len(final_content) > 120 else final_content
        logger.info("Response to {}:{}: {}", msg.channel, msg.sender_id, preview)
        return OutboundMessage(
            channel=msg.channel, chat_id=msg.chat_id, content=final_content,
            metadata=msg.metadata or {},
        )

    def _save_essential_turn(self, session: Any, user_content: str, assistant_content: str) -> None:
        """Save only essential messages (user input and final assistant response).
        
        Skip intermediate tool calls and results to avoid memory pollution.
        """
        # Add user message
        session.messages.append({
            "role": "user",
            "content": user_content,
            "timestamp": datetime.now().isoformat(),
        })
        
        # Add assistant message
        session.messages.append({
            "role": "assistant",
            "content": assistant_content,
            "timestamp": datetime.now().isoformat(),
        })
        
        session.updated_at = datetime.now()

    def _save_turn(self, session: Any, messages: list[dict], skip: int) -> None:
        """Save new-turn messages into session, truncating large tool results.
        
        Deprecated: Use _save_essential_turn instead for cleaner memory.
        """
        for m in messages[skip:]:
            session.messages.append(m)
        session.updated_at = datetime.now()

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        on_progress: Callable[[str], asyncio.coroutine] | None = None,
    ) -> str:
        """Process a message directly (for CLI or cron usage)."""
        msg = InboundMessage(channel=channel, sender_id="user", chat_id=chat_id, content=content)
        response = await self._process_message(msg, session_key=session_key, on_progress=on_progress)
        return response.content if response else ""

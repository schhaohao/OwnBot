from __future__ import annotations

from pathlib import Path
from typing import Any, List, Optional


class ContextBuilder:
    """
    Builds context for LLM calls by combining session history, system prompts, and current input.
    """

    _RUNTIME_CONTEXT_TAG = "[runtime-context]"

    def __init__(self, workspace: Path):
        self.workspace = workspace

    def build_messages(
        self,
        history: List[dict[str, Any]],
        current_message: str,
        media: Optional[List[str]] = None,
        channel: Optional[str] = None,
        chat_id: Optional[str] = None,
    ) -> List[dict[str, Any]]:
        """
        Build a list of messages for the LLM.
        
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

        # System prompt
        system_prompt = """
You are OwnBot, a helpful AI assistant. Your goal is to provide accurate and useful responses to user queries.

When responding, consider:
1. Be concise and clear
2. Provide relevant information
3. If you're unsure, ask for clarification
4. Respect user privacy

You can use tools to help you answer questions, but only when necessary.
        """
        messages.append({"role": "system", "content": system_prompt.strip()})

        # Add history
        messages.extend(history)

        # Add current message
        user_content: Any = current_message
        if media:
            user_content = []
            user_content.append({"type": "text", "text": current_message})
            for media_path in media:
                user_content.append({"type": "text", "text": f"[media: {media_path}]"})

        messages.append({"role": "user", "content": user_content})

        return messages

    def add_assistant_message(
        self,
        messages: List[dict[str, Any]],
        content: Optional[str],
        tool_calls: Optional[List[dict[str, Any]]] = None,
        reasoning_content: Optional[str] = None,
        thinking_blocks: Optional[List[dict]] = None,
    ) -> List[dict[str, Any]]:
        """
        Add an assistant message to the context.
        """
        assistant_message: dict[str, Any] = {"role": "assistant"}
        if content:
            assistant_message["content"] = content
        if tool_calls:
            assistant_message["tool_calls"] = tool_calls
        messages.append(assistant_message)
        return messages

    def add_tool_result(
        self,
        messages: List[dict[str, Any]],
        tool_call_id: str,
        tool_name: str,
        result: str,
    ) -> List[dict[str, Any]]:
        """
        Add a tool result to the context.
        """
        tool_message = {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "name": tool_name,
            "content": result,
        }
        messages.append(tool_message)
        return messages

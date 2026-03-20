"""Abstract base class for LLM providers.

Defines the interface that all LLM providers must implement,
along with supporting data structures for tool calls and responses.
"""

from __future__ import annotations

import asyncio
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar

from loguru import logger

from ownbot.constants import LLM_RETRY_DELAYS, LLM_TRANSIENT_ERROR_MARKERS
from ownbot.types import JsonDict, LLMModel, LLMUsage


@dataclass(frozen=True)
class ToolCallRequest:
    """A tool call request from the LLM.

    Represents a request from the model to invoke a tool with specific arguments.

    Attributes:
        id: Unique identifier for this tool call
        name: Name of the tool to invoke
        arguments: Dictionary of arguments to pass to the tool
        provider_specific_fields: Optional provider-specific additional data
        function_provider_specific_fields: Optional function-level provider data
    """

    id: str
    name: str
    arguments: JsonDict
    provider_specific_fields: JsonDict | None = None
    function_provider_specific_fields: JsonDict | None = None

    def to_openai_tool_call(self) -> JsonDict:
        """Serialize to OpenAI-compatible tool_call format.

        Returns:
            Dictionary matching OpenAI's tool_calls format.
        """
        tool_call: JsonDict = {
            "id": self.id,
            "type": "function",
            "function": {
                "name": self.name,
                "arguments": json.dumps(self.arguments, ensure_ascii=False),
            },
        }
        if self.provider_specific_fields:
            tool_call["provider_specific_fields"] = self.provider_specific_fields
        if self.function_provider_specific_fields:
            tool_call["function"]["provider_specific_fields"] = (
                self.function_provider_specific_fields
            )
        return tool_call


@dataclass
class LLMResponse:
    """Response from an LLM provider.

    Contains the model's output, including content, tool calls,
    usage statistics, and reasoning information.

    Attributes:
        content: Text content of the response (may be None if only tool calls)
        tool_calls: List of tool calls requested by the model
        finish_reason: Reason the generation finished (e.g., "stop", "tool_calls")
        usage: Token usage statistics
        reasoning_content: Model's reasoning/thinking content (if available)
        thinking_blocks: Extended thinking blocks (Anthropic-style)
    """

    content: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: LLMUsage = field(default_factory=dict)
    reasoning_content: str | None = None
    thinking_blocks: list[JsonDict] | None = None

    @property
    def has_tool_calls(self) -> bool:
        """Check if the response contains any tool calls."""
        return len(self.tool_calls) > 0

    @property
    def total_tokens(self) -> int:
        """Get total tokens used (prompt + completion)."""
        return self.usage.get("total_tokens", 0)

    @property
    def is_error(self) -> bool:
        """Check if this response represents an error."""
        return self.finish_reason == "error"


@dataclass(frozen=True)
class GenerationSettings:
    """Default generation parameters for LLM calls.

    These settings are stored on the provider so every call site
    inherits the same defaults without needing to pass parameters
    through every layer.

    Individual calls can still override by passing explicit
    keyword arguments to chat() / chat_with_retry().
    """

    temperature: float = 0.7
    max_tokens: int = 4096
    reasoning_effort: str | None = None

    def merge(
        self,
        temperature: float | None = None,
        max_tokens: int | None = None,
        reasoning_effort: str | None = None,
    ) -> GenerationSettings:
        """Create new settings with overrides applied.

        Args:
            temperature: Override temperature (if not None)
            max_tokens: Override max_tokens (if not None)
            reasoning_effort: Override reasoning_effort (if not None)

        Returns:
            New GenerationSettings with overrides applied.
        """
        return GenerationSettings(
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            reasoning_effort=(
                reasoning_effort if reasoning_effort is not None else self.reasoning_effort
            ),
        )


class LLMProvider(ABC):
    """Abstract base class for LLM providers.

    Implementations handle the specifics of each provider's API
    while maintaining a consistent interface for the agent.
    """

    # Sentinel value for detecting unset parameters
    _SENTINEL: ClassVar[object] = object()

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        generation: GenerationSettings | None = None,
    ) -> None:
        """Initialize the provider.

        Args:
            api_key: API key for authentication
            api_base: Base URL for the API
            generation: Default generation settings
        """
        self.api_key = api_key
        self.api_base = api_base
        self.generation: GenerationSettings = generation or GenerationSettings()

    @staticmethod
    def _sanitize_empty_content(
        messages: list[JsonDict],
    ) -> list[JsonDict]:
        """Replace empty text content that causes provider 400 errors.

        Empty content can appear when tools return nothing. Most providers
        reject empty-string content or empty text blocks.

        Args:
            messages: List of message dictionaries to sanitize

        Returns:
            Sanitized list of messages
        """
        result: list[JsonDict] = []

        for msg in messages:
            content = msg.get("content")

            # Handle empty string content
            if isinstance(content, str) and not content:
                clean = dict(msg)
                # Assistant messages with tool_calls can have None content
                if msg.get("role") == "assistant" and msg.get("tool_calls"):
                    clean["content"] = None
                else:
                    clean["content"] = "(empty)"
                result.append(clean)
                continue

            # Handle empty items in list content
            if isinstance(content, list):
                filtered = [
                    item
                    for item in content
                    if not (
                        isinstance(item, dict)
                        and item.get("type") in ("text", "input_text", "output_text")
                        and not item.get("text")
                    )
                ]
                if len(filtered) != len(content):
                    clean = dict(msg)
                    if filtered:
                        clean["content"] = filtered
                    elif msg.get("role") == "assistant" and msg.get("tool_calls"):
                        clean["content"] = None
                    else:
                        clean["content"] = "(empty)"
                    result.append(clean)
                    continue

            # Handle dict content (wrap in list)
            if isinstance(content, dict):
                clean = dict(msg)
                clean["content"] = [content]
                result.append(clean)
                continue

            result.append(msg)

        return result

    @staticmethod
    def _sanitize_request_messages(
        messages: list[JsonDict],
        allowed_keys: frozenset[str],
    ) -> list[JsonDict]:
        """Keep only provider-safe message keys.

        Args:
            messages: List of message dictionaries
            allowed_keys: Set of allowed keys to keep

        Returns:
            Sanitized list of messages
        """
        sanitized: list[JsonDict] = []

        for msg in messages:
            clean = {k: v for k, v in msg.items() if k in allowed_keys}

            # Ensure assistant messages have content field
            if clean.get("role") == "assistant" and "content" not in clean:
                clean["content"] = None

            sanitized.append(clean)

        return sanitized

    @classmethod
    def _is_transient_error(cls, content: str | None) -> bool:
        """Check if an error message indicates a transient failure.

        Transient errors are those that may succeed on retry,
        such as rate limits or temporary server errors.

        Args:
            content: Error message content

        Returns:
            True if the error appears to be transient
        """
        if not content:
            return False
        content_lower = content.lower()
        return any(marker in content_lower for marker in LLM_TRANSIENT_ERROR_MARKERS)

    @abstractmethod
    async def chat(
        self,
        messages: list[JsonDict],
        tools: list[JsonDict] | None = None,
        model: LLMModel | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | JsonDict | None = None,
    ) -> LLMResponse:
        """Send a chat completion request.

        Args:
            messages: List of message dicts with 'role' and 'content'
            tools: Optional list of tool definitions
            model: Model identifier (provider-specific)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            reasoning_effort: Reasoning effort for supported models
            tool_choice: Tool selection strategy ("auto", "required", etc.)

        Returns:
            LLMResponse with content and/or tool calls
        """
        raise NotImplementedError

    async def chat_with_retry(
        self,
        messages: list[JsonDict],
        tools: list[JsonDict] | None = None,
        model: LLMModel | None = None,
        max_tokens: object = _SENTINEL,
        temperature: object = _SENTINEL,
        reasoning_effort: object = _SENTINEL,
        tool_choice: str | JsonDict | None = None,
    ) -> LLMResponse:
        """Call chat() with retry on transient failures.

        Parameters default to self.generation when not explicitly passed.

        Args:
            messages: List of message dicts
            tools: Optional tool definitions
            model: Model identifier
            max_tokens: Maximum tokens (defaults to self.generation.max_tokens)
            temperature: Temperature (defaults to self.generation.temperature)
            reasoning_effort: Reasoning effort (defaults to self.generation.reasoning_effort)
            tool_choice: Tool selection strategy

        Returns:
            LLMResponse from the provider
        """
        # Resolve defaults from generation settings
        resolved_max_tokens: int = (
            self.generation.max_tokens if max_tokens is self._SENTINEL else max_tokens  # type: ignore
        )
        resolved_temperature: float = (
            self.generation.temperature if temperature is self._SENTINEL else temperature  # type: ignore
        )
        resolved_reasoning: str | None = (
            self.generation.reasoning_effort
            if reasoning_effort is self._SENTINEL
            else reasoning_effort  # type: ignore
        )

        last_error: Exception | None = None

        for attempt, delay in enumerate(LLM_RETRY_DELAYS, start=1):
            try:
                response = await self.chat(
                    messages=messages,
                    tools=tools,
                    model=model,
                    max_tokens=resolved_max_tokens,
                    temperature=resolved_temperature,
                    reasoning_effort=resolved_reasoning,
                    tool_choice=tool_choice,
                )
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                last_error = exc
                response = LLMResponse(
                    content=f"Error calling LLM: {exc}",
                    finish_reason="error",
                )

            if not response.is_error:
                return response

            if not self._is_transient_error(response.content):
                return response

            err_msg = (response.content or "").lower()[:120]
            logger.warning(
                "LLM transient error (attempt {}/{}), retrying in {}s: {}",
                attempt,
                len(LLM_RETRY_DELAYS),
                delay,
                err_msg,
            )

            try:
                await asyncio.sleep(delay)
            except asyncio.CancelledError:
                raise

        # Final attempt without retry
        try:
            return await self.chat(
                messages=messages,
                tools=tools,
                model=model,
                max_tokens=resolved_max_tokens,
                temperature=resolved_temperature,
                reasoning_effort=resolved_reasoning,
                tool_choice=tool_choice,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return LLMResponse(
                content=f"Error calling LLM: {exc}",
                finish_reason="error",
            )

    @abstractmethod
    def get_default_model(self) -> str:
        """Get the default model identifier for this provider.

        Returns:
            Default model name/identifier
        """
        raise NotImplementedError

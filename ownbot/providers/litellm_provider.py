"""LiteLLM provider implementation.

Uses LiteLLM's OpenAI-compatible API to access various language models.
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from ownbot.constants import DEFAULT_HTTP_TIMEOUT
from ownbot.providers.base import (
    GenerationSettings,
    LLMProvider,
    LLMResponse,
    ToolCallRequest,
)
from ownbot.types import JsonDict, LLMModel


class LiteLLMProvider(LLMProvider):
    """LLM provider using LiteLLM to access various models.

    Supports any model compatible with LiteLLM's OpenAI-compatible API,
    including OpenAI, Anthropic, Google, and many others.
    """

    DEFAULT_MODEL: str = "gpt-4.1-mini"
    DEFAULT_TIMEOUT: float = DEFAULT_HTTP_TIMEOUT

    def __init__(
        self,
        api_key: str | None = None,
        api_base: str | None = None,
        generation: GenerationSettings | None = None,
    ) -> None:
        """Initialize the LiteLLM provider.

        Args:
            api_key: API key for authentication
            api_base: Base URL for the LiteLLM API
            generation: Default generation settings
        """
        super().__init__(api_key=api_key, api_base=api_base, generation=generation)

    @staticmethod
    def _coerce_reasoning_text(value: Any) -> str | None:
        """Extract reasoning text from various provider formats.

        Different providers return reasoning content in different formats.
        This method normalizes them to a string.

        Args:
            value: Raw reasoning content from provider

        Returns:
            Normalized reasoning text or None
        """
        if isinstance(value, str):
            text = value.strip()
            return text or None

        if isinstance(value, list):
            parts: list[str] = []
            for item in value:
                if isinstance(item, str) and item.strip():
                    parts.append(item.strip())
                elif isinstance(item, dict):
                    text = item.get("text") or item.get("content")
                    if isinstance(text, str) and text.strip():
                        parts.append(text.strip())
            return "\n".join(parts) if parts else None

        if isinstance(value, dict):
            text = value.get("text") or value.get("content")
            if isinstance(text, str):
                text = text.strip()
                return text or None

        return None

    @staticmethod
    def _extract_reasoning_token_count(usage: JsonDict) -> int | None:
        """Extract reasoning token count from usage data.

        Args:
            usage: Usage statistics from provider

        Returns:
            Number of reasoning tokens or None
        """
        if not isinstance(usage, dict):
            return None

        # Try OpenAI-style completion_tokens_details
        details = usage.get("completion_tokens_details")
        if isinstance(details, dict):
            tokens = details.get("reasoning_tokens")
            if isinstance(tokens, int):
                return tokens

        # Try direct reasoning_tokens field
        tokens = usage.get("reasoning_tokens")
        return tokens if isinstance(tokens, int) else None

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
        """Send a chat completion request via LiteLLM.

        Args:
            messages: List of message dicts
            tools: Optional tool definitions
            model: Model identifier
            max_tokens: Maximum tokens
            temperature: Sampling temperature
            reasoning_effort: Reasoning effort for supported models
            tool_choice: Tool selection strategy

        Returns:
            LLMResponse with model output
        """
        resolved_model = model or self.DEFAULT_MODEL
        url = f"{self.api_base or 'https://api.openai.com/v1'}/chat/completions"

        headers: JsonDict = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key or ''}",
        }

        payload: JsonDict = {
            "model": resolved_model,
            "messages": self._sanitize_empty_content(messages),
            "max_tokens": max_tokens,
            "temperature": temperature,
        }

        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice

        async with httpx.AsyncClient(timeout=self.DEFAULT_TIMEOUT) as client:
            try:
                response = await client.post(
                    url,
                    headers=headers,
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                logger.error("LiteLLM HTTP error {}: {}", e.response.status_code, e)
                return LLMResponse(
                    content=f"HTTP error {e.response.status_code}: {e}",
                    finish_reason="error",
                )
            except httpx.RequestError as e:
                logger.error("LiteLLM request error: {}", e)
                return LLMResponse(
                    content=f"Request error: {e}",
                    finish_reason="error",
                )

        # Parse response
        try:
            return self._parse_response(data)
        except Exception as e:
            logger.error("Failed to parse LLM response: {}", e)
            return LLMResponse(
                content=f"Error parsing response: {e}",
                finish_reason="error",
            )

    def _parse_response(self, data: JsonDict) -> LLMResponse:
        """Parse the API response into an LLMResponse.

        Args:
            data: Raw JSON response from API

        Returns:
            Parsed LLMResponse
        """
        choice = data.get("choices", [{}])[0]
        message = choice.get("message", {})
        content = message.get("content")
        finish_reason = choice.get("finish_reason", "stop")
        usage = data.get("usage", {})

        # Extract reasoning content
        reasoning_content: str | None = None
        for key in ("reasoning_content", "reasoning", "reasoning_text"):
            reasoning_content = self._coerce_reasoning_text(message.get(key))
            if reasoning_content:
                break

        # Try extracting from choice level if not found
        if reasoning_content is None:
            for key in ("reasoning_content", "reasoning", "reasoning_text"):
                reasoning_content = self._coerce_reasoning_text(choice.get(key))
                if reasoning_content:
                    break

        # Extract thinking blocks (Anthropic-style)
        thinking_blocks: list[JsonDict] | None = None
        raw_thinking = message.get("thinking_blocks") or message.get("thinking")
        if isinstance(raw_thinking, list):
            thinking_blocks = raw_thinking

        # Parse tool calls
        tool_calls: list[ToolCallRequest] = []
        raw_tool_calls = message.get("tool_calls", [])
        if raw_tool_calls:
            for tc in raw_tool_calls:
                try:
                    arguments: JsonDict = {}
                    raw_args = tc.get("function", {}).get("arguments", "{}")
                    if isinstance(raw_args, str):
                        import json

                        arguments = json.loads(raw_args)
                    elif isinstance(raw_args, dict):
                        arguments = raw_args

                    tool_calls.append(
                        ToolCallRequest(
                            id=tc.get("id", ""),
                            name=tc.get("function", {}).get("name", ""),
                            arguments=arguments,
                        )
                    )
                except Exception as e:
                    logger.warning("Failed to parse tool call: {}", e)

        # Log summary
        logger.debug(
            "LLM response: model={}, finish_reason={}, has_content={}, "
            "tool_calls={}, has_reasoning={}",
            data.get("model", "unknown"),
            finish_reason,
            bool(content),
            len(tool_calls),
            bool(reasoning_content),
        )

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            finish_reason=finish_reason,
            usage=usage,
            reasoning_content=reasoning_content,
            thinking_blocks=thinking_blocks,
        )

    def get_default_model(self) -> str:
        """Get the default model identifier."""
        return self.DEFAULT_MODEL

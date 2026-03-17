from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

import httpx
from loguru import logger

from ownbot.providers.base import LLMProvider, LLMResponse, ToolCallRequest


class LiteLLMProvider(LLMProvider):
    """
    LLM provider using LiteLLM to access various models.
    """

    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        super().__init__(api_key=api_key, api_base=api_base)

    @staticmethod
    def _coerce_reasoning_text(value: Any) -> str | None:
        """Best-effort extraction of provider reasoning text."""
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
    def _extract_reasoning_token_count(usage: dict[str, Any]) -> int | None:
        """Best-effort extraction of reasoning token counts from provider usage."""
        if not isinstance(usage, dict):
            return None

        details = usage.get("completion_tokens_details")
        if isinstance(details, dict):
            tokens = details.get("reasoning_tokens")
            if isinstance(tokens, int):
                return tokens

        tokens = usage.get("reasoning_tokens")
        return tokens if isinstance(tokens, int) else None

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        reasoning_effort: str | None = None,
        tool_choice: str | dict[str, Any] | None = None,
    ) -> LLMResponse:
        """
        Send a chat completion request using LiteLLM.
        """
        # 使用 OpenAI 兼容的 API 格式
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        payload: Dict[str, Any] = {
            "model": model or "gpt-4.1-mini",
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if reasoning_effort:
            payload["reasoning_effort"] = reasoning_effort

        if tools:
            payload["tools"] = tools
            if tool_choice:
                payload["tool_choice"] = tool_choice

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                response.raise_for_status()
                data = response.json()

                # 解析响应
                choice = data.get("choices", [{}])[0]
                message = choice.get("message", {})
                content = message.get("content")
                tool_calls = []
                finish_reason = choice.get("finish_reason", "stop")
                usage = data.get("usage", {})
                reasoning_content = None
                thinking_blocks = None

                for key in ("reasoning_content", "reasoning", "reasoning_text"):
                    reasoning_content = self._coerce_reasoning_text(message.get(key))
                    if reasoning_content:
                        break
                if reasoning_content is None:
                    for key in ("reasoning_content", "reasoning", "reasoning_text"):
                        reasoning_content = self._coerce_reasoning_text(choice.get(key))
                        if reasoning_content:
                            break

                raw_thinking_blocks = message.get("thinking_blocks") or message.get("thinking")
                if isinstance(raw_thinking_blocks, list):
                    thinking_blocks = raw_thinking_blocks

                logger.info(
                    "LLM response summary: finish_reason={}, content={}, tool_calls={}, reasoning_text={}, thinking_blocks={}, reasoning_tokens={}",
                    finish_reason,
                    bool(content),
                    len(message.get("tool_calls", []) or []),
                    bool(reasoning_content),
                    len(thinking_blocks or []),
                    self._extract_reasoning_token_count(usage),
                )

                # 解析工具调用
                if "tool_calls" in message:
                    for tool_call in message["tool_calls"]:
                        try:
                            arguments = json.loads(tool_call["function"]["arguments"])
                        except json.JSONDecodeError:
                            arguments = {}
                        tool_calls.append(
                            ToolCallRequest(
                                id=tool_call["id"],
                                name=tool_call["function"]["name"],
                                arguments=arguments,
                            )
                        )

                return LLMResponse(
                    content=content,
                    tool_calls=tool_calls,
                    finish_reason=finish_reason,
                    usage=usage,
                    reasoning_content=reasoning_content,
                    thinking_blocks=thinking_blocks,
                )
            except httpx.HTTPError as e:
                logger.error(f"LiteLLM API error: {e}")
                return LLMResponse(
                    content=f"Error calling LLM: {e}",
                    finish_reason="error",
                )
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                return LLMResponse(
                    content=f"Error calling LLM: {e}",
                    finish_reason="error",
                )

    def get_default_model(self) -> str:
        """Get the default model for this provider."""
        return "gpt-4.1-mini"

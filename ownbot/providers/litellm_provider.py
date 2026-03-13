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
                content = data.get("choices", [{}])[0].get("message", {}).get("content")
                tool_calls = []
                finish_reason = data.get("choices", [{}])[0].get("finish_reason", "stop")
                usage = data.get("usage", {})

                # 解析工具调用
                message = data.get("choices", [{}])[0].get("message", {})
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

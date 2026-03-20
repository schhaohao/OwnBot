"""Web request tool for the agent.

Provides HTTP request capabilities with configurable timeouts and error handling.
"""

from __future__ import annotations

from typing import Any

import httpx
from loguru import logger

from ownbot.agent.tools.base import Tool
from ownbot.constants import DEFAULT_WEB_REQUEST_TIMEOUT, MAX_WEB_RESPONSE_LENGTH
from ownbot.exceptions import ToolValidationError, WebRequestError, WebTimeoutError


class WebRequestTool(Tool):
    """Make HTTP requests to external APIs and websites.

    Supports common HTTP methods with configurable headers, data, and JSON payloads.
    """

    name = "web_request"
    description = "Make HTTP requests (GET, POST, PUT, DELETE, PATCH) to external services"

    # Allowed HTTP methods
    ALLOWED_METHODS: frozenset[str] = frozenset(
        {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}
    )

    # Default timeout for requests
    DEFAULT_TIMEOUT: float = DEFAULT_WEB_REQUEST_TIMEOUT

    # Maximum response size to prevent memory issues
    MAX_RESPONSE_SIZE: int = MAX_WEB_RESPONSE_LENGTH

    async def execute(self, arguments: dict[str, Any]) -> str:
        """Execute an HTTP request.

        Args:
            arguments: Dictionary containing:
                - url (str, required): Request URL
                - method (str, optional): HTTP method (default: GET)
                - headers (dict, optional): Request headers
                - data (str, optional): Request body as string
                - json (dict, optional): Request body as JSON object
                - timeout (float, optional): Request timeout in seconds
                - params (dict, optional): URL query parameters

        Returns:
            Formatted response string with status, headers, and body.

        Raises:
            ToolValidationError: If URL is missing or invalid.
            WebRequestError: If request fails.
            WebTimeoutError: If request times out.
        """
        url = arguments.get("url", "").strip()
        method = arguments.get("method", "GET").upper().strip()
        headers = arguments.get("headers") or {}
        data = arguments.get("data")
        json_data = arguments.get("json")
        timeout = arguments.get("timeout", self.DEFAULT_TIMEOUT)
        params = arguments.get("params")

        # Validate URL
        if not url:
            raise ToolValidationError("URL is required")

        if not url.startswith(("http://", "https://")):
            raise ToolValidationError(f"URL must start with http:// or https://: {url}")

        # Validate method
        if method not in self.ALLOWED_METHODS:
            allowed = ", ".join(sorted(self.ALLOWED_METHODS))
            raise ToolValidationError(f"Invalid HTTP method '{method}'. Allowed: {allowed}")

        # Validate headers
        if headers and not isinstance(headers, dict):
            raise ToolValidationError("Headers must be a dictionary")

        logger.debug("Making {} request to {}", method, url[:100])

        try:
            async with httpx.AsyncClient(timeout=timeout, follow_redirects=True) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    params=params,
                    data=data,
                    json=json_data,
                )

            # Format response
            result_parts: list[str] = [
                f"Status: {response.status_code}",
                f"Headers: {dict(response.headers)}",
            ]

            # Handle response body
            content_type = response.headers.get("content-type", "").lower()
            is_text = any(
                t in content_type for t in ["text/", "application/json", "application/xml"]
            )

            if is_text:
                body = response.text
                if len(body) > self.MAX_RESPONSE_SIZE:
                    body = body[: self.MAX_RESPONSE_SIZE] + "\n... (response truncated)"
                result_parts.append(f"Body:\n{body}")
            else:
                result_parts.append(f"Body: [Binary content: {len(response.content)} bytes]")

            return "\n\n".join(result_parts)

        except httpx.TimeoutException as e:
            logger.error("Request to {} timed out after {}s", url[:100], timeout)
            raise WebTimeoutError(f"Request timed out after {timeout} seconds: {e}") from e

        except httpx.HTTPStatusError as e:
            logger.error("HTTP error for {}: {}", url[:100], e)
            raise WebRequestError(f"HTTP error {e.response.status_code}: {e}") from e

        except httpx.RequestError as e:
            logger.error("Request error for {}: {}", url[:100], e)
            raise WebRequestError(f"Request failed: {e}") from e

        except Exception as e:
            logger.error("Unexpected error for {}: {}", url[:100], e)
            raise WebRequestError(f"Unexpected error: {e}") from e

    def _get_parameters_schema(self) -> dict[str, Any]:
        return {
            "url": {
                "type": "string",
                "description": "Request URL (must include http:// or https://)",
            },
            "method": {
                "type": "string",
                "description": "HTTP method",
                "enum": sorted(self.ALLOWED_METHODS),
                "default": "GET",
            },
            "headers": {
                "type": "object",
                "description": "Request headers as key-value pairs",
            },
            "params": {
                "type": "object",
                "description": "URL query parameters as key-value pairs",
            },
            "data": {
                "type": "string",
                "description": "Request body as raw string",
            },
            "json": {
                "type": "object",
                "description": "Request body as JSON object (sets Content-Type: application/json)",
            },
            "timeout": {
                "type": "number",
                "description": f"Request timeout in seconds (default: {self.DEFAULT_TIMEOUT})",
                "default": self.DEFAULT_TIMEOUT,
            },
        }

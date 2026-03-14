from __future__ import annotations

import httpx
from typing import Any

from loguru import logger

from ownbot.agent.tools.base import Tool


class WebRequestTool(Tool):
    """Make HTTP requests."""

    name = "web_request"
    description = "Make HTTP requests (GET, POST, etc.)"

    async def execute(self, arguments: dict[str, Any]) -> str:
        url = arguments.get("url")
        method = arguments.get("method", "GET").upper()
        headers = arguments.get("headers", {})
        data = arguments.get("data")
        json_data = arguments.get("json")

        if not url:
            return "Error: url is required"

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=headers,
                    data=data,
                    json=json_data
                )

                result = f"Status: {response.status_code}\n"
                result += f"Headers: {dict(response.headers)}\n"
                result += f"Body: {response.text[:10000]}"

                if len(response.text) > 10000:
                    result += "\n... (truncated)"

                return result
        except Exception as e:
            logger.error("Error making web request to {}: {}", url, e)
            return f"Error making web request: {str(e)}"

    def _get_parameters_schema(self) -> dict[str, Any]:
        return {
            "url": {
                "type": "string",
                "description": "Request URL",
            },
            "method": {
                "type": "string",
                "description": "HTTP method (default: GET)",
                "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"],
            },
            "headers": {
                "type": "object",
                "description": "Request headers",
            },
            "data": {
                "type": "string",
                "description": "Request body data",
            },
            "json": {
                "type": "object",
                "description": "Request body as JSON",
            }
        }

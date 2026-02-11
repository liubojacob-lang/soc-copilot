"""HTTP request executor."""

import asyncio
from typing import Any
from .executor_base import BaseExecutor, ExecutorContext


class HttpRequestExecutor(BaseExecutor):
    """Executor for making HTTP requests."""

    async def execute(self, context: ExecutorContext) -> dict[str, Any]:
        """Execute HTTP request."""
        config = context.node_def.get("config", {})

        url = config.get("url")
        method = config.get("method", "GET").upper()
        headers = config.get("headers", {})
        body = config.get("body")

        if not url:
            return {
                "status": "error",
                "error": "No URL provided",
            }

        # Resolve URL template
        url = self._resolve_template(url, context)

        try:
            async with asyncio.ClientSession() as session:
                if method == "GET":
                    async with session.get(url, headers=headers) as response:
                        response_text = await response.text()
                        return {
                            "status": "success",
                            "status_code": response.status,
                            "body": response_text,
                        }
                elif method == "POST":
                    async with session.post(url, headers=headers, json=body) as response:
                        response_text = await response.text()
                        return {
                            "status": "success",
                            "status_code": response.status,
                            "body": response_text,
                        }
        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
            }

        return {
            "status": "error",
            "error": f"Unsupported method: {method}",
        }

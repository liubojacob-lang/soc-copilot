"""Parse JSON node plugin (v0.7.4)."""

import json
import logging
from typing import Any

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


class ParseJsonPlugin(BaseNodePlugin):
    """Parse JSON string into structured data.

    Useful for extracting structured data from API responses or text fields.
    """

    @property
    def node_id(self) -> str:
        return "builtin_parse_json"

    @property
    def name(self) -> str:
        return "Parse JSON"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return "Parse JSON string into structured data"

    def validate_input(self, input_json: dict[str, Any]) -> None:
        """Validate input before execution."""
        if "json_string" not in input_json and "data" not in input_json:
            raise ValueError("json_string or data is required")

    async def execute(self, context: NodeExecutionContext) -> dict[str, Any]:
        """Execute JSON parsing.

        Args:
            context: Execution context

        Returns:
            Parsed JSON data
        """
        json_string = context.input_json.get("json_string") or context.input_json.get(
            "data", "{}"
        )
        json_path = context.input_json.get("path", "")

        logger.info(f"[{context.run_id}] Parsing JSON (path: {json_path or 'root'})")

        try:
            # Parse JSON string
            if isinstance(json_string, str):
                parsed = json.loads(json_string)
            else:
                parsed = json_string

            # Apply JSONPath if specified
            if json_path:
                result = self._apply_path(parsed, json_path)
            else:
                result = parsed

            return {
                "status": "success",
                "parsed": result,
                "original_type": type(json_string).__name__,
                "path_applied": json_path,
            }

        except json.JSONDecodeError as e:
            logger.error(f"[{context.run_id}] JSON parse error: {e}")
            return {
                "status": "error",
                "error": f"Invalid JSON: {e!s}",
                "input": (
                    json_string[:200]
                    if isinstance(json_string, str)
                    else str(json_string)[:200]
                ),
            }

    def _apply_path(self, data: Any, path: str) -> Any:
        """Apply simple JSONPath-like extraction.

        Supports dot notation: "user.name" or "users.0.email"
        """
        if not path:
            return data

        current = data
        for key in path.split("."):
            if isinstance(current, dict):
                current = current.get(key)
            elif isinstance(current, list) and key.isdigit():
                idx = int(key)
                current = current[idx] if 0 <= idx < len(current) else None
            else:
                return None

            if current is None:
                break

        return current

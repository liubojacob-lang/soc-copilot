"""Sleep/delay node plugin (v0.7.4)."""

import asyncio
from typing import Any, Dict
import logging

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


class SleepPlugin(BaseNodePlugin):
    """Sleep/delay node for pacing workflow execution.

    In dry_run mode, this returns immediately without actually sleeping.
    """

    @property
    def node_id(self) -> str:
        return "builtin_sleep"

    @property
    def name(self) -> str:
        return "Sleep"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return "Pause execution for a specified duration"

    def validate_input(self, input_json: Dict[str, Any]) -> None:
        """Validate input before execution."""
        seconds = input_json.get("seconds", 0)
        if not isinstance(seconds, (int, float)) or seconds < 0:
            raise ValueError("seconds must be a non-negative number")

    async def execute(self, context: NodeExecutionContext) -> Dict[str, Any]:
        """Execute sleep.

        Args:
            context: Execution context

        Returns:
            Sleep completion result
        """
        seconds = context.input_json.get("seconds", 0)
        is_dry_run = context.mode == "dry_run"

        if is_dry_run:
            logger.info(f"[{context.run_id}] [DRY_RUN] Skipping sleep of {seconds}s")
            return {
                "status": "success",
                "slept_seconds": 0,
                "dry_run": True,
                "message": f"[DRY_RUN] Would have slept for {seconds}s"
            }

        logger.info(f"[{context.run_id}] Sleeping for {seconds}s")
        await asyncio.sleep(seconds)

        return {
            "status": "success",
            "slept_seconds": seconds,
            "message": f"Slept for {seconds}s"
        }

"""Sleep/delay node executor."""

import asyncio
from typing import Any
from .executor_base import BaseExecutor, ExecutorContext


class SleepExecutor(BaseExecutor):
    """Executor for adding delays between nodes."""

    async def execute(self, context: ExecutorContext) -> dict[str, Any]:
        """Sleep for specified duration."""
        config = context.node_def.get("config", {})
        seconds = config.get("seconds", 1)

        await asyncio.sleep(seconds)

        return {
            "status": "success",
            "slept_seconds": seconds,
        }

"""OTX Threat Intelligence lookup executor."""

from typing import Any
from .executor_base import BaseExecutor, ExecutorContext


class TiLookupOtxExecutor(BaseExecutor):
    """Executor for OTX threat intelligence lookup."""

    async def execute(self, context: ExecutorContext) -> dict[str, Any]:
        """Execute OTX TI lookup."""
        ioc = self._get_input(context, "ioc")

        if not ioc:
            return {
                "status": "skipped",
                "message": "No IOC provided",
                "matches": [],
            }

        # TODO: Call actual OTX service
        # For now, return mock data
        return {
            "status": "success",
            "ioc": ioc,
            "matches": [
                {
                    "indicator": ioc,
                    "threat_type": "malware",
                    "confidence": 85,
                }
            ],
            "score": 85,
        }

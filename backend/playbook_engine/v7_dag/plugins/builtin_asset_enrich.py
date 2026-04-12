"""Asset enrichment node plugin (v0.7.4)."""

import logging
from typing import Any

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


class AssetEnrichPlugin(BaseNodePlugin):
    """Enrich asset information with additional context.

    In dry_run mode, returns mock enrichment data.
    """

    @property
    def node_id(self) -> str:
        return "builtin_asset_enrich"

    @property
    def name(self) -> str:
        return "Asset Enrichment"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return "Enrich assets with additional context from CMDB/EDR"

    def validate_input(self, input_json: dict[str, Any]) -> None:
        """Validate input before execution."""
        if (
            "asset" not in input_json
            and "hostname" not in input_json
            and "ip" not in input_json
        ):
            raise ValueError("asset, hostname, or ip is required")

    async def execute(self, context: NodeExecutionContext) -> dict[str, Any]:
        """Execute asset enrichment.

        Args:
            context: Execution context

        Returns:
            Enriched asset information
        """
        asset = context.input_json.get("asset") or {}
        hostname = context.input_json.get("hostname") or asset.get("hostname")
        ip_address = context.input_json.get("ip") or asset.get("ip")
        is_dry_run = context.mode == "dry_run"

        logger.info(
            f"[{context.run_id}] Enriching asset: hostname={hostname}, ip={ip_address}"
        )

        if is_dry_run:
            # Mock enrichment data for dry_run
            return {
                "status": "success",
                "dry_run": True,
                "enriched": {
                    "hostname": hostname or "unknown-host",
                    "ip": ip_address or "0.0.0.0",
                    "os": "Linux (mock)",
                    "criticality": "medium (mock)",
                    "owner": "security-team@example.com (mock)",
                    "location": "production-env (mock)",
                    "edr_agent": "installed (mock)",
                    "patch_level": "latest (mock)",
                },
                "message": "[DRY_RUN] Mock asset enrichment",
            }

        # In apply mode, would query CMDB/EDR here
        # For now, return basic enrichment
        return {
            "status": "success",
            "enriched": {
                "hostname": hostname or "unknown-host",
                "ip": ip_address or "0.0.0.0",
                "enriched": True,
                "source": "cmdb_mock",
            },
        }

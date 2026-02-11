"""Asset enrichment step implementation."""

from typing import Any
from .base_step import BaseStepImpl
from ..registry import register_step


class AssetEnrichStep(BaseStepImpl):
    """Enrich assets with additional context."""

    @property
    def name(self) -> str:
        return "Asset Enrichment"

    @property
    def step_id(self) -> str:
        return "asset_enrich"

    @property
    def step_type(self) -> str:
        return "enrichment"

    @property
    def description(self) -> str:
        return "Enrich assets with criticality, owner, and business context"

    @property
    def supports_apply(self) -> bool:
        return True

    def execute(self, input_json: dict[str, Any], mode: str) -> dict[str, Any]:
        """Enrich assets with additional information.

        Args:
            input_json: Input containing asset information
            mode: Execution mode

        Returns:
            Dictionary with enriched asset data
        """
        iocs = input_json.get("iocs", {})
        alert_data = input_json.get("alert_data", {})

        assets = {
            "enriched": [],
            "summary": {
                "total": 0,
                "critical": 0,
                "high": 0,
                "medium": 0,
                "low": 0,
            },
            "affected_business_units": [],
        }

        # Extract asset information from alert data
        hostname = alert_data.get("hostname", "")
        ip_address = alert_data.get("dest_ip", "") or alert_data.get("src_ip", "")

        # Enrich each IP
        for ip in iocs.get("ips", []):
            asset_info = self._enrich_ip(ip, alert_data, mode)
            assets["enriched"].append(asset_info)
            assets["summary"][asset_info["criticality"]] += 1

        # Enrich hostname if present
        if hostname:
            asset_info = self._enrich_hostname(hostname, alert_data, mode)
            assets["enriched"].append(asset_info)
            assets["summary"][asset_info["criticality"]] += 1

        assets["summary"]["total"] = len(assets["enriched"])

        # Determine affected business units
        units = set()
        for asset in assets["enriched"]:
            if asset.get("business_unit"):
                units.add(asset["business_unit"])
        assets["affected_business_units"] = list(units)

        return assets

    def _enrich_ip(self, ip: str, alert_data: dict, mode: str) -> dict:
        """Enrich an IP address with asset information."""
        # Simulate asset lookup
        criticality = "medium"
        owner = "IT Operations"
        business_unit = "Infrastructure"

        # In real implementation, this would query CMDB
        # For critical systems detection
        if "server" in str(alert_data).lower() or "prod" in str(alert_data).lower():
            criticality = "high"
            owner = "Platform Engineering"
            business_unit = "Engineering"

        if ip.endswith(".1") or ip.endswith(".254"):
            # Likely gateway/router
            criticality = "critical"
            owner = "Network Engineering"
            business_unit = "Infrastructure"

        return {
            "type": "ip",
            "value": ip,
            "criticality": criticality,
            "owner": owner,
            "business_unit": business_unit,
            "os": "Unknown",
            "location": "Unknown",
        }

    def _enrich_hostname(self, hostname: str, alert_data: dict, mode: str) -> dict:
        """Enrich a hostname with asset information."""
        criticality = "medium"
        owner = "IT Operations"
        business_unit = "General"

        # Detect critical systems by hostname patterns
        hostname_lower = hostname.lower()
        if any(x in hostname_lower for x in ["db", "sql", "oracle", "mongo"]):
            criticality = "critical"
            owner = "Database Engineering"
            business_unit = "Engineering"
        elif any(x in hostname_lower for x in ["web", "app", "api"]):
            criticality = "high"
            owner = "Platform Engineering"
            business_unit = "Engineering"
        elif "dc" in hostname_lower or "prod" in hostname_lower:
            criticality = "high"

        return {
            "type": "hostname",
            "value": hostname,
            "criticality": criticality,
            "owner": owner,
            "business_unit": business_unit,
            "os": "Linux",
            "location": "Data Center",
        }


# Register the step
register_step("asset_enrich", AssetEnrichStep)

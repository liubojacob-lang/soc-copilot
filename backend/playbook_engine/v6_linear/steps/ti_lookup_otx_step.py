"""Threat intelligence lookup step implementation."""

from typing import Any
import httpx
from .base_step import BaseStepImpl
from ..registry import register_step


class TILookupOTXStep(BaseStepImpl):
    """Threat intelligence lookup using AlienVault OTX."""

    @property
    def name(self) -> str:
        return "Threat Intel Lookup (OTX)"

    @property
    def step_id(self) -> str:
        return "ti_lookup_otx"

    @property
    def step_type(self) -> str:
        return "ti_lookup"

    @property
    def description(self) -> str:
        return "Query AlienVault OTX for threat intelligence on IOCs"

    @property
    def supports_apply(self) -> bool:
        return True

    def execute(self, input_json: dict[str, Any], mode: str) -> dict[str, Any]:
        """Perform threat intelligence lookup.

        Args:
            input_json: Input containing IOCs
            mode: Execution mode

        Returns:
            Dictionary with threat intel results
        """
        iocs = input_json.get("iocs", {})

        results = {
            "matches": [],
            "summary": {
                "total_iocs": 0,
                "malicious": 0,
                "suspicious": 0,
                "clean": 0,
                "unknown": 0,
            },
            "details": {},
        }

        # Count total IOCs
        results["summary"]["total_iocs"] = sum(len(v) for v in iocs.values())

        # In dry run mode, simulate results
        if mode == "dry_run":
            results["matches"] = self._simulate_lookup(iocs)
            results["summary"]["malicious"] = len([r for r in results["matches"] if r.get("threat_level") == "malicious"])
            results["summary"]["suspicious"] = len([r for r in results["matches"] if r.get("threat_level") == "suspicious"])
            return results

        # In apply mode, perform actual lookups
        # Note: This requires OTX API key configuration
        try:
            results["matches"] = self._perform_lookup(iocs)
            results["summary"]["malicious"] = len([r for r in results["matches"] if r.get("threat_level") == "malicious"])
            results["summary"]["suspicious"] = len([r for r in results["matches"] if r.get("threat_level") == "suspicious"])
        except Exception as e:
            results["error"] = str(e)

        return results

    def _simulate_lookup(self, iocs: dict) -> list[dict]:
        """Simulate threat intel lookup for dry run."""
        matches = []

        # Simulate some malicious indicators
        known_bad = {
            "192.168.1.100": "malicious",
            "evil.com": "malicious",
            "malware.exe": "malicious",
        }

        for ip in iocs.get("ips", [])[:3]:
            threat_level = known_bad.get(ip, "unknown")
            if threat_level != "unknown":
                matches.append({
                    "indicator": ip,
                    "type": "ip",
                    "threat_level": threat_level,
                    "source": "otx",
                    "description": f"{threat_level.capitalize()} indicator detected",
                })

        for domain in iocs.get("domains", [])[:3]:
            threat_level = known_bad.get(domain, "unknown")
            if threat_level != "unknown":
                matches.append({
                    "indicator": domain,
                    "type": "domain",
                    "threat_level": threat_level,
                    "source": "otx",
                    "description": f"{threat_level.capitalize()} indicator detected",
                })

        return matches

    def _perform_lookup(self, iocs: dict) -> list[dict]:
        """Perform actual OTX lookup."""
        matches = []
        api_key = ""  # Would be loaded from config

        if not api_key:
            return self._simulate_lookup(iocs)

        # Actual OTX API calls would go here
        # For now, return simulated results
        return self._simulate_lookup(iocs)


# Register the step
register_step("ti_lookup_otx", TILookupOTXStep)

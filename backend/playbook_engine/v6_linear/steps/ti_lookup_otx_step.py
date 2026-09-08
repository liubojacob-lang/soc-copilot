"""Threat intelligence lookup step implementation."""

from typing import Any

from core.config import settings
from core.logger import get_logger
from utils.ti_filter import should_send_ioc_to_external_ti

from ..registry import register_step
from .base_step import BaseStepImpl

logger = get_logger(__name__)

# Cap external lookups per step run so a large IOC batch cannot hammer OTX
MAX_LOOKUPS_PER_RUN = 20


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

    async def execute(self, input_json: dict[str, Any], mode: str) -> dict[str, Any]:
        """Perform threat intelligence lookup.

        Args:
            input_json: Input containing IOCs
            mode: Execution mode ("dry_run" simulates; "apply" queries real OTX)

        Returns:
            Dictionary with threat intel results. In apply mode the lookup is
            real: without a configured OTX API key the step reports an error
            instead of fabricating matches.
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

        # Dry run mode is explicitly side-effect free; simulated matches are expected
        if mode == "dry_run":
            results["matches"] = self._simulate_lookup(iocs)
            results["simulated"] = True
            self._fill_threat_counts(results)
            return results

        results["simulated"] = False

        if not settings.allow_external_ti:
            results["error"] = "External threat intelligence is disabled by configuration"
            return results

        if not settings.otx_api_key:
            results["error"] = (
                "OTX API key not configured; set OTX_API_KEY to enable real lookups"
            )
            return results

        # Apply mode: perform actual lookups
        try:
            results["matches"] = await self._perform_lookup(iocs)
            self._fill_threat_counts(results)
        except Exception as e:
            logger.exception("OTX lookup step failed")
            results["error"] = str(e)

        return results

    @staticmethod
    def _fill_threat_counts(results: dict[str, Any]) -> None:
        """Fill malicious/suspicious counters from current matches."""
        results["summary"]["malicious"] = len(
            [r for r in results["matches"] if r.get("threat_level") == "malicious"]
        )
        results["summary"]["suspicious"] = len(
            [r for r in results["matches"] if r.get("threat_level") == "suspicious"]
        )

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
                matches.append(
                    {
                        "indicator": ip,
                        "type": "ip",
                        "threat_level": threat_level,
                        "source": "otx",
                        "description": f"{threat_level.capitalize()} indicator detected",
                    }
                )

        for domain in iocs.get("domains", [])[:3]:
            threat_level = known_bad.get(domain, "unknown")
            if threat_level != "unknown":
                matches.append(
                    {
                        "indicator": domain,
                        "type": "domain",
                        "threat_level": threat_level,
                        "source": "otx",
                        "description": f"{threat_level.capitalize()} indicator detected",
                    }
                )

        return matches

    async def _perform_lookup(self, iocs: dict) -> list[dict]:
        """Perform real OTX lookups with compliance filtering and a rate budget.

        Private IPs, internal domains and blocked TLDs are never sent to the
        external service (utils.ti_filter); at most MAX_LOOKUPS_PER_RUN
        indicators are queried per run.
        """
        from integrations.otx_client import OTXClient
        from services.threat_intel_service import (
            _parse_blocked_tlds,
            _parse_internal_domains,
        )

        internal_suffixes = _parse_internal_domains()
        blocked_tlds = _parse_blocked_tlds()

        matches: list[dict] = []
        budget = MAX_LOOKUPS_PER_RUN

        client = OTXClient(api_key=settings.otx_api_key)
        try:
            lookup_plan = [
                ("ip", iocs.get("ips", []), client.lookup_ip),
                ("domain", iocs.get("domains", []), client.lookup_domain),
                ("url", iocs.get("urls", []), client.lookup_url),
                ("hash", iocs.get("hashes", []), client.lookup_hash),
            ]

            for ioc_type, values, lookup in lookup_plan:
                for value in values:
                    if budget <= 0:
                        logger.warning(
                            "OTX lookup budget of %d reached; remaining IOCs skipped",
                            MAX_LOOKUPS_PER_RUN,
                        )
                        return matches

                    decision = should_send_ioc_to_external_ti(
                        ioc_type,
                        value,
                        internal_domain_suffixes=internal_suffixes,
                        blocked_tlds=blocked_tlds,
                    )
                    if not decision.allowed:
                        logger.debug(
                            "Skipped %s IOC %r: %s", ioc_type, value, decision.reason
                        )
                        continue

                    budget -= 1
                    result = await lookup(value)

                    if result.get("error"):
                        logger.warning(
                            "OTX lookup failed for %s %r: %s",
                            ioc_type,
                            value,
                            result.get("message"),
                        )
                        continue

                    if result.get("not_found"):
                        continue

                    verdict = result.get("verdict", "unknown")
                    if verdict in ("malicious", "suspicious"):
                        matches.append(
                            {
                                "indicator": value,
                                "type": ioc_type,
                                "threat_level": verdict,
                                "score": result.get("score", 0),
                                "pulse_count": result.get("pulse_count", 0),
                                "tags": result.get("tags", []),
                                "source": "otx",
                                "description": f"{verdict.capitalize()} indicator "
                                f"({result.get('pulse_count', 0)} pulses)",
                            }
                        )
        finally:
            await client.close()

        return matches


# Register the step
register_step("ti_lookup_otx", TILookupOTXStep)

"""OTX Threat Intelligence lookup node plugin (v0.7.4)."""

import logging
from typing import Any

import aiohttp

from core.config import settings

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


class OtxLookupPlugin(BaseNodePlugin):
    """OTX (AlienVault Open Threat Exchange) threat intelligence lookup.

    This node queries the OTX API for threat intelligence on indicators
    such as IPs, domains, URLs, and file hashes.
    """

    @property
    def node_id(self) -> str:
        return "builtin_otx_lookup"

    @property
    def name(self) -> str:
        return "OTX Threat Intel Lookup"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return "Query OTX (AlienVault) for threat intelligence on indicators"

    def validate_input(self, input_json: dict[str, Any]) -> None:
        """Validate input before execution."""
        ioc = input_json.get("ioc")
        if not ioc:
            raise ValueError("ioc (indicator of compromise) is required")

        ioc_type = input_json.get("ioc_type", "auto")
        valid_types = (
            "auto",
            "ipv4",
            "domain",
            "url",
            "hostname",
            "file_hash_md5",
            "file_hash_sha1",
            "file_hash_sha256",
            "email",
        )
        if ioc_type not in valid_types:
            raise ValueError(f"ioc_type must be one of: {valid_types}")

    async def execute(self, context: NodeExecutionContext) -> dict[str, Any]:
        """Execute OTX threat intelligence lookup.

        Args:
            context: Execution context

        Returns:
            Threat intelligence data including threat score and matches
        """
        ioc = context.input_json.get("ioc")
        ioc_type = context.input_json.get("ioc_type", "auto")

        # Check if external TI is allowed
        if not settings.allow_external_ti:
            logger.warning(
                f"[{context.run_id}] External TI is disabled, skipping OTX lookup"
            )
            return {
                "status": "skipped",
                "message": "External threat intelligence is disabled",
                "ioc": ioc,
            }

        # Get API key from config
        api_key = settings.otx_api_key
        if not api_key:
            logger.warning(f"[{context.run_id}] No OTX API key configured")
            return {
                "status": "error",
                "error": "OTX API key not configured",
                "ioc": ioc,
            }

        # Auto-detect IOC type if needed
        if ioc_type == "auto":
            ioc_type = self._detect_ioc_type(ioc)

        # Build OTX API endpoint
        endpoint = self._get_otx_endpoint(ioc_type, ioc)
        if not endpoint:
            return {
                "status": "error",
                "error": f"Unsupported IOC type or invalid IOC: {ioc_type}",
                "ioc": ioc,
            }

        logger.info(f"[{context.run_id}] OTX lookup: {ioc_type} {ioc}")

        # Make API request
        try:
            headers = {"X-OTX-API-KEY": api_key}
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    endpoint, headers=headers, timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return self._parse_otx_response(data, ioc, ioc_type)
                    elif response.status == 404:
                        return {
                            "status": "success",
                            "ioc": ioc,
                            "ioc_type": ioc_type,
                            "threat_score": 0,
                            "matches": [],
                            "message": "No threat intelligence found",
                        }
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"[{context.run_id}] OTX API error: {response.status} {error_text}"
                        )
                        return {
                            "status": "error",
                            "error": f"OTX API error: {response.status}",
                            "ioc": ioc,
                        }

        except aiohttp.ClientError as e:
            logger.error(f"[{context.run_id}] OTX lookup failed: {e}")
            return {
                "status": "error",
                "error": str(e),
                "ioc": ioc,
            }

    def _detect_ioc_type(self, ioc: str) -> str:
        """Auto-detect IOC type from indicator value."""
        import re

        # IPv4
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", ioc):
            return "ipv4"

        # Domain
        if re.match(
            r"^([a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$", ioc
        ):
            return "domain"

        # URL
        if ioc.startswith(("http://", "https://")):
            return "url"

        # MD5 hash
        if re.match(r"^[a-fA-F0-9]{32}$", ioc):
            return "file_hash_md5"

        # SHA1 hash
        if re.match(r"^[a-fA-F0-9]{40}$", ioc):
            return "file_hash_sha1"

        # SHA256 hash
        if re.match(r"^[a-fA-F0-9]{64}$", ioc):
            return "file_hash_sha256"

        # Email
        if re.match(r"^[^@]+@[^@]+\.[^@]+$", ioc):
            return "email"

        # Default to domain/hostname
        return "hostname"

    def _get_otx_endpoint(self, ioc_type: str, ioc: str) -> str:
        """Get OTX API endpoint for IOC type."""
        base_url = "https://otx.alienvault.com/api/v1/indicators"

        endpoints = {
            "ipv4": f"{base_url}/IPv4/{ioc}",
            "domain": f"{base_url}/domain/{ioc}",
            "hostname": f"{base_url}/hostname/{ioc}",
            "url": f"{base_url}/url/{ioc}",
            "file_hash_md5": f"{base_url}/file/{ioc}",
            "file_hash_sha1": f"{base_url}/file/{ioc}",
            "file_hash_sha256": f"{base_url}/file/{ioc}",
            "email": f"{base_url}/email/{ioc}",
        }

        return endpoints.get(ioc_type)

    def _parse_otx_response(
        self, data: dict[str, Any], ioc: str, ioc_type: str
    ) -> dict[str, Any]:
        """Parse OTX API response into standard format."""
        # Extract threat score
        threat_score = data.get("threat_score", 0)

        # Extract pulse info (threat reports)
        pulses = data.get("pulse_info", {}).get("pulses", [])

        matches = []
        for pulse in pulses[:10]:  # Limit to 10 matches
            matches.append(
                {
                    "name": pulse.get("name", "Unknown"),
                    "description": pulse.get("description", ""),
                    "tags": pulse.get("tags", []),
                    "created": pulse.get("created", ""),
                    "malware_families": pulse.get("malware_families", []),
                }
            )

        return {
            "status": "success",
            "ioc": ioc,
            "ioc_type": ioc_type,
            "threat_score": threat_score,
            "matches": matches,
            "is_malicious": threat_score > 0,
            "match_count": len(matches),
        }

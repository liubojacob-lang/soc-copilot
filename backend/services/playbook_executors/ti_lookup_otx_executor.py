"""OTX Threat Intelligence lookup executor.

v0.8.2: Integrated with actual OTX service instead of mock data.
"""

from typing import Any
from core.config import settings
from core.logger import get_logger
from .executor_base import BaseExecutor, ExecutorContext

logger = get_logger(__name__)


class TiLookupOtxExecutor(BaseExecutor):
    """Executor for OTX threat intelligence lookup."""

    async def execute(self, context: ExecutorContext) -> dict[str, Any]:
        """Execute OTX TI lookup.

        Args:
            context: Execution context with IOC to lookup

        Returns:
            Threat intelligence lookup results
        """
        ioc = self._get_input(context, "ioc")
        ioc_type = self._get_input(context, "ioc_type", "auto")  # auto, ip, domain, url, hash

        if not ioc:
            return {
                "status": "skipped",
                "message": "No IOC provided",
                "matches": [],
            }

        # Check if external TI is enabled
        if not settings.allow_external_ti:
            logger.warning(f"[{context.run_id}] External TI is disabled, skipping OTX lookup")
            return {
                "status": "skipped",
                "message": "External threat intelligence is disabled by configuration",
                "ioc": ioc,
                "matches": [],
            }

        # Check if OTX API key is configured
        if not settings.otx_api_key:
            logger.warning(f"[{context.run_id}] No OTX API key configured")
            return {
                "status": "error",
                "message": "OTX API key not configured",
                "ioc": ioc,
                "matches": [],
            }

        # Import OTX client
        from integrations.otx_client import OTXClient

        otx_client = OTXClient(api_key=settings.otx_api_key)

        try:
            # Auto-detect IOC type if not specified
            if ioc_type == "auto":
                ioc_type = self._detect_ioc_type(ioc)

            logger.info(f"[{context.run_id}] OTX lookup: {ioc_type} {ioc}")

            # Perform lookup based on IOC type
            if ioc_type == "ip":
                result = await otx_client.lookup_ip(ioc)
            elif ioc_type == "domain":
                result = await otx_client.lookup_domain(ioc)
            elif ioc_type == "url":
                result = await otx_client.lookup_url(ioc)
            elif ioc_type == "hash":
                result = await otx_client.lookup_hash(ioc)
            else:
                # Default to IP lookup for unknown types
                result = await otx_client.lookup_ip(ioc)

            # Parse result into standardized format
            return self._parse_otx_result(ioc, ioc_type, result)

        except Exception as e:
            logger.error(f"[{context.run_id}] OTX lookup failed: {e}")
            return {
                "status": "error",
                "message": str(e),
                "ioc": ioc,
                "ioc_type": ioc_type,
                "matches": [],
            }
        finally:
            await otx_client.close()

    def _detect_ioc_type(self, ioc: str) -> str:
        """Detect IOC type from value.

        Args:
            ioc: IOC value to detect type for

        Returns:
            Detected IOC type: ip, domain, url, or hash
        """
        import re

        # IP address pattern (IPv4)
        ip_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
        if re.match(ip_pattern, ioc):
            return "ip"

        # URL pattern
        if ioc.startswith('http://') or ioc.startswith('https://'):
            return "url"

        # Hash patterns (MD5, SHA1, SHA256)
        if re.match(r'^[a-fA-F0-9]{32}$', ioc):
            return "hash"  # MD5
        if re.match(r'^[a-fA-F0-9]{40}$', ioc):
            return "hash"  # SHA1
        if re.match(r'^[a-fA-F0-9]{64}$', ioc):
            return "hash"  # SHA256

        # Default to domain
        return "domain"

    def _parse_otx_result(self, ioc: str, ioc_type: str, result: dict) -> dict[str, Any]:
        """Parse OTX result into standardized format.

        Args:
            ioc: Original IOC value
            ioc_type: IOC type
            result: Raw OTX result

        Returns:
            Standardized result dictionary
        """
        # Handle error responses
        if result.get("error"):
            return {
                "status": "error",
                "message": result.get("message", "OTX lookup failed"),
                "ioc": ioc,
                "ioc_type": ioc_type,
                "matches": [],
            }

        # Handle not found responses
        if result.get("not_found"):
            return {
                "status": "success",
                "message": "No threat intelligence found",
                "ioc": ioc,
                "ioc_type": ioc_type,
                "matches": [],
                "score": 0,
            }

        # Extract threat information
        verdict = result.get("verdict", "unknown")
        score = result.get("score", 0)
        tags = result.get("tags", [])
        pulse_count = result.get("pulse_count", 0)

        # Build matches from pulses
        matches = []
        if pulse_count > 0:
            matches.append({
                "indicator": ioc,
                "threat_type": ", ".join(tags[:5]) if tags else "unknown",
                "confidence": min(score, 100),
                "pulse_count": pulse_count,
                "verdict": verdict,
            })

        return {
            "status": "success",
            "ioc": ioc,
            "ioc_type": ioc_type,
            "verdict": verdict,
            "score": score,
            "tags": tags,
            "pulse_count": pulse_count,
            "matches": matches,
            "references": result.get("references", []),
        }

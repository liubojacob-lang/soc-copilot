"""Extract secondary IOCs from threat intelligence results (v0.7.4)."""

import logging
import re
from typing import Any

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


class ExtractIOCsPlugin(BaseNodePlugin):
    """Extract secondary IOCs from OTX or other TI sources.

    This node parses threat intelligence results to extract
    additional IOCs like IPs, domains, URLs, and hashes.
    """

    @property
    def node_id(self) -> str:
        return "builtin_extract_iocs"

    @property
    def name(self) -> str:
        return "Extract Secondary IOCs"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return "Extract secondary IOCs from threat intelligence results"

    def validate_input(self, input_json: dict[str, Any]) -> None:
        """Validate input before execution."""
        ti_result = input_json.get("ti_result") or input_json.get("otx_result")
        if not ti_result:
            raise ValueError("ti_result or otx_result is required")

    async def execute(self, context: NodeExecutionContext) -> dict[str, Any]:
        """Execute IOC extraction.

        Args:
            context: Execution context

        Returns:
            Extracted IOCs organized by type
        """
        ti_result = context.input_json.get("ti_result") or context.input_json.get(
            "otx_result"
        )
        case_id = context.input_json.get("case_id", "unknown")

        logger.info(
            f"[{context.run_id}] Extracting IOCs from TI result for case {case_id}"
        )

        extracted = {"ips": [], "domains": [], "urls": [], "hashes": [], "emails": []}

        # Extract from OTX pulses
        if isinstance(ti_result, dict):
            pulses = ti_result.get("matches", [])

            for pulse in pulses:
                # Extract from pulse name and description
                text_to_scan = f"{pulse.get('name', '')} {pulse.get('description', '')}"

                # Extract IPs
                ips = self._extract_ips(text_to_scan)
                extracted["ips"].extend(ips)

                # Extract domains
                domains = self._extract_domains(text_to_scan)
                extracted["domains"].extend(domains)

                # Extract URLs
                urls = self._extract_urls(text_to_scan)
                extracted["urls"].extend(urls)

                # Extract hashes
                hashes = self._extract_hashes(text_to_scan)
                extracted["hashes"].extend(hashes)

            # Also check indicator details if available
            indicator_data = ti_result.get("indicator", {})
            if indicator_data:
                # Add related indicators from OTX
                related = indicator_data.get("related", [])
                for rel in related:
                    rel_type = rel.get("type", "").lower()
                    rel_val = rel.get("indicator", "")
                    if rel_type in ("ipv4", "ip") and rel_val:
                        extracted["ips"].append(rel_val)
                    elif rel_type == "domain" and rel_val:
                        extracted["domains"].append(rel_val)
                    elif rel_type in ("url", "uri") and rel_val:
                        extracted["urls"].append(rel_val)
                    elif "hash" in rel_type and rel_val:
                        extracted["hashes"].append(rel_val)

        # Deduplicate
        for key in extracted:
            extracted[key] = list(set(extracted[key]))

        total_extracted = sum(len(v) for v in extracted.values())

        logger.info(f"[{context.run_id}] Extracted {total_extracted} secondary IOCs")

        return {
            "status": "success",
            "case_id": case_id,
            "primary_ioc": ti_result.get("ioc", "unknown"),
            "extracted_iocs": extracted,
            "total_extracted": total_extracted,
            "summary": {
                "ips": len(extracted["ips"]),
                "domains": len(extracted["domains"]),
                "urls": len(extracted["urls"]),
                "hashes": len(extracted["hashes"]),
                "emails": len(extracted["emails"]),
            },
        }

    def _extract_ips(self, text: str) -> list[str]:
        """Extract IPv4 addresses from text."""
        pattern = r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b"
        return list(set(re.findall(pattern, text)))

    def _extract_domains(self, text: str) -> list[str]:
        """Extract domain names from text."""
        pattern = (
            r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b"
        )
        domains = re.findall(pattern, text)
        # Filter out common false positives
        filtered = [
            d
            for d in domains
            if not any(
                x in d.lower() for x in [".png", ".jpg", ".jpeg", ".gif", ".css", ".js"]
            )
        ]
        return list(set(filtered))

    def _extract_urls(self, text: str) -> list[str]:
        """Extract URLs from text."""
        pattern = r'https?://[^\s<>"\']+|www\.[^\s<>"\']+'
        return list(set(re.findall(pattern, text)))

    def _extract_hashes(self, text: str) -> list[str]:
        """Extract file hashes (MD5, SHA1, SHA256) from text."""
        hashes = []
        # MD5
        md5_pattern = r"\b[a-fA-F0-9]{32}\b"
        hashes.extend(re.findall(md5_pattern, text))
        # SHA1
        sha1_pattern = r"\b[a-fA-F0-9]{40}\b"
        hashes.extend(re.findall(sha1_pattern, text))
        # SHA256
        sha256_pattern = r"\b[a-fA-F0-9]{64}\b"
        hashes.extend(re.findall(sha256_pattern, text))
        return list(set(hashes))

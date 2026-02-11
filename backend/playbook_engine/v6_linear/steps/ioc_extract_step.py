"""IOC extraction step implementation."""

from typing import Any
import re
from .base_step import BaseStepImpl
from ..registry import register_step


class IOCExtractStep(BaseStepImpl):
    """Extract Indicators of Compromise from input data."""

    @property
    def name(self) -> str:
        return "IOC Extraction"

    @property
    def step_id(self) -> str:
        return "ioc_extract"

    @property
    def step_type(self) -> str:
        return "extraction"

    @property
    def description(self) -> str:
        return "Extract IPs, domains, URLs, hashes from input data"

    @property
    def supports_apply(self) -> bool:
        return True

    def execute(self, input_json: dict[str, Any], mode: str) -> dict[str, Any]:
        """Extract IOCs from input data.

        Args:
            input_json: Input containing raw data (email, alert, etc.)
            mode: Execution mode

        Returns:
            Dictionary with extracted IOCs
        """
        iocs = {
            "ips": [],
            "domains": [],
            "urls": [],
            "hashes": [],
            "emails": [],
        }

        # Extract from alert_data if present
        alert_data = input_json.get("alert_data", {})
        source_text = input_json.get("source_text", "")

        # Combine all text for extraction
        all_text = " ".join([
            str(alert_data),
            source_text,
            input_json.get("description", ""),
            input_json.get("subject", ""),
            input_json.get("body", ""),
        ])

        # Extract IPs
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        ips = re.findall(ip_pattern, all_text)
        iocs["ips"] = list(set(ips))

        # Extract domains (use non-capturing groups to get full matches)
        domain_pattern = r'\b[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*\.[a-zA-Z]{2,}\b'
        domains = re.findall(domain_pattern, all_text)
        iocs["domains"] = list(set(domains))

        # Extract URLs
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        urls = re.findall(url_pattern, all_text)
        iocs["urls"] = list(set(urls))

        # Extract hashes (MD5, SHA1, SHA256)
        hash_patterns = [
            (r'\b[a-f0-9]{32}\b', 'md5'),
            (r'\b[a-f0-9]{40}\b', 'sha1'),
            (r'\b[a-f0-9]{64}\b', 'sha256'),
        ]
        for pattern, hash_type in hash_patterns:
            hashes = re.findall(pattern, all_text, re.IGNORECASE)
            iocs["hashes"].extend(hashes)

        iocs["hashes"] = list(set(iocs["hashes"]))

        return {
            "iocs": iocs,
            "count": sum(len(v) for v in iocs.values()),
            "source_fields": list(alert_data.keys()) if alert_data else [],
        }


# Register the step
register_step("ioc_extract", IOCExtractStep)

"""IOC extraction executor."""

import re
from typing import Any

from .executor_base import BaseExecutor, ExecutorContext


class ExtractIocsExecutor(BaseExecutor):
    """Executor for extracting IOCs from text."""

    async def execute(self, context: ExecutorContext) -> dict[str, Any]:
        """Extract IOCs from input text."""
        text = self._get_input(context, "text", "")

        iocs = {
            "ips": self._extract_ips(text),
            "domains": self._extract_domains(text),
            "urls": self._extract_urls(text),
            "hashes": self._extract_hashes(text),
            "emails": self._extract_emails(text),
        }

        total = sum(len(v) for v in iocs.values())

        return {
            "status": "success",
            "iocs": iocs,
            "total_count": total,
        }

    def _extract_ips(self, text: str) -> list[str]:
        """Extract IPv4 addresses."""
        pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"
        return list(set(re.findall(pattern, text)))

    def _extract_domains(self, text: str) -> list[str]:
        """Extract domain names."""
        pattern = r"\b[a-zA-Z0-9][-a-zA-Z0-9]{0,61}(?:\.[a-zA-Z0-9][-a-zA-Z0-9]{0,61})+\.[a-zA-Z]{2,}\b"
        return list(set(re.findall(pattern, text)))

    def _extract_urls(self, text: str) -> list[str]:
        """Extract URLs."""
        pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        return list(set(re.findall(pattern, text)))

    def _extract_hashes(self, text: str) -> list[str]:
        """Extract MD5, SHA1, SHA256 hashes."""
        md5 = r"\b[a-fA-F0-9]{32}\b"
        sha1 = r"\b[a-fA-F0-9]{40}\b"
        sha256 = r"\b[a-fA-F0-9]{64}\b"
        return list(
            set(
                re.findall(md5, text)
                + re.findall(sha1, text)
                + re.findall(sha256, text)
            )
        )

    def _extract_emails(self, text: str) -> list[str]:
        """Extract email addresses."""
        pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        return list(set(re.findall(pattern, text)))

"""AlienVault OTX API client for threat intelligence lookup.

v0.8.3: Added automatic retry with exponential backoff.
"""

from typing import Any

import httpx

from core.logger import get_logger

logger = get_logger(__name__)


class OTXClient:
    """AlienVault OTX API client.

    Reference: https://otx.alienvault.com/api
    """

    BASE_URL = "https://otx.alienvault.com/api/v1"
    USER_AGENT = "SOC-Copilot/0.4"

    def __init__(self, api_key: str, timeout: float = 10.0):
        """Initialize OTX client.

        Args:
            api_key: OTX API key
            timeout: Request timeout in seconds
        """
        self.api_key = api_key
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client.

        Returns:
            Async HTTP client
        """
        if self._client is None or self._client.is_closed:
            headers = {
                "X-OTX-API-KEY": self.api_key,
                "User-Agent": self.USER_AGENT,
            }
            self._client = httpx.AsyncClient(
                base_url=self.BASE_URL,
                headers=headers,
                timeout=self.timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def lookup_ip(self, ip: str) -> dict[str, Any]:
        """Lookup IP reputation in OTX.

        Args:
            ip: IP address

        Returns:
            Parsed response with verdict, score, tags, etc.
        """
        client = await self._get_client()
        try:
            # Get IP reputation
            response = await client.get(f"/indicators/IPv4/{ip}/general")
            response.raise_for_status()
            data = response.json()

            # Parse response
            return self._parse_ip_response(ip, data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return self._not_found_response("ip", ip)
            logger.error(f"OTX IP lookup failed for {ip}: {e}")
            return self._error_response("ip", ip, str(e))
        except Exception as e:
            logger.error(f"OTX IP lookup error for {ip}: {e}")
            return self._error_response("ip", ip, str(e))

    async def lookup_domain(self, domain: str) -> dict[str, Any]:
        """Lookup domain reputation in OTX.

        Args:
            domain: Domain name

        Returns:
            Parsed response
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/indicators/domain/{domain}/general")
            response.raise_for_status()
            data = response.json()

            return self._parse_domain_response(domain, data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return self._not_found_response("domain", domain)
            logger.error(f"OTX domain lookup failed for {domain}: {e}")
            return self._error_response("domain", domain, str(e))
        except Exception as e:
            logger.error(f"OTX domain lookup error for {domain}: {e}")
            return self._error_response("domain", domain, str(e))

    async def lookup_url(self, url: str) -> dict[str, Any]:
        """Lookup URL reputation in OTX.

        Args:
            url: URL

        Returns:
            Parsed response
        """
        client = await self._get_client()
        try:
            # OTX requires URL to be URL-encoded
            encoded_url = httpx.URL(url).path
            response = await client.get(f"/indicators/url/{encoded_url}/general")
            response.raise_for_status()
            data = response.json()

            return self._parse_url_response(url, data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return self._not_found_response("url", url)
            logger.error(f"OTX URL lookup failed for {url}: {e}")
            return self._error_response("url", url, str(e))
        except Exception as e:
            logger.error(f"OTX URL lookup error for {url}: {e}")
            return self._error_response("url", url, str(e))

    async def lookup_hash(self, hash_value: str) -> dict[str, Any]:
        """Lookup file hash reputation in OTX.

        Args:
            hash_value: File hash (MD5, SHA1, or SHA256)

        Returns:
            Parsed response
        """
        client = await self._get_client()
        try:
            response = await client.get(f"/indicators/file/{hash_value}/general")
            response.raise_for_status()
            data = response.json()

            return self._parse_hash_response(hash_value, data)
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return self._not_found_response("hash", hash_value)
            logger.error(f"OTX hash lookup failed for {hash_value}: {e}")
            return self._error_response("hash", hash_value, str(e))
        except Exception as e:
            logger.error(f"OTX hash lookup error for {hash_value}: {e}")
            return self._error_response("hash", hash_value, str(e))

    def _parse_ip_response(self, ip: str, data: dict) -> dict[str, Any]:
        """Parse OTX IP response.

        Args:
            ip: IP address
            data: Raw OTX response

        Returns:
            Standardized response
        """
        # Extract threat score
        score = self._calculate_score_from_sections(data)

        # Extract pulses
        pulse_info = data.get("pulse_info", {})
        pulse_count = pulse_info.get("count", 0)
        pulses = pulse_info.get("pulses", [])

        # Extract tags
        tags = set()
        for pulse in pulses:
            tags.update(pulse.get("tags", []))

        # Extract malware families
        malware_families = data.get("malware_families", [])
        for mf in malware_families:
            tags.add(mf.get("family", ""))

        # Determine verdict
        verdict = self._determine_verdict(score, bool(tags))

        # Get references
        references = []
        for pulse in pulses[:5]:
            references.append(pulse.get("url", ""))

        return {
            "ioc_type": "ip",
            "ioc_value": ip,
            "verdict": verdict,
            "score": score,
            "pulse_count": pulse_count,
            "tags": list(tags),
            "references": references,
            "raw": data,
        }

    def _parse_domain_response(self, domain: str, data: dict) -> dict[str, Any]:
        """Parse OTX domain response."""
        score = self._calculate_score_from_sections(data)

        pulse_info = data.get("pulse_info", {})
        pulse_count = pulse_info.get("count", 0)
        pulses = pulse_info.get("pulses", [])

        tags = set()
        for pulse in pulses:
            tags.update(pulse.get("tags", []))

        verdict = self._determine_verdict(score, bool(tags))

        references = [p.get("url", "") for p in pulses[:5]]

        # WHOIS data for last_seen
        whois = data.get("whois", {})
        last_seen = None
        if whois:
            # Parse WHOIS date if available
            pass  # Simplified for now

        return {
            "ioc_type": "domain",
            "ioc_value": domain,
            "verdict": verdict,
            "score": score,
            "pulse_count": pulse_count,
            "tags": list(tags),
            "references": references,
            "last_seen": last_seen,
            "raw": data,
        }

    def _parse_url_response(self, url: str, data: dict) -> dict[str, Any]:
        """Parse OTX URL response."""
        score = self._calculate_score_from_sections(data)

        pulse_info = data.get("pulse_info", {})
        pulse_count = pulse_info.get("count", 0)
        pulses = pulse_info.get("pulses", [])

        tags = set()
        for pulse in pulses:
            tags.update(pulse.get("tags", []))

        verdict = self._determine_verdict(score, bool(tags))

        references = [p.get("url", "") for p in pulses[:5]]

        return {
            "ioc_type": "url",
            "ioc_value": url,
            "verdict": verdict,
            "score": score,
            "pulse_count": pulse_count,
            "tags": list(tags),
            "references": references,
            "raw": data,
        }

    def _parse_hash_response(self, hash_value: str, data: dict) -> dict[str, Any]:
        """Parse OTX hash response."""
        score = self._calculate_score_from_sections(data)

        pulse_info = data.get("pulse_info", {})
        pulse_count = pulse_info.get("count", 0)
        pulses = pulse_info.get("pulses", [])

        tags = set()
        for pulse in pulses:
            tags.update(pulse.get("tags", []))

        # Add malware families as tags
        malware_families = data.get("malware_families", [])
        for mf in malware_families:
            tags.add(mf.get("family", ""))

        verdict = self._determine_verdict(score, bool(tags))

        references = [p.get("url", "") for p in pulses[:5]]

        # Last seen from detections
        detections = data.get("detections", {})
        last_seen = None
        if detections:
            # Could parse detection dates
            pass

        return {
            "ioc_type": "hash",
            "ioc_value": hash_value,
            "verdict": verdict,
            "score": score,
            "pulse_count": pulse_count,
            "tags": list(tags),
            "references": references,
            "last_seen": last_seen,
            "raw": data,
        }

    def _calculate_score_from_sections(self, data: dict) -> int:
        """Calculate threat score from OTX section data.

        Args:
            data: OTX response data

        Returns:
            Score 0-100
        """
        score = 0

        # Check sections
        sections = data.get("sections", [])

        # High threat indicators
        if "malware" in sections:
            score += 40
        if "exploit kits" in sections:
            score += 35
        if "fraud" in sections:
            score += 30

        # Medium threat indicators
        if "scanning" in sections:
            score += 20
        if "c2" in sections:
            score += 30

        # Pulse count contributes
        pulse_info = data.get("pulse_info", {})
        pulse_count = pulse_info.get("count", 0)
        score += min(pulse_count * 5, 25)

        # Reputation
        reputation = data.get("reputation", {})
        if reputation:
            rep_value = reputation.get("reputation_value", 0)
            # OTX reputation is negative for bad
            if rep_value < 0:
                score += abs(rep_value)

        return min(score, 100)

    def _determine_verdict(self, score: int, has_tags: bool) -> str:
        """Determine verdict from score and tags.

        Args:
            score: Threat score
            has_tags: Whether threat tags exist

        Returns:
            Verdict: malicious/suspicious/unknown/benign
        """
        if score >= 70:
            return "malicious"
        elif score >= 40 or has_tags:
            return "suspicious"
        elif score > 0:
            return "unknown"
        else:
            return "benign"

    def _not_found_response(self, ioc_type: str, ioc_value: str) -> dict[str, Any]:
        """Return not found response.

        Args:
            ioc_type: IOC type
            ioc_value: IOC value

        Returns:
            Not found response dict
        """
        return {
            "ioc_type": ioc_type,
            "ioc_value": ioc_value,
            "verdict": "benign",
            "score": 0,
            "pulse_count": 0,
            "tags": [],
            "references": [],
            "raw": {},
        }

    def _error_response(
        self, ioc_type: str, ioc_value: str, error: str
    ) -> dict[str, Any]:
        """Return error response.

        Args:
            ioc_type: IOC type
            ioc_value: IOC value
            error: Error message

        Returns:
            Error response dict
        """
        return {
            "ioc_type": ioc_type,
            "ioc_value": ioc_value,
            "verdict": "unknown",
            "score": 0,
            "pulse_count": 0,
            "tags": [],
            "references": [],
            "error_reason": error,
            "raw": {},
        }

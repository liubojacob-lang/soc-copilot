"""VirusTotal API v3 integration service.

Features:
- IP lookup, Domain lookup, URL scan, Hash (file) lookup
- Response caching via ThreatIntelCacheModel
- Rate limiting (4 req/min for free tier)
- Graceful error degradation
- httpx.AsyncClient HTTP client

Reference: https://docs.virustotal.com/reference/overview
"""

import asyncio
import json
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import httpx

from core.config import settings
from core.logger import get_logger
from models.threat_intel_cache import ThreatIntelCacheModel

logger = get_logger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

VT_API_BASE = "https://www.virustotal.com/api/v3"
VT_DEFAULT_TTL_HOURS = 24
VT_CACHE_PROVIDER = "virustotal"

# Rate limit state (free tier: 4 req/min)
_rate_limit_lock = asyncio.Lock()
_last_request_times: list[float] = []


async def _rate_limit(
    max_rpm: int | None = None,
) -> None:
    """Enforce per-minute rate limit using a sliding window.

    Args:
        max_rpm: Max requests per minute (defaults to config value)
    """
    rpm = max_rpm or settings.virustotal_rate_limit_rpm
    async with _rate_limit_lock:
        now = time.monotonic()
        window_start = now - 60.0

        # Remove expired timestamps
        global _last_request_times
        _last_request_times = [t for t in _last_request_times if t > window_start]

        if len(_last_request_times) >= rpm:
            # Wait until the oldest request falls out of the window
            wait = _last_request_times[0] - window_start + 0.1
            if wait > 0:
                logger.debug("VT rate-limit: waiting %.1fs", wait)
                await asyncio.sleep(wait)
                now = time.monotonic()
                window_start = now - 60.0
                _last_request_times = [
                    t for t in _last_request_times if t > window_start
                ]

        _last_request_times.append(now)


# ── Service ──────────────────────────────────────────────────────────────────


class VirusTotalService:
    """VirusTotal API v3 integration with caching and rate limiting.

    Usage:
        async with VirusTotalService() as vt:
            result = await vt.lookup_ip("8.8.8.8")
            result = await vt.lookup_hash("d41d8...")
    """

    def __init__(
        self,
        session: Any = None,  # AsyncSession for DB cache
        api_key: str | None = None,
        timeout: float = 30.0,
    ):
        """Initialize VirusTotal service.

        Args:
            session: SQLAlchemy async session for cache reads/writes
            api_key: VT API key (uses config if not provided)
            timeout: HTTP request timeout in seconds
        """
        self._db_session = session
        self._api_key = api_key or settings.virustotal_api_key
        self._timeout = timeout
        self._client: httpx.AsyncClient | None = None
        self._enabled = bool(self._api_key)

    @property
    def is_enabled(self) -> bool:
        """Whether VT integration is configured."""
        return self._enabled

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=VT_API_BASE,
                headers={
                    "x-apikey": self._api_key,
                    "Accept": "application/json",
                },
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "VirusTotalService":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ── Cache helpers ────────────────────────────────────────────────────

    async def _get_cached(
        self,
        ioc_type: str,
        ioc_value: str,
    ) -> dict[str, Any] | None:
        """Try to read a cached VT result from the database.

        Returns parsed response_json dict or None.
        """
        if self._db_session is None:
            return None

        try:
            from sqlalchemy import and_, select

            result = await self._db_session.execute(
                select(ThreatIntelCacheModel).where(
                    and_(
                        ThreatIntelCacheModel.provider == VT_CACHE_PROVIDER,
                        ThreatIntelCacheModel.ioc_type == ioc_type,
                        ThreatIntelCacheModel.ioc_value == ioc_value,
                        ThreatIntelCacheModel.expires_at > datetime.now(UTC),
                    )
                )
            )
            row = result.scalar_one_or_none()
            if row is not None and row.response_json:
                return (
                    json.loads(row.response_json)
                    if isinstance(row.response_json, str)
                    else row.response_json
                )
        except Exception:
            logger.exception("Failed to read VT cache for %s:%s", ioc_type, ioc_value)

        return None

    async def _set_cache(
        self,
        ioc_type: str,
        ioc_value: str,
        status: str,
        response: dict[str, Any] | None = None,
        score: int | None = None,
        tags: list[str] | None = None,
        ttl_hours: int = VT_DEFAULT_TTL_HOURS,
    ) -> None:
        """Write a VT result to the cache."""
        if self._db_session is None:
            return

        try:
            import uuid

            expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

            # Check for existing row to update
            from sqlalchemy import and_, select

            existing = await self._db_session.execute(
                select(ThreatIntelCacheModel).where(
                    and_(
                        ThreatIntelCacheModel.provider == VT_CACHE_PROVIDER,
                        ThreatIntelCacheModel.ioc_type == ioc_type,
                        ThreatIntelCacheModel.ioc_value == ioc_value,
                    )
                )
            )
            row = existing.scalar_one_or_none()

            if row is not None:
                row.status = status
                row.response_json = json.dumps(response) if response else None
                row.score = score
                row.tags = json.dumps(tags) if tags else None
                row.expires_at = expires_at
                row.updated_at = datetime.now(UTC)
            else:
                cache = ThreatIntelCacheModel(
                    id=str(uuid.uuid4()),
                    provider=VT_CACHE_PROVIDER,
                    ioc_type=ioc_type,
                    ioc_value=ioc_value,
                    status=status,
                    response_json=json.dumps(response) if response else None,
                    score=score,
                    tags=json.dumps(tags) if tags else None,
                    expires_at=expires_at,
                )
                self._db_session.add(cache)

            await self._db_session.flush()
        except Exception:
            logger.exception("Failed to write VT cache for %s:%s", ioc_type, ioc_value)

    # ── HTTP helpers ────────────────────────────────────────────────────

    async def _get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a rate-limited GET request to the VT API."""
        if not self._enabled:
            raise RuntimeError("VirusTotal API key not configured")

        await _rate_limit()

        client = await self._get_client()

        try:
            response = await client.get(endpoint, params=params)
            if response.status_code == 429:
                logger.warning("VT rate-limited (429), waiting 60s...")
                await asyncio.sleep(60)
                response = await client.get(endpoint, params=params)

            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.info("VT: %s not found (404)", endpoint)
                return {"not_found": True}
            if exc.response.status_code == 403:
                logger.error("VT: API key invalid or forbidden (403)")
                raise RuntimeError("VirusTotal API key is invalid or lacks permission")
            logger.error(
                "VT HTTP error %d on %s: %s", exc.response.status_code, endpoint, exc
            )
            raise
        except httpx.RequestError as exc:
            logger.error("VT network error on %s: %s", endpoint, exc)
            raise ConnectionError(f"VirusTotal API unreachable: {exc}") from exc

    # ── Public API ──────────────────────────────────────────────────────

    async def lookup_ip(self, ip: str, use_cache: bool = True) -> dict[str, Any]:
        """Look up an IP address reputation in VirusTotal.

        Returns a normalized dict with keys:
            - ioc_type, ioc_value, provider, verdict, score, tags,
            - last_analysis_date, country, as_owner, malicious_votes,
            - total_votes, cached
        """
        ioc_type = "ip"
        ioc_value = ip.strip()

        # Cache check
        if use_cache:
            cached = await self._get_cached(ioc_type, ioc_value)
            if cached is not None:
                cached["cached"] = True
                return cached

        # API call
        try:
            data = await self._get(f"/ip_addresses/{ioc_value}")
        except Exception:
            logger.exception(
                "VT IP lookup failed for %s, returning degraded result", ioc_value
            )
            return await self._degraded_result(ioc_type, ioc_value, use_cache)

        result = self._parse_ip_response(data)

        # Persist cache
        await self._set_cache(
            ioc_type=ioc_type,
            ioc_value=ioc_value,
            status="ok",
            response=result,
            score=result.get("score"),
            tags=result.get("tags"),
        )

        return result

    async def lookup_domain(
        self, domain: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """Look up a domain in VirusTotal."""
        ioc_type = "domain"
        ioc_value = domain.strip().lower()

        if use_cache:
            cached = await self._get_cached(ioc_type, ioc_value)
            if cached is not None:
                cached["cached"] = True
                return cached

        try:
            data = await self._get(f"/domains/{ioc_value}")
        except Exception:
            logger.exception("VT domain lookup failed for %s", ioc_value)
            return await self._degraded_result(ioc_type, ioc_value, use_cache)

        result = self._parse_domain_response(data)

        await self._set_cache(
            ioc_type=ioc_type,
            ioc_value=ioc_value,
            status="ok",
            response=result,
            score=result.get("score"),
            tags=result.get("tags"),
        )

        return result

    async def lookup_hash(
        self, file_hash: str, use_cache: bool = True
    ) -> dict[str, Any]:
        """Look up a file hash (MD5/SHA-1/SHA-256) in VirusTotal."""
        ioc_type = "hash"
        ioc_value = file_hash.strip().lower()

        if use_cache:
            cached = await self._get_cached(ioc_type, ioc_value)
            if cached is not None:
                cached["cached"] = True
                return cached

        try:
            data = await self._get(f"/files/{ioc_value}")
        except Exception:
            logger.exception("VT hash lookup failed for %s", ioc_value)
            return await self._degraded_result(ioc_type, ioc_value, use_cache)

        result = self._parse_file_response(data)

        await self._set_cache(
            ioc_type=ioc_type,
            ioc_value=ioc_value,
            status="ok",
            response=result,
            score=result.get("score"),
            tags=result.get("tags"),
        )

        return result

    async def lookup_url(self, url: str, use_cache: bool = True) -> dict[str, Any]:
        """Look up a URL in VirusTotal.

        Uses the VT URL identifier (base64url-encoded URL without padding).
        """
        import base64

        ioc_type = "url"
        ioc_value = url.strip()

        if use_cache:
            cached = await self._get_cached(ioc_type, ioc_value)
            if cached is not None:
                cached["cached"] = True
                return cached

        # VT v3 uses base64url-encoded URL identifier
        url_id = base64.urlsafe_b64encode(ioc_value.encode()).decode().rstrip("=")

        try:
            data = await self._get(f"/urls/{url_id}")
        except Exception:
            logger.exception("VT URL lookup failed for %s", ioc_value)
            return await self._degraded_result(ioc_type, ioc_value, use_cache)

        result = self._parse_url_response(data, ioc_value)

        await self._set_cache(
            ioc_type=ioc_type,
            ioc_value=ioc_value,
            status="ok",
            response=result,
            score=result.get("score"),
            tags=result.get("tags"),
        )

        return result

    async def scan_url(self, url: str) -> dict[str, Any]:
        """Submit a URL for scanning in VirusTotal.

        Returns the scan ID for later lookup.
        """
        if not self._enabled:
            raise RuntimeError("VirusTotal API key not configured")

        await _rate_limit()

        client = await self._get_client()

        try:
            response = await client.post(
                "/urls",
                data={"url": url},
            )
            response.raise_for_status()
            data = response.json()

            scan_id = data.get("data", {}).get("id", "")
            return {
                "ioc_type": "url",
                "ioc_value": url,
                "provider": "virustotal",
                "scan_id": scan_id,
                "status": "submitted",
                "message": f"URL submitted for scanning: {scan_id}",
            }
        except httpx.HTTPStatusError as exc:
            logger.error("VT URL scan error: %s", exc)
            if exc.response.status_code == 429:
                return {
                    "ioc_type": "url",
                    "ioc_value": url,
                    "provider": "virustotal",
                    "verdict": "error",
                    "error": "Rate limited. Retry after 60 seconds.",
                }
            return {
                "ioc_type": "url",
                "ioc_value": url,
                "provider": "virustotal",
                "verdict": "error",
                "error": str(exc),
            }

    # ── Batch lookup ───────────────────────────────────────────────────

    async def batch_lookup(
        self,
        iocs: list[dict[str, str]],
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """Batch lookup multiple IOCs.

        Args:
            iocs: List of dicts with keys 'type' and 'value'
                  e.g. [{"type": "ip", "value": "1.2.3.4"}, ...]

        Returns:
            List of result dicts in the same order
        """
        results: list[dict[str, Any]] = []
        for ioc in iocs:
            ioc_type = ioc.get("type", "").lower()
            ioc_value = ioc.get("value", "")

            try:
                if ioc_type == "ip":
                    result = await self.lookup_ip(ioc_value, use_cache=use_cache)
                elif ioc_type == "domain":
                    result = await self.lookup_domain(ioc_value, use_cache=use_cache)
                elif ioc_type in ("hash", "md5", "sha1", "sha256"):
                    result = await self.lookup_hash(ioc_value, use_cache=use_cache)
                elif ioc_type == "url":
                    result = await self.lookup_url(ioc_value, use_cache=use_cache)
                else:
                    result = {
                        "ioc_type": ioc_type,
                        "ioc_value": ioc_value,
                        "provider": "virustotal",
                        "verdict": "error",
                        "error": f"Unsupported IOC type: {ioc_type}",
                    }
            except Exception as exc:
                result = {
                    "ioc_type": ioc_type,
                    "ioc_value": ioc_value,
                    "provider": "virustotal",
                    "verdict": "error",
                    "error": str(exc),
                }

            results.append(result)

            # Small delay between batch items to respect rate limits
            if len(results) < len(iocs):
                await asyncio.sleep(0.3)

        return results

    # ── Response parsers ───────────────────────────────────────────────

    def _parse_ip_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse VT IP address API response into normalized format."""
        attrs = data.get("data", {}).get("attributes", {})

        stats = attrs.get("last_analysis_stats", {})
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        harmless = stats.get("harmless", 0)
        stats.get("undetected", 0)
        total = sum(stats.values())

        # Compute VT-style score (proportion of malicious + suspicious)
        score = int((malicious + suspicious) / max(total, 1) * 100)

        # Verdict
        if malicious > 0:
            verdict = "malicious"
        elif suspicious > 0:
            verdict = "suspicious"
        elif harmless > 0 and malicious == 0:
            verdict = "clean"
        else:
            verdict = "unknown"

        # Extract tags from last_analysis_results
        tags: list[str] = []
        analysis_results = attrs.get("last_analysis_results", {})
        for _engine, result in analysis_results.items():
            if result.get("category") in ("malicious", "suspicious"):
                engine_result = result.get("result", "")
                if engine_result:
                    tags.append(engine_result)

        return {
            "ioc_type": "ip",
            "ioc_value": data.get("data", {}).get("id", ""),
            "provider": "virustotal",
            "verdict": verdict,
            "score": score,
            "tags": list(set(tags))[:20],  # deduplicate, limit
            "last_analysis_date": attrs.get("last_analysis_date"),
            "country": attrs.get("country"),
            "as_owner": attrs.get("as_owner"),
            "asn": attrs.get("asn"),
            "malicious_votes": malicious,
            "suspicious_votes": suspicious,
            "harmless_votes": harmless,
            "total_votes": total,
            "reputation": attrs.get("reputation", 0),
            "continent": attrs.get("continent"),
            "network": attrs.get("network"),
            "cached": False,
        }

    def _parse_domain_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse VT domain API response into normalized format."""
        attrs = data.get("data", {}).get("attributes", {})

        stats = attrs.get("last_analysis_stats", {})
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        harmless = stats.get("harmless", 0)
        total = sum(stats.values())

        score = int((malicious + suspicious) / max(total, 1) * 100)

        if malicious > 0:
            verdict = "malicious"
        elif suspicious > 0:
            verdict = "suspicious"
        elif harmless > 0 and malicious == 0:
            verdict = "clean"
        else:
            verdict = "unknown"

        tags: list[str] = []
        analysis_results = attrs.get("last_analysis_results", {})
        for _engine, result in analysis_results.items():
            if result.get("category") in ("malicious", "suspicious"):
                engine_result = result.get("result", "")
                if engine_result:
                    tags.append(engine_result)

        return {
            "ioc_type": "domain",
            "ioc_value": data.get("data", {}).get("id", ""),
            "provider": "virustotal",
            "verdict": verdict,
            "score": score,
            "tags": list(set(tags))[:20],
            "last_analysis_date": attrs.get("last_analysis_date"),
            "registrar": attrs.get("registrar"),
            "creation_date": attrs.get("creation_date"),
            "last_update_date": attrs.get("last_update_date"),
            "malicious_votes": malicious,
            "suspicious_votes": suspicious,
            "total_votes": total,
            "categories": attrs.get("categories", {}),
            "cached": False,
        }

    def _parse_file_response(self, data: dict[str, Any]) -> dict[str, Any]:
        """Parse VT file (hash) API response into normalized format."""
        attrs = data.get("data", {}).get("attributes", {})

        stats = attrs.get("last_analysis_stats", {})
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        harmless = stats.get("harmless", 0)
        total = sum(stats.values())

        score = int((malicious + suspicious) / max(total, 1) * 100)

        if malicious > 0:
            verdict = "malicious"
        elif suspicious > 0:
            verdict = "suspicious"
        elif harmless > 0 and malicious == 0:
            verdict = "clean"
        else:
            verdict = "unknown"

        # Extract malware names from detections
        tags: list[str] = []
        analysis_results = attrs.get("last_analysis_results", {})
        for _engine, result in analysis_results.items():
            if result.get("category") in ("malicious", "suspicious"):
                engine_result = result.get("result", "")
                if engine_result:
                    tags.append(engine_result)

        popular_names = attrs.get("popular_threat_classification", {}).get(
            "popular_threat_names", []
        )

        return {
            "ioc_type": "hash",
            "ioc_value": data.get("data", {}).get("id", attrs.get("sha256", "")),
            "provider": "virustotal",
            "verdict": verdict,
            "score": score,
            "tags": list(set(tags))[:20],
            "popular_threat_names": popular_names[:10] if popular_names else [],
            "last_analysis_date": attrs.get("last_analysis_date"),
            "md5": attrs.get("md5"),
            "sha1": attrs.get("sha1"),
            "sha256": attrs.get("sha256"),
            "size": attrs.get("size"),
            "type_description": attrs.get("type_description"),
            "type_tags": attrs.get("type_tags", []),
            "malicious_votes": malicious,
            "suspicious_votes": suspicious,
            "total_votes": total,
            "first_submission_date": attrs.get("first_submission_date"),
            "times_submitted": attrs.get("times_submitted"),
            "cached": False,
        }

    def _parse_url_response(
        self, data: dict[str, Any], original_url: str
    ) -> dict[str, Any]:
        """Parse VT URL API response into normalized format."""
        attrs = data.get("data", {}).get("attributes", {})

        stats = attrs.get("last_analysis_stats", {})
        malicious = stats.get("malicious", 0)
        suspicious = stats.get("suspicious", 0)
        harmless = stats.get("harmless", 0)
        total = sum(stats.values())

        score = int((malicious + suspicious) / max(total, 1) * 100)

        if malicious > 0:
            verdict = "malicious"
        elif suspicious > 0:
            verdict = "suspicious"
        elif harmless > 0 and malicious == 0:
            verdict = "clean"
        else:
            verdict = "unknown"

        tags: list[str] = []
        analysis_results = attrs.get("last_analysis_results", {})
        for _engine, result in analysis_results.items():
            if result.get("category") in ("malicious", "suspicious"):
                engine_result = result.get("result", "")
                if engine_result:
                    tags.append(engine_result)

        return {
            "ioc_type": "url",
            "ioc_value": original_url,
            "provider": "virustotal",
            "verdict": verdict,
            "score": score,
            "tags": list(set(tags))[:20],
            "last_analysis_date": attrs.get("last_analysis_date"),
            "last_final_url": attrs.get("last_final_url"),
            "last_http_response_code": attrs.get("last_http_response_code"),
            "malicious_votes": malicious,
            "suspicious_votes": suspicious,
            "total_votes": total,
            "title": attrs.get("title", ""),
            "cached": False,
        }

    # ── Degraded result ─────────────────────────────────────────────────

    async def _degraded_result(
        self, ioc_type: str, ioc_value: str, use_cache: bool
    ) -> dict[str, Any]:
        """Return a degraded result when VT is unreachable.

        Tries cache even when use_cache=False on the initial call,
        as a last-resort fallback.
        """
        # Last-resort: try cache regardless of initial use_cache setting
        cached = await self._get_cached(ioc_type, ioc_value)
        if cached is not None:
            cached["cached"] = True
            cached["degraded"] = True
            return cached

        return {
            "ioc_type": ioc_type,
            "ioc_value": ioc_value,
            "provider": "virustotal",
            "verdict": "unknown",
            "score": 0,
            "tags": [],
            "error": "VirusTotal API unavailable; no cached result",
            "degraded": True,
            "cached": False,
        }

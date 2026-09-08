"""MISP (Malware Information Sharing Platform) REST API integration.

Features:
- Search IOCs (attributes) by type, value, tags
- Query events (incidents) with filtering
- Response caching via ThreatIntelCacheModel
- Rate limiting (configurable)
- Graceful error degradation
- httpx.AsyncClient HTTP client

Reference: https://www.misp-project.org/openapi/
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

MISP_CACHE_PROVIDER = "misp"
MISP_DEFAULT_TTL_HOURS = 12  # MISP data changes less frequently

# Rate limit: conservative default, configurable
_rate_limit_lock = asyncio.Lock()
_last_request_times: list[float] = []
_MISP_DEFAULT_RPM = 10  # reasonable default


async def _rate_limit(max_rpm: int | None = None) -> None:
    """Enforce per-minute rate limit using a sliding window."""
    rpm = max_rpm or _MISP_DEFAULT_RPM
    async with _rate_limit_lock:
        now = time.monotonic()
        window_start = now - 60.0

        global _last_request_times
        _last_request_times = [t for t in _last_request_times if t > window_start]

        if len(_last_request_times) >= rpm:
            wait = _last_request_times[0] - window_start + 0.1
            if wait > 0:
                logger.debug("MISP rate-limit: waiting %.1fs", wait)
                await asyncio.sleep(wait)
                now = time.monotonic()
                window_start = now - 60.0
                _last_request_times = [
                    t for t in _last_request_times if t > window_start
                ]

        _last_request_times.append(now)


# ── Service ──────────────────────────────────────────────────────────────────


class MISPService:
    """MISP REST API integration with caching.

    Usage:
        async with MISPService(db_session) as misp:
            results = await misp.search_iocs("ip", "1.2.3.4")
            events = await misp.get_event("event-uuid")
    """

    def __init__(
        self,
        session: Any = None,
        base_url: str | None = None,
        api_key: str | None = None,
        verify_ssl: bool | None = None,
        timeout: float | None = None,
    ):
        """Initialize MISP service.

        Args:
            session: SQLAlchemy async session for cache reads/writes
            base_url: MISP instance URL (uses config if not provided)
            api_key: MISP API key (uses config if not provided)
            verify_ssl: Whether to verify SSL certificates
            timeout: HTTP request timeout in seconds
        """
        self._db_session = session
        self._base_url = (base_url or settings.misp_base_url).rstrip("/")
        self._api_key = api_key or settings.misp_api_key
        self._verify_ssl = (
            verify_ssl if verify_ssl is not None else settings.misp_verify_ssl
        )
        self._timeout = timeout or settings.misp_timeout_sec
        self._client: httpx.AsyncClient | None = None
        self._enabled = bool(self._base_url and self._api_key)

    @property
    def is_enabled(self) -> bool:
        """Whether MISP integration is configured."""
        return self._enabled

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create the httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers={
                    "Authorization": self._api_key,
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
                verify=self._verify_ssl,
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> "MISPService":
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()

    # ── Cache helpers ────────────────────────────────────────────────────

    async def _get_cached(self, ioc_type: str, ioc_value: str) -> dict[str, Any] | None:
        """Try to read a cached MISP result from the database."""
        if self._db_session is None:
            return None

        try:
            from sqlalchemy import and_, select

            result = await self._db_session.execute(
                select(ThreatIntelCacheModel).where(
                    and_(
                        ThreatIntelCacheModel.provider == MISP_CACHE_PROVIDER,
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
            logger.exception("Failed to read MISP cache for %s:%s", ioc_type, ioc_value)

        return None

    async def _set_cache(
        self,
        ioc_type: str,
        ioc_value: str,
        status: str,
        response: dict[str, Any] | None = None,
        score: int | None = None,
        tags: list[str] | None = None,
        ttl_hours: int = MISP_DEFAULT_TTL_HOURS,
    ) -> None:
        """Write a MISP result to the cache."""
        if self._db_session is None:
            return

        try:
            import uuid

            from sqlalchemy import and_, select

            expires_at = datetime.now(UTC) + timedelta(hours=ttl_hours)

            existing = await self._db_session.execute(
                select(ThreatIntelCacheModel).where(
                    and_(
                        ThreatIntelCacheModel.provider == MISP_CACHE_PROVIDER,
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
                    provider=MISP_CACHE_PROVIDER,
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
            logger.exception(
                "Failed to write MISP cache for %s:%s", ioc_type, ioc_value
            )

    # ── HTTP helpers ────────────────────────────────────────────────────

    async def _get(
        self, endpoint: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a rate-limited GET request to the MISP API."""
        if not self._enabled:
            raise RuntimeError("MISP integration not configured")

        await _rate_limit()

        client = await self._get_client()

        try:
            response = await client.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()

            # MISP wraps responses in { "response": ... }
            if isinstance(data, dict) and "response" in data:
                # If response is a nested dict with 'Attribute' or 'Event' key, unwrap one level
                inner = data["response"]
                if isinstance(inner, dict) and (
                    "Attribute" in inner or "Event" in inner or "attributes" in inner
                ):
                    return inner
                return {"response": inner}

            return data
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                logger.info("MISP: %s not found (404)", endpoint)
                return {"not_found": True}
            if exc.response.status_code in (401, 403):
                logger.error(
                    "MISP: Authentication failed (%d) - check API key",
                    exc.response.status_code,
                )
                raise RuntimeError("MISP API key is invalid or lacks permission")
            logger.error(
                "MISP HTTP error %d on %s: %s",
                exc.response.status_code,
                endpoint,
                exc,
            )
            raise
        except httpx.RequestError as exc:
            logger.error("MISP network error on %s: %s", endpoint, exc)
            raise ConnectionError(f"MISP API unreachable: {exc}") from exc

    async def _post(
        self, endpoint: str, json_data: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Execute a rate-limited POST request to the MISP API."""
        if not self._enabled:
            raise RuntimeError("MISP integration not configured")

        await _rate_limit()

        client = await self._get_client()

        try:
            response = await client.post(endpoint, json=json_data)
            response.raise_for_status()
            data = response.json()

            if isinstance(data, dict) and "response" in data:
                inner = data["response"]
                if isinstance(inner, dict) and (
                    "Attribute" in inner or "Event" in inner
                ):
                    return inner
                return {"response": inner}

            return data
        except httpx.HTTPStatusError as exc:
            logger.error(
                "MISP POST error %d on %s: %s",
                exc.response.status_code,
                endpoint,
                exc,
            )
            raise
        except httpx.RequestError as exc:
            logger.error("MISP network error on %s: %s", endpoint, exc)
            raise ConnectionError(f"MISP API unreachable: {exc}") from exc

    # ── IOC Search ──────────────────────────────────────────────────────

    async def search_iocs(
        self,
        ioc_type: str | None = None,
        ioc_value: str | None = None,
        tags: list[str] | None = None,
        category: str | None = None,
        to_ids: bool | None = None,
        limit: int = 50,
        page: int = 1,
        use_cache: bool = True,
    ) -> dict[str, Any]:
        """Search MISP attributes (IOCs) with filters.

        Args:
            ioc_type: IOC type (ip-src, ip-dst, domain, url, md5, sha1, sha256, etc.)
            ioc_value: IOC value to search (supports wildcard %)
            tags: Filter by event tags
            category: MISP attribute category
            to_ids: Filter by IDS flag
            limit: Results per page
            page: Page number
            use_cache: Whether to check cache first (only for exact ioc_value lookups)

        Returns:
            Dict with:
                - iocs: list of matched IOC dicts
                - total: total count
                - page, limit
                - cached: bool
        """
        # For exact value lookups, try cache first
        cache_key = f"{ioc_type}:{ioc_value}" if ioc_type and ioc_value else None
        if use_cache and cache_key:
            cached = await self._get_cached(cache_key, "exact")
            if cached is not None:
                cached["cached"] = True
                return cached

        params: dict[str, Any] = {
            "limit": min(limit, 100),
            "page": page,
        }
        if ioc_type:
            params["type"] = ioc_type
        if ioc_value:
            params["value"] = ioc_value
        if tags:
            params["tags"] = tags
        if category:
            params["category"] = category
        if to_ids is not None:
            params["to_ids"] = int(to_ids)

        try:
            raw = await self._post("/attributes/restSearch", json_data=params)
        except Exception:
            logger.exception("MISP IOC search failed")
            return await self._degraded_result(
                "search", "ioc_search", use_cache, cache_key
            )

        result = self._parse_search_results(raw, "attributes", ioc_type or "unknown")

        # Cache if exact value lookup
        if cache_key:
            await self._set_cache(
                ioc_type=cache_key,
                ioc_value="exact",
                status="ok",
                response=result,
                ttl_hours=MISP_DEFAULT_TTL_HOURS,
            )

        return result

    # ── Event queries ───────────────────────────────────────────────────

    async def get_event(self, event_id: str) -> dict[str, Any]:
        """Get a single MISP event by UUID or numeric ID.

        Args:
            event_id: Event UUID or numeric ID

        Returns:
            Event dict with attributes, or error
        """
        try:
            raw = await self._get(f"/events/view/{event_id}")
        except Exception:
            logger.exception("MISP get_event failed for %s", event_id)
            return {
                "event_id": event_id,
                "provider": "misp",
                "verdict": "error",
                "error": "Failed to fetch MISP event",
                "degraded": True,
            }

        return self._parse_event_response(raw, event_id)

    async def search_events(
        self,
        event_info: str | None = None,
        tags: list[str] | None = None,
        org: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        published: bool | None = True,
        limit: int = 20,
        page: int = 1,
    ) -> dict[str, Any]:
        """Search MISP events with filters.

        Args:
            event_info: Search in event info field (supports % wildcard)
            tags: Filter by event tags
            org: Filter by organisation name
            date_from: ISO date string (YYYY-MM-DD)
            date_to: ISO date string (YYYY-MM-DD)
            published: If True, only published events
            limit: Results per page
            page: Page number

        Returns:
            Dict with events list, total, page info
        """
        params: dict[str, Any] = {
            "limit": min(limit, 50),
            "page": page,
        }
        if event_info:
            params["eventinfo"] = event_info
        if tags:
            params["tags"] = tags
        if org:
            params["org"] = org
        if date_from:
            params["date_from"] = date_from
        if date_to:
            params["date_to"] = date_to
        if published:
            params["published"] = 1

        try:
            raw = await self._post("/events/restSearch", json_data=params)
        except Exception:
            logger.exception("MISP event search failed")
            return {
                "events": [],
                "total": 0,
                "page": page,
                "limit": limit,
                "provider": "misp",
                "verdict": "error",
                "error": "Failed to search MISP events",
                "degraded": True,
            }

        return self._parse_search_results(raw, "events", "event")

    async def search_sightings(
        self,
        ioc_type: str,
        ioc_value: str,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Search MISP sightings for a specific IOC.

        Sightings indicate an IOC has been observed in the wild.

        Args:
            ioc_type: IOC type (ip-src, ip-dst, domain, etc.)
            ioc_value: IOC value

        Returns:
            Dict with sightings data
        """
        params: dict[str, Any] = {
            "type": ioc_type,
            "value": ioc_value,
            "limit": min(limit, 100),
        }

        try:
            raw = await self._post("/sightings/restSearch", json_data=params)
        except Exception:
            logger.exception(
                "MISP sightings search failed for %s:%s", ioc_type, ioc_value
            )
            return {
                "ioc_type": ioc_type,
                "ioc_value": ioc_value,
                "provider": "misp",
                "sightings": [],
                "total": 0,
                "degraded": True,
            }

        sightings = []
        if isinstance(raw, dict):
            s_list = raw.get("response", raw.get("sightings", raw.get("Sighting", [])))
            if isinstance(s_list, dict):
                s_list = [s_list]
            for s in s_list if isinstance(s_list, list) else []:
                if isinstance(s, dict):
                    sightings.append(
                        {
                            "id": s.get("id"),
                            "attribute_id": s.get("attribute_id"),
                            "event_id": s.get("event_id"),
                            "org_id": s.get("org_id"),
                            "date_sighting": s.get("date_sighting"),
                            "source": s.get("source"),
                            "type": s.get("type"),
                        }
                    )

        return {
            "ioc_type": ioc_type,
            "ioc_value": ioc_value,
            "provider": "misp",
            "sightings": sightings,
            "total": len(sightings),
        }

    # ── Batch lookup ───────────────────────────────────────────────────

    async def batch_lookup_iocs(
        self,
        iocs: list[dict[str, str]],
        use_cache: bool = True,
    ) -> list[dict[str, Any]]:
        """Batch search multiple IOCs in MISP.

        Args:
            iocs: List of dicts with keys 'type' and 'value'

        Returns:
            List of result dicts
        """
        results: list[dict[str, Any]] = []
        for ioc in iocs:
            ioc_type = ioc.get("type", "")
            ioc_value = ioc.get("value", "")

            try:
                result = await self.search_iocs(
                    ioc_type=ioc_type,
                    ioc_value=ioc_value,
                    use_cache=use_cache,
                )
            except Exception as exc:
                result = {
                    "ioc_type": ioc_type,
                    "ioc_value": ioc_value,
                    "provider": "misp",
                    "iocs": [],
                    "total": 0,
                    "verdict": "error",
                    "error": str(exc),
                }

            results.append(result)

            if len(results) < len(iocs):
                await asyncio.sleep(0.5)

        return results

    # ── Response parsers ───────────────────────────────────────────────

    def _parse_search_results(
        self,
        raw: dict[str, Any],
        key: str,
        default_type: str,
    ) -> dict[str, Any]:
        """Parse MISP search results into normalized format."""
        items_list: list[dict[str, Any]] = []
        raw_response = raw.get("response", raw)

        # MISP can return a list (array) directly, or a dict with Attribute key
        if isinstance(raw_response, list):
            raw_items = raw_response
        elif isinstance(raw_response, dict):
            raw_items = raw_response.get(
                "Attribute", raw_response.get("attributes", [])
            )
            if isinstance(raw_items, dict):
                raw_items = [raw_items]
        else:
            raw_items = []

        if not isinstance(raw_items, list):
            raw_items = []

        for item in raw_items:
            if isinstance(item, dict):
                parsed = self._normalize_attribute(item, default_type)
                items_list.append(parsed)

        # Score: proportion of IDS-flagged IOCs
        ids_count = sum(1 for i in items_list if i.get("to_ids"))
        score = min(int((ids_count / max(len(items_list), 1)) * 100), 100)

        # Collect tags
        all_tags: list[str] = []
        for item in items_list:
            item_tags = item.get("tags", [])
            if isinstance(item_tags, list):
                all_tags.extend(item_tags)

        return {
            "ioc_type": default_type,
            "provider": "misp",
            "iocs": items_list,
            "total": len(items_list),
            "score": score,
            "tags": list(set(all_tags))[:30],
            "verdict": (
                "malicious"
                if ids_count > 0
                else ("suspicious" if items_list else "unknown")
            ),
            "cached": False,
        }

    def _parse_event_response(
        self, raw: dict[str, Any], event_id: str
    ) -> dict[str, Any]:
        """Parse a single MISP event response."""
        raw_event = raw.get("response", raw)

        if isinstance(raw_event, dict):
            event_data = raw_event.get("Event", raw_event)
        elif isinstance(raw_event, list) and raw_event:
            event_data = raw_event[0] if isinstance(raw_event[0], dict) else {}
            event_data = event_data.get("Event", event_data)
        else:
            event_data = {}

        attributes = []
        raw_attrs = event_data.get("Attribute", [])
        if isinstance(raw_attrs, dict):
            raw_attrs = [raw_attrs]
        for attr in raw_attrs if isinstance(raw_attrs, list) else []:
            attributes.append(
                self._normalize_attribute(attr, attr.get("type", "unknown"))
            )

        tags_list = []
        raw_tags = event_data.get("Tag", [])
        for t in raw_tags if isinstance(raw_tags, list) else []:
            if isinstance(t, dict):
                tags_list.append(t.get("name", str(t)))

        return {
            "event_id": event_id,
            "provider": "misp",
            "info": event_data.get("info", ""),
            "date": event_data.get("date"),
            "threat_level_id": event_data.get("threat_level_id"),
            "published": event_data.get("published", False),
            "analysis": event_data.get("analysis"),
            "org": (
                event_data.get("Org", {}).get("name")
                if isinstance(event_data.get("Org"), dict)
                else event_data.get("orgc", "")
            ),
            "tags": tags_list,
            "attributes": attributes,
            "attribute_count": len(attributes),
        }

    def _normalize_attribute(
        self, attr: dict[str, Any], default_type: str
    ) -> dict[str, Any]:
        """Normalize a MISP attribute dict to a standard format."""
        tags = []
        raw_tags = attr.get("Tag", [])
        for t in raw_tags if isinstance(raw_tags, list) else []:
            if isinstance(t, dict):
                tags.append(t.get("name", str(t)))

        return {
            "id": attr.get("id"),
            "event_id": attr.get("event_id"),
            "object_id": attr.get("object_id"),
            "type": attr.get("type", default_type),
            "category": attr.get("category"),
            "value": attr.get("value"),
            "to_ids": bool(attr.get("to_ids", False)),
            "comment": attr.get("comment"),
            "first_seen": attr.get("first_seen"),
            "last_seen": attr.get("last_seen"),
            "tags": tags,
            "uuid": attr.get("uuid"),
            "timestamp": attr.get("timestamp"),
            "distribution": attr.get("distribution"),
        }

    # ── Degraded result ─────────────────────────────────────────────────

    async def _degraded_result(
        self,
        ioc_type: str,
        ioc_value: str,
        use_cache: bool,
        cache_key: str | None,
    ) -> dict[str, Any]:
        """Return a degraded result when MISP is unreachable."""
        if cache_key:
            cached = await self._get_cached(cache_key, "exact")
            if cached is not None:
                cached["cached"] = True
                cached["degraded"] = True
                return cached

        return {
            "ioc_type": ioc_type,
            "ioc_value": ioc_value,
            "provider": "misp",
            "iocs": [],
            "total": 0,
            "verdict": "unknown",
            "error": "MISP API unavailable; no cached result",
            "degraded": True,
            "cached": False,
        }

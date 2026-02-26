"""Threat Intelligence service for OTX integration.

v0.4.1: Integrated IOC compliance filter for external TI transmission.
"""

import uuid
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.config import settings
from schemas.threat_intel import (
    ThreatIntelResponse,
    BulkThreatIntelResponse,
    ThreatIntelItem,
    ThreatIntelAnalysis,
    Verdict,
    IOCType,
)
from repositories.threat_intel_repository import ThreatIntelRepository
from integrations.otx_client import OTXClient
from utils.ti_filter import should_send_ioc_to_external_ti, FilterDecision

logger = get_logger(__name__)


def _parse_internal_domains() -> List[str]:
    """Parse internal domain suffixes from config.

    Returns:
        List of internal domain suffixes
    """
    if not settings.ti_internal_domain_suffixes:
        return []
    return [d.strip() for d in settings.ti_internal_domain_suffixes.split(",") if d.strip()]


def _parse_blocked_tlds() -> List[str]:
    """Parse blocked TLDs from config.

    Returns:
        List of blocked TLDs
    """
    if not settings.ti_blocked_tlds:
        return []
    return [t.strip() for t in settings.ti_blocked_tlds.split(",") if t.strip()]


class ThreatIntelService:
    """Service for threat intelligence lookups with caching and compliance filtering."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize threat intel service.

        Args:
            session: Database session
        """
        self.session = session
        self.repository = ThreatIntelRepository()
        self._otx_client: Optional[OTXClient] = None

        # v0.4.1: Cache filter settings
        self._internal_domains = _parse_internal_domains()
        self._blocked_tlds = _parse_blocked_tlds()

    def _get_otx_client(self) -> Optional[OTXClient]:
        """Get OTX client if configured.

        Returns:
            OTX client or None if not configured
        """
        if not settings.otx_api_key:
            return None
        if self._otx_client is None:
            self._otx_client = OTXClient(api_key=settings.otx_api_key)
        return self._otx_client

    async def is_enabled(self) -> Tuple[bool, Optional[str]]:
        """Check if external threat intel is enabled.

        Returns:
            Tuple of (enabled, error_reason)
        """
        if not settings.allow_external_ti:
            return False, "External TI disabled by configuration"

        if not settings.otx_api_key:
            return False, "OTX API key not configured"

        return True, None

    async def lookup(
        self,
        ioc_type: str,
        ioc_value: str,
    ) -> ThreatIntelResponse:
        """Lookup single IOC threat intelligence.

        v0.4.1: Applies compliance filter before external lookup.

        Args:
            ioc_type: IOC type (ip/domain/url/hash)
            ioc_value: IOC value

        Returns:
            Threat intel response
        """
        request_id = str(uuid.uuid4())

        # v0.4.1: Check compliance filter before external lookup
        filter_decision = should_send_ioc_to_external_ti(
            ioc_type=ioc_type,
            ioc_value=ioc_value,
            allow_private_ip=settings.ti_allow_private_ip,
            internal_domain_suffixes=self._internal_domains,
            blocked_tlds=self._blocked_tlds,
            allow_url_with_private_host=settings.ti_allow_url_with_private_host,
        )

        if not filter_decision.allowed:
            # IOC filtered by compliance policy - log and return unknown result
            logger.info(
                f"IOC {ioc_type}:{ioc_value} filtered by compliance policy: {filter_decision.reason}"
            )
            return ThreatIntelResponse(
                request_id=request_id,
                provider="otx",
                disabled=False,
                cached=False,
                degraded=False,
                ioc_type=ioc_type,
                ioc_value=ioc_value,
                verdict=Verdict.unknown,
                score=0,
                pulse_count=0,
                tags=[],
                references=[],
                raw={},
                skipped_reason=filter_decision.reason,
            )

        # Check if enabled
        enabled, error_reason = await self.is_enabled()
        if not enabled:
            return ThreatIntelResponse(
                request_id=request_id,
                provider="otx",
                disabled=True,
                degraded=False,
                ioc_type=ioc_type,
                ioc_value=ioc_value,
                verdict=Verdict.unknown,
                score=0,
                pulse_count=0,
                tags=[],
                references=[],
                raw={},
                error_reason=error_reason,
            )

        # Check cache first
        cached = await self.repository.get_by_ioc(
            self.session, "otx", ioc_type, ioc_value
        )
        if cached:
            import json

            # Parse verdict from cached response (not from status field)
            raw_data = json.loads(cached.response_json) if cached.response_json else {}
            cached_verdict = raw_data.get("verdict", Verdict.unknown)

            return ThreatIntelResponse(
                request_id=request_id,
                provider="otx",
                disabled=False,
                cached=True,
                degraded=False,
                ioc_type=ioc_type,
                ioc_value=ioc_value,
                verdict=Verdict(cached_verdict),
                score=cached.score or 0,
                pulse_count=cached.pulse_count or 0,
                tags=json.loads(cached.tags) if cached.tags else [],
                references=[],
                raw=raw_data,
            )

        # Query OTX
        client = self._get_otx_client()
        if not client:
            return ThreatIntelResponse(
                request_id=request_id,
                provider="otx",
                disabled=False,
                cached=False,
                degraded=True,
                ioc_type=ioc_type,
                ioc_value=ioc_value,
                verdict=Verdict.unknown,
                score=0,
                pulse_count=0,
                tags=[],
                references=[],
                raw={},
                error_reason="OTX client not available",
            )

        try:
            result = await self._lookup_otx(client, ioc_type, ioc_value)

            # Cache the result (store full result dict to include verdict)
            await self.repository.create(
                self.session,
                provider="otx",
                ioc_type=ioc_type,
                ioc_value=ioc_value,
                status="ok",  # Successful lookup
                response_json=result,  # Store full result with verdict
                score=result.get("score", 0),
                tags=result.get("tags", []),
                pulse_count=result.get("pulse_count", 0),
                last_seen=None,
                error_reason=result.get("error_reason"),
            )

            return ThreatIntelResponse(
                request_id=request_id,
                provider="otx",
                disabled=False,
                cached=False,
                degraded=False,
                ioc_type=ioc_type,
                ioc_value=ioc_value,
                verdict=Verdict(result.get("verdict", "unknown")),
                score=result.get("score", 0),
                pulse_count=result.get("pulse_count", 0),
                tags=result.get("tags", []),
                references=result.get("references", []),
                raw=result.get("raw", {}),
            )

        except Exception as e:
            logger.error(f"Threat intel lookup error for {ioc_type}:{ioc_value}: {e}")
            return ThreatIntelResponse(
                request_id=request_id,
                provider="otx",
                disabled=False,
                cached=False,
                degraded=True,
                ioc_type=ioc_type,
                ioc_value=ioc_value,
                verdict=Verdict.unknown,
                score=0,
                pulse_count=0,
                tags=[],
                references=[],
                raw={},
                error_reason=str(e),
            )

    async def bulk_lookup(
        self,
        items: List[Dict[str, str]],
    ) -> BulkThreatIntelResponse:
        """Bulk lookup threat intelligence for multiple IOCs.

        v0.4.1: Applies compliance filter and separates filtered items.

        Args:
            items: List of {ioc_type, ioc_value} dicts

        Returns:
            Bulk threat intel response
        """
        request_id = str(uuid.uuid4())

        # Check if enabled
        enabled, error_reason = await self.is_enabled()
        if not enabled:
            return BulkThreatIntelResponse(
                request_id=request_id,
                provider="otx",
                disabled=True,
                results=[],
                skipped_count=0,
                skipped_items=[],
                filtered_count=0,
                filtered_items=[],
            )

        # v0.4.1: Apply compliance filter first
        allowed_items = []
        filtered_items = []

        for item in items:
            filter_decision = should_send_ioc_to_external_ti(
                ioc_type=item["ioc_type"],
                ioc_value=item["ioc_value"],
                allow_private_ip=settings.ti_allow_private_ip,
                internal_domain_suffixes=self._internal_domains,
                blocked_tlds=self._blocked_tlds,
                allow_url_with_private_host=settings.ti_allow_url_with_private_host,
            )

            if filter_decision.allowed:
                allowed_items.append(item)
            else:
                # Create filtered item entry
                filtered_items.append(
                    ThreatIntelItem(
                        ioc_type=item["ioc_type"],
                        ioc_value=item["ioc_value"],
                        verdict=Verdict.unknown,
                        score=0,
                        pulse_count=0,
                        tags=[],
                        references=[],
                        cached=False,
                        skipped=True,
                        skipped_reason=filter_decision.reason,
                    )
                )
                logger.info(
                    f"Bulk lookup: IOC {item['ioc_type']}:{item['ioc_value']} filtered: {filter_decision.reason}"
                )

        # Apply rate limiting to allowed items
        max_iocs = settings.ti_max_iocs_per_request
        results = []
        skipped_items = []

        if len(allowed_items) > max_iocs:
            # Process first N items, skip rest
            process_items = allowed_items[:max_iocs]
            skip_items = allowed_items[max_iocs:]
        else:
            process_items = allowed_items
            skip_items = []

        # Look up each allowed IOC
        for item in process_items:
            result = await self.lookup(
                ioc_type=item["ioc_type"],
                ioc_value=item["ioc_value"],
            )
            results.append(result)

        # Create rate-limited skipped items
        for item in skip_items:
            skipped_items.append(
                ThreatIntelItem(
                    ioc_type=item["ioc_type"],
                    ioc_value=item["ioc_value"],
                    verdict=Verdict.unknown,
                    score=0,
                    pulse_count=0,
                    tags=[],
                    references=[],
                    cached=False,
                    skipped=True,
                    skipped_reason="rate_limit",
                )
            )

        return BulkThreatIntelResponse(
            request_id=request_id,
            provider="otx",
            disabled=False,
            results=results,
            skipped_count=len(skipped_items),
            skipped_items=skipped_items,
            # v0.4.1: Filtered items (compliance)
            filtered_count=len(filtered_items),
            filtered_items=filtered_items,
        )

    async def enrich_iocs(
        self,
        iocs: Dict[str, List[str]],
    ) -> ThreatIntelAnalysis:
        """Enrich extracted IOCs with threat intelligence.

        v0.4.1: Applies compliance filter and includes filtered_items in response.

        This is called by alert_service and timeline_service to add
        threat intel to analysis results.

        Args:
            iocs: Dictionary of IOC types to values

        Returns:
            Threat intelligence analysis
        """
        enabled, error_reason = await self.is_enabled()
        if not enabled:
            return ThreatIntelAnalysis(
                provider="otx",
                disabled=True,
                degraded=False,
                skipped=False,
                items=[],
                filtered_items=[],
                error_reason=error_reason,
            )

        # Flatten IOCs into lookup list
        lookup_items = []
        for ioc_type, values in iocs.items():
            if ioc_type not in ["ips", "domains", "urls", "hashes"]:
                continue
            mapped_type = ioc_type.rstrip("s")  # ips -> ip
            for value in values:
                lookup_items.append({"ioc_type": mapped_type, "ioc_value": value})

        if not lookup_items:
            return ThreatIntelAnalysis(
                provider="otx",
                disabled=False,
                degraded=False,
                skipped=False,
                items=[],
                filtered_items=[],
            )

        try:
            # Bulk lookup (includes compliance filtering)
            bulk_response = await self.bulk_lookup(lookup_items)

            # Convert to ThreatIntelItem list
            items = []
            for result in bulk_response.results:
                items.append(
                    ThreatIntelItem(
                        ioc_type=result.ioc_type,
                        ioc_value=result.ioc_value,
                        verdict=result.verdict,
                        score=result.score,
                        pulse_count=result.pulse_count,
                        tags=result.tags,
                        references=result.references,
                        cached=result.cached,
                        skipped=False,
                    )
                )

            # Add rate-limited skipped items
            for skipped in bulk_response.skipped_items:
                items.append(skipped)

            return ThreatIntelAnalysis(
                provider="otx",
                disabled=False,
                degraded=any(r.degraded for r in bulk_response.results),
                skipped=len(bulk_response.skipped_items) > 0,
                items=items,
                # v0.4.1: Include compliance-filtered items
                filtered_items=bulk_response.filtered_items,
            )

        except Exception as e:
            logger.error(f"Threat intel enrichment error: {e}")
            return ThreatIntelAnalysis(
                provider="otx",
                disabled=False,
                degraded=True,
                skipped=False,
                items=[],
                filtered_items=[],
                error_reason=str(e),
            )

    async def _lookup_otx(
        self,
        client: OTXClient,
        ioc_type: str,
        ioc_value: str,
    ) -> Dict[str, Any]:
        """Perform OTX lookup based on IOC type.

        Args:
            client: OTX client
            ioc_type: IOC type
            ioc_value: IOC value

        Returns:
            Parsed OTX response
        """
        if ioc_type == "ip":
            return await client.lookup_ip(ioc_value)
        elif ioc_type == "domain":
            return await client.lookup_domain(ioc_value)
        elif ioc_type == "url":
            return await client.lookup_url(ioc_value)
        elif ioc_type == "hash":
            return await client.lookup_hash(ioc_value)
        else:
            return {
                "status": "error",
                "ioc_type": ioc_type,
                "ioc_value": ioc_value,
                "verdict": "unknown",
                "score": 0,
                "pulse_count": 0,
                "tags": [],
                "references": [],
                "error_reason": f"Unsupported IOC type: {ioc_type}",
                "raw": {},
            }


def get_degraded_threat_intel() -> ThreatIntelAnalysis:
    """Get degraded mode threat intel analysis.

    Returns:
        Minimal threat intel analysis for degraded mode
    """
    return ThreatIntelAnalysis(
        provider="otx",
        disabled=False,
        degraded=True,
        skipped=False,
        items=[],
        filtered_items=[],
        error_reason="Threat intel lookup failed in degraded mode",
    )

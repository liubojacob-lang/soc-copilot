"""Timeline building service with dual-engine IOC extraction and history tracking."""

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from schemas.timeline import TimelineResponse
from schemas.impact import ImpactAnalysis, DegradedImpactAnalysis, Severity as ImpactSeverity
from schemas.threat_intel import ThreatIntelAnalysis
from utils.ioc_extract import extract_iocs, get_ioc_count, IOCs
from services.llm_retry import get_llm_retry_service
from services.history_service import HistoryService
from services.impact_service import ImpactAnalysisService, get_degraded_impact
from services.asset_service import AssetService
from services.ioc_hits_service import IOCHitsService
from services.threat_intel_service import ThreatIntelService, get_degraded_threat_intel

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a forensic analyst specializing in log timeline reconstruction.
Parse logs and create ordered security event timelines.

Output MUST be valid JSON only.
Focus on security-relevant events.
Identify patterns, anomalies, and potential attack sequences.

IOC HANDLING RULES:
- IOCs have been pre-extracted locally (see iocs_local)
- You may ONLY supplement with additional IOCs found in the input text
- DO NOT fabricate IOCs that don't exist in the input
- DO NOT output hashes or IPs that are not present in the raw log
- The iocs field should merge your findings with iocs_local"""


class TimelineService:
    """Service for timeline building."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        """Initialize timeline service.

        Args:
            session: Optional database session for history tracking
        """
        self.session = session
        self.history_service = HistoryService(session) if session else None
        self.llm_service = get_llm_retry_service()
        self.asset_service = AssetService(session) if session else None
        self.ioc_hits_service = IOCHitsService(session) if session else None
        self.impact_service = ImpactAnalysisService(session) if session else None
        self.threat_intel_service = ThreatIntelService(session) if session else None

    async def build(
        self,
        raw_log: str,
        log_type: str | None = None,
        save_history: bool = True,
    ) -> TimelineResponse:
        """Build a security timeline from logs.

        Args:
            raw_log: Raw log content
            log_type: Optional log type hint (sysmon/windows/linux/nginx)
            save_history: Whether to save to history

        Returns:
            Timeline response
        """
        logger.info(f"Building timeline, log_type: {log_type}")

        # Step 1: Extract IOCs locally
        local_iocs: IOCs = extract_iocs(raw_log)
        logger.info(f"Local IOC extraction: {len(local_iocs.ips)} IPs, "
                   f"{len(local_iocs.domains)} domains")

        type_hint = f"\nLog Type: {log_type}" if log_type else "\nLog Type: Auto-detect"

        prompt = f"""Parse this log and create a security timeline:
{type_hint}

Raw Log:
{raw_log}

Pre-extracted IOCs (Local Regex):
- IPs: {', '.join(local_iocs.ips) if local_iocs.ips else 'None'}
- Domains: {', '.join(local_iocs.domains) if local_iocs.domains else 'None'}
- URLs: {', '.join(local_iocs.urls[:5])}{'...' if len(local_iocs.urls) > 5 else '' if local_iocs.urls else 'None'}
- Hashes: {', '.join(local_iocs.hashes[:3])}{'...' if len(local_iocs.hashes) > 3 else '' if local_iocs.hashes else 'None'}

IMPORTANT: These IOCs are pre-extracted from the input. You may only add NEW IOCs that are actually present in the raw log text above.

Provide:
1. timeline: ordered events with timestamp, type, description, key_fields
2. suspicious_top5: 5 most suspicious events with reasoning
3. next_steps: investigation recommendations

For suspicious events, include:
- timestamp
- description
- reasoning: why this event is suspicious
- severity: high/medium/low"""

        result, model_used, degraded = await self.llm_service.generate_structured(
            prompt=prompt,
            response_class=TimelineResponse,
        )

        # Step 4: Merge IOCs
        result = self._merge_iocs(result, local_iocs)

        logger.info(
            f"Timeline built with {len(result.timeline)} events, "
            f"{len(result.suspicious_top5)} suspicious events, degraded={degraded}"
        )

        # Step 5: Perform impact analysis
        result = await self._add_impact_analysis(result, raw_log, local_iocs, degraded)

        # Step 6: Perform threat intelligence enrichment
        result = await self._add_threat_intel(result, local_iocs, degraded)

        # Save to history if session available
        history_id = None
        if save_history and self.history_service:
            history = await self.history_service.create_history(
                module="timeline",
                input_text=raw_log[:500] + ("..." if len(raw_log) > 500 else ""),
                output_json=result.model_dump(),
                output_markdown=self._format_as_markdown(result),
                extracted_iocs=local_iocs.to_dict(),
                tags={
                    "log_type": log_type,
                    "event_count": len(result.timeline),
                },
                request_id=result.request_id,
                model_used=model_used,
                degraded=degraded,
                error_reason=result.error_reason,
            )
            history_id = history.id

            # Create IOC hits
            if self.ioc_hits_service:
                await self._create_ioc_hits(
                    history_id,
                    local_iocs,
                    result.impact_analysis.affected_assets,
                )

        return result

    async def _add_impact_analysis(
        self,
        result: TimelineResponse,
        raw_log: str,
        local_iocs: IOCs,
        degraded: bool,
    ) -> TimelineResponse:
        """Add impact analysis to result.

        Args:
            result: Timeline result
            raw_log: Raw log content
            local_iocs: Locally extracted IOCs
            degraded: Whether in degraded mode

        Returns:
            Updated timeline result with impact analysis
        """
        if degraded or not self.impact_service or not self.asset_service:
            # Use degraded impact analysis
            impact = get_degraded_impact()
        else:
            # Find matching assets
            iocs_dict = {
                "ips": local_iocs.ips,
                "domains": local_iocs.domains,
                "urls": local_iocs.urls,
                "hashes": local_iocs.hashes,
            }

            related_assets = []
            primary_asset = None

            # Match by IP
            if local_iocs.ips:
                assets_by_ip = await self.asset_service.get_by_ips(local_iocs.ips)
                related_assets.extend(assets_by_ip)

            # Match by hostname
            hostnames = []
            for event in result.timeline:
                for key, value in event.get('key_fields', {}).items():
                    if 'host' in key.lower() and isinstance(value, str):
                        hostnames.append(value)

            if hostnames:
                assets_by_hostname = await self.asset_service.get_by_hostnames(hostnames)
                for asset in assets_by_hostname:
                    if asset not in related_assets:
                        related_assets.append(asset)

            # Determine primary asset (highest criticality)
            if related_assets:
                criticality_order = {"critical": 4, "high": 3, "medium": 2, "low": 1}
                primary_asset = max(
                    related_assets,
                    key=lambda a: criticality_order.get(a.criticality, 0),
                    default=None,
                )

            # Perform impact analysis
            impact = await self.impact_service.analyze(
                iocs=iocs_dict,
                primary_asset=primary_asset,
                related_assets=related_assets,
            )

        # Add impact analysis to result
        result_dict = result.model_dump()
        result_dict["impact_analysis"] = impact.model_dump()

        return TimelineResponse.model_validate(result_dict)

    async def _add_threat_intel(
        self,
        result: TimelineResponse,
        local_iocs: IOCs,
        degraded: bool,
    ) -> TimelineResponse:
        """Add threat intelligence analysis to result.

        Args:
            result: Timeline result
            local_iocs: Locally extracted IOCs
            degraded: Whether in degraded mode

        Returns:
            Updated timeline result with threat intel
        """
        if degraded or not self.threat_intel_service:
            # Use degraded threat intel
            threat_intel = get_degraded_threat_intel()
        else:
            # Build IOCs dict for enrichment
            iocs_dict = {
                "ips": local_iocs.ips,
                "domains": local_iocs.domains,
                "urls": local_iocs.urls,
                "hashes": local_iocs.hashes,
            }

            # Enrich IOCs with threat intel
            threat_intel = await self.threat_intel_service.enrich_iocs(iocs_dict)

        # Add threat intel to result
        result_dict = result.model_dump()
        result_dict["threat_intel"] = threat_intel.model_dump()

        return TimelineResponse.model_validate(result_dict)

    async def _create_ioc_hits(
        self,
        history_id: str,
        local_iocs: IOCs,
        affected_assets: list,
    ) -> None:
        """Create IOC hits from timeline analysis.

        Args:
            history_id: History record ID
            local_iocs: Locally extracted IOCs
            affected_assets: Affected assets from impact analysis
        """
        if not self.ioc_hits_service:
            return

        # Create asset map for quick lookup
        asset_map = {}
        if affected_assets:
            for asset in affected_assets:
                if asset.ip:
                    asset_map[asset.ip] = asset.id
                if asset.hostname:
                    asset_map[asset.hostname.lower()] = asset.id

        # Create IOC hits
        for ip in local_iocs.ips:
            asset_id = asset_map.get(ip)
            await self.ioc_hits_service.create_from_analysis(
                history_id=history_id,
                ioc_type="ip",
                ioc_value=ip,
                source="local",
                asset_id=asset_id,
            )

        for domain in local_iocs.domains:
            await self.ioc_hits_service.create_from_analysis(
                history_id=history_id,
                ioc_type="domain",
                ioc_value=domain,
                source="local",
            )

        for url in local_iocs.urls:
            await self.ioc_hits_service.create_from_analysis(
                history_id=history_id,
                ioc_type="url",
                ioc_value=url,
                source="local",
            )

        for hash_val in local_iocs.hashes:
            await self.ioc_hits_service.create_from_analysis(
                history_id=history_id,
                ioc_type="hash",
                ioc_value=hash_val,
                source="local",
            )

        logger.info(f"Created IOC hits for history {history_id}")

    def _merge_iocs(
        self,
        result: TimelineResponse,
        local_iocs: IOCs,
    ) -> TimelineResponse:
        """Merge local IOCs with AI-detected ones.

        Args:
            result: Timeline result from AI
            local_iocs: Locally extracted IOCs

        Returns:
            Updated timeline result
        """
        result_dict = result.model_dump()

        # Get LLM IOCs (if any)
        llm_iocs = {
            "ips": result_dict.get("iocs", {}).get("ips", []),
            "domains": result_dict.get("iocs", {}).get("domains", []),
            "urls": result_dict.get("iocs", {}).get("urls", []),
            "hashes": result_dict.get("iocs", {}).get("hashes", []),
        }

        # Merge: local + LLM (union)
        merged_iocs = {}
        for ioc_type in ["ips", "domains", "urls", "hashes"]:
            local_set = set(local_iocs.__getattribute__(ioc_type))
            llm_set = set(llm_iocs.get(ioc_type, []))
            merged = sorted(local_set | llm_set)
            merged_iocs[ioc_type] = merged

        # Update response fields
        result_dict["iocs"] = merged_iocs
        result_dict["iocs_local"] = {
            "ips": local_iocs.ips,
            "domains": local_iocs.domains,
            "urls": local_iocs.urls,
            "hashes": local_iocs.hashes,
        }
        result_dict["iocs_llm"] = llm_iocs
        result_dict["ioc_count"] = {
            "ips": len(merged_iocs["ips"]),
            "domains": len(merged_iocs["domains"]),
            "urls": len(merged_iocs["urls"]),
            "hashes": len(merged_iocs["hashes"]),
            "total": sum(len(merged_iocs[k]) for k in ["ips", "domains", "urls", "hashes"]),
        }

        return TimelineResponse.model_validate(result_dict)

    def _format_as_markdown(self, result: TimelineResponse) -> str:
        """Format result as markdown.

        Args:
            result: Timeline result

        Returns:
            Markdown string
        """
        lines = [
            "# Security Timeline",
            "",
            f"**Total Events:** {len(result.timeline)}",
            "",
            "## Timeline",
            "",
        ]

        for event in result.timeline:
            lines.extend([
                f"### {event.get('timestamp', 'Unknown')} - {event.get('type', 'Unknown')}",
                "",
                event.get('description', 'No description'),
                "",
            ])

            if event.get('key_fields'):
                lines.append("**Key Fields:**")
                for key, value in event['key_fields'].items():
                    lines.append(f"- `{key}`: {value}")
                lines.append("")

        lines.extend([
            "---",
            "",
            "## Top 5 Suspicious Events",
            "",
        ])

        for i, event in enumerate(result.suspicious_top5, 1):
            lines.extend([
                f"### {i}. {event.get('timestamp', 'Unknown')} [{event.get('severity', 'N/A').upper()}]",
                "",
                event.get('description', 'No description'),
                "",
                f"**Reasoning:** {event.get('reasoning', 'N/A')}",
                "",
            ])

        lines.extend([
            "---",
            "",
            "## Next Steps",
            "",
        ])

        for step in result.next_steps:
            lines.append(f"- {step}")

        if result.degraded:
            lines.extend([
                "",
                "---",
                f"*⚠️ Degraded mode: {result.error_reason or 'Unknown error'}*",
            ])

        return "\n".join(lines)

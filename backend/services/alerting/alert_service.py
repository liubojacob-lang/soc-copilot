"""Alert analysis service with dual-engine IOC extraction and history tracking."""

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from schemas.alert import AlertAnalysisResponse
from services.asset_service import AssetService
from services.history_service import HistoryService
from services.impact_service import ImpactAnalysisService, get_degraded_impact
from services.ioc_hits_service import IOCHitsService
from services.llm_retry import get_llm_retry_service
from services.prompt_resolution import resolve_prompt
from services.threat_intel_service import ThreatIntelService, get_degraded_threat_intel
from utils.ioc_extract import IOCs, extract_iocs

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a SOC (Security Operations Center) analyst with 10+ years of experience.
Your task is to analyze security alerts and logs to identify threats.

IMPORTANT CONSTRAINTS:
- Output MUST be valid JSON only
- Focus on DEFENSIVE actions only
- NEVER suggest: clearing logs, disabling audit, covering tracks, bypassing detection
- Confidence should be realistic (0-100)
- Only escalate if genuine security concern

ALLOWED actions:
- Blocking, isolating, or quarantining threats
- Collecting evidence for forensics
- Querying threat intelligence sources
- Hardening systems and networks
- Monitoring and surveillance

Event Types:
- scan: Port/service scanning
- bruteforce: Repeated login attempts
- malware: Malicious code execution
- c2: Command & Control communication
- phishing: Credential harvesting
- abnormal_login: Unusual access patterns
- lateral_movement: Network/internal spread
- data_exfil: Data theft
- unknown: Cannot classify

IOC HANDLING RULES:
- IOCs have been pre-extracted locally (see iocs_local)
- You may ONLY supplement with additional IOCs found in the input text
- DO NOT fabricate IOCs that don't exist in the input
- DO NOT output hashes or IPs that are not present in the raw log
- The iocs field should merge your findings with iocs_local

Recommended actions MUST include:
- action: clear description of what to do
- priority: high/medium/low
- details: explanation of why this action
- verification: how to verify the action was effective"""


# Builtin user-prompt template (T3.2): overridable at runtime via an active
# "alert_analysis_user" row in the prompt registry. Keep placeholders stable.
_ALERT_USER_PROMPT_BUILTIN = """Analyze this security alert/log:

Raw Log:
{raw_log}

Pre-extracted IOCs (Local Regex):
- IPs: {ips_str}
- Domains: {domains_str}
- URLs: {urls_str}
- Hashes: {hashes_str}

IMPORTANT: These IOCs are pre-extracted from the input. You may only add NEW IOCs that are actually present in the raw log text above. DO NOT fabricate any IOCs.

Provide structured analysis including:
1. Event type classification
2. Severity assessment
3. IOCs (merge your findings with pre-extracted IOCs)
4. Entities (users, hosts, processes)
5. Summary of what happened
6. Evidence points supporting your analysis
7. Recommended actions with verification steps
8. Escalation decision
9. Confidence score"""


class AlertService:
    """Service for alert analysis."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        """Initialize alert service.

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

    async def analyze(
        self,
        raw_log: str,
        save_history: bool = True,
    ) -> AlertAnalysisResponse:
        """Analyze a security alert.

        Args:
            raw_log: Raw log content to analyze
            save_history: Whether to save to history

        Returns:
            Alert analysis response
        """
        logger.info(f"Analyzing alert, log length: {len(raw_log)}")

        # Step 1: Extract IOCs locally
        local_iocs: IOCs = extract_iocs(raw_log)
        logger.info(
            f"Local IOC extraction: {len(local_iocs.ips)} IPs, "
            f"{len(local_iocs.domains)} domains, "
            f"{len(local_iocs.urls)} URLs, "
            f"{len(local_iocs.hashes)} hashes"
        )

        # Build prompt with local IOC context. The template is resolvable via
        # the prompt registry (T3.2): an active "alert_analysis_user" row
        # overrides the builtin; misses fall back to it.
        template = await resolve_prompt(
            "alert_analysis_user", _ALERT_USER_PROMPT_BUILTIN
        )
        prompt = template.format(
            raw_log=raw_log,
            ips_str=", ".join(local_iocs.ips) if local_iocs.ips else "None",
            domains_str=", ".join(local_iocs.domains) if local_iocs.domains else "None",
            urls_str=(
                ", ".join(local_iocs.urls[:5])
                + ("..." if len(local_iocs.urls) > 5 else "")
                if local_iocs.urls
                else "None"
            ),
            hashes_str=(
                ", ".join(local_iocs.hashes[:3])
                + ("..." if len(local_iocs.hashes) > 3 else "")
                if local_iocs.hashes
                else "None"
            ),
        )

        # Generate response with retry and degraded fallback
        result, model_used, degraded = await self.llm_service.generate_structured(
            prompt=prompt,
            response_class=AlertAnalysisResponse,
            extracted_iocs=local_iocs.to_dict(),
        )

        # Step 4: Merge IOCs - local takes precedence, LLM supplements
        result = self._merge_iocs(result, local_iocs)

        logger.info(
            f"Analysis complete: event_type={result.event_type}, "
            f"severity={result.severity}, degraded={degraded}"
        )

        # Step 5: Perform impact analysis
        result = await self._add_impact_analysis(result, raw_log, local_iocs, degraded)

        # Step 6: Perform threat intelligence enrichment
        result = await self._add_threat_intel(result, local_iocs, degraded)

        # Save to history if session available
        history_id = None
        if save_history and self.history_service:
            history = await self.history_service.create_history(
                module="analyzer",
                input_text=raw_log,
                output_json=result.model_dump(),
                output_markdown=self._format_as_markdown(result),
                extracted_iocs=local_iocs.to_dict(),
                tags={
                    "event_type": result.event_type,
                    "severity": result.severity,
                },
                request_id=result.request_id,
                model_used=model_used,
                degraded=degraded,
                error_reason=result.error_reason,
            )
            history_id = history.id

            # v0.8.1: Return history_id in response to avoid extra API call
            result.history_id = history_id

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
        result: AlertAnalysisResponse,
        raw_log: str,
        local_iocs: IOCs,
        degraded: bool,
    ) -> AlertAnalysisResponse:
        """Add impact analysis to result.

        Args:
            result: Analysis result
            raw_log: Raw log content
            local_iocs: Locally extracted IOCs
            degraded: Whether in degraded mode

        Returns:
            Updated analysis result with impact analysis
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

            # Match by hostname (from entities or input text)
            hostnames = result.entities.hosts if result.entities.hosts else []
            if hostnames:
                assets_by_hostname = await self.asset_service.get_by_hostnames(
                    hostnames
                )
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

        return AlertAnalysisResponse.model_validate(result_dict)

    async def _add_threat_intel(
        self,
        result: AlertAnalysisResponse,
        local_iocs: IOCs,
        degraded: bool,
    ) -> AlertAnalysisResponse:
        """Add threat intelligence analysis to result.

        v0.4.1: Re-enabled with compliance filtering. Private/internal IOCs are
        not sent to external TI services but are included in filtered_items.

        Args:
            result: Analysis result
            local_iocs: Locally extracted IOCs
            degraded: Whether in degraded mode

        Returns:
            Updated analysis result with threat intel
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

            # Enrich IOCs with threat intel (includes compliance filtering)
            threat_intel = await self.threat_intel_service.enrich_iocs(iocs_dict)

        # Add threat intel to result
        result_dict = result.model_dump()
        result_dict["threat_intel"] = threat_intel.model_dump()

        return AlertAnalysisResponse.model_validate(result_dict)

    async def _create_ioc_hits(
        self,
        history_id: str,
        local_iocs: IOCs,
        affected_assets: list,
    ) -> None:
        """Create IOC hits from analysis.

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
                    asset_map[asset.ip] = asset.asset_id
                if asset.hostname:
                    asset_map[asset.hostname.lower()] = asset.asset_id

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
            # Don't auto-associate domains to assets
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
        result: AlertAnalysisResponse,
        local_iocs: IOCs,
    ) -> AlertAnalysisResponse:
        """Merge local IOCs with AI-detected ones.

        Args:
            result: Analysis result from AI
            local_iocs: Locally extracted IOCs

        Returns:
            Updated analysis result
        """
        result_dict = result.model_dump()

        # Get LLM IOCs (if any) - empty if degraded mode
        llm_iocs = {
            "ips": result_dict.get("iocs", {}).get("ips", []),
            "domains": result_dict.get("iocs", {}).get("domains", []),
            "urls": result_dict.get("iocs", {}).get("urls", []),
            "hashes": result_dict.get("iocs", {}).get("hashes", []),
        }

        # Merge: local + LLM (union), local takes precedence
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
            "total": sum(
                len(merged_iocs[k]) for k in ["ips", "domains", "urls", "hashes"]
            ),
        }

        return AlertAnalysisResponse.model_validate(result_dict)

    def _format_as_markdown(self, result: AlertAnalysisResponse) -> str:
        """Format result as markdown for display.

        Args:
            result: Analysis result

        Returns:
            Markdown formatted string
        """
        lines = [
            "# Alert Analysis",
            "",
            f"**Event Type:** {result.event_type}",
            f"**Severity:** {result.severity}",
            f"**Confidence:** {result.confidence}%",
            "",
            "## Summary",
            f"{result.summary}",
            "",
            "## IOCs",
        ]

        for ioc_type, items in result.iocs.model_dump().items():
            if items:
                lines.append(f"- **{ioc_type}:** {', '.join(items)}")

        lines.extend(
            [
                "",
                "## Entities",
            ]
        )

        for entity_type, items in result.entities.model_dump().items():
            if items:
                lines.append(f"- **{entity_type}:** {', '.join(items)}")

        lines.extend(
            [
                "",
                "## Evidence",
            ]
        )

        for point in result.evidence_points:
            lines.append(f"- {point}")

        lines.extend(
            [
                "",
                "## Recommended Actions",
            ]
        )

        for action in result.recommended_actions:
            if isinstance(action, dict):
                lines.extend(
                    [
                        f"- **{action.get('action', 'Unknown')}** [{action.get('priority', 'N/A')}]",
                        f"  - {action.get('details', '')}",
                        f"  - *Verification:* {action.get('verification', 'N/A')}",
                    ]
                )

        lines.extend(
            [
                "",
                f"**Escalation Required:** {'Yes' if result.escalation_needed else 'No'}",
            ]
        )

        if result.degraded:
            lines.extend(
                [
                    "",
                    "---",
                    f"*⚠️ Degraded mode: {result.error_reason or 'Unknown error'}*",
                ]
            )

        return "\n".join(lines)

"""Impact analysis service."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from schemas.impact import (
    AffectedAsset,
    ContainmentPriority,
    ImpactAnalysis,
)
from schemas.impact import (
    Severity as ImpactSeverity,
)

logger = get_logger(__name__)


class ImpactAnalysisService:
    """Service for impact analysis."""

    # Criticality weights
    CRITICALITY_WEIGHTS = {
        "low": 1,
        "medium": 2,
        "high": 3,
        "critical": 5,
    }

    # IOC type weights
    IOC_WEIGHTS = {
        "ip": 2,
        "domain": 3,
        "url": 4,
        "hash": 5,
    }

    def __init__(self, session: AsyncSession) -> None:
        """Initialize impact analysis service.

        Args:
            session: Database session
        """
        self.session = session

    async def analyze(
        self,
        iocs: dict[str, list[str]],
        history_record: Any | None = None,
        primary_asset: Any | None = None,
        related_assets: list[Any] | None = None,
    ) -> ImpactAnalysis:
        """Perform impact analysis.

        Args:
            iocs: Dictionary of IOC types to values
            history_record: Associated history record
            primary_asset: Primary affected asset
            related_assets: Related assets from IOC matching

        Returns:
            Impact analysis result
        """
        logger.info("Performing impact analysis")

        # Calculate risk score
        risk_score = await self._calculate_risk_score(
            iocs, history_record, primary_asset, related_assets
        )

        # Determine severity
        severity = self._determine_severity(risk_score, len(related_assets or []))

        # Build affected assets list
        affected_assets = await self._build_affected_assets(
            iocs, primary_asset, related_assets
        )

        # Generate business impact description
        business_impact = self._generate_business_impact(
            affected_assets, iocs, severity
        )

        # Build containment priorities
        containment_priority = self._build_containment_priorities(affected_assets, iocs)

        # Generate recommended queries
        recommended_queries = self._generate_recommended_queries(
            iocs, primary_asset, related_assets
        )

        return ImpactAnalysis(
            affected_assets=affected_assets,
            business_impact=business_impact,
            risk_score=risk_score,
            severity=severity,
            containment_priority=containment_priority,
            recommended_next_queries=recommended_queries,
        )

    async def _calculate_risk_score(
        self,
        iocs: dict[str, list[str]],
        history_record: Any | None,
        primary_asset: Any | None,
        related_assets: list[Any] | None,
    ) -> int:
        """Calculate risk score (0-100).

        Args:
            iocs: Dictionary of IOC types to values
            history_record: Associated history record
            primary_asset: Primary affected asset
            related_assets: Related assets from IOC matching

        Returns:
            Risk score from 0 to 100
        """
        score = 20  # Base score

        # Factor 1: Number of IOCs
        total_iocs = sum(len(v) for v in iocs.values())
        score += min(total_iocs * 3, 20)

        # Factor 2: Affected assets and their criticality
        if related_assets:
            for asset in related_assets:
                weight = self.CRITICALITY_WEIGHTS.get(asset.criticality, 2)
                score += weight * 5

        # Factor 3: IOC types (hash + URL is concerning)
        if iocs.get("hashes") and iocs.get("urls"):
            score += 15

        # Factor 4: Hash presence alone is high risk
        if iocs.get("hashes"):
            score += 10

        # Factor 5: Critical asset affected
        if primary_asset and primary_asset.criticality == "critical":
            score += 20

        # Check for historical IOC hits
        if related_assets:
            ioc_values = [v for values in iocs.values() for v in values]
            # In a real implementation, would query for historical hits
            # For now, simulate based on IOC count
            if len(ioc_values) > 3:
                score += 10

        return min(score, 100)

    def _determine_severity(
        self, risk_score: int, affected_count: int
    ) -> ImpactSeverity:
        """Determine severity from risk score and affected assets.

        Args:
            risk_score: Calculated risk score
            affected_count: Number of affected assets

        Returns:
            Severity level
        """
        if risk_score >= 80:
            return ImpactSeverity.critical
        elif risk_score >= 60:
            return ImpactSeverity.high
        elif risk_score >= 40:
            return ImpactSeverity.medium
        else:
            return ImpactSeverity.low

    async def _build_affected_assets(
        self,
        iocs: dict[str, list[str]],
        primary_asset: Any | None,
        related_assets: list[Any] | None,
    ) -> list[AffectedAsset]:
        """Build list of affected assets.

        Args:
            iocs: Dictionary of IOC types to values
            primary_asset: Primary affected asset
            related_assets: Related assets from IOC matching

        Returns:
            List of affected assets
        """
        affected = []

        # Add related assets
        if related_assets:
            for asset in related_assets:
                affected.append(
                    AffectedAsset(
                        asset_id=asset.id,
                        hostname=asset.hostname,
                        ip=asset.ip,
                        criticality=asset.criticality,
                        reason=self._get_asset_reason(iocs, asset),
                    )
                )

        # Add primary asset if not already included
        if primary_asset and not any(a.asset_id == primary_asset.id for a in affected):
            affected.append(
                AffectedAsset(
                    asset_id=primary_asset.id,
                    hostname=primary_asset.hostname,
                    ip=primary_asset.ip,
                    criticality=primary_asset.criticality,
                    reason="Primary affected asset from analysis context",
                )
            )

        return affected

    def _get_asset_reason(self, iocs: dict[str, list[str]], asset: Any) -> str:
        """Get reason for asset being affected.

        Args:
            iocs: Dictionary of IOC types to values
            asset: Asset

        Returns:
            Reason description
        """
        reasons = []

        if asset.ip and asset.ip in iocs.get("ips", []):
            reasons.append(f"IP {asset.ip} found in IOCs")

        if asset.hostname:
            for hostname in iocs.get("domains", []):
                if asset.hostname.lower() in hostname.lower():
                    reasons.append(
                        f"Hostname {asset.hostname} matches IOC domain {hostname}"
                    )

        return "; ".join(reasons) if reasons else "IOC correlation detected"

    def _generate_business_impact(
        self,
        affected_assets: list[AffectedAsset],
        iocs: dict[str, list[str]],
        severity: ImpactSeverity,
    ) -> str:
        """Generate business impact description.

        Args:
            affected_assets: List of affected assets
            iocs: Dictionary of IOC types to values
            severity: Impact severity

        Returns:
            Business impact description
        """
        if not affected_assets:
            return "No assets directly impacted. IOCs detected require investigation."

        critical_count = sum(1 for a in affected_assets if a.criticality == "critical")
        high_count = sum(1 for a in affected_assets if a.criticality == "high")

        if severity == ImpactSeverity.critical:
            return (
                f"CRITICAL: {critical_count} critical and {high_count} high-value assets affected. "
                f"Immediate isolation and investigation required. "
                f"{sum(len(v) for v in iocs.values())} IOCs detected indicate potential active threat."
            )
        elif severity == ImpactSeverity.high:
            return (
                f"HIGH: {len(affected_assets)} assets affected. "
                f"Prompt investigation and containment recommended. "
                f"Multiple IOCs detected requiring validation."
            )
        elif severity == ImpactSeverity.medium:
            return (
                f"MEDIUM: {len(affected_assets)} assets potentially affected. "
                f"Investigation and monitoring recommended. "
                f"IOCs should be validated and tracked."
            )
        else:
            return "LOW: Limited impact detected. Routine investigation recommended."

    def _build_containment_priorities(
        self, affected_assets: list[AffectedAsset], iocs: dict[str, list[str]]
    ) -> list[ContainmentPriority]:
        """Build containment priority list.

        Args:
            affected_assets: List of affected assets
            iocs: Dictionary of IOC types to values

        Returns:
            List of containment priorities
        """
        priorities = []

        for asset in affected_assets:
            self.CRITICALITY_WEIGHTS.get(asset.criticality, 2)

            if asset.criticality == "critical":
                priority = 1
                reason = "Critical asset - immediate isolation required"
            elif asset.criticality == "high":
                priority = 3
                reason = "High-value asset - prompt containment recommended"
            elif asset.criticality == "medium":
                priority = 6
                reason = "Medium-value asset - investigation within 4 hours"
            else:
                priority = 8
                reason = "Low-value asset - routine investigation"

            # Increase priority if hash IOC present
            if iocs.get("hashes"):
                priority = max(1, priority - 2)
                reason += " - malicious hash detected"

            priorities.append(
                ContainmentPriority(
                    asset_id=asset.asset_id, priority=priority, reason=reason
                )
            )

        # Sort by priority (lower = higher priority)
        priorities.sort(key=lambda x: x.priority)
        return priorities

    def _generate_recommended_queries(
        self,
        iocs: dict[str, list[str]],
        primary_asset: Any | None,
        related_assets: list[Any] | None,
    ) -> list[str]:
        """Generate recommended follow-up queries.

        Args:
            iocs: Dictionary of IOC types to values
            primary_asset: Primary affected asset
            related_assets: Related assets

        Returns:
            List of recommended queries
        """
        queries = []

        # Query for each IP
        for ip in iocs.get("ips", [])[:3]:
            queries.append(f"Search for recent activity from IP: {ip}")

        # Query for each domain
        for domain in iocs.get("domains", [])[:3]:
            queries.append(f"Search for connections to domain: {domain}")

        # Query for each hash
        for hash_val in iocs.get("hashes", [])[:2]:
            queries.append(f"Search for file hash: {hash_val}")

        # Asset-specific queries
        if primary_asset:
            if primary_asset.hostname:
                queries.append(
                    f"Search for all activity on hostname: {primary_asset.hostname}"
                )
            if primary_asset.ip:
                queries.append(
                    f"Search for network connections from: {primary_asset.ip}"
                )

        # Related asset queries
        if related_assets and len(related_assets) > 1:
            queries.append(
                f"Correlate activity across {len(related_assets)} affected assets"
            )

        # Historical IOC query
        if iocs.get("ips") or iocs.get("domains"):
            queries.append("Search for historical hits of these IOCs")

        return queries[:10]  # Limit to 10 queries


def get_degraded_impact() -> ImpactAnalysis:
    """Get degraded mode impact analysis.

    Returns:
        Minimal valid impact analysis for degraded mode
    """
    return ImpactAnalysis(
        affected_assets=[],
        business_impact="Unable to perform impact analysis in degraded mode",
        risk_score=0,
        severity=ImpactSeverity.low,
        containment_priority=[],
        recommended_next_queries=[],
    )

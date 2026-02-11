"""Risk scoring step implementation."""

from typing import Any
from .base_step import BaseStepImpl
from ..registry import register_step


@register_step("risk_score", RiskScoreStep)
class RiskScoreStep(BaseStepImpl):
    """Calculate risk score based on threat intel and asset context."""

    @property
    def name(self) -> str:
        return "Risk Scoring"

    @property
    def step_id(self) -> str:
        return "risk_score"

    @property
    def step_type(self) -> str:
        return "analysis"

    @property
    def description(self) -> str:
        return "Calculate composite risk score based on multiple factors"

    @property
    def supports_apply(self) -> bool:
        return True

    def execute(self, input_json: dict[str, Any], mode: str) -> dict[str, Any]:
        """Calculate risk score.

        Args:
            input_json: Input containing IOCs, threat intel, and asset data
            mode: Execution mode

        Returns:
            Dictionary with risk assessment
        """
        iocs = input_json.get("iocs", {})
        ti_results = input_json.get("ti_results", {})
        asset_results = input_json.get("asset_results", {})

        # Base risk factors
        risk_factors = {
            "threat_intel_score": 0,
            "asset_criticality_score": 0,
            "ioc_count_score": 0,
            "source_reliability_score": 50,  # Default medium
        }

        # Calculate threat intel score
        if ti_results:
            summary = ti_results.get("summary", {})
            total_iocs = summary.get("total_iocs", 0)
            malicious = summary.get("malicious", 0)
            suspicious = summary.get("suspicious", 0)

            if total_iocs > 0:
                threat_ratio = (malicious * 100 + suspicious * 50) / total_iocs
                risk_factors["threat_intel_score"] = min(threat_ratio, 100)

        # Calculate asset criticality score
        if asset_results:
            summary = asset_results.get("summary", {})
            critical_count = summary.get("critical", 0)
            high_count = summary.get("high", 0)
            medium_count = summary.get("medium", 0)

            criticality_score = (
                critical_count * 100 +
                high_count * 75 +
                medium_count * 50
            )
            total_assets = max(summary.get("total", 1), 1)
            risk_factors["asset_criticality_score"] = min(criticality_score / total_assets, 100)

        # Calculate IOC count score
        ioc_count = sum(len(v) for v in iocs.values())
        risk_factors["ioc_count_score"] = min(ioc_count * 10, 100)

        # Calculate composite risk score
        weights = {
            "threat_intel_score": 0.4,
            "asset_criticality_score": 0.35,
            "ioc_count_score": 0.15,
            "source_reliability_score": 0.1,
        }

        composite_score = sum(
            risk_factors[factor] * weights[factor]
            for factor in weights
        )

        # Determine risk level
        if composite_score >= 75:
            risk_level = "critical"
        elif composite_score >= 50:
            risk_level = "high"
        elif composite_score >= 25:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "composite_score": round(composite_score, 2),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "weights": weights,
            "recommendation": self._get_recommendation(risk_level),
        }

    def _get_recommendation(self, risk_level: str) -> str:
        """Get recommendation based on risk level."""
        recommendations = {
            "critical": "Immediate containment required. Escalate to incident response team.",
            "high": "Rapid response required. Investigate and contain within 1 hour.",
            "medium": "Investigate within 4 hours. Monitor for additional indicators.",
            "low": "Standard investigation process. Monitor for correlation.",
        }
        return recommendations.get(risk_level, "Investigation recommended.")

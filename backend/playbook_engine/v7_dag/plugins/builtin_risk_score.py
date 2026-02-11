"""Risk scoring node plugin (v0.7.4)."""

from typing import Any, Dict
import logging

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


class RiskScorePlugin(BaseNodePlugin):
    """Calculate risk score for threats or incidents.

    Combines multiple factors to produce a normalized risk score (0-10).
    """

    @property
    def node_id(self) -> str:
        return "builtin_risk_score"

    @property
    def name(self) -> str:
        return "Risk Scoring"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return "Calculate risk score based on threat indicators"

    def validate_input(self, input_json: Dict[str, Any]) -> None:
        """Validate input before execution."""
        # Risk scoring can work with various inputs
        pass

    async def execute(self, context: NodeExecutionContext) -> Dict[str, Any]:
        """Execute risk calculation.

        Args:
            context: Execution context

        Returns:
            Risk score and breakdown
        """
        # Get threat intelligence results
        ti_results = context.input_json.get("ti_results") or {}
        ioc_count = context.input_json.get("ioc_count", 0)
        severity = context.input_json.get("severity", "unknown")

        logger.info(f"[{context.run_id}] Calculating risk score")

        # Calculate base score from TI results
        base_score = 0

        # Check for malicious indicators
        if isinstance(ti_results, dict):
            pulse_count = len(ti_results.get("matches", []))
            base_score += min(pulse_count, 5)

        # Add IOC count factor
        base_score += min(ioc_count, 3)

        # Severity adjustment
        severity_map = {"critical": 3, "high": 2, "medium": 1, "low": 0, "unknown": 0}
        base_score += severity_map.get(severity.lower(), 0)

        # Normalize to 0-10
        final_score = min(base_score, 10)

        # Determine risk level
        if final_score >= 8:
            risk_level = "critical"
        elif final_score >= 6:
            risk_level = "high"
        elif final_score >= 4:
            risk_level = "medium"
        elif final_score >= 2:
            risk_level = "low"
        else:
            risk_level = "informational"

        return {
            "status": "success",
            "risk_score": final_score,
            "risk_level": risk_level,
            "breakdown": {
                "base_score": min(base_score, 10),
                "ti_factor": len(ti_results.get("matches", [])) if isinstance(ti_results, dict) else 0,
                "ioc_factor": min(ioc_count, 3),
                "severity_factor": severity_map.get(severity.lower(), 0),
            },
            "recommendation": self._get_recommendation(risk_level)
        }

    def _get_recommendation(self, risk_level: str) -> str:
        """Get recommendation based on risk level."""
        recommendations = {
            "critical": "Immediate containment and incident response",
            "high": "Rapid investigation and containment preparation",
            "medium": "Standard investigation procedures",
            "low": "Monitor and document",
            "informational": "Log for future reference"
        }
        return recommendations.get(risk_level, "Review findings")

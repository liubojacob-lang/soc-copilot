"""Action plan generation node plugin (v0.7.4)."""

from typing import Any, Dict, List
import logging

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


class ActionPlanPlugin(BaseNodePlugin):
    """Generate actionable response plan based on analysis results.

    Creates prioritized list of actions for security responders.
    """

    @property
    def node_id(self) -> str:
        return "builtin_action_plan"

    @property
    def name(self) -> str:
        return "Action Plan"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return "Generate prioritized action plan for incident response"

    def validate_input(self, input_json: Dict[str, Any]) -> None:
        """Validate input before execution."""
        pass

    async def execute(self, context: NodeExecutionContext) -> Dict[str, Any]:
        """Execute action plan generation.

        Args:
            context: Execution context

        Returns:
            Prioritized action plan
        """
        risk_score = context.input_json.get("risk_score", 0)
        risk_level = context.input_json.get("risk_level", "unknown")
        iocs = context.input_json.get("iocs") or context.input_json.get("extracted_iocs") or {}
        ti_results = context.input_json.get("ti_results") or {}

        logger.info(f"[{context.run_id}] Generating action plan for risk_level={risk_level}")

        actions = self._generate_actions(risk_level, iocs, ti_results)

        return {
            "status": "success",
            "risk_level": risk_level,
            "action_count": len(actions),
            "actions": actions,
            "summary": f"Generated {len(actions)} actions for {risk_level} risk level"
        }

    def _generate_actions(
        self,
        risk_level: str,
        iocs: Dict[str, Any],
        ti_results: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Generate prioritized action list.

        Args:
            risk_level: Calculated risk level
            iocs: Extracted IOCs
            ti_results: Threat intelligence results

        Returns:
            List of prioritized actions
        """
        actions = []

        # Priority 1: Critical actions
        if risk_level in ("critical", "high"):
            actions.append({
                "priority": 1,
                "category": "containment",
                "action": "Isolate affected endpoints",
                "description": "Network containment of compromised systems",
                "assignee": "incident-response",
                "estimated_minutes": 15
            })
            actions.append({
                "priority": 1,
                "category": "communication",
                "action": "Notify stakeholders",
                "description": "Alert security leadership and affected teams",
                "assignee": "incident-commander",
                "estimated_minutes": 10
            })

        # Priority 2: Investigation actions
        actions.append({
            "priority": 2,
            "category": "investigation",
            "action": "Preserve evidence",
            "description": "Collect logs, memory dumps, and artifacts",
            "assignee": "forensics",
            "estimated_minutes": 30
        })

        # Priority 3: IOC hunting actions
        if iocs:
            ioc_types = list(iocs.keys())
            actions.append({
                "priority": 3,
                "category": "threat-hunting",
                "action": f"Hunt for IOCs across environment",
                "description": f"Search for {', '.join(ioc_types)} in logs and endpoints",
                "assignee": "threat-hunters",
                "estimated_minutes": 60
            })

        # Priority 4: Documentation actions
        actions.append({
            "priority": 4,
            "category": "documentation",
            "action": "Document incident timeline",
            "description": "Create detailed incident report with timeline",
            "assignee": "incident-response",
            "estimated_minutes": 45
        })

        # Priority 5: Recovery actions
        if risk_level in ("critical", "high"):
            actions.append({
                "priority": 5,
                "category": "recovery",
                "action": "Plan remediation steps",
                "description": "Prepare recovery and remediation procedures",
                "assignee": "incident-response",
                "estimated_minutes": 30
            })

        return actions

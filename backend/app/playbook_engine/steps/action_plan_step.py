"""Action plan step implementation."""

from typing import Any
from .base_step import BaseStepImpl
from ..registry import register_step


@register_step("action_plan", ActionPlanStep)
class ActionPlanStep(BaseStepImpl):
    """Generate remediation action plan."""

    @property
    def name(self) -> str:
        return "Action Plan Generation"

    @property
    def step_id(self) -> str:
        return "action_plan"

    @property
    def step_type(self) -> str:
        return "response"

    @property
    def description(self) -> str:
        return "Generate prioritized remediation action plan"

    @property
    def supports_apply(self) -> bool:
        return True

    def execute(self, input_json: dict[str, Any], mode: str) -> dict[str, Any]:
        """Generate action plan.

        Args:
            input_json: Input containing risk score, assets, and IOCs
            mode: Execution mode

        Returns:
            Dictionary with remediation actions
        """
        risk_results = input_json.get("risk_results", {})
        asset_results = input_json.get("asset_results", {})
        iocs = input_json.get("iocs", {})
        alert_data = input_json.get("alert_data", {})

        risk_level = risk_results.get("risk_level", "medium")
        composite_score = risk_results.get("composite_score", 50)

        actions = {
            "risk_level": risk_level,
            "composite_score": composite_score,
            "actions": [],
            "summary": {
                "total_actions": 0,
                "containment": 0,
                "eradication": 0,
                "recovery": 0,
            },
        }

        # Generate containment actions
        containment_actions = self._generate_containment_actions(
            risk_level, asset_results, iocs, alert_data
        )
        actions["actions"].extend(containment_actions)
        actions["summary"]["containment"] = len(containment_actions)

        # Generate eradication actions
        eradication_actions = self._generate_eradication_actions(
            risk_level, iocs, alert_data
        )
        actions["actions"].extend(eradication_actions)
        actions["summary"]["eradication"] = len(eradication_actions)

        # Generate recovery actions
        recovery_actions = self._generate_recovery_actions(
            risk_level, asset_results
        )
        actions["actions"].extend(recovery_actions)
        actions["summary"]["recovery"] = len(recovery_actions)

        # Sort by priority and category
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        actions["actions"].sort(key=lambda x: (
            priority_order.get(x.get("risk", "medium"), 2),
            {"containment": 0, "eradication": 1, "recovery": 2}.get(x.get("category", "recovery"), 2)
        ))

        actions["summary"]["total_actions"] = len(actions["actions"])

        return actions

    def _generate_containment_actions(self, risk_level: str, asset_results: dict, iocs: dict, alert_data: dict) -> list[dict]:
        """Generate containment actions."""
        actions = []

        # Network containment
        for ip in iocs.get("ips", [])[:3]:
            actions.append({
                "title": f"Block malicious IP: {ip}",
                "category": "containment",
                "risk": risk_level,
                "priority": "1" if risk_level in ["critical", "high"] else "2",
                "rationale": f"Prevent communication with known malicious IP address {ip}",
                "steps": [
                    {
                        "action": "Add firewall rule",
                        "method": "Firewall / Security Group",
                        "command": f"iptables -A INPUT -s {ip} -j DROP",
                    },
                ],
                "verification": [
                    f"Verify no traffic from {ip} in firewall logs",
                    "Confirm outbound connections to {ip} are blocked",
                ],
                "rollback": [
                    f"Remove firewall rule for IP {ip}",
                    "Document in change control system",
                ],
            })

        # Host containment
        hostname = alert_data.get("hostname")
        if hostname and risk_level in ["critical", "high"]:
            actions.append({
                "title": f"Isolate compromised host: {hostname}",
                "category": "containment",
                "risk": risk_level,
                "priority": "1",
                "rationale": f"Prevent lateral movement from potentially compromised host {hostname}",
                "steps": [
                    {
                        "action": "Network isolation",
                        "method": "EDR / Network ACL",
                        "command": f"# Isolate host via EDR console\n# Host: {hostname}",
                    },
                ],
                "verification": [
                    f"Confirm {hostname} cannot communicate with other internal systems",
                    "Verify only EDR/management connectivity remains",
                ],
                "rollback": [
                    f"Restore network connectivity for {hostname}",
                    "Monitor for suspicious activity post-restoration",
                ],
            })

        return actions

    def _generate_eradication_actions(self, risk_level: str, iocs: dict, alert_data: dict) -> list[dict]:
        """Generate eradication actions."""
        actions = []

        # Domain blocking
        for domain in iocs.get("domains", [])[:3]:
            actions.append({
                "title": f"Block malicious domain: {domain}",
                "category": "eradication",
                "risk": risk_level,
                "priority": "2",
                "rationale": f"Prevent connections to malicious domain {domain}",
                "steps": [
                    {
                        "action": "Add DNS sinkhole rule",
                        "method": "DNS / RPZ",
                        "command": f'zone "{domain}" {{ type master; file "blocked.zone"; }};',
                    },
                ],
                "verification": [
                    f"Verify DNS queries for {domain} return sinkhole address",
                    "Monitor DNS logs for blocked queries",
                ],
                "rollback": [
                    f"Remove DNS sinkhole rule for {domain}",
                    "Clear DNS cache if necessary",
                ],
            })

        # Threat hunting action
        actions.append({
            "title": "Hunt for additional compromised systems",
            "category": "eradication",
            "risk": "high" if risk_level == "critical" else "medium",
            "priority": "2",
            "rationale": "Identify all potentially compromised systems using extracted IOCs",
            "steps": [
                {
                    "action": "Execute threat hunt queries",
                    "method": "SIEM",
                    "command": "# Run SIEM queries with extracted IOCs across 30-day window",
                },
            ],
            "verification": [
                "Review search results for additional matches",
                "Correlate findings across multiple data sources",
            ],
            "rollback": [],
        })

        return actions

    def _generate_recovery_actions(self, risk_level: str, asset_results: dict) -> list[dict]:
        """Generate recovery actions."""
        actions = []

        # Incident documentation
        actions.append({
            "title": "Document incident findings",
            "category": "recovery",
            "risk": "low",
            "priority": "3",
            "rationale": "Create comprehensive incident report for stakeholders",
            "steps": [
                {
                    "action": "Compile incident report",
                    "method": "Documentation",
                    "command": "# Document timeline, IOCs, affected assets, and actions taken",
                },
            ],
            "verification": [
                "Review report completeness with incident response team",
                "Obtain management sign-off",
            ],
            "rollback": [],
        })

        # Post-incident review
        actions.append({
            "title": "Schedule post-incident review",
            "category": "recovery",
            "risk": "low",
            "priority": "3",
            "rationale": "Identify lessons learned and improve detection/response capabilities",
            "steps": [
                {
                    "action": "Schedule review meeting",
                    "method": "Planning",
                    "command": "# Schedule within 5 business days with all stakeholders",
                },
            ],
            "verification": [
                "Review meeting scheduled and attendees confirmed",
                "Action items assigned and tracked",
            ],
            "rollback": [],
        })

        return actions

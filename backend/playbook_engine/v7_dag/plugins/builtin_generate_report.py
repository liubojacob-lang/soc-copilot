"""Generate incident response report node plugin (v0.7.4)."""

from typing import Any, Dict
from datetime import datetime
import logging

from ..base_node import BaseNodePlugin, NodeExecutionContext

logger = logging.getLogger(__name__)


class GenerateReportPlugin(BaseNodePlugin):
    """Generate markdown incident response report.
    
    This node creates a comprehensive markdown report with
    IOC analysis, threat intelligence results, and remediation actions.
    """

    @property
    def node_id(self) -> str:
        return "builtin_generate_report"

    @property
    def name(self) -> str:
        return "Generate Report"

    @property
    def node_type(self) -> str:
        return "action"

    @property
    def description(self) -> str:
        return "Generate markdown incident response report"

    def validate_input(self, input_json: Dict[str, Any]) -> None:
        """Validate input before execution."""
        if not input_json.get("case_id"):
            raise ValueError("case_id is required")
        if not input_json.get("ioc"):
            raise ValueError("ioc is required")

    async def execute(self, context: NodeExecutionContext) -> Dict[str, Any]:
        """Execute report generation.

        Args:
            context: Execution context

        Returns:
            Report metadata and markdown content
        """
        case_id = context.input_json.get("case_id", "UNKNOWN")
        ioc = context.input_json.get("ioc", "unknown")
        ioc_type = context.input_json.get("ioc_type", "unknown")
        alert_source = context.input_json.get("alert_source", "email-gateway")
        severity = context.input_json.get("severity", "medium")
        reporter = context.input_json.get("reporter", "soc@company.com")
        
        ti_result = context.input_json.get("ti_result") or context.input_json.get("otx_result", {})
        secondary_iocs = context.input_json.get("secondary_iocs", {})
        action_result = context.input_json.get("action_result", {})
        note = context.input_json.get("note", "")

        logger.info(f"[{context.run_id}] Generating report for case {case_id}")

        # Build markdown report
        report_lines = []
        
        # Header
        report_lines.append(f"# Incident Response Report: {case_id}")
        report_lines.append("")
        report_lines.append(f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
        report_lines.append(f"**Playbook Run ID:** {context.run_id}")
        report_lines.append("")

        # Executive Summary
        report_lines.append("## Executive Summary")
        report_lines.append("")
        threat_score = ti_result.get("threat_score", 0) if isinstance(ti_result, dict) else 0
        is_malicious = threat_score >= 3
        
        if is_malicious:
            report_lines.append(f"⚠️ **THREAT CONFIRMED** - IOC `{ioc}` has been identified as malicious.")
        else:
            report_lines.append(f"ℹ️ **LOW CONFIDENCE** - IOC `{ioc}` did not return significant threat intelligence.")
        report_lines.append("")

        # IOC Details
        report_lines.append("## IOC Details")
        report_lines.append("")
        report_lines.append(f"| Field | Value |")
        report_lines.append(f"|-------|-------|")
        report_lines.append(f"| **Case ID** | {case_id} |")
        report_lines.append(f"| **IOC** | `{ioc}` |")
        report_lines.append(f"| **Type** | {ioc_type} |")
        report_lines.append(f"| **Source** | {alert_source} |")
        report_lines.append(f"| **Severity** | {severity} |")
        report_lines.append(f"| **Reporter** | {reporter} |")
        report_lines.append("")

        # Threat Intelligence Results
        report_lines.append("## Threat Intelligence Analysis")
        report_lines.append("")
        
        if isinstance(ti_result, dict):
            report_lines.append(f"### OTX Lookup Results")
            report_lines.append("")
            report_lines.append(f"- **Threat Score:** {ti_result.get('threat_score', 0)}/10")
            report_lines.append(f"- **Match Count:** {ti_result.get('match_count', 0)} pulses")
            report_lines.append(f"- **Malicious:** {'Yes' if ti_result.get('is_malicious') else 'No'}")
            report_lines.append("")
            
            matches = ti_result.get("matches", [])
            if matches:
                report_lines.append("#### Matched Threat Pulses")
                report_lines.append("")
                for i, match in enumerate(matches[:5], 1):
                    report_lines.append(f"{i}. **{match.get('name', 'Unknown')}**")
                    if match.get('description'):
                        report_lines.append(f"   - Description: {match['description'][:100]}...")
                    if match.get('tags'):
                        report_lines.append(f"   - Tags: {', '.join(match['tags'][:5])}")
                    report_lines.append("")
        else:
            report_lines.append("*No threat intelligence data available*")
            report_lines.append("")

        # Secondary IOCs
        extracted = secondary_iocs.get("extracted_iocs", {}) if isinstance(secondary_iocs, dict) else {}
        if extracted and any(extracted.values()):
            report_lines.append("## Secondary IOCs Extracted")
            report_lines.append("")
            report_lines.append(f"**Total Extracted:** {secondary_iocs.get('total_extracted', 0)}")
            report_lines.append("")
            
            for ioc_type_key, ioc_list in extracted.items():
                if ioc_list:
                    report_lines.append(f"### {ioc_type_key.upper()}")
                    report_lines.append("")
                    for item in ioc_list[:10]:  # Limit to 10 per type
                        report_lines.append(f"- `{item}`")
                    if len(ioc_list) > 10:
                        report_lines.append(f"- *... and {len(ioc_list) - 10} more*")
                    report_lines.append("")

        # Actions Taken
        report_lines.append("## Actions Taken")
        report_lines.append("")
        
        if isinstance(action_result, dict) and action_result.get("status") == "success":
            report_lines.append("✅ **IOC Blocked** - The indicator has been added to the blocklist.")
        elif is_malicious:
            report_lines.append("⚠️ **Action Required** - Manual blocking recommended.")
        else:
            report_lines.append("ℹ️ **No Action** - Low confidence, monitoring only.")
        report_lines.append("")

        # Recommendations
        report_lines.append("## Recommendations")
        report_lines.append("")
        if is_malicious:
            report_lines.append("1. ✅ Block the primary IOC at network perimeter")
            report_lines.append("2. 🔍 Hunt for secondary IOCs in environment")
            report_lines.append("3. 📧 Check for related phishing emails")
            report_lines.append("4. 📝 Update threat detection rules")
        else:
            report_lines.append("1. 👁️ Continue monitoring the IOC")
            report_lines.append("2. 📊 Review alert source configuration")
            report_lines.append("3. 🔄 Re-run analysis if new intelligence becomes available")
        report_lines.append("")

        # Notes
        if note:
            report_lines.append("## Notes")
            report_lines.append("")
            report_lines.append(note)
            report_lines.append("")

        # Footer
        report_lines.append("---")
        report_lines.append("*This report was automatically generated by SOC Copilot Playbook Engine*")

        markdown = "\n".join(report_lines)
        report_id = f"RPT-{case_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        logger.info(f"[{context.run_id}] Report generated: {report_id}")

        return {
            "status": "success",
            "report_id": report_id,
            "case_id": case_id,
            "markdown": markdown,
            "report_url": f"/api/reports/{report_id}",
            "generated_at": datetime.utcnow().isoformat(),
            "threat_level": "high" if is_malicious else "low",
            "word_count": len(markdown.split())
        }

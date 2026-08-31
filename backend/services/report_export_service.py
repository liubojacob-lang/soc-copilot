"""Report Export Service — F3-6: PDF export & F3-7: Compliance templates.

Generates PDF reports from markdown/JSON data using Jinja2 HTML templates
and WeasyPrint for PDF rendering. Includes 3 compliance report templates:
ISO 27001, GDPR, and NIST CSF.
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

from core.logger import get_logger

logger = get_logger(__name__)

# Template directory relative to this module
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates" / "reports"


class ReportExportService:
    """Generates PDF reports from incident/alert data using HTML templates.

    Supports:
    - Incident response reports
    - ISO 27001 compliance reports
    - GDPR compliance reports
    - NIST CSF compliance reports
    """

    def __init__(self) -> None:
        self._weasyprint_available = self._check_weasyprint()

    @staticmethod
    def _check_weasyprint() -> bool:
        """Check if WeasyPrint is available."""
        try:
            import weasyprint  # type: ignore[import-untyped] # noqa: F401

            return True
        except ImportError:
            logger.warning(
                "WeasyPrint not installed. PDF export will be unavailable. "
                "Install with: pip install weasyprint"
            )
            return False

    # ── Template helpers ───────────────────────────────────────────────

    @staticmethod
    def _get_template_path(template_name: str) -> Path | None:
        """Resolve a template file path.

        Checks explicit path, then templates/reports/ directory.
        """
        # If it looks like an absolute path or exists as-is
        path = Path(template_name)
        if path.exists():
            return path

        # Try templates/reports/ directory
        candidate = _TEMPLATES_DIR / template_name
        if candidate.exists():
            return candidate
        if candidate.with_suffix(".html").exists():
            return candidate.with_suffix(".html")

        return None

    @staticmethod
    def _render_template(template_path: Path, context: dict[str, Any]) -> str:
        """Render a Jinja2 HTML template with context data.

        Args:
            template_path: Path to .html template file
            context: Template variables

        Returns:
            Rendered HTML string
        """
        try:
            from jinja2 import Environment, FileSystemLoader, select_autoescape
        except ImportError:
            logger.error("Jinja2 not installed. Install with: pip install jinja2")
            return ReportExportService._fallback_html(context)

        env = Environment(
            loader=FileSystemLoader(str(template_path.parent)),
            autoescape=select_autoescape(["html", "xml"]),
        )

        # Add custom filters
        env.filters["datetime"] = lambda v: (
            v.strftime("%Y-%m-%d %H:%M:%S") if hasattr(v, "strftime") else str(v)
        )
        env.filters["severity_color"] = lambda v: {
            "critical": "#dc3545",
            "high": "#fd7e14",
            "medium": "#ffc107",
            "low": "#28a745",
            "info": "#17a2b8",
        }.get(str(v).lower(), "#6c757d")

        template = env.get_template(template_path.name)
        return template.render(**context)

    @staticmethod
    def _fallback_html(context: dict[str, Any]) -> str:
        """Generate a basic HTML report without Jinja2."""
        title = context.get("title", "Security Report")
        generated = context.get("generated_at", datetime.now().isoformat())
        body = context.get("body", json.dumps(context, indent=2))

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; line-height: 1.6; }}
        h1 {{ color: #1a1a2e; }}
        .meta {{ color: #666; font-size: 0.9em; }}
        .content {{ white-space: pre-wrap; background: #f5f5f5; padding: 20px; border-radius: 4px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <p class="meta">Generated: {generated}</p>
    <div class="content">{body}</div>
</body>
</html>"""

    # ── PDF generation ─────────────────────────────────────────────────

    async def export_pdf(
        self,
        report_data: dict[str, Any],
        template_name: str = "incident_report.html",
        output_path: str | None = None,
    ) -> bytes:
        """Export report data to PDF.

        Args:
            report_data: Report data dictionary. Key fields:
                - title: Report title
                - alert_data: Alert/incident details
                - timeline: List of timeline events
                - iocs: IOCs found
                - response_measures: Response actions
                - compliance_map: Compliance control mapping
            template_name: Template file name or path
            output_path: Optional path to save PDF file

        Returns:
            PDF bytes (empty bytes if WeasyPrint unavailable)
        """
        # Prepare context
        context = {
            **report_data,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
        }

        # Find and render template
        template_path = self._get_template_path(template_name)
        if template_path is None:
            logger.error(f"Template not found: {template_name}")
            return b""

        html_content = self._render_template(template_path, context)

        if not self._weasyprint_available:
            logger.warning("PDF export unavailable — returning HTML as fallback")
            return html_content.encode("utf-8")

        try:
            import weasyprint  # type: ignore[import-untyped]

            pdf_bytes = weasyprint.HTML(string=html_content).write_pdf()

            if output_path:
                os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(pdf_bytes)
                logger.info(f"PDF saved to {output_path}")

            return pdf_bytes
        except Exception as e:
            logger.error(f"PDF generation failed: {e}")
            return b""

    async def export_html(
        self,
        report_data: dict[str, Any],
        template_name: str = "incident_report.html",
    ) -> str:
        """Export report data to HTML.

        Args:
            report_data: Report data dictionary
            template_name: Template file name

        Returns:
            HTML string
        """
        context = {
            **report_data,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "version": "1.0",
        }

        template_path = self._get_template_path(template_name)
        if template_path is None:
            logger.error(f"Template not found: {template_name}")
            return self._fallback_html(context)

        return self._render_template(template_path, context)

    # ── Compliance report generators ───────────────────────────────────

    async def generate_iso27001_report(self, report_data: dict[str, Any]) -> bytes:
        """Generate ISO 27001 compliance report.

        Maps incident to ISO 27001 Annex A controls:
        - A.12: Operations Security
        - A.13: Communications Security
        - A.16: Information Security Incident Management
        - A.18: Compliance

        Args:
            report_data: Report data with incident details

        Returns:
            PDF bytes
        """
        # Auto-map incident type to ISO 27001 controls
        iso_mapping = self._map_iso27001_controls(report_data)
        context = {**report_data, "iso_controls": iso_mapping}
        return await self.export_pdf(context, "compliance_iso27001.html")

    async def generate_gdpr_report(self, report_data: dict[str, Any]) -> bytes:
        """Generate GDPR compliance report.

        Maps incident to GDPR articles:
        - Art. 5: Principles
        - Art. 32: Security of Processing
        - Art. 33: Notification of Data Breach
        - Art. 34: Communication to Data Subjects

        Args:
            report_data: Report data with incident details

        Returns:
            PDF bytes
        """
        gdpr_mapping = self._map_gdpr_articles(report_data)
        context = {**report_data, "gdpr_articles": gdpr_mapping}
        return await self.export_pdf(context, "compliance_gdpr.html")

    async def generate_nist_report(self, report_data: dict[str, Any]) -> bytes:
        """Generate NIST CSF compliance report.

        Maps incident to NIST CSF categories:
        - IDENTIFY (ID): Asset management, risk assessment
        - PROTECT (PR): Access control, data security
        - DETECT (DE): Anomalies, continuous monitoring
        - RESPOND (RS): Response planning, mitigation
        - RECOVER (RC): Recovery planning, improvements

        Args:
            report_data: Report data with incident details

        Returns:
            PDF bytes
        """
        nist_mapping = self._map_nist_csf(report_data)
        context = {**report_data, "nist_controls": nist_mapping}
        return await self.export_pdf(context, "compliance_nist.html")

    @staticmethod
    def _map_iso27001_controls(report_data: dict[str, Any]) -> list[dict]:
        """Map incident data to ISO 27001 Annex A controls."""
        incident_type = report_data.get("incident_type", "").lower()
        severity = report_data.get("severity", "").lower()

        mappings = [
            {
                "control_id": "A.16.1",
                "control_name": "Management of Information Security Incidents",
                "description": "Ensure a consistent and effective approach to incident management",
                "applicable": True,
                "evidence": f"{incident_type} incident, severity {severity}",
            },
            {
                "control_id": "A.12.4",
                "control_name": "Logging and Monitoring",
                "description": "Event logs recording user activities, exceptions, faults",
                "applicable": True,
                "evidence": "Alert generated from monitoring system",
            },
            {
                "control_id": "A.13.1",
                "control_name": "Network Security Management",
                "description": "Ensure protection of information in networks",
                "applicable": "network" in incident_type or "ip" in incident_type,
                "evidence": "Network traffic analysis conducted",
            },
            {
                "control_id": "A.9.2",
                "control_name": "User Access Management",
                "description": "Ensure authorized user access and prevent unauthorized access",
                "applicable": "authentication" in incident_type
                or "login" in incident_type,
                "evidence": "Access control review initiated",
            },
            {
                "control_id": "A.18.1",
                "control_name": "Compliance with Legal Requirements",
                "description": "Identify applicable legislation and regulatory requirements",
                "applicable": severity in ("high", "critical"),
                "evidence": "Compliance review triggered",
            },
        ]
        return mappings

    @staticmethod
    def _map_gdpr_articles(report_data: dict[str, Any]) -> list[dict]:
        """Map incident data to relevant GDPR articles."""
        incident_type = report_data.get("incident_type", "").lower()

        articles = [
            {
                "article": "Art. 32",
                "title": "Security of Processing",
                "description": "Implement appropriate technical and organizational measures",
                "applicable": True,
                "action_required": "Review security controls",
            },
            {
                "article": "Art. 33",
                "title": "Notification of Personal Data Breach",
                "description": "Notify supervisory authority within 72 hours",
                "applicable": "data" in incident_type
                or "exfil" in incident_type
                or "breach" in incident_type,
                "action_required": "Assess data exposure; prepare notification",
            },
            {
                "article": "Art. 34",
                "title": "Communication of Data Breach to Data Subjects",
                "description": "Communicate breach to affected individuals",
                "applicable": "data" in incident_type or "pii" in incident_type,
                "action_required": "Identify affected data subjects",
            },
            {
                "article": "Art. 5",
                "title": "Principles Relating to Processing",
                "description": "Lawfulness, fairness, transparency, purpose limitation",
                "applicable": True,
                "action_required": "Document data processing context",
            },
            {
                "article": "Art. 30",
                "title": "Records of Processing Activities",
                "description": "Maintain records of processing activities",
                "applicable": True,
                "action_required": "Update processing records with incident details",
            },
        ]
        return articles

    @staticmethod
    def _map_nist_csf(report_data: dict[str, Any]) -> list[dict]:
        """Map incident data to NIST Cybersecurity Framework categories."""
        incident_type = report_data.get("incident_type", "").lower()

        mappings = [
            {
                "function": "IDENTIFY (ID)",
                "category": "ID.AM — Asset Management",
                "description": "Identify assets to enable effective cybersecurity management",
                "applicable": True,
                "evidence": "Affected assets identified in alert",
            },
            {
                "function": "PROTECT (PR)",
                "category": "PR.AC — Identity Management and Access Control",
                "description": "Limit access to authorized users and devices",
                "applicable": "auth" in incident_type
                or "login" in incident_type
                or "access" in incident_type,
                "evidence": "Access control mechanisms triggered",
            },
            {
                "function": "DETECT (DE)",
                "category": "DE.AE — Anomalies and Events",
                "description": "Detect anomalous activity in a timely manner",
                "applicable": True,
                "evidence": "Alert detected via monitoring system",
            },
            {
                "function": "DETECT (DE)",
                "category": "DE.CM — Continuous Monitoring",
                "description": "Monitor assets to identify cybersecurity events",
                "applicable": True,
                "evidence": "Continuous monitoring infrastructure",
            },
            {
                "function": "RESPOND (RS)",
                "category": "RS.AN — Analysis",
                "description": "Analyze to ensure effective response",
                "applicable": True,
                "evidence": "Incident analysis completed",
            },
            {
                "function": "RESPOND (RS)",
                "category": "RS.MI — Mitigation",
                "description": "Execute response plan to contain the incident",
                "applicable": True,
                "evidence": "Containment measures deployed",
            },
            {
                "function": "RECOVER (RC)",
                "category": "RC.RP — Recovery Planning",
                "description": "Execute recovery processes to restore systems",
                "applicable": True,
                "evidence": "Recovery procedures initiated",
            },
        ]
        return mappings

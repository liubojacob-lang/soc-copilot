"""Unit tests for ReportExportService and compliance mapping."""

from pathlib import Path
from unittest.mock import patch

import pytest

from services.report_export_service import ReportExportService


@pytest.fixture
def sample_report_data():
    return {
        "title": "Data Exfiltration Incident Report",
        "incident_type": "data_leak",
        "severity": "critical",
        "summary": "Unauthorized transfer of sensitive database records detected.",
        "affected_systems": ["srv-db-01", "srv-app-02"],
        "timeline": [
            {"time": "2026-09-21 10:00:00", "description": "Abnormal outbound traffic detected"},
            {"time": "2026-09-21 10:05:00", "description": "Host isolated by automated playbook"},
        ],
        "iocs": ["198.51.100.24", "bad-exfil.net"],
        "recommendations": [
            "Rotate all database credentials",
            "Enable strict egress firewall filtering",
        ],
    }


def test_weasyprint_check():
    svc = ReportExportService()
    assert isinstance(svc._weasyprint_available, bool)


def test_template_path_resolution():
    svc = ReportExportService()
    # Nonexistent template
    assert svc._get_template_path("nonexistent_template_123.html") is None

    # Real template fallback or fallback_html
    fallback = svc._fallback_html({"title": "Test Report", "body": "Report details"})
    assert "<!DOCTYPE html>" in fallback
    assert "Test Report" in fallback


def test_compliance_mappings(sample_report_data):
    # ISO 27001 mapping
    iso_controls = ReportExportService._map_iso27001_controls(sample_report_data)
    assert len(iso_controls) > 0
    control_ids = [c["control_id"] for c in iso_controls]
    assert any("A.16" in cid for cid in control_ids)

    # GDPR mapping
    gdpr_articles = ReportExportService._map_gdpr_articles(sample_report_data)
    assert len(gdpr_articles) > 0
    articles = [g["article"] for g in gdpr_articles]
    assert any("Art. 33" in a for a in articles)

    # NIST CSF mapping
    nist_controls = ReportExportService._map_nist_csf(sample_report_data)
    assert len(nist_controls) > 0
    functions = [n["function"] for n in nist_controls]
    assert any("RESPOND" in f for f in functions)


@pytest.mark.asyncio
async def test_export_html_and_fallback(sample_report_data):
    svc = ReportExportService()

    # Export with fallback template
    html = await svc.export_html(sample_report_data, template_name="nonexistent.html")
    assert "<!DOCTYPE html>" in html
    assert "Data Exfiltration Incident Report" in html


@pytest.mark.asyncio
async def test_export_pdf_fallback_and_generators(sample_report_data):
    svc = ReportExportService()

    # When weasyprint is not available or mock template
    with patch.object(svc, "_get_template_path", return_value=Path("/dummy/incident.html")):
        with patch.object(svc, "_render_template", return_value="<html>Rendered HTML</html>"):
            # 1. Fallback when weasyprint is disabled
            svc._weasyprint_available = False
            pdf_bytes = await svc.export_pdf(sample_report_data, template_name="incident.html")
            assert pdf_bytes == b"<html>Rendered HTML</html>"

            # 2. ISO 27001 report generator
            iso_bytes = await svc.generate_iso27001_report(sample_report_data)
            assert len(iso_bytes) > 0

            # 3. GDPR report generator
            gdpr_bytes = await svc.generate_gdpr_report(sample_report_data)
            assert len(gdpr_bytes) > 0

            # 4. NIST report generator
            nist_bytes = await svc.generate_nist_report(sample_report_data)
            assert len(nist_bytes) > 0

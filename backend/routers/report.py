"""Report generation API endpoint."""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel
from schemas.report import ReportGenerationRequest, ReportGenerationResponse
from services.report_service import ReportService

logger = get_logger(__name__)
router = APIRouter(tags=["report"])


@router.post("/api/v1/generate-report", response_model=ReportGenerationResponse)
async def generate_report(
    request: ReportGenerationRequest,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> ReportGenerationResponse:
    """Generate report templates from alert analysis.

    Args:
        request: Report generation request
        session: Database session

    Returns:
        Report generation response with three templates
    """
    request_id = str(uuid.uuid4())[:8]
    logger.info(f"Received report generation request: {request_id}")

    try:
        service = ReportService(session=session)
        result = await service.generate(
            request.alert_json,
            request.additional_notes,
        )
        return result
    except Exception as e:
        logger.error(f"Report generation error: {e!s}")
        raise HTTPException(status_code=500, detail="Report generation failed")

@router.post("/api/v1/reports/{report_id}/export")
async def export_report_pdf(
    report_id: str,
    format: str | None = Query(default="pdf", description="Export format: pdf, html"),
    template: str | None = Query(default="incident_report", description="Template: incident_report, iso27001, gdpr, nist"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Export a report as PDF or HTML using Jinja2 templates.

    Supported templates:
    - incident_report: Standard security incident report
    - iso27001: ISO 27001:2022 compliance report
    - gdpr: GDPR data breach compliance report
    - nist: NIST CSF 2.0 compliance report

    Format: pdf (default), html
    """
    from fastapi.responses import Response
    from services.report_export_service import ReportExportService

    try:
        # Load report data from history
        from services.history_service import HistoryService
        history_service = HistoryService(session)
        history_entry = await history_service.get_by_request_id(report_id)

        if not history_entry:
            raise HTTPException(status_code=404, detail=f"Report {report_id} not found")

        report_data = {
            "report_id": report_id,
            "title": history_entry.get("title", "Security Incident Report"),
            "description": history_entry.get("output_markdown", ""),
            "alert_data": history_entry.get("input_text", ""),
            "generated_at": history_entry.get("created_at", ""),
        }

        svc = ReportExportService()
        template_map = {
            "iso27001": "compliance_iso27001.html",
            "gdpr": "compliance_gdpr.html",
            "nist": "compliance_nist.html",
            "incident_report": "incident_report.html",
        }
        template_file = template_map.get(template, template_map["incident_report"])

        if format == "html":
            html_content = await svc.export_html(report_data, template_file)
            return Response(
                content=html_content,
                media_type="text/html",
                headers={{"Content-Disposition": f"inline; filename=report-{report_id}.html"}},
            )

        pdf_bytes = await svc.export_pdf(report_data, template_file)
        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="PDF generation failed or WeasyPrint not installed")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={{"Content-Disposition": f"attachment; filename=report-{report_id}.pdf"}},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report export failed: {e}")
        raise HTTPException(status_code=500, detail=f"Report export failed: {e!s}")


@router.post("/api/v1/reports/compliance/{framework}")
async def generate_compliance_report(
    framework: str,
    report_data: dict,
    format: str | None = Query(default="pdf", description="Export format: pdf, html"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Generate a compliance-specific report.

    Frameworks: iso27001, gdpr, nist

    Request body should contain:
    - title: Report title
    - description: Incident description
    - summary: Executive summary
    - severity: Incident severity
    - iocs: [{{"type": "...", "value": "...", "severity": "..."}}]
    - timeline: [{{"time": "...", "description": "..."}}]
    - response_measures: [{{"type": "...", "description": "..."}}]
    - containment/eradication/recovery: Response phase descriptions (optional)
    - lessons_learned: Post-incident review (optional)
    - recommendations: ["..."] (optional)
    """
    from fastapi.responses import Response
    from services.report_export_service import ReportExportService

    try:
        svc = ReportExportService()

        if framework == "iso27001":
            pdf_bytes = await svc.generate_iso27001_report(report_data)
        elif framework == "gdpr":
            pdf_bytes = await svc.generate_gdpr_report(report_data)
        elif framework == "nist":
            pdf_bytes = await svc.generate_nist_report(report_data)
        else:
            raise HTTPException(status_code=400, detail=f"Unknown framework: {{framework}}")

        if not pdf_bytes:
            raise HTTPException(status_code=500, detail="PDF generation failed")

        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={{"Content-Disposition": f"attachment; filename={{framework}}-report.pdf"}},
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Compliance report generation failed: {{e}}")
        raise HTTPException(status_code=500, detail=f"Compliance report failed: {{e!s}}")

"""Report generation service with history tracking."""

import json

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from schemas.report import ReportGenerationResponse
from services.history_service import HistoryService
from services.llm_retry import get_llm_retry_service

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are a SOC report writer. Generate professional security incident documentation.
Output MUST be valid JSON with three fields.
Templates should use Markdown formatting.

Security guidelines:
- Focus on defensive and investigative actions
- Include evidence collection steps
- Suggest verification procedures
- Never suggest: log deletion, audit disabling, evidence destruction"""


class ReportService:
    """Service for report generation."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        """Initialize report service.

        Args:
            session: Optional database session for history tracking
        """
        self.session = session
        self.history_service = HistoryService(session) if session else None
        self.llm_service = get_llm_retry_service()

    async def generate(
        self,
        alert_json: str,
        additional_notes: str | None = None,
        save_history: bool = True,
    ) -> ReportGenerationResponse:
        """Generate report templates from alert analysis.

        Args:
            alert_json: JSON string from analyzer output
            additional_notes: Optional user notes
            save_history: Whether to save to history

        Returns:
            Report generation response
        """
        logger.info("Generating report templates")

        try:
            alert_data = json.loads(alert_json)
        except json.JSONDecodeError:
            alert_data = {}
            logger.warning("Invalid alert JSON provided")

        notes_text = (
            f"\n\nAdditional Notes:\n{additional_notes}" if additional_notes else ""
        )

        prompt = f"""Based on this alert analysis, generate three report templates:

Alert Data:
{json.dumps(alert_data, indent=2, ensure_ascii=False)}{notes_text}

Generate:
1. ticket_template: Incident ticket format (title, description, severity, next steps)
2. daily_report_template: Daily SOC report summary format
3. postmortem_template: Post-incident review format

Each template should be professional Markdown with:
- Clear sections and headers
- Action items with verification steps
- Evidence collection procedures
- Timeline if applicable"""

        result, model_used, degraded = await self.llm_service.generate_structured(
            prompt=prompt,
            response_class=ReportGenerationResponse,
        )

        logger.info(f"Report generation complete, degraded={degraded}")

        # Save to history if session available
        if save_history and self.history_service:
            await self.history_service.create_history(
                module="report",
                input_text=f"Alert: {alert_json[:200]}...",
                output_json=result.model_dump(),
                output_markdown=self._format_as_markdown(result),
                extracted_iocs={},
                tags={
                    "has_notes": bool(additional_notes),
                },
                request_id=result.request_id,
                model_used=model_used,
                degraded=degraded,
                error_reason=result.error_reason,
            )

        return result

    def _format_as_markdown(self, result: ReportGenerationResponse) -> str:
        """Format result as markdown.

        Args:
            result: Report generation result

        Returns:
            Markdown string
        """
        lines = [
            "# Report Templates",
            "",
            "## Incident Ticket",
            "",
            result.ticket_template,
            "",
            "---",
            "",
            "## Daily Report",
            "",
            result.daily_report_template,
            "",
            "---",
            "",
            "## Postmortem",
            "",
            result.postmortem_template,
        ]

        if result.degraded:
            lines.extend(
                [
                    "",
                    "---",
                    f"*⚠️ Degraded mode: {result.error_reason or 'Unknown error'}*",
                ]
            )

        return "\n".join(lines)

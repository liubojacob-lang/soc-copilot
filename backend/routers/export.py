"""Data export router for SOC Copilot.

Supports exporting audit logs, reports, and other data in multiple formats:
- JSON (default, for API integration)
- CSV (for spreadsheet analysis)
- XLSX (for business reporting)
"""

import csv
import io
import json
from datetime import datetime

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel
from repositories.audit_repository import AuditRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/export", tags=["Export"])


# Export format enum
class ExportFormat:
    JSON = "json"
    CSV = "csv"
    XLSX = "xlsx"


def get_content_type(format: str) -> str:
    """Get MIME type for export format."""
    types = {
        ExportFormat.JSON: "application/json",
        ExportFormat.CSV: "text/csv",
        ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    }
    return types.get(format, "application/octet-stream")


def audit_log_to_dict(log) -> dict:
    """Convert audit log model to dictionary."""
    return {
        "id": log.id,
        "user_id": log.user_id,
        "action": log.action,
        "method": log.method,
        "path": log.path,
        "status_code": log.status_code,
        "target_type": log.target_type,
        "target_id": log.target_id,
        "ip_address": log.ip_address,
        "user_agent": log.user_agent,
        "duration_ms": log.duration_ms,
        "extra_json": log.extra_json,
        "created_at": log.created_at,
    }


def generate_csv(data: list[dict], columns: list[str]) -> str:
    """Generate CSV content from data."""
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    for row in data:
        # Handle nested JSON
        if "extra_json" in row and isinstance(row["extra_json"], dict):
            row["extra_json"] = json.dumps(row["extra_json"])
        writer.writerow(row)
    return output.getvalue()


async def generate_xlsx(data: list[dict], columns: list[str]) -> bytes:
    """Generate XLSX content from data.

    Note: Requires openpyxl package. Falls back to CSV if not available.
    """
    try:
        from openpyxl import Workbook
        from openpyxl.styles import Alignment, Font, PatternFill

        wb = Workbook()
        ws = wb.active
        ws.title = "Export Data"

        # Header style
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(
            start_color="4472C4", end_color="4472C4", fill_type="solid"
        )
        header_alignment = Alignment(horizontal="center", vertical="center")

        # Write headers
        for col_idx, col_name in enumerate(columns, 1):
            cell = ws.cell(row=1, column=col_idx, value=col_name)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = header_alignment

        # Write data
        for row_idx, row_data in enumerate(data, 2):
            for col_idx, col_name in enumerate(columns, 1):
                value = row_data.get(col_name, "")
                # Handle nested JSON
                if isinstance(value, dict):
                    value = json.dumps(value)
                ws.cell(row=row_idx, column=col_idx, value=value)

        # Auto-adjust column widths
        for col_idx, col_name in enumerate(columns, 1):
            max_length = len(str(col_name))
            for row_idx in range(2, len(data) + 2):
                cell_value = ws.cell(row=row_idx, column=col_idx).value
                if cell_value:
                    max_length = max(max_length, len(str(cell_value)) + 2)
            ws.column_dimensions[ws.cell(row=1, column=col_idx).column_letter].width = (
                min(max_length, 50)
            )

        # Save to bytes
        output = io.BytesIO()
        wb.save(output)
        output.seek(0)
        return output.getvalue()

    except ImportError:
        logger.warning("openpyxl not installed, falling back to CSV")
        raise ImportError("openpyxl package required for XLSX export")


@router.get("/audit-logs", summary="Export audit logs")
async def export_audit_logs(
    format: str = Query(
        default=ExportFormat.JSON, description="Export format: json, csv, xlsx"
    ),
    user_id: str | None = Query(default=None, description="Filter by user ID"),
    action: str | None = Query(
        default=None, description="Filter by action (supports wildcards)"
    ),
    path: str | None = Query(
        default=None, description="Filter by path (supports wildcards)"
    ),
    status_code: str | None = Query(
        default=None, description="Filter by status code (2xx, 4xx, 5xx, etc.)"
    ),
    date_from: str | None = Query(
        default=None, description="Start date (ISO format)"
    ),
    date_to: str | None = Query(default=None, description="End date (ISO format)"),
    limit: int = Query(
        default=10000, ge=1, le=50000, description="Maximum records to export"
    ),
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Export audit logs in various formats.

    **Formats:**
    - `json`: JSON array (default)
    - `csv`: Comma-separated values
    - `xlsx`: Excel spreadsheet (requires openpyxl)

    **Status Code Filters:**
    - `success` or `2xx`: All successful responses
    - `4xx`: Client errors
    - `5xx`: Server errors
    - `error` or `4xx+5xx`: All errors

    **Permissions:**
    - Requires authenticated user
    - Admin users can export all logs
    - Non-admin users can only export their own logs
    """
    # Authorization check
    if current_user.role != "admin" and user_id and user_id != current_user.id:
        logger.warning(
            "Non-admin user attempted to export other user's logs",
            extra={"user_id": current_user.id, "target_user_id": user_id},
        )
        user_id = current_user.id  # Force to own logs

    # Non-admin can only see their own logs
    if current_user.role != "admin":
        user_id = current_user.id

    # Fetch data
    repo = AuditRepository(session)
    logs, total = await repo.list(
        skip=0,
        limit=limit,
        user_id=user_id,
        action=action,
        path=path,
        status_code=status_code,
        date_from=date_from,
        date_to=date_to,
    )

    # Convert to dict
    data = [audit_log_to_dict(log) for log in logs]

    # Define columns for export
    columns = [
        "id",
        "user_id",
        "action",
        "method",
        "path",
        "status_code",
        "target_type",
        "target_id",
        "ip_address",
        "user_agent",
        "duration_ms",
        "created_at",
    ]

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"audit_logs_{timestamp}"

    logger.info(
        "Exporting audit logs",
        extra={
            "user_id": current_user.id,
            "format": format,
            "record_count": len(data),
            "filters": {
                "user_id": user_id,
                "action": action,
                "path": path,
                "status_code": status_code,
            },
        },
    )

    # Return based on format
    if format == ExportFormat.CSV:
        content = generate_csv(data, columns)
        return Response(
            content=content,
            media_type=get_content_type(ExportFormat.CSV),
            headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
        )

    elif format == ExportFormat.XLSX:
        try:
            content = await generate_xlsx(data, columns)
            return Response(
                content=content,
                media_type=get_content_type(ExportFormat.XLSX),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}.xlsx"'
                },
            )
        except ImportError:
            # Fall back to CSV
            content = generate_csv(data, columns)
            return Response(
                content=content,
                media_type=get_content_type(ExportFormat.CSV),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}.csv"'
                },
            )

    else:  # JSON
        return Response(
            content=json.dumps(data, indent=2, default=str),
            media_type=get_content_type(ExportFormat.JSON),
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )


@router.get("/playbook-runs", summary="Export playbook run history")
async def export_playbook_runs(
    format: str = Query(
        default=ExportFormat.JSON, description="Export format: json, csv, xlsx"
    ),
    playbook_id: str | None = Query(
        default=None, description="Filter by playbook ID"
    ),
    status: str | None = Query(default=None, description="Filter by status"),
    date_from: str | None = Query(
        default=None, description="Start date (ISO format)"
    ),
    date_to: str | None = Query(default=None, description="End date (ISO format)"),
    limit: int = Query(
        default=10000, ge=1, le=50000, description="Maximum records to export"
    ),
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Export playbook run history in various formats.

    **Permissions:**
    - Requires authenticated user
    - Admin users can export all runs
    - Non-admin users can only export their own runs
    """
    from sqlalchemy import select

    from models.playbook_run import PlaybookRunModel

    # Build query
    query = select(PlaybookRunModel)

    # Authorization filter
    if current_user.role != "admin":
        query = query.where(PlaybookRunModel.triggered_by == current_user.id)

    # Apply filters
    if playbook_id:
        query = query.where(PlaybookRunModel.playbook_id == playbook_id)
    if status:
        query = query.where(PlaybookRunModel.status == status)
    if date_from:
        query = query.where(PlaybookRunModel.created_at >= date_from)
    if date_to:
        query = query.where(PlaybookRunModel.created_at <= date_to)

    query = query.order_by(PlaybookRunModel.created_at.desc()).limit(limit)

    result = await session.execute(query)
    runs = list(result.scalars().all())

    # Convert to dict
    data = []
    for run in runs:
        data.append(
            {
                "id": run.id,
                "playbook_id": run.playbook_id,
                "playbook_name": run.playbook_name,
                "status": run.status,
                "triggered_by": run.triggered_by,
                "trigger_type": run.trigger_type,
                "alert_id": run.alert_id,
                "started_at": run.started_at,
                "completed_at": run.completed_at,
                "error_message": run.error_message,
                "created_at": run.created_at,
            }
        )

    # Define columns
    columns = [
        "id",
        "playbook_id",
        "playbook_name",
        "status",
        "triggered_by",
        "trigger_type",
        "alert_id",
        "started_at",
        "completed_at",
        "error_message",
        "created_at",
    ]

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"playbook_runs_{timestamp}"

    logger.info(
        "Exporting playbook runs",
        extra={
            "user_id": current_user.id,
            "format": format,
            "record_count": len(data),
        },
    )

    # Return based on format
    if format == ExportFormat.CSV:
        content = generate_csv(data, columns)
        return Response(
            content=content,
            media_type=get_content_type(ExportFormat.CSV),
            headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
        )

    elif format == ExportFormat.XLSX:
        try:
            content = await generate_xlsx(data, columns)
            return Response(
                content=content,
                media_type=get_content_type(ExportFormat.XLSX),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}.xlsx"'
                },
            )
        except ImportError:
            content = generate_csv(data, columns)
            return Response(
                content=content,
                media_type=get_content_type(ExportFormat.CSV),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}.csv"'
                },
            )

    else:  # JSON
        return Response(
            content=json.dumps(data, indent=2, default=str),
            media_type=get_content_type(ExportFormat.JSON),
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )


@router.get("/alerts", summary="Export alert history")
async def export_alerts(
    format: str = Query(
        default=ExportFormat.JSON, description="Export format: json, csv, xlsx"
    ),
    severity: str | None = Query(default=None, description="Filter by severity"),
    status: str | None = Query(default=None, description="Filter by status"),
    date_from: str | None = Query(
        default=None, description="Start date (ISO format)"
    ),
    date_to: str | None = Query(default=None, description="End date (ISO format)"),
    limit: int = Query(
        default=10000, ge=1, le=50000, description="Maximum records to export"
    ),
    current_user: UserModel = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Export alert history in various formats.

    **Permissions:**
    - Requires authenticated user
    """
    from sqlalchemy import select

    from models.security_alert import SecurityAlert

    # Build query
    query = select(SecurityAlert).where(SecurityAlert.deleted_at.is_(None))

    # Apply filters
    if severity:
        query = query.where(SecurityAlert.severity == severity)
    if status:
        query = query.where(SecurityAlert.status == status)
    if date_from:
        query = query.where(SecurityAlert.created_at >= date_from)
    if date_to:
        query = query.where(SecurityAlert.created_at <= date_to)

    query = query.order_by(SecurityAlert.created_at.desc()).limit(limit)

    result = await session.execute(query)
    alerts = list(result.scalars().all())

    # Convert to dict
    data = []
    for alert in alerts:
        data.append(
            {
                "id": alert.id,
                "source": alert.source,
                "title": alert.title,
                "severity": alert.severity,
                "status": alert.status,
                "source_ip": alert.source_ip,
                "assigned_to": alert.assigned_to,
                "created_at": alert.created_at,
                "updated_at": alert.updated_at,
            }
        )

    # Define columns
    columns = [
        "id",
        "source",
        "title",
        "severity",
        "status",
        "source_ip",
        "assigned_to",
        "created_at",
        "updated_at",
    ]

    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"alerts_{timestamp}"

    logger.info(
        "Exporting alerts",
        extra={
            "user_id": current_user.id,
            "format": format,
            "record_count": len(data),
        },
    )

    # Return based on format
    if format == ExportFormat.CSV:
        content = generate_csv(data, columns)
        return Response(
            content=content,
            media_type=get_content_type(ExportFormat.CSV),
            headers={"Content-Disposition": f'attachment; filename="{filename}.csv"'},
        )

    elif format == ExportFormat.XLSX:
        try:
            content = await generate_xlsx(data, columns)
            return Response(
                content=content,
                media_type=get_content_type(ExportFormat.XLSX),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}.xlsx"'
                },
            )
        except ImportError:
            content = generate_csv(data, columns)
            return Response(
                content=content,
                media_type=get_content_type(ExportFormat.CSV),
                headers={
                    "Content-Disposition": f'attachment; filename="{filename}.csv"'
                },
            )

    else:  # JSON
        return Response(
            content=json.dumps(data, indent=2, default=str),
            media_type=get_content_type(ExportFormat.JSON),
            headers={"Content-Disposition": f'attachment; filename="{filename}.json"'},
        )

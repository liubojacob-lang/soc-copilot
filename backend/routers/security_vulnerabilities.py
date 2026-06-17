"""Security vulnerability management API endpoints."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user, require_admin
from middleware.trace_middleware import get_trace_id
from models.security_vulnerability import (
    VulnerabilitySeverity,
    VulnerabilityStatus,
    VulnerabilityType,
)
from models.user import UserModel
from schemas.common import paginated_response, success_response
from services.security.security_vulnerability_service import (
    get_security_vulnerability_service,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/security/vulnerabilities",
    tags=["security-vulnerabilities"],
    responses={404: {"description": "Not found"}},
)


@router.post("", response_model=dict)
async def create_vulnerability(
    title: str,
    description: str,
    severity: VulnerabilitySeverity,
    vulnerability_type: VulnerabilityType,
    affected_component: str,
    affected_version: str | None = None,
    attack_vector: str | None = None,
    impact: str | None = None,
    reproduction_steps: str | None = None,
    fix_recommendation: str | None = None,
    cve_id: str | None = None,
    cvss_score: float | None = None,
    reference_urls: str | None = None,
    assigned_to: str | None = None,
    current_user: UserModel = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """Create a new security vulnerability."""
    service = get_security_vulnerability_service(db_session)

    vulnerability = await service.create_vulnerability(
        title=title,
        description=description,
        severity=severity,
        vulnerability_type=vulnerability_type,
        affected_component=affected_component,
        affected_version=affected_version,
        attack_vector=attack_vector,
        impact=impact,
        reproduction_steps=reproduction_steps,
        fix_recommendation=fix_recommendation,
        cve_id=cve_id,
        cvss_score=cvss_score,
        reference_urls=reference_urls,
        assigned_to=assigned_to,
        reporter=current_user.username,
    )

    return success_response(
        data={
            "id": vulnerability.id,
            "title": vulnerability.title,
            "status": vulnerability.status.value,
            "severity": vulnerability.severity.value,
        },
        message="Vulnerability created successfully",
        trace_id=get_trace_id(),
    )


@router.get("/{vulnerability_id}", response_model=dict)
async def get_vulnerability(
    vulnerability_id: str,
    current_user: UserModel = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """Get a specific vulnerability by ID."""
    service = get_security_vulnerability_service(db_session)
    vulnerability = await service.get_vulnerability(vulnerability_id)

    if not vulnerability:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vulnerability not found")

    # Get notes
    notes = await service.get_vulnerability_notes(vulnerability_id)

    return success_response(
        data={
            "id": vulnerability.id,
            "title": vulnerability.title,
            "description": vulnerability.description,
            "severity": vulnerability.severity.value,
            "status": vulnerability.status.value,
            "type": vulnerability.vulnerability_type.value,
            "affected_component": vulnerability.affected_component,
            "affected_version": vulnerability.affected_version,
            "attack_vector": vulnerability.attack_vector,
            "impact": vulnerability.impact,
            "reproduction_steps": vulnerability.reproduction_steps,
            "fix_recommendation": vulnerability.fix_recommendation,
            "fix_implementation": vulnerability.fix_implementation,
            "reporter": vulnerability.reporter,
            "reported_at": (
                vulnerability.reported_at.isoformat() if vulnerability.reported_at else None
            ),
            "triaged_at": (
                vulnerability.triaged_at.isoformat() if vulnerability.triaged_at else None
            ),
            "in_progress_at": (
                vulnerability.in_progress_at.isoformat() if vulnerability.in_progress_at else None
            ),
            "fixed_at": (vulnerability.fixed_at.isoformat() if vulnerability.fixed_at else None),
            "verified_at": (
                vulnerability.verified_at.isoformat() if vulnerability.verified_at else None
            ),
            "closed_at": (vulnerability.closed_at.isoformat() if vulnerability.closed_at else None),
            "cve_id": vulnerability.cve_id,
            "cvss_score": vulnerability.cvss_score,
            "reference_urls": vulnerability.reference_urls,
            "assigned_to": vulnerability.assigned_to,
            "last_updated_by": vulnerability.last_updated_by,
            "last_updated_at": vulnerability.last_updated_at.isoformat(),
            "is_public": vulnerability.is_public,
            "is_false_positive": vulnerability.is_false_positive,
            "notes": [
                {
                    "id": note.id,
                    "content": note.content,
                    "author": note.author,
                    "created_at": note.created_at.isoformat(),
                }
                for note in notes
            ],
        },
        trace_id=get_trace_id(),
    )


@router.get("", response_model=dict)
async def list_vulnerabilities(
    severity: VulnerabilitySeverity | None = None,
    status: VulnerabilityStatus | None = None,
    vulnerability_type: VulnerabilityType | None = None,
    affected_component: str | None = None,
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    sort_by: str = Query("reported_at", pattern="^(reported_at|severity|status)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    current_user: UserModel = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """List vulnerabilities with filters."""
    service = get_security_vulnerability_service(db_session)
    vulnerabilities = await service.list_vulnerabilities(
        severity=severity,
        status=status,
        vulnerability_type=vulnerability_type,
        affected_component=affected_component,
        limit=limit,
        offset=offset,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    # Get statistics
    stats = await service.get_vulnerability_statistics()

    vulnerability_items = [
        {
            "id": v.id,
            "title": v.title,
            "severity": v.severity.value,
            "status": v.status.value,
            "type": v.vulnerability_type.value,
            "affected_component": v.affected_component,
            "reported_at": v.reported_at.isoformat(),
            "reporter": v.reporter,
        }
        for v in vulnerabilities
    ]

    return paginated_response(
        items=vulnerability_items,
        total=len(vulnerabilities),
        page=(offset // limit) + 1,
        page_size=limit,
        message="Vulnerabilities retrieved successfully",
        trace_id=get_trace_id(),
    )


@router.put("/{vulnerability_id}", response_model=dict)
async def update_vulnerability(
    vulnerability_id: str,
    title: str | None = None,
    description: str | None = None,
    severity: VulnerabilitySeverity | None = None,
    vulnerability_type: VulnerabilityType | None = None,
    status: VulnerabilityStatus | None = None,
    affected_component: str | None = None,
    affected_version: str | None = None,
    attack_vector: str | None = None,
    impact: str | None = None,
    reproduction_steps: str | None = None,
    fix_recommendation: str | None = None,
    fix_implementation: str | None = None,
    cve_id: str | None = None,
    cvss_score: float | None = None,
    reference_urls: str | None = None,
    assigned_to: str | None = None,
    is_public: bool | None = None,
    current_user: UserModel = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """Update a vulnerability."""
    service = get_security_vulnerability_service(db_session)

    # Prepare update data
    update_data = {}
    if title is not None:
        update_data["title"] = title
    if description is not None:
        update_data["description"] = description
    if severity is not None:
        update_data["severity"] = severity
    if vulnerability_type is not None:
        update_data["vulnerability_type"] = vulnerability_type
    if status is not None:
        update_data["status"] = status
    if affected_component is not None:
        update_data["affected_component"] = affected_component
    if affected_version is not None:
        update_data["affected_version"] = affected_version
    if attack_vector is not None:
        update_data["attack_vector"] = attack_vector
    if impact is not None:
        update_data["impact"] = impact
    if reproduction_steps is not None:
        update_data["reproduction_steps"] = reproduction_steps
    if fix_recommendation is not None:
        update_data["fix_recommendation"] = fix_recommendation
    if fix_implementation is not None:
        update_data["fix_implementation"] = fix_implementation
    if cve_id is not None:
        update_data["cve_id"] = cve_id
    if cvss_score is not None:
        update_data["cvss_score"] = cvss_score
    if reference_urls is not None:
        update_data["reference_urls"] = reference_urls
    if assigned_to is not None:
        update_data["assigned_to"] = assigned_to
    if is_public is not None:
        update_data["is_public"] = is_public

    vulnerability = await service.update_vulnerability(
        vulnerability_id=vulnerability_id,
        updated_by=current_user.username,
        **update_data,
    )

    if not vulnerability:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vulnerability not found")

    return success_response(
        data={
            "id": vulnerability.id,
            "title": vulnerability.title,
            "status": vulnerability.status.value,
            "severity": vulnerability.severity.value,
        },
        message="Vulnerability updated successfully",
        trace_id=get_trace_id(),
    )


@router.post("/{vulnerability_id}/notes", response_model=dict)
async def add_vulnerability_note(
    vulnerability_id: str,
    content: str,
    current_user: UserModel = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """Add a note to a vulnerability."""
    service = get_security_vulnerability_service(db_session)

    # Check if vulnerability exists
    vulnerability = await service.get_vulnerability(vulnerability_id)
    if not vulnerability:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vulnerability not found")

    note = await service.add_vulnerability_note(
        vulnerability_id=vulnerability_id, content=content, author=current_user.username
    )

    return success_response(
        data={
            "id": note.id,
            "content": note.content,
            "author": note.author,
            "created_at": note.created_at.isoformat(),
        },
        message="Note added successfully",
        trace_id=get_trace_id(),
    )


@router.get("/stats/summary", response_model=dict)
async def get_vulnerability_statistics(
    current_user: UserModel = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """Get vulnerability statistics summary."""
    service = get_security_vulnerability_service(db_session)
    stats = await service.get_vulnerability_statistics()

    return success_response(
        data={"statistics": stats, "last_updated": datetime.now(UTC).isoformat()},
        message="Statistics retrieved successfully",
        trace_id=get_trace_id(),
    )


@router.get("/search", response_model=dict)
async def search_vulnerabilities(
    q: str = Query(..., description="Search term"),
    limit: int = Query(50, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
    db_session: AsyncSession = Depends(get_session),
):
    """Search vulnerabilities."""
    service = get_security_vulnerability_service(db_session)
    vulnerabilities = await service.search_vulnerabilities(search_term=q, limit=limit)

    search_results = [
        {
            "id": v.id,
            "title": v.title,
            "severity": v.severity.value,
            "status": v.status.value,
            "affected_component": v.affected_component,
            "reported_at": v.reported_at.isoformat(),
        }
        for v in vulnerabilities
    ]

    return success_response(
        data={
            "vulnerabilities": search_results,
            "total": len(vulnerabilities),
            "search_term": q,
        },
        message="Search completed successfully",
        trace_id=get_trace_id(),
    )


@router.get("/export/{export_format}", response_model=dict)
async def export_vulnerabilities(
    export_format: str = Path(..., pattern="^(json)$"),
    current_user: UserModel = Depends(require_admin),
    db_session: AsyncSession = Depends(get_session),
):
    """Export vulnerabilities in specified format."""
    service = get_security_vulnerability_service(db_session)

    try:
        export_data = await service.export_vulnerabilities(format=format)
        return success_response(
            data={
                "format": format,
                "data": export_data,
                "exported_at": datetime.now(UTC).isoformat(),
            },
            message="Export completed successfully",
            trace_id=get_trace_id(),
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Bad request")

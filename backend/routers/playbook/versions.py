"""Version management, replay, and import/export endpoints.

This module contains endpoints for:
- Publishing playbook definitions
- Version history management
- Restoring previous versions
- Replay functionality
- Import/Export definitions
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.playbook_run import PlaybookRunModel
from models.user import UserModel, UserRole
from repositories.audit_repository import AuditRepository

logger = get_logger(__name__)

router = APIRouter(tags=["playbook-versions"])


# ============================================
# Version Management Endpoints
# ============================================


@router.post("/definitions/{definition_id}/publish")
async def publish_playbook_definition(
    definition_id: str,
    request: dict = None,  # Optional: {"change_note": "..."}
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Publish a draft playbook definition.

    Creates a version snapshot and sets status to published.
    Published definitions cannot be modified.

    - RBAC: admin and analyst can publish
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST]:
        raise HTTPException(
            status_code=403, detail="Only admin and analyst can publish definitions"
        )

    from services.playbook.playbook_version_service import PlaybookVersionService

    version_service = PlaybookVersionService(session)
    change_note = (request or {}).get("change_note") if request else None

    try:
        definition = await version_service.publish_definition(
            definition_id=definition_id,
            change_note=change_note,
            created_by_user_id=current_user.id,
        )

        # Audit log
        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="playbook.publish",
            method="POST",
            path=f"/api/playbook/definitions/{definition_id}/publish",
            status_code=200,
            user_id=current_user.id,
            target_type="playbook_definition",
            target_id=definition_id,
            extra_json={
                "name": definition.name,
                "version_no": definition.current_version_no,
                "change_note": change_note,
            },
        )
        await session.commit()

        return {
            "message": "Playbook definition published successfully",
            "definition_id": definition_id,
            "version_no": definition.current_version_no,
            "status": definition.status,
            "published_at": (
                definition.published_at.isoformat() if definition.published_at else None
            ),
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Bad request")


@router.get("/definitions/{definition_id}/versions")
async def get_playbook_version_history(
    definition_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Get version history for a playbook definition.

    - RBAC: All authenticated users can view version history
    """
    from services.playbook.playbook_version_service import PlaybookVersionService

    version_service = PlaybookVersionService(session)

    try:
        history = await version_service.get_version_history(definition_id)

        return {
            "definition_id": definition_id,
            "versions": [v.model_dump(mode="json") for v in history.versions],
            "total": history.total,
            "current_version_no": history.current_version_no,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/definitions/{definition_id}/restore/{version_no}")
async def restore_playbook_definition_version(
    definition_id: str,
    version_no: int,
    request: dict = None,  # Optional: {"change_note": "..."}
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Restore a playbook definition from a historical version.

    Creates a new draft with content from the specified version.
    Original version is preserved in history.

    - RBAC: admin and analyst can restore versions
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST]:
        raise HTTPException(
            status_code=403, detail="Only admin and analyst can restore versions"
        )

    from services.playbook.playbook_version_service import PlaybookVersionService

    version_service = PlaybookVersionService(session)
    change_note = (request or {}).get("change_note") if request else None

    try:
        definition = await version_service.restore_from_version(
            definition_id=definition_id,
            version_no=version_no,
            change_note=change_note or f"Restored from version {version_no}",
            created_by_user_id=current_user.id,
        )

        # Audit log
        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="playbook.restore",
            method="POST",
            path=f"/api/playbook/definitions/{definition_id}/restore/{version_no}",
            status_code=200,
            user_id=current_user.id,
            target_type="playbook_definition",
            target_id=definition_id,
            extra_json={
                "name": definition.name,
                "from_version_no": version_no,
                "new_version_no": definition.current_version_no,
            },
        )
        await session.commit()

        return {
            "message": "Playbook definition restored successfully",
            "definition_id": definition_id,
            "restored_from_version": version_no,
            "new_version_no": definition.current_version_no,
            "status": definition.status,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Bad request")


# ============================================
# Replay Endpoints
# ============================================


@router.post("/runs/{run_id}/replay")
async def replay_playbook_run(
    run_id: str,
    request: dict,  # {"mode": "dry_run"|"apply", "override_context": {...}}
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Replay a playbook run with historical input.

    Creates a new run with the same input context and definition.
    Optionally allows overriding context values.

    - RBAC: All users can replay their own runs; admin/auditor can replay any run

    Args:
        run_id: Original run ID to replay
        request: {"mode": "dry_run"|"apply", "override_context": {...}}

    Returns:
        New replay run details
    """
    # Check apply mode permission
    mode = request.get("mode", "dry_run")
    if mode == "apply" and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403,
            detail="Playbook replay with apply mode requires admin role",
        )

    from services.playbook.playbook_replay_service import get_replay_service

    # Check if user can replay this run
    stmt = select(PlaybookRunModel).where(PlaybookRunModel.id == run_id)
    result = await session.execute(stmt)
    original_run = result.scalar_one_or_none()

    if not original_run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Check permissions
    if (
        original_run.created_by_user_id != current_user.id
        and current_user.role not in [UserRole.ADMIN, UserRole.AUDITOR]
    ):
        raise HTTPException(
            status_code=403,
            detail="You can only replay your own runs",
        )

    replay_service = get_replay_service(session)

    try:
        replay_result = await replay_service.replay_run(
            run_id=run_id,
            mode=mode,
            override_context=request.get("override_context"),
            created_by_user_id=current_user.id,
        )

        # Audit log
        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="playbook.replay",
            method="POST",
            path=f"/api/playbook/runs/{run_id}/replay",
            status_code=200,
            user_id=current_user.id,
            target_type="playbook_run",
            target_id=replay_result.run_id,
            extra_json={
                "original_run_id": run_id,
                "mode": mode,
            },
        )
        await session.commit()

        return {
            "run_id": replay_result.run_id,
            "original_run_id": replay_result.original_run_id,
            "mode": replay_result.mode,
            "status": replay_result.status,
            "message": replay_result.message,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Bad request")


@router.get("/runs/{run_id}/replay-chain")
async def get_playbook_replay_chain(
    run_id: str,
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Get the replay chain for a playbook run.

    Traverses from the root run to the latest replay.

    - RBAC: All authenticated users can view replay chains
    """
    from services.playbook.playbook_replay_service import get_replay_service

    replay_service = get_replay_service(session)

    try:
        chain = await replay_service.get_replay_chain(run_id)

        return {
            "root_run_id": chain.root_run_id,
            "chain": [node.model_dump(mode="json") for node in chain.chain],
            "total": chain.total,
            "depth": chain.depth,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found")


# ============================================
# Import/Export Endpoints
# ============================================


@router.get("/definitions/{definition_id}/export")
async def export_playbook_definition(
    definition_id: str,
    format: str = Query("json", pattern="^(json|yaml)$", description="Export format"),
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Export a playbook definition to JSON or YAML.

    - RBAC: All authenticated users can export definitions

    Args:
        definition_id: ID of the definition to export
        format: Export format ('json' or 'yaml')

    Returns:
        Export data with content and mime_type
    """
    from services.playbook.playbook_import_export_service import (
        get_import_export_service,
    )

    export_service = get_import_export_service(session)

    try:
        content, mime_type = await export_service.export_definition(
            definition_id=definition_id, format=format
        )

        # Audit log
        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="playbook.export",
            method="GET",
            path=f"/api/playbook/definitions/{definition_id}/export",
            status_code=200,
            user_id=current_user.id,
            target_type="playbook_definition",
            target_id=definition_id,
            extra_json={"format": format},
        )
        await session.commit()

        return {
            "definition_id": definition_id,
            "format": format,
            "content": content,
            "mime_type": mime_type,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail="Not found")


@router.post("/definitions/import")
async def import_playbook_definition(
    request: dict,  # {"format": "json"|"yaml", "content": "...", "name": "...", "publish": bool}
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> dict:
    """Import a playbook definition from JSON or YAML.

    Creates a new draft definition (or published if publish=true).

    - RBAC: admin and analyst can import definitions

    Args:
        request: {
            "format": "json"|"yaml",
            "content": "...",
            "name": "...",  # Optional: override name
            "publish": false  # Optional: auto-publish
        }

    Returns:
        Imported definition details
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.ANALYST]:
        raise HTTPException(
            status_code=403, detail="Only admin and analyst can import definitions"
        )

    from services.playbook.playbook_import_export_service import (
        get_import_export_service,
    )

    import_service = get_import_export_service(session)

    format = request.get("format", "json")
    content = request.get("content", "")
    name_override = request.get("name")
    publish = request.get("publish", False)

    if not content:
        raise HTTPException(status_code=400, detail="Content is required")

    try:
        result = await import_service.import_definition(
            content=content,
            format=format,
            name_override=name_override,
            publish=publish,
            created_by_user_id=current_user.id,
        )

        # Audit log
        audit_repo = AuditRepository(session)
        await audit_repo.create(
            action="playbook.import",
            method="POST",
            path="/api/playbook/definitions/import",
            status_code=200,
            user_id=current_user.id,
            target_type="playbook_definition",
            target_id=result.definition_id,
            extra_json={
                "name": result.name,
                "version": result.version,
                "format": format,
            },
        )
        await session.commit()

        return {
            "definition_id": result.definition_id,
            "name": result.name,
            "version": result.version,
            "status": result.status,
            "message": result.message,
        }
    except ValueError:
        raise HTTPException(status_code=400, detail="Bad request")

"""Router for trigger CRUD operations."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel, UserRole
from repositories.playbook_definition_repository import PlaybookDefinitionRepository
from repositories.trigger_repository import TriggerRepository
from schemas.trigger import (
    CronTriggerCreate,
    CronTriggerResponse,
    SecretRegenerateResponse,
    TriggerInvocationOut,
    TriggerListResponse,
    TriggerOut,
    TriggerUpdate,
    TriggerWithDefinition,
    WebhookTriggerCreate,
    WebhookTriggerResponse,
)
from services.trigger_service import TriggerService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/triggers", tags=["triggers"])


# Helper dependencies that can be reused
def require_admin_or_analyst(
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> UserModel:
    """Require admin or analyst role."""
    if current_user.role not in (UserRole.ADMIN, UserRole.ANALYST):
        raise HTTPException(status_code=403, detail="Permission denied")
    return current_user


def require_any_role_internal(
    current_user: Annotated[UserModel, Depends(get_current_user)],
) -> UserModel:
    """Require any authenticated role (admin, analyst, or auditor)."""
    return current_user


@router.get("", response_model=TriggerListResponse)
async def list_triggers(
    trigger_type: Annotated[
        str | None, Query(description="Filter by trigger type")
    ] = None,
    is_active: Annotated[
        bool | None, Query(description="Filter by active status")
    ] = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 50,
    current_user: Annotated[UserModel, Depends(require_any_role_internal)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> TriggerListResponse:
    """List all triggers with optional filters."""
    trigger_repo = TriggerRepository(session)
    items, total = await trigger_repo.list_all(
        trigger_type=trigger_type,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )

    # Convert to response format with webhook URLs
    from core.config import settings

    base_url = getattr(settings, "base_url", "http://localhost:8000")

    trigger_outs = []
    for trigger in items:
        trigger_dict = TriggerOut.model_validate(trigger).model_dump()
        # Add webhook URL for webhook triggers
        if trigger.type == "webhook":
            trigger_dict["webhook_url"] = f"{base_url}/api/webhooks/{trigger.id}"
            trigger_dict["secret_prefix"] = (
                (trigger.secret or "")[:10] + "***" if trigger.secret else None
            )
        # Add cron expression for cron triggers
        if trigger.type == "cron":
            trigger_dict["cron_expr"] = trigger.cron_expr
        trigger_outs.append(TriggerOut(**trigger_dict))

    return TriggerListResponse(
        items=trigger_outs,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{trigger_id}", response_model=TriggerWithDefinition)
async def get_trigger(
    trigger_id: str,
    current_user: Annotated[UserModel, Depends(require_any_role_internal)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> TriggerWithDefinition:
    """Get trigger details by ID."""
    trigger_repo = TriggerRepository(session)
    definition_repo = PlaybookDefinitionRepository(session)

    trigger = await trigger_repo.get_by_id(trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    # Get definition name
    definition = await definition_repo.get_by_id(trigger.definition_id)
    if not definition:
        raise HTTPException(
            status_code=404, detail="Associated playbook definition not found"
        )

    from core.config import settings

    base_url = getattr(settings, "base_url", "http://localhost:8000")

    trigger_dict = TriggerOut.model_validate(trigger).model_dump()
    if trigger.type == "webhook":
        trigger_dict["webhook_url"] = f"{base_url}/api/webhooks/{trigger.id}"
        trigger_dict["secret_prefix"] = (
            (trigger.secret or "")[:10] + "***" if trigger.secret else None
        )
    if trigger.type == "cron":
        trigger_dict["cron_expr"] = trigger.cron_expr

    return TriggerWithDefinition(
        **trigger_dict,
        definition_name=definition.name,
    )


@router.post("/webhook", response_model=WebhookTriggerResponse)
async def create_webhook_trigger(
    data: WebhookTriggerCreate,
    current_user: Annotated[UserModel, Depends(require_admin_or_analyst)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> WebhookTriggerResponse:
    """Create a new webhook trigger."""
    # Verify definition exists
    definition_repo = PlaybookDefinitionRepository(session)
    definition = await definition_repo.get_by_id(data.definition_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Playbook definition not found")

    trigger_service = TriggerService(session)
    trigger = await trigger_service.create_webhook_trigger(
        definition_id=data.definition_id,
        name=data.name,
        config=data.config,
        is_active=data.is_active,
        created_by_user_id=current_user.id,
    )

    from core.config import settings

    base_url = getattr(settings, "base_url", "http://localhost:8000")

    return WebhookTriggerResponse(
        id=trigger.id,
        definition_id=trigger.definition_id,
        type="webhook",
        name=trigger.name,
        config=trigger.config_json,
        secret=trigger.secret,
        webhook_url=f"{base_url}/api/webhooks/{trigger.id}",
        is_active=trigger.is_active,
        created_at=trigger.created_at,
        updated_at=trigger.updated_at,
        last_triggered_at=trigger.last_triggered_at,
    )


@router.post("/cron", response_model=CronTriggerResponse)
async def create_cron_trigger(
    data: CronTriggerCreate,
    current_user: Annotated[UserModel, Depends(require_admin_or_analyst)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> CronTriggerResponse:
    """Create a new cron trigger."""
    # Verify definition exists
    definition_repo = PlaybookDefinitionRepository(session)
    definition = await definition_repo.get_by_id(data.definition_id)
    if not definition:
        raise HTTPException(status_code=404, detail="Playbook definition not found")

    trigger_service = TriggerService(session)
    try:
        trigger = await trigger_service.create_cron_trigger(
            definition_id=data.definition_id,
            cron_expr=data.cron_expr,
            name=data.name,
            config=data.config,
            is_active=data.is_active,
            created_by_user_id=current_user.id,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Bad request")

    return CronTriggerResponse(
        id=trigger.id,
        definition_id=trigger.definition_id,
        type="cron",
        name=trigger.name,
        config=trigger.config_json,
        cron_expr=trigger.cron_expr,
        is_active=trigger.is_active,
        created_at=trigger.created_at,
        updated_at=trigger.updated_at,
        last_triggered_at=trigger.last_triggered_at,
    )


@router.put("/{trigger_id}", response_model=TriggerOut)
async def update_trigger(
    trigger_id: str,
    data: TriggerUpdate,
    current_user: Annotated[UserModel, Depends(require_admin_or_analyst)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> TriggerOut:
    """Update a trigger."""
    trigger_repo = TriggerRepository(session)

    # Get trigger to check type
    trigger = await trigger_repo.get_by_id(trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    # Validate cron_expr if provided for cron trigger
    if trigger.type == "cron" and data.cron_expr is not None:
        from services.trigger_service import TriggerService

        service = TriggerService(session)
        if not service._validate_cron_expr(data.cron_expr):
            raise HTTPException(
                status_code=400, detail=f"Invalid cron expression: {data.cron_expr}"
            )

    # Update trigger
    updated = await trigger_repo.update(
        trigger_id=trigger_id,
        name=data.name,
        config=data.config,
        cron_expr=data.cron_expr,
        is_active=data.is_active,
    )

    if not updated:
        raise HTTPException(status_code=404, detail="Trigger not found")

    from core.config import settings

    base_url = getattr(settings, "base_url", "http://localhost:8000")

    trigger_dict = TriggerOut.model_validate(updated).model_dump()
    if updated.type == "webhook":
        trigger_dict["webhook_url"] = f"{base_url}/api/webhooks/{updated.id}"
        trigger_dict["secret_prefix"] = (
            (updated.secret or "")[:10] + "***" if updated.secret else None
        )
    if updated.type == "cron":
        trigger_dict["cron_expr"] = updated.cron_expr

    return TriggerOut(**trigger_dict)


@router.delete("/{trigger_id}")
async def delete_trigger(
    trigger_id: str,
    current_user: Annotated[UserModel, Depends(require_admin_or_analyst)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> dict[str, str]:
    """Delete a trigger."""
    trigger_repo = TriggerRepository(session)
    success = await trigger_repo.delete(trigger_id)

    if not success:
        raise HTTPException(status_code=404, detail="Trigger not found")

    return {"message": "Trigger deleted successfully"}


@router.post("/{trigger_id}/test")
async def test_webhook_trigger(
    trigger_id: str,
    current_user: Annotated[UserModel, Depends(require_any_role_internal)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> dict[str, str]:
    """Test a webhook trigger by sending a test invocation."""
    trigger_repo = TriggerRepository(session)
    trigger = await trigger_repo.get_by_id(trigger_id)

    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    if trigger.type != "webhook":
        raise HTTPException(
            status_code=400, detail="Only webhook triggers can be tested"
        )

    from core.config import settings

    base_url = getattr(settings, "base_url", "http://localhost:8000")
    webhook_url = f"{base_url}/api/webhooks/{trigger.id}"

    try:
        import httpx

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                webhook_url,
                json={"__test": True, "test_payload": True},
                headers={"X-Webhook-Test": "true"},
            )
            if response.status_code >= 200 and response.status_code < 300:
                return {
                    "success": True,
                    "message": f"Webhook test successful! (Status: {response.status_code})",
                }
            else:
                return {
                    "success": False,
                    "message": f"Webhook test failed with status {response.status_code}",
                }
    except httpx.RequestError as e:
        return {"success": False, "message": f"Failed to connect: {e!s}"}
    except Exception as e:
        return {"success": False, "message": f"Test error: {e!s}"}


@router.post(
    "/{trigger_id}/webhook/regenerate-secret", response_model=SecretRegenerateResponse
)
async def regenerate_webhook_secret(
    trigger_id: str,
    current_user: Annotated[UserModel, Depends(require_admin_or_analyst)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> SecretRegenerateResponse:
    """Regenerate a webhook trigger's secret."""
    trigger_service = TriggerService(session)

    # Verify trigger exists and is a webhook
    trigger = await trigger_service.trigger_repo.get_by_id(trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")
    if trigger.type != "webhook":
        raise HTTPException(status_code=400, detail="Trigger is not a webhook trigger")

    new_secret = await trigger_service.regenerate_webhook_secret(trigger_id)

    return SecretRegenerateResponse(
        secret=new_secret,
        message="Webhook secret regenerated successfully. Please update any systems using this webhook.",
    )


@router.get("/{trigger_id}/invocations")
async def list_trigger_invocations(
    trigger_id: str,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    current_user: Annotated[UserModel, Depends(require_any_role_internal)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> dict[str, list[TriggerInvocationOut]]:
    """List recent invocations for a trigger."""
    from sqlalchemy import desc, select

    from models.trigger import TriggerInvocationModel

    # Verify trigger exists
    trigger_repo = TriggerRepository(session)
    trigger = await trigger_repo.get_by_id(trigger_id)
    if not trigger:
        raise HTTPException(status_code=404, detail="Trigger not found")

    # Get recent invocations
    stmt = (
        select(TriggerInvocationModel)
        .where(TriggerInvocationModel.trigger_id == trigger_id)
        .order_by(desc(TriggerInvocationModel.created_at))
        .limit(limit)
    )
    result = await session.execute(stmt)
    invocations = list(result.scalars().all())

    return {
        "invocations": [
            TriggerInvocationOut.model_validate(inv) for inv in invocations
        ],
    }


@router.post("/cron/cleanup")
async def cleanup_old_invocations(
    hours: Annotated[int, Query(ge=1, le=168)] = 24,
    current_user: Annotated[UserModel, Depends(require_admin_or_analyst)] = None,
    session: Annotated[AsyncSession, Depends(get_session)] = None,
) -> dict[str, int]:
    """Clean up old trigger invocations."""
    trigger_service = TriggerService(session)
    deleted = await trigger_service.cleanup_invocations(hours=hours)

    return {
        "deleted_count": deleted,
        "message": f"Deleted {deleted} invocations older than {hours} hours",
    }

"""Prompt Registry Router - CRUD + version switching + environment-based query.

P1-23: AI Prompt unified registry with versioning.
"""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user, require_admin
from models.prompt_registry import PromptEnvironment, PromptRegistryModel
from models.user import UserModel
from repositories.prompt_registry_repository import PromptRegistryRepository

logger = get_logger(__name__)

router = APIRouter(prefix="/api/prompt-registry", tags=["Prompt Registry"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------
class PromptCreate(BaseModel):
    """Create a new prompt version."""

    name: str = Field(..., min_length=1, max_length=255)
    version: str = Field(..., min_length=1, max_length=50)
    content: str = Field(..., min_length=1)
    variables: list[str] = Field(default_factory=list)
    environment: str = Field(default=PromptEnvironment.DEV.value)
    is_active: bool = Field(default=False)

    model_config = ConfigDict(protected_namespaces=())


class PromptUpdate(BaseModel):
    """Update an existing prompt (only content and variables are mutable)."""

    content: str | None = Field(default=None, min_length=1)
    variables: list[str] | None = Field(default=None)
    is_active: bool | None = Field(default=None)

    model_config = ConfigDict(protected_namespaces=())


class PromptResponse(BaseModel):
    """Prompt response model."""

    id: str
    name: str
    version: str
    content: str
    variables: list[str] | dict | list
    environment: str
    is_active: bool
    created_by: str
    created_at: str
    updated_at: str

    model_config = ConfigDict(protected_namespaces=())


class PromptListResponse(BaseModel):
    """List response."""

    items: list[PromptResponse]
    total: int


class VersionSwitchRequest(BaseModel):
    """Request to switch active version."""

    version: str

    model_config = ConfigDict(protected_namespaces=())


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------
def get_prompt_repo(
    session: AsyncSession = Depends(get_session),
) -> PromptRegistryRepository:
    return PromptRegistryRepository(session)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _to_response(model: PromptRegistryModel) -> PromptResponse:
    vars_data = model.variables
    if isinstance(vars_data, dict):
        vars_data = list(vars_data.keys()) if vars_data else []
    elif not isinstance(vars_data, list):
        vars_data = []
    return PromptResponse(
        id=model.id,
        name=model.name,
        version=model.version,
        content=model.content,
        variables=vars_data,
        environment=model.environment,
        is_active=model.is_active,
        created_by=model.created_by,
        created_at=model.created_at,
        updated_at=model.updated_at,
    )


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@router.post(
    "",
    response_model=PromptResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_prompt(
    data: PromptCreate,
    current_user: UserModel = Depends(require_admin),
    repo: PromptRegistryRepository = Depends(get_prompt_repo),
):
    """Create a new prompt version (admin only)."""
    # Validate environment
    if data.environment not in {e.value for e in PromptEnvironment}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid environment. Must be one of: {[e.value for e in PromptEnvironment]}",
        )

    # Check for duplicate name+version+environment
    existing = await repo.get_by_name_version_env(
        data.name, data.version, data.environment
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Prompt with same name, version and environment already exists",
        )

    prompt = await repo.create(
        name=data.name,
        version=data.version,
        content=data.content,
        variables=data.variables,
        environment=data.environment,
        is_active=data.is_active,
        created_by=current_user.username,
    )

    logger.info(
        f"Prompt created: {data.name} v{data.version} ({data.environment}) by {current_user.username}"
    )
    return _to_response(prompt)


@router.get("", response_model=PromptListResponse)
async def list_prompts(
    environment: str = Query(PromptEnvironment.DEV.value),
    name: str | None = None,
    is_active: bool | None = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: UserModel = Depends(get_current_user),
    repo: PromptRegistryRepository = Depends(get_prompt_repo),
):
    """List prompts by environment with optional filters."""
    if environment not in {e.value for e in PromptEnvironment}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid environment. Must be one of: {[e.value for e in PromptEnvironment]}",
        )

    items = await repo.list_by_environment(
        environment=environment,
        name=name,
        is_active=is_active,
        limit=limit,
        offset=offset,
    )

    # Count total (simplified for common cases)
    total = len(items)  # In production, use a separate count query

    return PromptListResponse(
        items=[_to_response(i) for i in items],
        total=total,
    )


@router.get("/{prompt_id}", response_model=PromptResponse)
async def get_prompt(
    prompt_id: str,
    current_user: UserModel = Depends(get_current_user),
    repo: PromptRegistryRepository = Depends(get_prompt_repo),
):
    """Get a prompt by ID."""
    prompt = await repo.get(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )
    return _to_response(prompt)


@router.patch("/{prompt_id}", response_model=PromptResponse)
async def update_prompt(
    prompt_id: str,
    data: PromptUpdate,
    current_user: UserModel = Depends(require_admin),
    repo: PromptRegistryRepository = Depends(get_prompt_repo),
):
    """Update a prompt (admin only)."""
    prompt = await repo.get(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )

    update_kwargs: dict[str, Any] = {}
    if data.content is not None:
        update_kwargs["content"] = data.content
    if data.variables is not None:
        update_kwargs["variables"] = data.variables
    if data.is_active is not None:
        update_kwargs["is_active"] = data.is_active

    if not update_kwargs:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    from datetime import UTC, datetime

    update_kwargs["updated_at"] = datetime.now(UTC).isoformat()

    updated = await repo.update(prompt_id, **update_kwargs)
    if not updated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update prompt",
        )

    logger.info(
        f"Prompt updated: {prompt.name} v{prompt.version} by {current_user.username}"
    )
    return _to_response(updated)


@router.post("/{prompt_id}/activate", response_model=PromptResponse)
async def activate_prompt_version(
    prompt_id: str,
    current_user: UserModel = Depends(require_admin),
    repo: PromptRegistryRepository = Depends(get_prompt_repo),
):
    """Activate a specific prompt version and deactivate siblings (admin only)."""
    prompt = await repo.get(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )

    activated = await repo.activate_version(
        name=prompt.name,
        version=prompt.version,
        environment=prompt.environment,
    )
    if not activated:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to activate prompt version",
        )

    logger.info(
        f"Prompt activated: {prompt.name} v{prompt.version} ({prompt.environment}) by {current_user.username}"
    )
    return _to_response(activated)


@router.delete("/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_prompt(
    prompt_id: str,
    current_user: UserModel = Depends(require_admin),
    repo: PromptRegistryRepository = Depends(get_prompt_repo),
):
    """Delete a prompt version (admin only)."""
    prompt = await repo.get(prompt_id)
    if not prompt:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prompt not found",
        )

    # Prevent deleting an active prompt if it's the only active one
    if prompt.is_active:
        siblings = await repo.list_all_versions(prompt.name, prompt.environment)
        active_siblings = [s for s in siblings if s.is_active and s.id != prompt_id]
        if not active_siblings:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the only active version. Activate another version first.",
            )

    await repo.delete(prompt_id)
    logger.info(
        f"Prompt deleted: {prompt.name} v{prompt.version} by {current_user.username}"
    )
    return None


@router.get("/{name}/versions", response_model=PromptListResponse)
async def get_all_versions(
    name: str,
    environment: str = Query(PromptEnvironment.DEV.value),
    current_user: UserModel = Depends(get_current_user),
    repo: PromptRegistryRepository = Depends(get_prompt_repo),
):
    """Get all versions of a prompt in a specific environment."""
    if environment not in {e.value for e in PromptEnvironment}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid environment. Must be one of: {[e.value for e in PromptEnvironment]}",
        )

    items = await repo.list_all_versions(name, environment)
    return PromptListResponse(
        items=[_to_response(i) for i in items],
        total=len(items),
    )

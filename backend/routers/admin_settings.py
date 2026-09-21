"""Router for system settings management.

This module provides API endpoints for managing system-wide settings,
including Dify integration configuration.
"""

import re
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user, require_permission
from models.user import UserModel

logger = get_logger(__name__)


def _update_env_file(key: str, value: str | None) -> None:
    """Update a key in the .env file.

    Args:
        key: Environment variable name
        value: New value (if None, the line will be removed or set to empty)
    """
    env_path = Path(__file__).parent.parent / ".env"

    if not env_path.exists():
        logger.warning(f".env file not found at {env_path}")
        return

    try:
        content = env_path.read_text(encoding="utf-8")

        # Pattern to match the key (handle both KEY=value and KEY= formats)
        pattern = rf"^{re.escape(key)}=.*$"

        if value is not None:
            new_line = f"{key}={value}"
            if re.search(pattern, content, re.MULTILINE):
                # Update existing line
                content = re.sub(pattern, new_line, content, flags=re.MULTILINE)
            else:
                # Add new line
                content = content.rstrip() + "\n" + new_line + "\n"
        else:
            # Remove the line if value is None
            content = re.sub(pattern + r"\n?", "", content, flags=re.MULTILINE)

        env_path.write_text(content, encoding="utf-8")
        logger.info(f"Updated {key} in .env file")

    except Exception as e:
        logger.error(f"Failed to update .env file: {e}")
        raise


router = APIRouter(prefix="/api/v1/admin/settings", tags=["admin", "settings"])


class SettingsUpdateRequest(BaseModel):
    """Request model for updating system settings."""


class SettingsResponse(BaseModel):
    """Response model for system settings."""


class TimeoutConfigResponse(BaseModel):
    """Response model for API timeout configuration."""

    analysis_ms: int
    default_ms: int
    health_ms: int
    report_ms: int
    timeline_ms: int
    dag_run_ms: int


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: UserModel = Depends(require_permission("admin", "write")),
) -> SettingsResponse:
    """Get current system settings.

    Requires: admin:write permission
    """
    return SettingsResponse()


@router.post("")
async def update_settings(
    request: SettingsUpdateRequest,
    current_user: UserModel = Depends(require_permission("admin", "write")),
    db: AsyncSession = Depends(get_session),
):
    """Update system settings.

    This updates the in-memory settings. For persistence, these should be
    saved to environment variables or a settings file.

    Requires: admin:write permission
    """

    try:
        # Update settings in-memory and persist to .env file
        updated_fields = []

        logger.info(f"Settings updated by {current_user.username}: {updated_fields}")

        return {
            "success": True,
            "message": "Settings updated successfully",
            "updated_fields": updated_fields,
        }

    except Exception as e:
        import traceback

        logger.error(f"Failed to update settings: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        # Do NOT expose exception details or traceback to the client — info leak.
        return {
            "success": False,
            "error": "Failed to update settings. Check server logs for details.",
        }


@router.get("/timeouts", response_model=TimeoutConfigResponse)
async def get_timeout_config(
    current_user: UserModel = Depends(get_current_user),
) -> TimeoutConfigResponse:
    """Get API timeout configuration.

    Returns timeout values in milliseconds for various API operations.
    Requires: authenticated user
    """
    return TimeoutConfigResponse(
        analysis_ms=settings.api_timeout_analysis_ms,
        default_ms=settings.api_timeout_default_ms,
        health_ms=settings.api_timeout_health_ms,
        report_ms=settings.api_timeout_report_ms,
        timeline_ms=settings.api_timeout_timeline_ms,
        dag_run_ms=settings.api_timeout_dag_run_ms,
    )


class DynamicConfigItem(BaseModel):
    """Dynamic configuration item definition."""

    key: str
    current_value: Any
    default_value: Any = None
    is_overridden: bool
    type: str
    description: str = ""


class DynamicConfigSetRequest(BaseModel):
    """Request model to update dynamic configuration parameter."""

    value: Any


@router.get("/dynamic", response_model=list[DynamicConfigItem])
async def list_dynamic_settings(
    current_user: UserModel = Depends(require_permission("admin", "read")),
) -> list[DynamicConfigItem]:
    """List all dynamic configuration settings with override status and defaults."""
    from core.dynamic_config import get_dynamic_config

    dyn = get_dynamic_config()
    items = await dyn.get_all()
    return [DynamicConfigItem(**item) for item in items]


@router.get("/dynamic/{key}")
async def get_dynamic_setting(
    key: str,
    current_user: UserModel = Depends(require_permission("admin", "read")),
):
    """Get a specific dynamic configuration setting value."""
    from core.dynamic_config import get_dynamic_config

    dyn = get_dynamic_config()
    val = await dyn.get(key)
    return {"key": key, "value": val}


@router.put("/dynamic/{key}")
async def set_dynamic_setting(
    key: str,
    body: DynamicConfigSetRequest,
    current_user: UserModel = Depends(require_permission("admin", "write")),
):
    """Override a dynamic configuration setting and broadcast hot-reload across all pods."""
    from core.dynamic_config import get_dynamic_config

    dyn = get_dynamic_config()
    success = await dyn.set(key, body.value)
    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to persist dynamic config override"
        )
    return {"success": True, "key": key, "value": body.value}


@router.delete("/dynamic/{key}")
async def reset_dynamic_setting(
    key: str,
    current_user: UserModel = Depends(require_permission("admin", "write")),
):
    """Reset a dynamic configuration setting back to default and broadcast."""
    from core.dynamic_config import get_dynamic_config

    dyn = get_dynamic_config()
    success = await dyn.delete(key)
    if not success:
        raise HTTPException(
            status_code=500, detail="Failed to reset dynamic config override"
        )
    return {"success": True, "key": key, "message": "Reset to default"}

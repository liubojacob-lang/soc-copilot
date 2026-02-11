"""Router for system settings management.

This module provides API endpoints for managing system-wide settings,
including Dify integration configuration.
"""

import logging
import os
import re
from pathlib import Path
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.config import settings
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel, UserRole

logger = get_logger(__name__)


def _update_env_file(key: str, value: Optional[str]) -> None:
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


router = APIRouter(prefix="/api/admin/settings", tags=["admin", "settings"])


class SettingsUpdateRequest(BaseModel):
    """Request model for updating system settings."""

    dify_api_url: Optional[str] = Field(None, description="Dify API base URL")
    dify_api_key: Optional[str] = Field(None, description="Dify API key")
    dify_workspace_id: Optional[str] = Field(None, description="Dify workspace ID")


class SettingsResponse(BaseModel):
    """Response model for system settings."""

    dify_api_url: str
    dify_workspace_id: Optional[str] = None
    dify_configured: bool


@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: UserModel = Depends(get_current_user),
) -> SettingsResponse:
    """Get current system settings.

    Requires: admin role
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Only administrators can view settings"
        )

    return SettingsResponse(
        dify_api_url=getattr(settings, "dify_api_url", ""),
        dify_workspace_id=getattr(settings, "dify_workspace_id", None),
        dify_configured=bool(getattr(settings, "dify_api_url", "")),
    )


@router.post("")
async def update_settings(
    request: SettingsUpdateRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """Update system settings.

    This updates the in-memory settings. For persistence, these should be
    saved to environment variables or a settings file.

    Requires: admin role
    """
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=403, detail="Only administrators can update settings"
        )

    try:
        # Update settings in-memory and persist to .env file
        updated_fields = []

        if request.dify_api_url is not None:
            settings.dify_api_url = request.dify_api_url
            _update_env_file("DIFY_API_URL", request.dify_api_url)
            updated_fields.append("dify_api_url")
            logger.info(f"Updated dify_api_url: {request.dify_api_url}")

        if request.dify_api_key is not None:
            settings.dify_api_key = request.dify_api_key
            _update_env_file("DIFY_API_KEY", request.dify_api_key)
            updated_fields.append("dify_api_key")
            logger.info(f"Updated dify_api_key: {request.dify_api_key[:20]}...")

        if request.dify_workspace_id is not None:
            settings.dify_workspace_id = request.dify_workspace_id
            _update_env_file("DIFY_WORKSPACE_ID", request.dify_workspace_id or "")
            updated_fields.append("dify_workspace_id")

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
        return {"success": False, "error": str(e), "traceback": traceback.format_exc()}

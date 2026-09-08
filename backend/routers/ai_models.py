"""
AI Model Management Router - API endpoints for model selection and testing
"""

import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user, require_admin
from middleware.rate_limiter import rate_limit
from models.user import UserModel
from repositories.ai_model_repository import (
    AIModelRepository,
    AIUserSettingRepository,
)
from schemas.ai_model import (
    AIModelListResponse,
    AIModelResponse,
    SetDefaultModelRequest,
    SetDefaultModelResponse,
    TestModelRequest,
    TestModelResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/ai/models", tags=["AI Models"])


@router.get("", response_model=AIModelListResponse)
async def list_models(
    skip: int = 0,
    limit: int = 100,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Get list of available AI models.

    Returns all models with their capabilities and status.
    """
    try:
        model_repo = AIModelRepository(db)
        setting_repo = AIUserSettingRepository(db)
        models, total = await model_repo.list_all(skip=skip, limit=limit)

        if total == 0:
            from init_ai_models import seed_ai_models

            await seed_ai_models(db)
            models, total = await model_repo.list_all(skip=skip, limit=limit)

        # Get user's preferred default model
        user_settings = await setting_repo.get_by_user_id(str(current_user.id))
        user_default_model_id = (
            user_settings.default_model_id if user_settings else None
        )

        # If no user default, get global default
        if not user_default_model_id:
            global_default = await model_repo.get_default_model()
            user_default_model_id = global_default.id if global_default else None

        return AIModelListResponse(
            models=models,
            total=total,
            default_model_id=user_default_model_id,
        )

    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list models: {e!s}",
        )


@router.get("/default", response_model=AIModelResponse)
async def get_default_model(
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Get the current default AI model.

    Returns user's preferred model or global default.
    """
    try:
        model_repo = AIModelRepository(db)
        setting_repo = AIUserSettingRepository(db)

        # Get user's preferred default model
        user_settings = await setting_repo.get_by_user_id(str(current_user.id))
        model_id = user_settings.default_model_id if user_settings else None

        # If no user default, get global default
        if not model_id:
            global_default = await model_repo.get_default_model()
            if global_default:
                return global_default
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No default model configured",
                )

        model = await model_repo.get_by_id(model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Default model not found",
            )

        return model

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting default model: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get default model: {e!s}",
        )


@router.post("/default", response_model=SetDefaultModelResponse)
async def set_default_model(
    request: SetDefaultModelRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Set the default AI model for current user.

    Sets user's preferred model (does not affect global default).
    """
    try:
        model_repo = AIModelRepository(db)
        setting_repo = AIUserSettingRepository(db)

        # Verify model exists and is enabled
        model = await model_repo.get_by_id(request.model_id)
        if not model:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Model {request.model_id} not found",
            )

        if not model.enabled:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Model {request.model_id} is not enabled",
            )

        # Set user's default
        await setting_repo.set_default_model(str(current_user.id), request.model_id)
        await db.commit()

        return SetDefaultModelResponse(
            success=True,
            model_id=request.model_id,
            message="Default model updated successfully",
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting default model: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to set default model: {e!s}",
        )


@router.post("/test", response_model=TestModelResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def test_model(
    payload: TestModelRequest,
    request: Request,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Test connectivity to an AI model.

    Performs a lightweight request to verify the model is accessible.
    Returns latency and status information.
    """
    try:
        model_repo = AIModelRepository(db)

        # Get model
        model = await model_repo.get_by_id(payload.model_id)
        if not model:
            return TestModelResponse(
                success=False,
                model_id=payload.model_id,
                error_message=f"Model {payload.model_id} not found",
            )

        if not model.enabled:
            return TestModelResponse(
                success=False,
                model_id=payload.model_id,
                error_message=f"Model {payload.model_id} is not enabled",
            )

        # Import here to avoid circular imports
        from services.ai_providers import LLMFactory

        # Test the model
        start_time = time.time()
        error_message = None
        provider_raw = None
        response_text = None

        try:
            # Create provider for the model
            provider = LLMFactory.create_provider_for_model(model.id, model.provider)

            # Test with a minimal prompt
            test_messages = [{"role": "user", "content": "Respond with exactly: OK"}]

            response = await provider.chat_completion(
                messages=test_messages,
                model=model.id,
                max_tokens=5,
                temperature=0,
                timeout=10,
            )

            latency_ms = (time.time() - start_time) * 1000
            provider_raw = getattr(response, "model", None) or model.id

            # Try to extract response text
            if isinstance(response, str):
                response_text = response
            elif hasattr(response, "content"):
                response_text = response.content
            elif hasattr(response, "choices") and response.choices:
                response_text = response.choices[0].message.content
            else:
                response_text = "OK"

            if response_text and len(response_text.strip()) > 0:
                return TestModelResponse(
                    success=True,
                    model_id=payload.model_id,
                    latency_ms=round(latency_ms, 2),
                    provider_raw=provider_raw,
                    response=response_text[:100],
                )
            else:
                return TestModelResponse(
                    success=False,
                    model_id=payload.model_id,
                    latency_ms=round(latency_ms, 2),
                    error_message=f"Unexpected response: {response_text[:100]}",
                )

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            error_message = f"{type(e).__name__}: {e!s}"
            logger.error(f"Error testing model {payload.model_id}: {e}")

            return TestModelResponse(
                success=False,
                model_id=payload.model_id,
                latency_ms=round(latency_ms, 2),
                error_message=error_message,
            )

    except Exception as e:
        logger.error(f"Error in test_model endpoint: {e}")
        return TestModelResponse(
            success=False,
            model_id=payload.model_id,
            error_message=f"Test failed: {e!s}",
        )


class RefreshModelsResponse(BaseModel):
    """Response for model refresh."""

    success: bool
    message: str
    models_added: int = 0
    models_updated: int = 0


@router.post("/refresh", response_model=RefreshModelsResponse)
@rate_limit(max_requests=2, window_seconds=60)
async def refresh_models(
    request: Request,
    current_user: UserModel = Depends(require_admin),
    db: AsyncSession = Depends(get_session),
):
    """
    Refresh the model list from available providers.

    Scans configured providers and adds/updates available models.
    Admin only.
    """

    try:
        from init_ai_models import seed_ai_models

        models_added, models_updated = await seed_ai_models(db)

        return RefreshModelsResponse(
            success=True,
            message=f"Models refreshed: {models_added} added, {models_updated} updated",
            models_added=models_added,
            models_updated=models_updated,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing models: {e}")
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to refresh models: {e!s}",
        )

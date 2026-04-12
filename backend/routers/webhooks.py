"""Webhook router for external playbook triggers."""

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from services.trigger_service import TriggerService

logger = get_logger(__name__)

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


@router.post("/{trigger_id}")
async def receive_webhook(
    trigger_id: str,
    request: Request,
    x_webhook_secret: str = Header(
        ..., description="Webhook secret for authentication", alias="X-Webhook-Secret"
    ),
    x_idempotency_key: str | None = Header(
        None, description="Idempotency key", alias="X-Idempotency-Key"
    ),
    session: AsyncSession = Depends(get_session),
) -> dict[str, object]:
    """Receive external webhook to trigger playbook execution.

    This endpoint does NOT require authentication. It verifies the request
    using the X-Webhook-Secret header.

    Args:
        trigger_id: Webhook trigger ID
        request: FastAPI request object
        x_webhook_secret: Webhook secret for authentication
        x_idempotency_key: Optional idempotency key for deduplication
        session: Database session

    Returns:
        Execution result with run_id

    Raises:
        HTTPException: If trigger not found or signature invalid
    """
    # Read raw payload
    payload = await request.body()

    # Handle webhook using TriggerService
    trigger_service = TriggerService(session)

    try:
        result = await trigger_service.handle_webhook(
            trigger_id=trigger_id,
            payload=payload,
            signature=x_webhook_secret,
            idempotency_key=x_idempotency_key,
        )

        await session.commit()

        return {
            "run_id": result["run_id"],
            "status": result["status"],
            "message": "Webhook processed successfully",
            "cached": result.get("cached", False),
        }

    except ValueError:
        raise HTTPException(status_code=400, detail="Bad request")
    except Exception as e:
        logger.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/health")
async def health() -> dict[str, str]:
    """Webhook module health check."""
    return {"status": "ok", "module": "webhooks", "version": "0.7"}

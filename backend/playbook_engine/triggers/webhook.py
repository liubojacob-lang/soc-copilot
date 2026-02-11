"""Webhook trigger handler with HMAC signature verification."""

import hmac
import hashlib
import base64
import json
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.logger import get_logger
from models.playbook_definition import PlaybookTriggerModel, PlaybookDefinitionModel

logger = get_logger(__name__)


def verify_hmac_signature(
    payload: bytes,
    signature: str,
    secret: str,
) -> bool:
    """Verify HMAC signature for webhook payload.

    Args:
        payload: Raw payload bytes
        signature: Base64-encoded signature from X-Signature header
        secret: Webhook secret key

    Returns:
        True if signature is valid, False otherwise
    """
    try:
        # Calculate expected signature
        expected = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).digest()

        # Decode provided signature
        provided = base64.b64decode(signature)

        # Timing-safe comparison
        return hmac.compare_digest(expected, provided)
    except Exception as e:
        logger.error(f"Failed to verify HMAC signature: {e}")
        return False


class WebhookHandler:
    """Handler for webhook-triggered playbook executions."""

    def __init__(self, session: AsyncSession):
        """Initialize the webhook handler.

        Args:
            session: Database session
        """
        self.session = session

    async def get_trigger(self, trigger_id: str) -> Optional[PlaybookTriggerModel]:
        """Get a trigger configuration by ID.

        Args:
            trigger_id: Trigger ID

        Returns:
            Trigger model or None if not found
        """
        stmt = select(PlaybookTriggerModel).where(
            PlaybookTriggerModel.id == trigger_id,
            PlaybookTriggerModel.type == "webhook",
            PlaybookTriggerModel.is_active == True,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def check_idempotency(
        self,
        idempotency_key: str,
    ) -> bool:
        """Check if an idempotency key has already been processed.

        Args:
            idempotency_key: Unique key for this request

        Returns:
            True if key is unique (first time), False if already processed
        """
        from models.playbook_run import PlaybookRunModel

        stmt = select(PlaybookRunModel).where(
            PlaybookRunModel.idempotency_key == idempotency_key,
        )
        result = await self.session.execute(stmt)
        existing = result.scalar_one_or_none()

        return existing is None

    async def handle_webhook(
        self,
        trigger_id: str,
        payload: bytes,
        signature: str,
        idempotency_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Handle an incoming webhook trigger.

        Args:
            trigger_id: Trigger ID
            payload: Raw request payload
            signature: HMAC signature from X-Signature header
            idempotency_key: Optional idempotency key from X-Idempotency-Key header

        Returns:
            Dictionary with run_id and status

        Raises:
            ValueError: If trigger not found or signature invalid
        """
        # Get trigger configuration
        trigger = await self.get_trigger(trigger_id)
        if not trigger:
            raise ValueError(f"Webhook trigger not found: {trigger_id}")

        # Verify signature
        secret = trigger.config_json.get("webhook_secret", "")
        if not verify_hmac_signature(payload, signature, secret):
            raise ValueError("Invalid HMAC signature")

        # Check idempotency
        if idempotency_key:
            is_unique = await self.check_idempotency(idempotency_key)
            if not is_unique:
                logger.info(f"Duplicate webhook request with idempotency key: {idempotency_key}")
                # Return existing run instead of creating new one
                from models.playbook_run import PlaybookRunModel
                stmt = select(PlaybookRunModel).where(
                    PlaybookRunModel.idempotency_key == idempotency_key,
                )
                result = await self.session.execute(stmt)
                existing_run = result.scalar_one_or_none()
                if existing_run:
                    return {
                        "run_id": existing_run.id,
                        "status": existing_run.status,
                        "message": "Duplicate request, returning existing run",
                    }

        # Parse payload
        try:
            input_json = json.loads(payload.decode('utf-8'))
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON payload: {e}")

        # Get playbook definition
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == trigger.definition_id,
        )
        result = await self.session.execute(stmt)
        definition = result.scalar_one_or_none()

        if not definition:
            raise ValueError(f"Playbook definition not found: {trigger.definition_id}")

        # Execute the playbook
        from .dag import DAGBuilder, DAGExecutionEngine

        dag_definition = DAGBuilder.from_json(definition.definition_json)
        engine = DAGExecutionEngine(self.session)

        # Create run record
        from models.playbook_run import PlaybookRunModel
        from repositories.playbook_run_repository import PlaybookRunRepository
        import uuid

        run_repo = PlaybookRunRepository(self.session)
        run_id = str(uuid.uuid4())

        await run_repo.create(
            playbook_name=f"webhook:{definition.name}",
            playbook_version=definition.version,
            mode="dry_run",
            status="running",
            created_by_user_id=None,
            input_json=input_json,
            output_json={},
            execution_mode="dag",
            definition_id=definition.id,
            idempotency_key=idempotency_key,
            trigger_source="webhook",
        )

        await self.session.flush()

        # Execute the DAG
        result = await engine.execute_dag(
            definition=dag_definition,
            run_id=run_id,
            input_json=input_json,
            mode="dry_run",
        )

        return {
            "run_id": run_id,
            "status": result["status"],
            "outputs": result.get("outputs", {}),
        }

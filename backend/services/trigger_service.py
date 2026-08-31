"""Service for trigger management and execution."""

import hashlib
import secrets
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.playbook_definition import PlaybookTriggerModel
from repositories.audit_repository import AuditRepository
from repositories.playbook_run_repository import PlaybookRunRepository
from repositories.trigger_repository import TriggerRepository

logger = get_logger(__name__)


class TriggerService:
    """Service for managing playbook triggers."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.trigger_repo = TriggerRepository(session)
        self.run_repo = PlaybookRunRepository(session)
        self.audit_repo = AuditRepository(session)

    async def create_webhook_trigger(
        self,
        definition_id: str,
        name: str | None = None,
        config: dict[str, Any] | None = None,
        is_active: bool = True,
        created_by_user_id: str | None = None,
    ) -> PlaybookTriggerModel:
        """Create a webhook trigger with auto-generated secret.

        The secret is formatted as: wh_{token_urlsafe(32)}
        """
        # Generate webhook secret
        secret = f"wh_{secrets.token_urlsafe(32)}"

        trigger = await self.trigger_repo.create_trigger(
            definition_id=definition_id,
            trigger_type="webhook",
            name=name or "Webhook Trigger",
            config=config or {},
            secret=secret,
            is_active=is_active,
            created_by_user_id=created_by_user_id,
        )

        logger.info(
            f"Created webhook trigger: {trigger.id} with secret: {secret[:10]}..."
        )
        return trigger

    async def create_cron_trigger(
        self,
        definition_id: str,
        cron_expr: str,
        name: str | None = None,
        config: dict[str, Any] | None = None,
        is_active: bool = True,
        created_by_user_id: str | None = None,
    ) -> PlaybookTriggerModel:
        """Create a cron trigger with schedule validation.

        Validates the cron expression before creating the trigger.
        """
        # Validate cron expression
        if not self._validate_cron_expr(cron_expr):
            raise ValueError(f"Invalid cron expression: {cron_expr}")

        trigger = await self.trigger_repo.create_trigger(
            definition_id=definition_id,
            trigger_type="cron",
            name=name or f"Cron Trigger: {cron_expr}",
            config=config or {},
            cron_expr=cron_expr,
            is_active=is_active,
            created_by_user_id=created_by_user_id,
        )

        logger.info(f"Created cron trigger: {trigger.id} with schedule: {cron_expr}")
        return trigger

    def _validate_cron_expr(self, cron_expr: str) -> bool:
        """Validate a cron expression with safety checks."""
        try:
            from croniter import croniter

            # Length check
            if len(cron_expr) > 100:
                raise ValueError("Cron expression too long")

            # Block dangerous patterns - every minute cron not allowed
            if cron_expr.strip() == "* * * * *" or cron_expr.strip() == "* * * * * *":
                raise ValueError(
                    "Every-minute cron expression not allowed (minimum interval: 5 minutes)"
                )

            # Validate with croniter
            cron = croniter(cron_expr)

            # Check minimum interval (5 minutes = 300 seconds)
            datetime.now(UTC)
            next1 = cron.get_next(datetime)
            next2 = cron.get_next(datetime)
            min_interval = (next2 - next1).total_seconds()

            if min_interval < 300:  # 5 minutes minimum
                raise ValueError(
                    f"Cron interval too short: {int(min_interval)}s (minimum 300s)"
                )

            return True
        except ValueError:
            raise
        except Exception as e:
            logger.warning(f"Invalid cron expression '{cron_expr}': {e}")
            return False

    async def handle_webhook(
        self,
        trigger_id: str,
        payload: bytes,
        signature: str | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        """Handle a webhook invocation.

        Verifies signature, checks idempotency, and executes the playbook.

        Args:
            trigger_id: The trigger ID
            payload: Raw request body bytes
            signature: HMAC signature from X-Webhook-Secret header
            idempotency_key: Optional idempotency key

        Returns:
            Dict with run_id and status

        Raises:
            ValueError: If trigger not found, invalid signature, or inactive
        """
        # Validate idempotency key format if provided
        if idempotency_key:
            if len(idempotency_key) > 100:
                raise ValueError("Idempotency key too long (max 100 characters)")

        # Get trigger
        trigger = await self.trigger_repo.get_by_id(trigger_id)
        if not trigger:
            raise ValueError(f"Trigger not found: {trigger_id}")

        if trigger.type != "webhook":
            raise ValueError(f"Trigger is not a webhook: {trigger.type}")

        if not trigger.is_active:
            raise ValueError(f"Trigger is inactive: {trigger_id}")

        # Webhook triggers MUST have a secret configured
        if not trigger.secret:
            raise ValueError("Webhook trigger not configured with a secret")

        # Signature is REQUIRED for webhook triggers
        if not signature:
            raise ValueError("Signature header required")

        # Verify signature
        if not self._verify_signature(payload, signature, trigger.secret):
            logger.warning(f"Invalid signature for trigger {trigger_id}")
            raise ValueError("Invalid signature")

        # Check idempotency
        existing_invocation = await self.trigger_repo.check_idempotency(
            trigger_id, idempotency_key, payload
        )
        if existing_invocation:
            logger.info(f"Returning cached invocation: {existing_invocation.id}")
            return {
                "run_id": existing_invocation.run_id,
                "status": existing_invocation.status,
                "cached": True,
                "invocation_id": existing_invocation.id,
            }

        # Parse payload as JSON for input context
        import json

        try:
            input_context = json.loads(payload.decode("utf-8")) if payload else {}
        except json.JSONDecodeError:
            input_context = {"raw_payload": payload.decode("utf-8", errors="ignore")}

        # Record invocation
        invocation = await self.trigger_repo.record_invocation(
            trigger_id=trigger_id,
            idempotency_key=idempotency_key,
            payload=payload,
            status="pending",
        )

        # Execute playbook
        run = None
        try:
            # Get definition
            from repositories.playbook_definition_repository import (
                PlaybookDefinitionRepository,
            )

            definition_repo = PlaybookDefinitionRepository(self.session)
            definition = await definition_repo.get_by_id(trigger.definition_id)
            if not definition:
                raise ValueError(f"Definition not found: {trigger.definition_id}")

            # Validate and compile DAG
            from services.playbook_dag_compiler import DAGCompiler, DAGValidationError

            try:
                compiled = await DAGCompiler.validate_and_compile(
                    definition.definition_json, self.session
                )
            except DAGValidationError as e:
                raise ValueError(f"Invalid DAG definition: {e}")

            # Create run
            run = await self.run_repo.create(
                playbook_name=definition.name,
                playbook_version=definition.version,
                mode="apply",
                input_json=input_context,
                engine_version="v0.7",
                execution_mode="dag",
                definition_id=trigger.definition_id,
                failure_strategy="fail_fast",
                trigger_source="webhook",
                trigger_id=trigger_id,
            )

            # Execute DAG (for now, mark as success immediately)
            # In production, this would be an async background task
            from services.playbook_dag_scheduler import DAGScheduler

            scheduler = DAGScheduler(
                session=self.session,
                run_id=run.id,
                compiled_dag=compiled,
                input_context=input_context,
                mode="apply",
                failure_strategy="fail_fast",
            )
            output = await scheduler.execute()

            final_status = (
                "cancelled"
                if scheduler.cancelled
                else ("failed" if scheduler.failed_nodes else "success")
            )
            invocation_status = "success" if final_status == "success" else "failed"
            invocation_error = None
            run_error_message = None
            if final_status == "cancelled":
                invocation_error = "Run cancelled during execution"
                run_error_message = invocation_error
            elif final_status == "failed":
                invocation_error = f"Node failures: {len(scheduler.failed_nodes)}"
                run_error_message = invocation_error

            await self.run_repo.update(
                run.id,
                status=final_status,
                output_json=output,
                error_message=run_error_message,
            )

            # Update invocation
            await self.trigger_repo.update_invocation(
                invocation_id=invocation.id,
                run_id=run.id,
                status=invocation_status,
                error_message=invocation_error,
            )

            # Update last triggered
            await self.trigger_repo.update_last_triggered(trigger_id)

            # Create audit log
            await self.audit_repo.create(
                action="webhook:invoke",
                method="POST",
                path=f"/api/webhooks/{trigger_id}",
                status_code=200,
                target_type="trigger",
                target_id=trigger_id,
                extra_json={
                    "trigger_type": "webhook",
                    "idempotency_key": idempotency_key,
                    "run_id": run.id,
                },
            )
            await self.session.commit()

            return {
                "run_id": run.id,
                "status": final_status,
                "cached": False,
                "invocation_id": invocation.id,
            }

        except Exception as e:
            logger.error(f"Failed to execute webhook trigger: {e}")

            if run:
                await self.run_repo.update(
                    run.id,
                    status="failed",
                    error_message=str(e),
                )

            # Update invocation with error
            await self.trigger_repo.update_invocation(
                invocation_id=invocation.id,
                run_id=run.id if run else None,
                status="failed",
                error_message=str(e),
            )

            # Create audit log
            await self.audit_repo.create(
                action="webhook:invoke",
                method="POST",
                path=f"/api/webhooks/{trigger_id}",
                status_code=500,
                target_type="trigger",
                target_id=trigger_id,
                extra_json={
                    "trigger_type": "webhook",
                    "idempotency_key": idempotency_key,
                    "error": str(e),
                },
            )
            await self.session.commit()

            raise

    def _verify_signature(self, payload: bytes, signature: str, secret: str) -> bool:
        """Verify HMAC signature."""
        import base64
        import hmac

        try:
            # Compute expected signature
            expected = hmac.new(
                secret.encode("utf-8"),
                payload,
                hashlib.sha256,
            ).digest()
            expected_b64 = base64.b64encode(expected).decode("utf-8")

            # Constant-time comparison
            return hmac.compare_digest(signature, expected_b64)
        except Exception as e:
            logger.error(f"Signature verification error: {e}")
            return False

    async def execute_cron_trigger(
        self,
        trigger_id: str,
    ) -> str | None:
        """Execute a cron trigger.

        Returns the run_id if execution was started, None otherwise.
        """
        # Get trigger
        trigger = await self.trigger_repo.get_by_id(trigger_id)
        if not trigger:
            logger.warning(f"Cron trigger not found: {trigger_id}")
            return None

        if trigger.type != "cron":
            logger.warning(f"Trigger is not a cron: {trigger.type}")
            return None

        if not trigger.is_active:
            logger.debug(f"Cron trigger is inactive: {trigger_id}")
            return None

        if not trigger.cron_expr:
            logger.warning(f"Cron trigger has no expression: {trigger_id}")
            return None

        # Check if should run (compare with last_triggered_at)
        if trigger.last_triggered_at:
            from croniter import croniter

            cron = croniter(trigger.cron_expr, trigger.last_triggered_at)
            next_run = cron.get_next(datetime)
            if next_run > datetime.now(UTC):
                logger.debug(f"Cron trigger {trigger_id} not due yet: {next_run}")
                return None

        # Execute playbook
        run = None
        try:
            # Get definition
            from repositories.playbook_definition_repository import (
                PlaybookDefinitionRepository,
            )

            definition_repo = PlaybookDefinitionRepository(self.session)
            definition = await definition_repo.get_by_id(trigger.definition_id)
            if not definition:
                logger.warning(f"Definition not found: {trigger.definition_id}")
                return None

            # Validate and compile DAG
            from services.playbook_dag_compiler import DAGCompiler, DAGValidationError

            try:
                compiled = await DAGCompiler.validate_and_compile(
                    definition.definition_json, self.session
                )
            except DAGValidationError as e:
                logger.error(
                    f"Invalid DAG definition for cron trigger {trigger_id}: {e}"
                )
                return None

            # Create run
            input_context = {"trigger_source": "cron"}
            run = await self.run_repo.create(
                playbook_name=definition.name,
                playbook_version=definition.version,
                mode="apply",
                input_json=input_context,
                engine_version="v0.7",
                execution_mode="dag",
                definition_id=trigger.definition_id,
                failure_strategy="fail_fast",
                trigger_source="cron",
                trigger_id=trigger_id,
            )

            # Execute DAG
            from services.playbook_dag_scheduler import DAGScheduler

            scheduler = DAGScheduler(
                session=self.session,
                run_id=run.id,
                compiled_dag=compiled,
                input_context=input_context,
                mode="apply",
                failure_strategy="fail_fast",
            )
            output = await scheduler.execute()

            final_status = (
                "cancelled"
                if scheduler.cancelled
                else ("failed" if scheduler.failed_nodes else "success")
            )
            run_error_message = None
            if final_status == "cancelled":
                run_error_message = "Run cancelled during execution"
            elif final_status == "failed":
                run_error_message = f"Node failures: {len(scheduler.failed_nodes)}"

            await self.run_repo.update(
                run.id,
                status=final_status,
                output_json=output,
                error_message=run_error_message,
            )

            # Update last triggered
            await self.trigger_repo.update_last_triggered(trigger_id)

            # Create audit log
            await self.audit_repo.create(
                action="trigger:execute",
                method="cron",
                path=f"/api/triggers/{trigger_id}/cron",
                status_code=200,
                target_type="trigger",
                target_id=trigger_id,
                extra_json={
                    "trigger_type": "cron",
                    "cron_expr": trigger.cron_expr,
                    "run_id": run.id,
                },
            )
            await self.session.commit()

            logger.info(
                f"Cron trigger executed: {trigger_id} -> run {run.id} ({final_status})"
            )
            return run.id

        except Exception as e:
            logger.error(f"Failed to execute cron trigger {trigger_id}: {e}")

            if run:
                await self.run_repo.update(
                    run.id,
                    status="failed",
                    error_message=str(e),
                )

            # Create audit log
            await self.audit_repo.create(
                action="trigger:execute",
                method="cron",
                path=f"/api/triggers/{trigger_id}/cron",
                status_code=500,
                target_type="trigger",
                target_id=trigger_id,
                extra_json={
                    "trigger_type": "cron",
                    "cron_expr": trigger.cron_expr if trigger else "unknown",
                    "error": str(e),
                },
            )
            await self.session.commit()

            return None

    async def cleanup_invocations(self, hours: int = 24) -> int:
        """Clean up old invocations."""
        return await self.trigger_repo.cleanup_old_invocations(hours)

    async def regenerate_webhook_secret(self, trigger_id: str) -> str:
        """Regenerate a webhook trigger's secret.

        Returns the new secret.
        """
        trigger = await self.trigger_repo.get_by_id(trigger_id)
        if not trigger:
            raise ValueError(f"Trigger not found: {trigger_id}")

        if trigger.type != "webhook":
            raise ValueError(f"Trigger is not a webhook: {trigger.type}")

        new_secret = f"wh_{secrets.token_urlsafe(32)}"
        await self.trigger_repo.update(trigger_id, secret=new_secret)

        logger.info(f"Regenerated webhook secret for: {trigger_id}")
        return new_secret


# Import hashlib at module level

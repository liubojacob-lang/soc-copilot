"""Playbook Engine Adapter - v6/v7 compatibility layer."""

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from models.playbook_run import PlaybookRunModel

logger = get_logger(__name__)


class PlaybookEngineAdapter:
    """Adapter for running playbooks with v6 linear or v7 DAG engine."""

    @staticmethod
    async def run_playbook(
        run: PlaybookRunModel,
        session: AsyncSession,
        playbook_steps: list[str] | None = None,
        dag_definition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run a playbook using the appropriate engine version.

        Args:
            run: Playbook run record
            session: Database session
            playbook_steps: List of step names for v6 linear playbooks
            dag_definition: DAG definition for v7 DAG playbooks

        Returns:
            Execution output dictionary
        """
        engine_version = run.engine_version if run.engine_version else "v0.6"

        logger.info(f"Running playbook {run.id} with engine {engine_version}")

        if engine_version == "v0.6":
            return await PlaybookEngineAdapter._run_v6_linear(
                run, session, playbook_steps
            )
        else:
            return await PlaybookEngineAdapter._run_v7_dag(run, session, dag_definition)

    @staticmethod
    async def _run_v6_linear(
        run: PlaybookRunModel,
        session: AsyncSession,
        steps: list[str] | None = None,
    ) -> dict[str, Any]:
        """Run v0.6 linear playbook."""
        # Import v6 engine
        from .v6_linear.registry import get_registry

        registry = get_registry()

        # Get steps from playbook name or provided steps
        if not steps:
            # Map playbook name to steps (simplified)
            steps_map = {
                "phishing_triage": [
                    "ioc_extract",
                    "ti_lookup_otx",
                    "asset_enrich",
                    "risk_score",
                    "action_plan",
                ],
                "endpoint_malware_triage": [
                    "ioc_extract",
                    "ti_lookup_otx",
                    "asset_enrich",
                    "risk_score",
                    "timeline_build",
                    "action_plan",
                ],
                "suspicious_login_triage": [
                    "ioc_extract",
                    "ti_lookup_otx",
                    "asset_enrich",
                    "risk_score",
                    "action_plan",
                ],
            }
            steps = steps_map.get(run.playbook_name, [])

        # Execute each step
        outputs = {}
        for i, step_id in enumerate(steps):
            step_impl = registry.get_step(step_id)
            if not step_impl:
                logger.warning(f"Step not found: {step_id}, skipping")
                continue

            step_input = {**run.input_json, "prev_output": outputs.get(f"step_{i - 1}")}
            result = await step_impl.execute(step_input)
            outputs[f"step_{i}"] = result

        return {
            "steps": outputs,
            "status": "success",
        }

    @staticmethod
    async def _run_v7_dag(
        run: PlaybookRunModel,
        session: AsyncSession,
        dag_definition: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run v0.7 DAG playbook."""
        from services.playbook_dag_compiler import DAGCompiler
        from services.playbook_dag_scheduler import DAGScheduler

        # Get DAG definition
        if dag_definition:
            dag_json = dag_definition
        elif run.definition_id:
            # Load from database
            from repositories.playbook_definition_repository import (
                PlaybookDefinitionRepository,
            )

            repo = PlaybookDefinitionRepository(session)
            definition = await repo.get_by_id(run.definition_id)
            if not definition:
                raise ValueError(f"DAG definition not found: {run.definition_id}")
            dag_json = definition.dag_json
        else:
            raise ValueError("DAG definition required for v0.7 execution")

        # Compile DAG
        compiled = await DAGCompiler.validate_and_compile(dag_json, session)

        # Execute DAG
        scheduler = DAGScheduler(
            session=session,
            run_id=run.id,
            compiled_dag=compiled,
            input_context=run.input_json,
            failure_strategy=run.failure_strategy or "fail_fast",
        )

        return await scheduler.execute()

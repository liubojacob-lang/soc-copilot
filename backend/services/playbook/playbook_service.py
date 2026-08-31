"""Playbook service for generating queries and actions."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from playbooks.playbook_engine import (
    generate_remediation_actions,
    generate_siem_queries,
)
from repositories.history_repository import HistoryRepository
from repositories.playbook_repository import PlaybookRepository
from schemas.playbook import (
    GenerateActionsRequest,
    GenerateActionsResponse,
    GenerateQueriesRequest,
    GenerateQueriesResponse,
    PlatformQueries,
    PlaybookHistoryResponse,
    RemediationAction,
)

logger = get_logger(__name__)


class PlaybookService:
    """Service for playbook operations."""

    def __init__(self, session: AsyncSession) -> None:
        """Initialize playbook service."""
        self.session = session
        self.playbook_repo = PlaybookRepository(session)
        self.history_repo = HistoryRepository(session)

    async def generate_queries(
        self,
        request: GenerateQueriesRequest,
    ) -> GenerateQueriesResponse:
        """Generate SIEM queries based on IOCs.

        Args:
            request: Query generation request

        Returns:
            Generate queries response with platform-specific queries
        """
        request_id = str(uuid.uuid4())[:8]

        logger.info(
            f"[{request_id}] Generating queries for module={request.module}, "
            f"platforms={request.platforms}, time_ranges={request.time_ranges}"
        )

        degraded = False
        error_reason = None

        try:
            # Get IOCs from history or direct input
            iocs = await self._get_iocs_for_request(request)

            if not any(iocs.values()):
                logger.warning(f"[{request_id}] No IOCs available for query generation")
                degraded = True
                error_reason = "No IOCs provided or found in history"

            # Generate queries for each platform
            results = generate_siem_queries(
                iocs=iocs,
                platforms=request.platforms,
                time_ranges=request.time_ranges,
            )

            # Convert to response format
            platform_queries = []
            for result in results:
                platform_queries.append(
                    PlatformQueries(
                        platform=result["platform"],
                        queries=[
                            {
                                "name": q["name"],
                                "description": q["description"],
                                "query": q["query"],
                                "time_range": q["time_range"],
                                "fields_expected": q["fields_expected"],
                                "prerequisite": q["prerequisite"],
                            }
                            for q in result["queries"]
                        ],
                    )
                )

            # Save to database
            output_json = {
                "platforms": results,
                "meta": {
                    "ioc_counts": {k: len(v) for k, v in iocs.items()},
                    "platforms": request.platforms,
                    "time_ranges": request.time_ranges,
                },
            }

            await self.playbook_repo.create(
                history_id=request.history_id,
                output_type="queries",
                platform=None,
                output_json=output_json,
                request_id=request_id,
                degraded=degraded,
                error_reason=error_reason,
            )

            logger.info(
                f"[{request_id}] Generated {len(platform_queries)} platform query sets"
            )

            return GenerateQueriesResponse(
                request_id=request_id,
                degraded=degraded,
                error_reason=error_reason,
                results=[p.model_dump() for p in platform_queries],
                meta={
                    "ioc_counts": {k: len(v) for k, v in iocs.items()},
                },
            )

        except Exception as e:
            logger.error(f"[{request_id}] Error generating queries: {e}")
            degraded = True
            error_reason = str(e)

            return GenerateQueriesResponse(
                request_id=request_id,
                degraded=True,
                error_reason=error_reason,
                results=[],
            )

    async def generate_actions(
        self,
        request: GenerateActionsRequest,
    ) -> GenerateActionsResponse:
        """Generate remediation actions based on history record.

        Args:
            request: Actions generation request

        Returns:
            Generate actions response with remediation actions
        """
        request_id = str(uuid.uuid4())[:8]

        logger.info(
            f"[{request_id}] Generating actions for history_id={request.history_id}, "
            f"policy={request.policy}"
        )

        degraded = False
        error_reason = None

        try:
            # Get history record
            history = await self.history_repo.get_by_id(request.history_id)
            if not history:
                degraded = True
                error_reason = f"History record {request.history_id} not found"
                logger.error(f"[{request_id}] {error_reason}")
                return GenerateActionsResponse(
                    request_id=request_id,
                    degraded=True,
                    error_reason=error_reason,
                    actions=[],
                )

            # Extract data from history
            output_json = history.output_json
            iocs = history.extracted_iocs or {}
            primary_asset = None
            impact_analysis = output_json.get("impact_analysis")
            threat_intel = output_json.get("threat_intel")

            # Get primary asset info if available
            if impact_analysis and impact_analysis.get("affected_assets"):
                affected_assets = impact_analysis["affected_assets"]
                if affected_assets:
                    # Find highest criticality asset
                    criticality_order = {
                        "critical": 4,
                        "high": 3,
                        "medium": 2,
                        "low": 1,
                    }
                    primary_asset = max(
                        affected_assets,
                        key=lambda a: criticality_order.get(
                            a.get("criticality", "low"), 0
                        ),
                        default=None,
                    )

            # Generate remediation actions
            actions_data = generate_remediation_actions(
                iocs=iocs,
                primary_asset=primary_asset,
                impact_analysis=impact_analysis,
                threat_intel=threat_intel,
                policy=request.policy,
            )

            # Convert to response format
            actions = []
            for action in actions_data:
                actions.append(
                    RemediationAction(
                        title=action["title"],
                        risk=action["risk"],
                        category=action["category"],
                        priority=action["priority"],
                        steps=[
                            {
                                "action": s["action"],
                                "method": s["method"],
                                "command": s.get("command"),
                            }
                            for s in action["steps"]
                        ],
                        verification=action["verification"],
                        rollback=action["rollback"],
                        rationale=action["rationale"],
                    )
                )

            # Save to database
            output_json_data = {
                "actions": actions_data,
                "meta": {
                    "history_id": request.history_id,
                    "policy": request.policy,
                    "primary_asset": primary_asset,
                    "ioc_counts": {k: len(v) for k, v in iocs.items()},
                },
            }

            await self.playbook_repo.create(
                history_id=request.history_id,
                output_type="actions",
                platform=None,
                output_json=output_json_data,
                request_id=request_id,
                degraded=degraded,
                error_reason=error_reason,
            )

            logger.info(f"[{request_id}] Generated {len(actions)} remediation actions")

            return GenerateActionsResponse(
                request_id=request_id,
                degraded=degraded,
                error_reason=error_reason,
                actions=[a.model_dump() for a in actions],
                meta={
                    "history_id": request.history_id,
                    "ioc_counts": {k: len(v) for k, v in iocs.items()},
                },
            )

        except Exception as e:
            logger.error(f"[{request_id}] Error generating actions: {e}")
            degraded = True
            error_reason = str(e)

            return GenerateActionsResponse(
                request_id=request_id,
                degraded=True,
                error_reason=error_reason,
                actions=[],
            )

    async def get_history(
        self,
        history_id: str | None = None,
        limit: int = 50,
    ) -> PlaybookHistoryResponse:
        """Get playbook generation history.

        Args:
            history_id: Optional filter by source history ID
            limit: Maximum number of records to return

        Returns:
            Playbook history response
        """
        if history_id:
            records = await self.playbook_repo.list_by_history(history_id, limit=limit)
        else:
            records = await self.playbook_repo.list_all(limit=limit)

        items = [self.playbook_repo.to_response(r) for r in records]

        return PlaybookHistoryResponse(
            items=items,
            total=len(items),
        )

    async def _get_iocs_for_request(
        self,
        request: GenerateQueriesRequest,
    ) -> dict[str, list[str]]:
        """Get IOCs from direct input or history record.

        Args:
            request: Query generation request

        Returns:
            Dict with 'ips', 'domains', 'urls', 'hashes' lists
        """
        # Direct input takes precedence
        if request.iocs:
            return {
                "ips": request.iocs.get("ips", []),
                "domains": request.iocs.get("domains", []),
                "urls": request.iocs.get("urls", []),
                "hashes": request.iocs.get("hashes", []),
            }

        # Load from history
        if request.history_id:
            history = await self.history_repo.get_by_id(request.history_id)
            if history:
                return history.extracted_iocs or {
                    "ips": [],
                    "domains": [],
                    "urls": [],
                    "hashes": [],
                }

        return {
            "ips": [],
            "domains": [],
            "urls": [],
            "hashes": [],
        }

    # ══════════════════════════════════════════════════════════════════════════
    # DAG Definition Execution (S0-8/9: extracted from routers/playbook/definitions.py)
    # ══════════════════════════════════════════════════════════════════════════

    async def list_definitions(
        self, is_active: bool | None = None, page: int = 1, page_size: int = 20
    ) -> dict[str, object]:
        """List DAG playbook definitions with pagination."""
        from sqlalchemy import func

        from models.playbook_definition import PlaybookDefinitionModel

        base_stmt = select(PlaybookDefinitionModel)
        if is_active is not None:
            base_stmt = base_stmt.where(PlaybookDefinitionModel.is_active == is_active)

        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        count_result = await self.session.execute(count_stmt)
        total = count_result.scalar() or 0

        stmt = base_stmt.order_by(PlaybookDefinitionModel.created_at.desc())
        stmt = stmt.offset((page - 1) * page_size).limit(page_size)

        result = await self.session.execute(stmt)
        definitions = result.scalars().all()

        return {
            "definitions": [
                {
                    "id": d.id,
                    "name": d.name,
                    "description": d.description,
                    "version": d.version,
                    "is_active": d.is_active,
                    "created_at": d.created_at.isoformat(),
                    "updated_at": d.updated_at.isoformat(),
                }
                for d in definitions
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    async def create_definition(
        self,
        name: str,
        description: str | None,
        version: str,
        definition_json: dict,
        created_by: str,
    ) -> dict[str, object]:
        """Create a new DAG playbook definition."""
        import uuid

        from models.playbook_definition import PlaybookDefinitionModel

        definition = PlaybookDefinitionModel(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            version=version,
            definition_json=definition_json,
            created_by=created_by,
            is_active=True,
        )
        self.session.add(definition)
        await self.session.commit()
        return {
            "id": definition.id,
            "name": definition.name,
            "description": definition.description,
            "version": definition.version,
            "is_active": definition.is_active,
            "created_at": definition.created_at.isoformat(),
        }

    async def get_definition(self, definition_id: str) -> dict[str, object] | None:
        """Get a DAG playbook definition by ID."""
        from models.playbook_definition import PlaybookDefinitionModel

        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == definition_id
        )
        result = await self.session.execute(stmt)
        definition = result.scalar_one_or_none()

        if not definition:
            return None

        return {
            "id": definition.id,
            "name": definition.name,
            "description": definition.description,
            "version": definition.version,
            "definition_json": definition.definition_json,
            "is_active": definition.is_active,
            "created_at": definition.created_at.isoformat(),
            "updated_at": definition.updated_at.isoformat(),
        }

    async def execute_dag_definition(
        self,
        definition_id: str,
        input_json: dict[str, object],
        mode: str,
        created_by_user_id: str,
    ) -> dict[str, object]:
        """Execute a DAG-based playbook definition.

        Orchestrates definition lookup, run creation, DAG parsing, execution,
        and result compilation.
        """
        import uuid

        from models.playbook_definition import PlaybookDefinitionModel
        from playbook_engine.dag import DAGBuilder, DAGExecutionEngine
        from repositories.playbook_run_repository import PlaybookRunRepository

        # Get definition
        stmt = select(PlaybookDefinitionModel).where(
            PlaybookDefinitionModel.id == definition_id
        )
        result = await self.session.execute(stmt)
        definition = result.scalar_one_or_none()

        if not definition:
            raise ValueError(f"Definition not found: {definition_id}")
        if not definition.is_active:
            raise ValueError("Definition is not active")

        # Create run record
        run_repo = PlaybookRunRepository(self.session)
        run_id = str(uuid.uuid4())

        await run_repo.create(
            playbook_name=definition.name,
            playbook_version=definition.version,
            mode=mode,
            status="running",
            created_by_user_id=created_by_user_id,
            input_json=input_json or {},
            output_json={},
            execution_mode="dag",
            definition_id=definition.id,
            trigger_source="manual",
        )
        await self.session.flush()

        # Parse and execute DAG
        dag_definition = DAGBuilder.from_json(definition.definition_json)
        engine = DAGExecutionEngine(self.session)

        result_data = await engine.execute_dag(
            definition=dag_definition,
            run_id=run_id,
            input_json=input_json or {},
            mode=mode,
            created_by_user_id=created_by_user_id,
        )

        return {
            "run_id": run_id,
            "status": result_data["status"],
            "failed_nodes": result_data.get("failed_nodes", []),
            "skipped_nodes": result_data.get("skipped_nodes", []),
        }

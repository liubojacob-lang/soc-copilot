"""Event correlation API endpoints."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from core.metrics import observe_correlation_rule_hit
from db.session import get_session
from dependencies.auth import get_current_user
from models.correlated_event import CorrelatedEvent
from models.correlation_rule import CorrelationRule
from models.user import UserModel
from services.correlation import CorrelationRuleDSL, RuleEngine
from services.event_bus import get_event_bus
from services.event_correlation_service import (
    EventCorrelationService,
)

logger = get_logger(__name__)

router = APIRouter(tags=["correlation"], prefix="/api/correlation")


# Request/Response Schemas
class CorrelationRequest(BaseModel):
    """Request to correlate events."""

    events: list[dict]
    rule_ids: list[str] | None = None


class CorrelationRuleCreate(BaseModel):
    """Request to create a correlation rule."""

    name: str
    description: str | None = None
    time_window_seconds: int = 300
    entity_types: dict = None
    min_similarity: float = 0.7
    conditions: dict | None = None
    action: str = "aggregate"
    action_params: dict | None = None
    priority: int = 50
    group_by_field: str | None = None


class CorrelationRuleUpdate(BaseModel):
    """Request to update a correlation rule."""

    name: str | None = None
    description: str | None = None
    enabled: bool | None = None
    time_window_seconds: int | None = None
    entity_types: dict | None = None
    min_similarity: float | None = None
    conditions: dict | None = None
    action: str | None = None
    action_params: dict | None = None
    priority: int | None = None
    group_by_field: str | None = None


class CorrelatedEventResponse(BaseModel):
    """Response for correlated event."""

    id: str
    title: str
    description: str | None
    severity: str
    attack_type: str | None
    confidence_score: float
    raw_event_count: int
    common_entities: dict
    first_seen: str
    last_seen: str
    status: str
    risk_score: float
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class RuleEngineEvaluateRequest(BaseModel):
    events: list[dict]
    rules: list[CorrelationRuleDSL]


class RuleEngineEvaluateResponse(BaseModel):
    incidents: list[dict]
    execution_logs: list[dict]


# Endpoints
@router.post("/correlate", response_model=list[CorrelatedEventResponse])
async def correlate_events(
    http_request: Request,
    request: CorrelationRequest,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Correlate a batch of events into incidents.

    This endpoint processes raw events/alerts and groups related events
    into higher-level security incidents using correlation rules.
    """
    try:
        service = EventCorrelationService(db)
        correlated_events = await service.correlate_events(
            events=request.events, rule_ids=request.rule_ids
        )

        # Update rule statistics
        tenant_id = http_request.headers.get("x-tenant-id", "default")
        for event in correlated_events:
            rule = await db.get(CorrelationRule, event.rule_id)
            if rule:
                rule.total_correlations += 1
                rule.last_triggered = datetime.now(UTC).isoformat()
                observe_correlation_rule_hit(str(rule.id), tenant_id)

        await db.commit()

        # Publish correlation result events to unified event bus
        event_bus = get_event_bus()
        for incident in correlated_events:
            await event_bus.publish(
                event_type="correlation.incident.created",
                source="correlation-engine",
                payload={
                    "incident_id": incident.id,
                    "rule_id": incident.rule_id,
                    "severity": incident.severity,
                    "raw_event_count": incident.raw_event_count,
                },
                event_id=str(incident.id),
                priority=str(incident.severity).lower(),
            )

        return correlated_events

    except Exception as e:
        logger.error(f"Error during correlation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/dsl/example", response_model=dict)
async def get_rule_dsl_example(current_user: UserModel = Depends(get_current_user)) -> dict:
    """Get a DSL sample for building advanced correlation rules."""
    return RuleEngine().dsl_example()


@router.post("/engine/evaluate", response_model=RuleEngineEvaluateResponse)
async def evaluate_rule_engine(
    request: RuleEngineEvaluateRequest,
    current_user: UserModel = Depends(get_current_user),
) -> RuleEngineEvaluateResponse:
    """Evaluate rules using DSL engine (non-persistent)."""
    engine = RuleEngine()
    incidents = engine.execute(request.events, request.rules)
    return RuleEngineEvaluateResponse(
        incidents=incidents,
        execution_logs=[log.model_dump(mode="json") for log in engine.execution_logs],
    )


@router.get("/incidents", response_model=list[CorrelatedEventResponse])
async def list_correlated_events(
    status: str | None = Query(None, description="Filter by status"),
    severity: str | None = Query(None, description="Filter by severity"),
    attack_type: str | None = Query(None, description="Filter by attack type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """
    List correlated incidents.

    Supports filtering by status, severity, and attack type.
    """
    from sqlalchemy import desc, select

    query = select(CorrelatedEvent).order_by(desc(CorrelatedEvent.first_seen))

    # Apply filters
    if status:
        query = query.where(CorrelatedEvent.status == status)
    if severity:
        query = query.where(CorrelatedEvent.severity == severity)
    if attack_type:
        query = query.where(CorrelatedEvent.attack_type == attack_type)

    # Pagination
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    incidents = result.scalars().all()

    return incidents


@router.get("/incidents/{incident_id}", response_model=CorrelatedEventResponse)
async def get_correlated_event(
    incident_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """Get details of a specific correlated incident."""
    from sqlalchemy import select

    query = select(CorrelatedEvent).where(CorrelatedEvent.id == incident_id)
    result = await db.execute(query)
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    return incident


@router.put("/incidents/{incident_id}/status")
async def update_incident_status(
    incident_id: str,
    status: str = Query(..., description="New status"),
    assigned_to: str | None = Query(None, description="Assign to analyst"),
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Update incident status and assignment.

    Valid statuses: open, investigating, resolved, false_positive, closed
    """
    from sqlalchemy import select

    query = select(CorrelatedEvent).where(CorrelatedEvent.id == incident_id)
    result = await db.execute(query)
    incident = result.scalar_one_or_none()

    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")

    # Validate status
    valid_statuses = ["open", "investigating", "resolved", "false_positive", "closed"]
    if status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}",
        )

    # Update
    incident.status = status
    if assigned_to:
        incident.assigned_to = assigned_to

    if status in ["resolved", "false_positive", "closed"]:
        incident.resolved_at = datetime.now(UTC).isoformat()

    incident.updated_at = datetime.now(UTC).isoformat()

    await db.commit()

    return {
        "success": True,
        "incident_id": incident_id,
        "status": status,
        "assigned_to": assigned_to,
        "updated_at": incident.updated_at,
    }


# Correlation Rules CRUD
@router.get("/rules")
async def list_correlation_rules(
    enabled_only: bool = Query(False, description="Only show enabled rules"),
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """List all correlation rules."""
    from sqlalchemy import select

    query = select(CorrelationRule).order_by(CorrelationRule.priority.desc())

    if enabled_only:
        query = query.where(CorrelationRule.enabled == True)

    result = await db.execute(query)
    rules = result.scalars().all()

    return {
        "rules": [
            {
                "id": rule.id,
                "name": rule.name,
                "description": rule.description,
                "enabled": rule.enabled,
                "is_builtin": rule.is_builtin,
                "time_window_seconds": rule.time_window_seconds,
                "entity_types": rule.entity_types,
                "min_similarity": rule.min_similarity,
                "action": rule.action,
                "priority": rule.priority,
                "total_correlations": rule.total_correlations,
                "last_triggered": rule.last_triggered,
                "created_at": rule.created_at,
            }
            for rule in rules
        ],
        "count": len(rules),
    }


@router.post("/rules")
async def create_correlation_rule(
    rule: CorrelationRuleCreate,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """Create a new correlation rule."""
    try:
        new_rule = CorrelationRule(
            name=rule.name,
            description=rule.description,
            time_window_seconds=rule.time_window_seconds,
            entity_types=rule.entity_types or {"ip_address": True, "username": True},
            min_similarity=rule.min_similarity,
            conditions=rule.conditions,
            action=rule.action,
            action_params=rule.action_params,
            priority=rule.priority,
            group_by_field=rule.group_by_field,
        )

        db.add(new_rule)
        await db.commit()
        await db.refresh(new_rule)

        logger.info(f"Created correlation rule: {new_rule.id}")

        return {
            "success": True,
            "rule_id": new_rule.id,
            "rule": {
                "id": new_rule.id,
                "name": new_rule.name,
                "enabled": new_rule.enabled,
                "priority": new_rule.priority,
            },
        }

    except Exception as e:
        logger.error(f"Error creating rule: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/rules/{rule_id}")
async def update_correlation_rule(
    rule_id: str,
    updates: CorrelationRuleUpdate,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """Update an existing correlation rule."""
    from sqlalchemy import select

    query = select(CorrelationRule).where(CorrelationRule.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Don't allow updating builtin rules
    if rule.is_builtin:
        raise HTTPException(status_code=403, detail="Cannot update built-in rules")

    # Apply updates
    update_data = updates.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)

    rule.updated_at = datetime.now(UTC).isoformat()

    await db.commit()

    return {
        "success": True,
        "rule_id": rule_id,
        "updated_fields": list(update_data.keys()),
    }


@router.delete("/rules/{rule_id}")
async def delete_correlation_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """Delete a correlation rule."""
    from sqlalchemy import select

    query = select(CorrelationRule).where(CorrelationRule.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    # Don't allow deleting builtin rules
    if rule.is_builtin:
        raise HTTPException(status_code=403, detail="Cannot delete built-in rules")

    await db.delete(rule)
    await db.commit()

    logger.info(f"Deleted correlation rule: {rule_id}")

    return {"success": True, "message": f"Rule {rule_id} deleted"}


@router.post("/rules/{rule_id}/toggle")
async def toggle_correlation_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """Enable or disable a correlation rule."""
    from sqlalchemy import select

    query = select(CorrelationRule).where(CorrelationRule.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    rule.enabled = not rule.enabled
    rule.updated_at = datetime.now(UTC).isoformat()

    await db.commit()

    logger.info(f"Toggled rule {rule_id} to {rule.enabled}")

    return {"success": True, "rule_id": rule_id, "enabled": rule.enabled}


# Statistics
@router.get("/stats")
async def get_correlation_stats(
    db: AsyncSession = Depends(get_session), current_user: UserModel = Depends(get_current_user)
):
    """Get correlation statistics."""
    from sqlalchemy import func, select

    # Total incidents
    total_incidents = await db.execute(select(func.count(CorrelatedEvent.id)))
    total_count = total_incidents.scalar() or 0

    # Incidents by status
    status_counts = await db.execute(
        select(CorrelatedEvent.status, func.count(CorrelatedEvent.id)).group_by(
            CorrelatedEvent.status
        )
    )
    by_status = {status: count for status, count in status_counts.all()}

    # Incidents by severity
    severity_counts = await db.execute(
        select(CorrelatedEvent.severity, func.count(CorrelatedEvent.id)).group_by(
            CorrelatedEvent.severity
        )
    )
    by_severity = {severity: count for severity, count in severity_counts.all()}

    # Total rules
    total_rules = await db.execute(select(func.count(CorrelationRule.id)))
    rules_count = total_rules.scalar() or 0

    # Active rules
    active_rules = await db.execute(
        select(func.count(CorrelationRule.id)).where(CorrelationRule.enabled == True)
    )
    active_count = active_rules.scalar() or 0

    # Total correlations performed
    total_correlations = await db.execute(select(func.sum(CorrelationRule.total_correlations)))
    correlations_count = total_correlations.scalar() or 0

    return {
        "incidents": {
            "total": total_count,
            "by_status": by_status,
            "by_severity": by_severity,
        },
        "rules": {
            "total": rules_count,
            "active": active_count,
            "total_correlations_performed": correlations_count,
        },
        "generated_at": datetime.now(UTC).isoformat(),
    }


@router.post("/test")
async def test_correlation_rule(
    rule_id: str,
    test_events: list[dict],
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Test a correlation rule against sample events.

    Does not persist results. Useful for rule development.
    """
    from sqlalchemy import select

    query = select(CorrelationRule).where(CorrelationRule.id == rule_id)
    result = await db.execute(query)
    rule = result.scalar_one_or_none()

    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    try:
        service = EventCorrelationService(db)
        correlated_events = await service.correlate_events(events=test_events, rule_ids=[rule_id])

        return {
            "success": True,
            "rule_id": rule_id,
            "rule_name": rule.name,
            "input_events": len(test_events),
            "correlated_incidents": len(correlated_events),
            "incidents": [
                {
                    "title": inc.title,
                    "raw_event_count": inc.raw_event_count,
                    "confidence_score": inc.confidence_score,
                    "common_entities": inc.common_entities,
                }
                for inc in correlated_events
            ],
        }

    except Exception as e:
        logger.error(f"Error testing rule: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

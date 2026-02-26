"""
Monitoring Alert Rules API

REST API endpoints for managing monitoring alert rules.

Endpoints:
- POST /api/v1/monitoring/alerts/rules - Create alert rule
- GET /api/v1/monitoring/alerts/rules - List alert rules
- GET /api/v1/monitoring/alerts/rules/{id} - Get alert rule
- PUT /api/v1/monitoring/alerts/rules/{id} - Update alert rule
- DELETE /api/v1/monitoring/alerts/rules/{id} - Delete alert rule
- GET /api/v1/monitoring/alerts/history - Get alert history
- GET /api/v1/monitoring/alerts/stats - Get alert statistics
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from core.logger import get_logger, set_request_context
from dependencies.auth import get_current_user
from models.monitoring_alerts import (
    AlertRule,
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertHistory,
    AlertStats,
)
from services.alert_evaluator import get_alert_evaluator
from schemas.user import UserResponse

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/monitoring/alerts", tags=["Monitoring Alerts"])


# Dependency
async def get_evaluator_dep():
    """Get alert evaluator dependency."""
    return get_alert_evaluator()


@router.post("/rules", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    current_user: UserResponse = Depends(get_current_user),
    evaluator = Depends(get_evaluator_dep)
):
    """
    Create a new alert rule.

    Creates an alert rule that will trigger when the specified
    metric conditions are met.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        rule = AlertRule(
            user_id=str(current_user.id),
            **rule_data.model_dump()
        )

        await evaluator.add_rule(rule)

        logger.info(f"Created alert rule '{rule.name}' for user {current_user.id}")

        return AlertRuleResponse.model_validate(rule)

    except Exception as e:
        logger.error(f"Error creating alert rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create alert rule: {str(e)}")


@router.get("/rules", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    enabled_only: bool = False,
    current_user: UserResponse = Depends(get_current_user),
    evaluator = Depends(get_evaluator_dep)
):
    """
    List alert rules for the current user.

    Returns all alert rules owned by the current user.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        rules = await evaluator.get_rules(user_id=str(current_user.id))

        if enabled_only:
            rules = [r for r in rules if r.enabled]

        return [AlertRuleResponse.model_validate(r) for r in rules]

    except Exception as e:
        logger.error(f"Error listing alert rules: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list alert rules: {str(e)}")


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: str,
    current_user: UserResponse = Depends(get_current_user),
    evaluator = Depends(get_evaluator_dep)
):
    """
    Get a specific alert rule.

    Returns the alert rule with the specified ID if owned by the user.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        rule = await evaluator.get_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        if rule.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        return AlertRuleResponse.model_validate(rule)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting alert rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alert rule: {str(e)}")


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: str,
    updates: AlertRuleUpdate,
    current_user: UserResponse = Depends(get_current_user),
    evaluator = Depends(get_evaluator_dep)
):
    """
    Update an alert rule.

    Updates the specified alert rule if owned by the user.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        # Check ownership
        rule = await evaluator.get_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        if rule.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Update rule
        update_dict = updates.model_dump(exclude_unset=True)
        success = await evaluator.update_rule(rule_id, update_dict)

        if not success:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        # Get updated rule
        updated_rule = await evaluator.get_rule(rule_id)

        logger.info(f"Updated alert rule {rule_id}")

        return AlertRuleResponse.model_validate(updated_rule)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update alert rule: {str(e)}")


@router.delete("/rules/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    current_user: UserResponse = Depends(get_current_user),
    evaluator = Depends(get_evaluator_dep)
):
    """
    Delete an alert rule.

    Deletes the specified alert rule if owned by the user.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        # Check ownership
        rule = await evaluator.get_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        if rule.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Delete rule
        success = await evaluator.remove_rule(rule_id)

        if not success:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        logger.info(f"Deleted alert rule {rule_id}")

        return {"message": "Alert rule deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting alert rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete alert rule: {str(e)}")


@router.get("/history", response_model=List[AlertHistory])
async def get_alert_history(
    limit: int = Query(100, ge=1, le=1000),
    current_user: UserResponse = Depends(get_current_user),
    evaluator = Depends(get_evaluator_dep)
):
    """
    Get alert history for the current user.

    Returns historical triggered alerts for the user's rules.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        history = await evaluator.get_history(user_id=str(current_user.id), limit=limit)

        return history

    except Exception as e:
        logger.error(f"Error getting alert history: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alert history: {str(e)}")


@router.get("/stats", response_model=AlertStats)
async def get_alert_stats(
    current_user: UserResponse = Depends(get_current_user),
    evaluator = Depends(get_evaluator_dep)
):
    """
    Get alert statistics for the current user.

    Returns statistics about alert rules and triggers.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        stats = await evaluator.get_stats(user_id=str(current_user.id))

        return AlertStats(**stats)

    except Exception as e:
        logger.error(f"Error getting alert stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get alert stats: {str(e)}")


@router.post("/test/{rule_id}")
async def test_alert_rule(
    rule_id: str,
    current_user: UserResponse = Depends(get_current_user),
    evaluator = Depends(get_evaluator_dep)
):
    """
    Test an alert rule against current metrics.

    Evaluates the rule against current WebSocket metrics
    without sending actual notifications.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        # Check ownership
        rule = await evaluator.get_rule(rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="Alert rule not found")

        if rule.user_id != str(current_user.id):
            raise HTTPException(status_code=403, detail="Access denied")

        # Get current metrics
        from services.websocket_monitoring import get_websocket_monitoring
        monitoring = get_websocket_monitoring()
        metrics = await monitoring.get_current_metrics()

        # Evaluate rule
        metric_values = evaluator._extract_metric_values(metrics)
        should_trigger, reason = rule.should_trigger(metric_values)

        return {
            "rule_id": rule_id,
            "rule_name": rule.name,
            "should_trigger": should_trigger,
            "reason": reason,
            "current_metrics": metric_values,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing alert rule: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test alert rule: {str(e)}")

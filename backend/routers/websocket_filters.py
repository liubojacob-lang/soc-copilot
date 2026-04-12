"""
WebSocket Filter Management API

REST API endpoints for managing server-side WebSocket message filters.

Endpoints:
- GET /api/v1/websocket/filters - Get user's filters
- PUT /api/v1/websocket/filters - Set user's filters
- DELETE /api/v1/websocket/filters - Remove user's filters
- GET /api/v1/websocket/filters/stats - Get filter statistics
"""


from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.logger import get_logger, set_request_context
from dependencies.auth import get_current_user
from models.message_filters import (
    FilterRule,
    FilterSet,
    FilterStats,
    FilterValidationResult,
    SeverityLevel,
    StringFilter,
)
from schemas.user import UserResponse
from services.message_filter import get_filter_service

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/websocket/filters", tags=["WebSocket Filters"])


# Pydantic schemas for API
class FilterRuleCreate(BaseModel):
    """Schema for creating a filter rule"""

    name: str
    description: str = ""
    priority: int = 0
    enabled: bool = True
    min_severity: SeverityLevel | None = None
    max_severity: SeverityLevel | None = None
    event_types: StringFilter | None = None
    agent_ids: StringFilter | None = None
    source_ips: StringFilter | None = None
    content_search: StringFilter | None = None
    enable_aggregation: bool = True
    max_messages_per_minute: int | None = None


class FilterRuleResponse(BaseModel):
    """Schema for filter rule response"""

    id: str | None
    name: str
    description: str
    enabled: bool
    priority: int
    min_severity: SeverityLevel | None = None
    max_severity: SeverityLevel | None = None
    event_types: StringFilter | None = None
    agent_ids: StringFilter | None = None
    source_ips: StringFilter | None = None
    content_search: StringFilter | None = None
    enable_aggregation: bool
    max_messages_per_minute: int | None
    created_at: str
    updated_at: str
    last_triggered_at: str | None

    class Config:
        from_attributes = True


class FilterSetCreate(BaseModel):
    """Schema for creating a filter set"""

    default_action: str = "allow"
    rules: list[FilterRuleCreate] = []


class FilterSetResponse(BaseModel):
    """Schema for filter set response"""

    user_id: str
    default_action: str
    rules: list[FilterRuleResponse]
    updated_at: str

    class Config:
        from_attributes = True


# Dependency
async def get_filter_service_dep():
    """Get filter service dependency."""
    return get_filter_service()


@router.get("/", response_model=FilterSetResponse)
async def get_filters(
    current_user: UserResponse = Depends(get_current_user),
    filter_service=Depends(get_filter_service_dep),
):
    """
    Get current user's WebSocket message filters.

    Returns the user's filter set with all rules.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        filter_set = await filter_service.get_user_filters(str(current_user.id))

        if not filter_set:
            # Return empty filter set
            return FilterSetResponse(
                user_id=str(current_user.id),
                default_action="allow",
                rules=[],
                updated_at="",
            )

        return FilterSetResponse.model_validate(filter_set)

    except Exception as e:
        logger.error(f"Error getting filters: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get filters: {e!s}")


@router.put("/", response_model=FilterSetResponse)
async def set_filters(
    filters_data: FilterSetCreate,
    current_user: UserResponse = Depends(get_current_user),
    filter_service=Depends(get_filter_service_dep),
):
    """
    Set or replace user's WebSocket message filters.

    Creates a new filter set with the provided rules.
    Replaces any existing filters for the user.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        # Convert API models to domain models
        rules = []
        for rule_data in filters_data.rules:
            rule = FilterRule(
                user_id=str(current_user.id),
                name=rule_data.name,
                description=rule_data.description,
                priority=rule_data.priority,
                enabled=rule_data.enabled,
                min_severity=rule_data.min_severity,
                max_severity=rule_data.max_severity,
                event_types=rule_data.event_types,
                agent_ids=rule_data.agent_ids,
                source_ips=rule_data.source_ips,
                content_search=rule_data.content_search,
                enable_aggregation=rule_data.enable_aggregation,
                max_messages_per_minute=rule_data.max_messages_per_minute,
            )
            rules.append(rule)

        filter_set = FilterSet(
            user_id=str(current_user.id),
            default_action=filters_data.default_action,
            rules=rules,
        )

        await filter_service.set_user_filters(str(current_user.id), filter_set)

        logger.info(f"Set {len(rules)} filter rules for user {current_user.id}")

        return FilterSetResponse.model_validate(filter_set)

    except Exception as e:
        logger.error(f"Error setting filters: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to set filters: {e!s}")


@router.delete("/")
async def delete_filters(
    current_user: UserResponse = Depends(get_current_user),
    filter_service=Depends(get_filter_service_dep),
):
    """
    Delete all filters for the current user.

    Removes the user's filter set, allowing all messages through.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        success = await filter_service.remove_user_filters(str(current_user.id))

        if not success:
            raise HTTPException(status_code=404, detail="No filters found for user")

        logger.info(f"Deleted filters for user {current_user.id}")

        return {"message": "Filters deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting filters: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to delete filters: {e!s}"
        )


@router.get("/stats", response_model=FilterStats)
async def get_filter_stats(
    current_user: UserResponse = Depends(get_current_user),
    filter_service=Depends(get_filter_service_dep),
):
    """
    Get filter statistics for the current user.

    Returns statistics about message filtering performance.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        stats = await filter_service.get_user_stats(str(current_user.id))

        if not stats:
            # Return empty stats
            return FilterStats(user_id=str(current_user.id))

        return stats

    except Exception as e:
        logger.error(f"Error getting filter stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get stats: {e!s}")


@router.post("/stats/reset")
async def reset_filter_stats(
    current_user: UserResponse = Depends(get_current_user),
    filter_service=Depends(get_filter_service_dep),
):
    """
    Reset filter statistics for the current user.

    Clears all accumulated statistics, starting fresh.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        success = await filter_service.reset_user_stats(str(current_user.id))

        if not success:
            raise HTTPException(status_code=404, detail="No stats found for user")

        logger.info(f"Reset filter stats for user {current_user.id}")

        return {"message": "Filter statistics reset successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resetting stats: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to reset stats: {e!s}")


@router.post("/test", response_model=FilterValidationResult)
async def test_filter(
    message_data: dict,
    current_user: UserResponse = Depends(get_current_user),
    filter_service=Depends(get_filter_service_dep),
):
    """
    Test a message against user's filters without sending it.

    Useful for previewing whether a message would be allowed or blocked.
    """
    set_request_context(user_id=str(current_user.id), user_role=current_user.role)

    try:
        result = await filter_service.should_send_message(
            user_id=str(current_user.id), message_data=message_data
        )

        return result

    except Exception as e:
        logger.error(f"Error testing filter: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to test filter: {e!s}")

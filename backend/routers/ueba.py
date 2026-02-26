"""
UEBA Router - User and Entity Behavior Analytics API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import datetime

from core.logger import get_logger
from dependencies.auth import get_current_user
from models.user import UserModel, UserRole
from services.ueba_service import (
    get_ueba_engine,
    BehaviorType,
    RiskLevel,
    AnomalyDetection,
    UserRiskProfile,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/ueba", tags=["ueba", "analytics"])


# Request/Response Models
class BehaviorDataInput(BaseModel):
    """Input for behavior analysis."""

    entity_id: str
    entity_type: str = Field(default="user", pattern="^(user|host|ip)$")
    login_time: Optional[datetime] = None
    data_volume_mb: Optional[float] = None
    accessed_hosts: Optional[List[str]] = None
    accessed_files: Optional[List[str]] = None
    processes_created: Optional[List[str]] = None


class AnomalyDetectionResponse(BaseModel):
    """Response for anomaly detection."""

    entity_id: str
    behavior_type: str
    anomaly_score: float
    risk_level: str
    description: str
    indicators: List[str]
    recommended_actions: List[str]
    detected_at: datetime


class RiskProfileResponse(BaseModel):
    """User risk profile response."""

    user_id: str
    username: str
    overall_risk_score: float
    risk_level: str
    risk_factors: List[dict]
    anomalous_behaviors: List[AnomalyDetectionResponse]
    compromised_probability: float
    last_activity: datetime


class BaselineBuildRequest(BaseModel):
    """Request to build behavior baseline."""

    entity_id: str
    entity_type: str = Field(default="user", pattern="^(user|host|ip)$")
    days_of_history: int = Field(default=30, ge=7, le=90)


@router.post("/detect", response_model=List[AnomalyDetectionResponse])
async def detect_anomalies(
    data: BehaviorDataInput,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Detect behavioral anomalies for an entity.

    Analyzes current behavior against established baseline to identify:
    - Unusual login times
    - Abnormal data access patterns
    - Lateral movement
    - Data exfiltration attempts
    """
    try:
        engine = get_ueba_engine()

        current_behavior = {
            "login_time": data.login_time,
            "data_volume_mb": data.data_volume_mb,
            "accessed_hosts": data.accessed_hosts,
            "accessed_files": data.accessed_files,
            "processes_created": data.processes_created,
        }

        # Remove None values
        current_behavior = {k: v for k, v in current_behavior.items() if v is not None}

        anomalies = await engine.detect_anomalies(
            entity_id=data.entity_id, current_behavior=current_behavior
        )

        return [
            AnomalyDetectionResponse(
                entity_id=a.entity_id,
                behavior_type=a.behavior_type.value,
                anomaly_score=a.anomaly_score,
                risk_level=a.risk_level.value,
                description=a.description,
                indicators=a.indicators,
                recommended_actions=a.recommended_actions,
                detected_at=a.detected_at,
            )
            for a in anomalies
        ]

    except Exception as e:
        logger.error(f"Error detecting anomalies: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Anomaly detection failed: {str(e)}",
        )


@router.get("/risk-profile/{user_id}", response_model=RiskProfileResponse)
async def get_user_risk_profile(
    user_id: str,
    days_to_analyze: int = Query(default=7, ge=1, le=30),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get comprehensive risk profile for a user.

    Returns overall risk score, risk factors, and anomalous behaviors.
    """
    try:
        engine = get_ueba_engine()

        profile = await engine.get_user_risk_profile(
            user_id=user_id, days_to_analyze=days_to_analyze
        )

        return RiskProfileResponse(
            user_id=profile.user_id,
            username=profile.username,
            overall_risk_score=profile.overall_risk_score,
            risk_level=profile.risk_level.value,
            risk_factors=profile.risk_factors,
            anomalous_behaviors=[
                AnomalyDetectionResponse(
                    entity_id=a.entity_id,
                    behavior_type=a.behavior_type.value,
                    anomaly_score=a.anomaly_score,
                    risk_level=a.risk_level.value,
                    description=a.description,
                    indicators=a.indicators,
                    recommended_actions=a.recommended_actions,
                    detected_at=a.detected_at,
                )
                for a in profile.anomalous_behaviors
            ],
            compromised_probability=profile.compromised_probability,
            last_activity=profile.last_activity,
        )

    except Exception as e:
        logger.error(f"Error getting risk profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get risk profile: {str(e)}",
        )


@router.post("/build-baseline")
async def build_baseline(
    request: BaselineBuildRequest,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Build behavior baseline for an entity.

    Analyzes historical data to establish normal behavior patterns.
    """
    try:
        engine = get_ueba_engine()

        baseline = await engine.build_baseline(
            entity_id=request.entity_id,
            entity_type=request.entity_type,
            days_of_history=request.days_of_history,
        )

        return {
            "entity_id": baseline.entity_id,
            "entity_type": baseline.entity_type,
            "login_times": baseline.login_times,
            "typical_data_volume": baseline.typical_data_volume,
            "typical_connections": baseline.typical_connections,
            "last_updated": baseline.last_updated,
            "status": "baseline_created",
        }

    except Exception as e:
        logger.error(f"Error building baseline: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Baseline building failed: {str(e)}",
        )


@router.get("/high-risk-users")
async def get_high_risk_users(
    risk_threshold: float = Query(default=70.0, ge=0, le=100),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get list of high-risk users.

    Returns users with risk score above threshold.
    """
    try:
        # In production, query from database
        # For now, return sample data

        sample_users = [
            {
                "user_id": "user_001",
                "username": "john.doe",
                "risk_score": 85.5,
                "risk_level": "high",
                "anomaly_count": 3,
                "last_anomaly": "2024-01-15T14:30:00",
                "primary_risks": ["off_hours_login", "unusual_data_access"],
            },
            {
                "user_id": "user_002",
                "username": "jane.smith",
                "risk_score": 72.0,
                "risk_level": "medium",
                "anomaly_count": 2,
                "last_anomaly": "2024-01-15T10:15:00",
                "primary_risks": ["geolocation_anomaly"],
            },
        ]

        # Filter by threshold
        high_risk = [u for u in sample_users if u["risk_score"] >= risk_threshold]

        return {
            "users": high_risk[:limit],
            "total_count": len(high_risk),
            "threshold": risk_threshold,
        }

    except Exception as e:
        logger.error(f"Error getting high risk users: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get high risk users: {str(e)}",
        )


@router.get("/dashboard")
async def get_ueba_dashboard(
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get UEBA dashboard summary.

    Returns overall statistics and recent alerts.
    """
    try:
        return {
            "summary": {
                "total_users_monitored": 150,
                "high_risk_users": 5,
                "medium_risk_users": 12,
                "anomalies_detected_24h": 8,
                "critical_alerts": 2,
            },
            "recent_anomalies": [
                {
                    "user_id": "user_001",
                    "username": "john.doe",
                    "type": "off_hours_login",
                    "risk_level": "high",
                    "detected_at": "2024-01-15T02:30:00",
                }
            ],
            "top_risk_factors": [
                {"factor": "off_hours_login", "count": 15},
                {"factor": "unusual_data_access", "count": 8},
                {"factor": "geolocation_anomaly", "count": 5},
            ],
            "trend": {"period": "7d", "anomaly_change": "+12%", "risk_score_avg": 35.2},
        }

    except Exception as e:
        logger.error(f"Error getting UEBA dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}",
        )

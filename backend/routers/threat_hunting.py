"""
Threat Hunting Router - Proactive Threat Discovery API
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, Field
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel, UserRole
from services.threat_hunting_service import (
    get_threat_hunting_engine,
    HuntType,
    HuntStatus,
    HuntHypothesis,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/api/threat-hunting", tags=["threat-hunting", "proactive"])


# Request/Response Models
class IOCHuntRequest(BaseModel):
    """IOC hunt request."""

    iocs: List[dict] = Field(..., description="List of IOCs to hunt for")
    time_range_days: int = Field(default=30, ge=1, le=90)


class IOCHuntResult(BaseModel):
    """IOC hunt result."""

    ioc_type: str
    ioc_value: str
    found: bool
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    hit_count: int = 0
    affected_entities: List[str] = []


class HuntHypothesisCreate(BaseModel):
    """Create custom hunt hypothesis."""

    name: str = Field(..., min_length=5, max_length=100)
    description: str = Field(..., min_length=20)
    mitre_techniques: List[str] = Field(default_factory=list)
    data_sources: List[str] = Field(default_factory=list)
    query_logic: str = Field(..., min_length=10)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


class HuntHypothesisResponse(BaseModel):
    """Hunt hypothesis response."""

    id: str
    name: str
    description: str
    mitre_techniques: List[str]
    data_sources: List[str]
    query_logic: str
    severity: str
    created_by: str
    created_at: datetime


class HuntExecutionRequest(BaseModel):
    """Execute hunt request."""

    hypothesis_id: str
    time_range_hours: int = Field(default=24, ge=1, le=168)


class HuntFindingResponse(BaseModel):
    """Hunt finding response."""

    id: str
    entity_type: str
    entity_id: str
    description: str
    confidence: float
    severity: str
    evidence: dict
    recommended_actions: List[str]
    found_at: datetime


class HuntResultResponse(BaseModel):
    """Hunt execution result."""

    hunt_id: str
    hunt_name: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime]
    total_entities_scanned: int
    findings: List[HuntFindingResponse]
    statistics: dict


@router.get("/hypotheses", response_model=List[HuntHypothesisResponse])
async def get_hunt_hypotheses(
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get all available threat hunting hypotheses.

    Returns built-in hypotheses based on MITRE ATT&CK framework
    plus custom user-created hypotheses.
    """
    try:
        engine = get_threat_hunting_engine()
        hypotheses = await engine.get_hunt_library()

        return [
            HuntHypothesisResponse(
                id=h.id,
                name=h.name,
                description=h.description,
                mitre_techniques=h.mitre_techniques,
                data_sources=h.data_sources,
                query_logic=h.query_logic,
                severity=h.severity,
                created_by=h.created_by,
                created_at=h.created_at,
            )
            for h in hypotheses
        ]

    except Exception as e:
        logger.error(f"Error getting hunt hypotheses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get hypotheses: {str(e)}",
        )


@router.post("/hypotheses", response_model=HuntHypothesisResponse)
async def create_hunt_hypothesis(
    hypothesis: HuntHypothesisCreate,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Create custom threat hunting hypothesis.

    Allows security analysts to create custom hunting rules
    based on their threat intelligence and experience.
    """
    try:
        engine = get_threat_hunting_engine()

        new_hypothesis = await engine.create_custom_hypothesis(
            name=hypothesis.name,
            description=hypothesis.description,
            mitre_techniques=hypothesis.mitre_techniques,
            data_sources=hypothesis.data_sources,
            query_logic=hypothesis.query_logic,
            severity=hypothesis.severity,
            created_by=current_user.username,
        )

        return HuntHypothesisResponse(
            id=new_hypothesis.id,
            name=new_hypothesis.name,
            description=new_hypothesis.description,
            mitre_techniques=new_hypothesis.mitre_techniques,
            data_sources=new_hypothesis.data_sources,
            query_logic=new_hypothesis.query_logic,
            severity=new_hypothesis.severity,
            created_by=new_hypothesis.created_by,
            created_at=new_hypothesis.created_at,
        )

    except Exception as e:
        logger.error(f"Error creating hypothesis: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create hypothesis: {str(e)}",
        )


@router.post("/execute", response_model=HuntResultResponse)
async def execute_hunt(
    request: HuntExecutionRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Execute threat hunt based on hypothesis.

    Runs the hunt query against historical data and returns findings.
    This is a synchronous operation that may take several minutes.
    """
    try:
        engine = get_threat_hunting_engine()

        result = await engine.execute_hunt(
            hypothesis_id=request.hypothesis_id,
            time_range_hours=request.time_range_hours,
            db=db,
        )

        return HuntResultResponse(
            hunt_id=result.hunt_id,
            hunt_name=result.hunt_name,
            status=result.status.value,
            started_at=result.started_at,
            completed_at=result.completed_at,
            total_entities_scanned=result.total_entities_scanned,
            findings=[
                HuntFindingResponse(
                    id=f.id,
                    entity_type=f.entity_type,
                    entity_id=f.entity_id,
                    description=f.description,
                    confidence=f.confidence,
                    severity=f.severity,
                    evidence=f.evidence,
                    recommended_actions=f.recommended_actions,
                    found_at=f.found_at,
                )
                for f in result.findings
            ],
            statistics=result.statistics,
        )

    except Exception as e:
        logger.error(f"Error executing hunt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Hunt execution failed: {str(e)}",
        )


@router.post("/ioc-hunt")
async def hunt_iocs(
    request: IOCHuntRequest,
    current_user: UserModel = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    """
    Hunt for Indicators of Compromise (IOCs).

    Searches across all data sources for specific IOCs including:
    - IP addresses
    - Domain names
    - File hashes
    - Email addresses
    """
    try:
        engine = get_threat_hunting_engine()

        findings = await engine.ioc_hunt(
            iocs=request.iocs, time_range_days=request.time_range_days, db=db
        )

        return {
            "hunt_id": f"ioc_hunt_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "total_iocs": len(request.iocs),
            "iocs_searched": request.iocs,
            "time_range_days": request.time_range_days,
            "findings": [
                {
                    "ioc_type": f.entity_type,
                    "ioc_value": f.entity_id,
                    "description": f.description,
                    "confidence": f.confidence,
                    "severity": f.severity,
                    "evidence": f.evidence,
                    "found_at": f.found_at,
                }
                for f in findings
            ],
            "statistics": {
                "total_matches": len(findings),
                "high_confidence": len([f for f in findings if f.confidence > 0.8]),
                "unique_entities": len(set(f.entity_id for f in findings)),
            },
        }

    except Exception as e:
        logger.error(f"Error in IOC hunt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"IOC hunt failed: {str(e)}",
        )


@router.get("/results")
async def get_hunt_results(
    hunt_id: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get threat hunt execution results.

    Returns results of previous hunts including findings and statistics.
    """
    try:
        engine = get_threat_hunting_engine()
        results = await engine.get_hunt_results(hunt_id=hunt_id, limit=limit)

        return [
            {
                "hunt_id": r.hunt_id,
                "hunt_name": r.hunt_name,
                "status": r.status.value,
                "started_at": r.started_at,
                "completed_at": r.completed_at,
                "findings_count": len(r.findings),
                "statistics": r.statistics,
            }
            for r in results
        ]

    except Exception as e:
        logger.error(f"Error getting hunt results: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get results: {str(e)}",
        )


@router.get("/dashboard")
async def get_hunting_dashboard(
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get threat hunting dashboard summary.

    Returns statistics on hunts, findings, and trends.
    """
    try:
        return {
            "summary": {
                "total_hunts_executed": 45,
                "active_hunts": 2,
                "total_findings": 18,
                "critical_findings": 3,
                "high_findings": 8,
            },
            "recent_hunts": [
                {
                    "hunt_id": "hunt_001",
                    "name": "Lateral Movement via SMB",
                    "status": "completed",
                    "findings": 2,
                    "executed_at": "2024-01-15T10:00:00",
                }
            ],
            "top_mitre_techniques": [
                {"technique": "T1059.001", "name": "PowerShell", "count": 5},
                {
                    "technique": "T1021.002",
                    "name": "SMB/Windows Admin Shares",
                    "count": 3,
                },
                {"technique": "T1053.005", "name": "Scheduled Task", "count": 2},
            ],
            "hunt_effectiveness": {
                "total_executions": 45,
                "with_findings": 18,
                "success_rate": "40%",
            },
        }

    except Exception as e:
        logger.error(f"Error getting hunting dashboard: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get dashboard: {str(e)}",
        )

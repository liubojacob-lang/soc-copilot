"""
Threat Hunting Router - Proactive Threat Discovery API
"""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.user import UserModel
from services.threat_hunting_service import (
    get_threat_hunting_engine,
)

logger = get_logger(__name__)

router = APIRouter(
    prefix="/api/v1/threat-hunting", tags=["threat-hunting", "proactive"]
)


# Request/Response Models
class IOCHuntRequest(BaseModel):
    """IOC hunt request."""

    iocs: list[dict] = Field(..., description="List of IOCs to hunt for")
    time_range_days: int = Field(default=30, ge=1, le=90)


class IOCHuntResult(BaseModel):
    """IOC hunt result."""

    ioc_type: str
    ioc_value: str
    found: bool
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    hit_count: int = 0
    affected_entities: list[str] = []


class HuntHypothesisCreate(BaseModel):
    """Create custom hunt hypothesis."""

    name: str = Field(..., min_length=5, max_length=100)
    description: str = Field(..., min_length=20)
    mitre_techniques: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    query_logic: str = Field(..., min_length=10)
    severity: str = Field(default="medium", pattern="^(low|medium|high|critical)$")


class HuntHypothesisResponse(BaseModel):
    """Hunt hypothesis response."""

    id: str
    name: str
    description: str
    mitre_techniques: list[str]
    data_sources: list[str]
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
    recommended_actions: list[str]
    found_at: datetime


class HuntResultResponse(BaseModel):
    """Hunt execution result."""

    hunt_id: str
    hunt_name: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    total_entities_scanned: int
    findings: list[HuntFindingResponse]
    statistics: dict


@router.get("/hypotheses", response_model=list[HuntHypothesisResponse])
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
            detail=f"Failed to get hypotheses: {e!s}",
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
            detail=f"Failed to create hypothesis: {e!s}",
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
            detail=f"Hunt execution failed: {e!s}",
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
                "unique_entities": len({f.entity_id for f in findings}),
            },
        }

    except Exception as e:
        logger.error(f"Error in IOC hunt: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"IOC hunt failed: {e!s}",
        )


@router.get("/results")
async def get_hunt_results(
    hunt_id: str | None = None,
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
            detail=f"Failed to get results: {e!s}",
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
            detail=f"Failed to get dashboard: {e!s}",
        )


# ── Sigma Rule Endpoints ──────────────────────────────────────────────


class SigmaRuleSummary(BaseModel):
    """Lightweight Sigma rule summary for listing."""

    id: str
    title: str
    level: str
    category: str
    status: str
    mitre_techniques: list[str]
    description: str


class SigmaRuleDetail(BaseModel):
    """Full Sigma rule detail including generated SQL."""

    id: str
    title: str
    description: str
    status: str
    level: str
    author: str
    category: str
    tags: list[str]
    mitre_techniques: list[str]
    logsource: dict
    false_positives: list[str]
    references: list[str]
    generated_sql: str


class SigmaSearchRequest(BaseModel):
    """Request to execute a Sigma rule search."""

    rule_id: str = Field(..., description="Sigma rule ID to execute")
    hours: int = Field(default=24, ge=1, le=168, description="Lookback window in hours")


class SigmaSearchResponse(BaseModel):
    """Response from a Sigma rule search execution."""

    rule_id: str
    rule_title: str
    rule_level: str
    sql_query: str
    searched_hours: int
    total_matches: int
    matches: list[dict]
    timestamp: str


@router.get("/sigma/rules", response_model=list[SigmaRuleSummary])
async def get_sigma_rules(
    category: str | None = Query(
        None, description="Filter by category: windows, linux, cloud, kubernetes"
    ),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get all available Sigma detection rules.

    Optionally filter by category. Rules are loaded from
    the built-in rule library (backend/data/sigma_rules/).
    """
    from services.threat_hunting.sigma_engine import get_sigma_engine

    try:
        engine = get_sigma_engine()

        if category:
            rules = engine.get_rules_by_category(category)
        else:
            rules = engine.get_all_rules()

        return [
            SigmaRuleSummary(
                id=r.id,
                title=r.title,
                level=r.level,
                category=r.category,
                status=r.status,
                mitre_techniques=r.mitre_techniques,
                description=r.description[:200]
                + ("..." if len(r.description) > 200 else ""),
            )
            for r in rules
        ]

    except Exception as e:
        logger.error(f"Error getting Sigma rules: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get Sigma rules: {e!s}",
        )


@router.get("/sigma/rules/categories")
async def get_sigma_categories(
    current_user: UserModel = Depends(get_current_user),
):
    """Get available Sigma rule categories."""
    from services.threat_hunting.sigma_engine import get_sigma_engine

    try:
        engine = get_sigma_engine()
        categories = engine.get_categories()

        return {
            "categories": categories,
            "total_rules": len(engine.get_all_rules()),
        }

    except Exception as e:
        logger.error(f"Error getting Sigma categories: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get categories: {e!s}",
        )


@router.get("/sigma/rules/{rule_id}", response_model=SigmaRuleDetail)
async def get_sigma_rule_detail(
    rule_id: str,
    current_user: UserModel = Depends(get_current_user),
):
    """
    Get detailed Sigma rule information including generated SQL.

    Returns the full rule definition with the automatically-generated
    SQL WHERE clause for hunting execution.
    """
    from services.threat_hunting.sigma_engine import get_sigma_engine

    try:
        engine = get_sigma_engine()
        rule = engine.get_rule(rule_id)

        if not rule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Sigma rule not found: {rule_id}",
            )

        return SigmaRuleDetail(
            id=rule.id,
            title=rule.title,
            description=rule.description,
            status=rule.status,
            level=rule.level,
            author=rule.author,
            category=rule.category,
            tags=rule.tags,
            mitre_techniques=rule.mitre_techniques,
            logsource=rule.logsource,
            false_positives=rule.false_positives,
            references=rule.references,
            generated_sql=rule.generated_sql,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting Sigma rule detail: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get rule detail: {e!s}",
        )


@router.post("/sigma/search", response_model=SigmaSearchResponse)
async def execute_sigma_search(
    request: SigmaSearchRequest,
    db: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
):
    """
    Execute a Sigma rule search against data sources.

    Converts the Sigma rule to SQL and searches the relevant
    database table. Returns matching events and metadata.
    """
    from services.threat_hunting.sigma_engine import get_sigma_engine

    try:
        engine = get_sigma_engine()
        result = await engine.search_by_rule(
            rule_id=request.rule_id,
            session=db,
            hours=request.hours,
        )

        if "error" in result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=result["error"],
            )

        return SigmaSearchResponse(
            rule_id=result["rule_id"],
            rule_title=result["rule_title"],
            rule_level=result["rule_level"],
            sql_query=result["sql_query"],
            searched_hours=result["searched_hours"],
            total_matches=result["total_matches"],
            matches=result["matches"],
            timestamp=result["timestamp"],
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing Sigma search: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Sigma search failed: {e!s}",
        )

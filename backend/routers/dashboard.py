"""Operational Dashboard API for SOC Copilot.

Provides real-time operational metrics including:
- Alert statistics (total, unresolved, by severity/status)
- Case tracking (open, overdue, MTTR)
- Trend data (7-day alert/case trends)
- Top sources, risky assets, IOC hits, playbook runs
"""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import func, select, case as sa_case
from sqlalchemy.ext.asyncio import AsyncSession

from core.logger import get_logger
from db.session import get_session
from dependencies.auth import get_current_user
from models.case import CaseModel
from models.ioc_hit import IOCHitModel
from models.playbook_run import PlaybookRunModel
from models.security_alert import SecurityAlert
from models.user import UserModel
from services.query_cache import get_query_cache

router = APIRouter(prefix="/api/v1/dashboard", tags=["Dashboard"])
logger = get_logger(__name__)


# ── Response Schema ────────────────────────────────────────────────


class SeverityDistribution(BaseModel):
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class StatusDistribution(BaseModel):
    new: int = 0
    investigating: int = 0
    resolved: int = 0
    false_positive: int = 0
    escalated: int = 0


class TrendPoint(BaseModel):
    date: str
    count: int


class TrendPointBySeverity(BaseModel):
    date: str
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0


class TopSource(BaseModel):
    source: str
    count: int


class TopRiskyAsset(BaseModel):
    asset: str
    alert_count: int
    risk_score: float = 0.0
    asset_type: str = "agent"
    ip_address: str | None = None
    critical_count: int = 0
    high_count: int = 0


class DashboardStats(BaseModel):
    """Real-time operational dashboard statistics."""

    alerts_total: int = 0
    alerts_unresolved: int = 0
    alerts_by_severity: SeverityDistribution = Field(default_factory=SeverityDistribution)
    alerts_by_status: StatusDistribution = Field(default_factory=StatusDistribution)
    cases_open: int = 0
    cases_overdue: int = 0
    mttr_minutes: float | None = None
    alerts_trend: list[TrendPoint] = Field(default_factory=list)
    alerts_trend_by_severity: list[TrendPointBySeverity] = Field(default_factory=list)
    top_alert_sources: list[TopSource] = Field(default_factory=list)
    top_risky_assets: list[TopRiskyAsset] = Field(default_factory=list)
    ioc_hits_today: int = 0
    playbook_runs_today: int = 0


# ── Endpoint ───────────────────────────────────────────────────────


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    session: AsyncSession = Depends(get_session),
    current_user: UserModel = Depends(get_current_user),
) -> DashboardStats:
    """Get real-time operational dashboard statistics.

    Aggregates are cached for 60s: the dashboard is polled by every open
    browser tab, so uncached per-request aggregates scale with viewers.
    """
    cache_key = "dashboard_stats:v1"
    cached = get_query_cache().get(cache_key)
    if cached is not None:
        return cached

    stats = await _compute_dashboard_stats(session)
    get_query_cache().set(cache_key, stats, ttl=60)
    return stats


async def _compute_dashboard_stats(session: AsyncSession) -> DashboardStats:
    now = datetime.now(UTC)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    live = SecurityAlert.deleted_at.is_(None)

    # ── Severity × Status in ONE grouped query ─────────────────────
    # Derives alerts_total, alerts_unresolved and both distributions.
    sev_status_result = await session.execute(
        select(
            SecurityAlert.severity,
            SecurityAlert.status,
            func.count(SecurityAlert.id),
        )
        .where(live)
        .group_by(SecurityAlert.severity, SecurityAlert.status)
    )
    alerts_total = 0
    alerts_unresolved = 0
    sev_map: dict[str, int] = {}
    status_map: dict[str, int] = {}
    for severity, status, count in sev_status_result.all():
        alerts_total += count
        sev_map[severity] = sev_map.get(severity, 0) + count
        status_map[status] = status_map.get(status, 0) + count
        if status in ("new", "investigating"):
            alerts_unresolved += count

    alerts_by_severity = SeverityDistribution(
        critical=sev_map.get("critical", 0),
        high=sev_map.get("high", 0),
        medium=sev_map.get("medium", 0),
        low=sev_map.get("low", 0),
        info=sev_map.get("info", 0),
    )
    alerts_by_status = StatusDistribution(
        new=status_map.get("new", 0),
        investigating=status_map.get("investigating", 0),
        resolved=status_map.get("resolved", 0),
        false_positive=status_map.get("false_positive", 0),
        escalated=status_map.get("escalated", 0),
    )

    # ── Cases Open / Overdue ───────────────────────────────────────
    cases_open_result = await session.execute(
        select(func.count(CaseModel.id)).where(
            CaseModel.status.in_(["new", "investigating", "pending_review"])
        )
    )
    cases_open = cases_open_result.scalar() or 0

    cases_overdue_result = await session.execute(
        select(func.count(CaseModel.id)).where(
            CaseModel.sla_due_at.isnot(None),
            CaseModel.sla_due_at < now,
            CaseModel.status.notin_(["resolved", "closed"]),
        )
    )
    cases_overdue = cases_overdue_result.scalar() or 0

    # ── MTTR (Mean Time to Resolve) ────────────────────────────────
    # Portable epoch arithmetic: julianday() is SQLite-only and breaks on
    # PostgreSQL; extract(epoch) is PostgreSQL-only. Pick per dialect.
    if session.bind is not None and session.bind.dialect.name == "postgresql":
        duration_seconds = func.extract(
            "epoch", SecurityAlert.resolved_at
        ) - func.extract("epoch", SecurityAlert.created_at)
    else:
        duration_seconds = func.strftime(
            "%s", SecurityAlert.resolved_at
        ) - func.strftime("%s", SecurityAlert.created_at)
    mttr_result = await session.execute(
        select(func.avg(duration_seconds) * 60).where(
            live,
            SecurityAlert.resolved_at.isnot(None),
            SecurityAlert.status == "resolved",
        )
    )
    mttr_seconds = mttr_result.scalar()
    mttr_minutes = round(float(mttr_seconds), 1) if mttr_seconds else None

    # ── 7-Day Alert Trend (single GROUP BY instead of 7 COUNTs) ────
    week_start = today_start - timedelta(days=6)
    trend_result = await session.execute(
        select(
            func.date(SecurityAlert.created_at).label("day"),
            func.count(SecurityAlert.id),
        )
        .where(live, SecurityAlert.created_at >= week_start)
        .group_by(func.date(SecurityAlert.created_at))
    )
    counts_by_day = {str(row[0]): row[1] for row in trend_result.all()}
    alerts_trend = [
        TrendPoint(
            date=(today_start - timedelta(days=offset)).strftime("%Y-%m-%d"),
            count=counts_by_day.get(
                (today_start - timedelta(days=offset)).strftime("%Y-%m-%d"), 0
            ),
        )
        for offset in range(6, -1, -1)
    ]

    # ── 7-Day Trend by Severity (one grouped query, per-day rows) ──
    sev_trend_result = await session.execute(
        select(
            func.date(SecurityAlert.created_at).label("day"),
            SecurityAlert.severity,
            func.count(SecurityAlert.id),
        )
        .where(live, SecurityAlert.created_at >= week_start)
        .group_by(func.date(SecurityAlert.created_at), SecurityAlert.severity)
    )
    sev_by_day: dict[str, dict[str, int]] = {}
    for day, severity, count in sev_trend_result.all():
        sev_by_day.setdefault(str(day), {})[severity] = count
    alerts_trend_by_severity = [
        TrendPointBySeverity(
            date=(today_start - timedelta(days=offset)).strftime("%Y-%m-%d"),
            **{
                level: sev_by_day.get(
                    (today_start - timedelta(days=offset)).strftime("%Y-%m-%d"), {}
                ).get(level, 0)
                for level in ("critical", "high", "medium", "low", "info")
            },
        )
        for offset in range(6, -1, -1)
    ]

    # ── Top Alert Sources ──────────────────────────────────────────
    top_sources_query = (
        select(SecurityAlert.source, func.count(SecurityAlert.id))
        .where(live)
        .group_by(SecurityAlert.source)
        .order_by(func.count(SecurityAlert.id).desc())
        .limit(10)
    )
    top_sources_result = await session.execute(top_sources_query)
    top_alert_sources = [
        TopSource(source=row[0], count=row[1])
        for row in top_sources_result.all()
    ]

    # ── Top Risky Assets ───────────────────────────────────────────
    risk_score = func.sum(
        sa_case(
            (SecurityAlert.severity == "critical", 10),
            (SecurityAlert.severity == "high", 7),
            (SecurityAlert.severity == "medium", 4),
            (SecurityAlert.severity == "low", 2),
            else_=1,
        )
    )
    critical_count = func.sum(
        sa_case((SecurityAlert.severity == "critical", 1), else_=0)
    )
    high_count = func.sum(sa_case((SecurityAlert.severity == "high", 1), else_=0))
    top_assets_query = (
        select(
            SecurityAlert.agent_name,
            func.count(SecurityAlert.id).label("cnt"),
            risk_score.label("risk_score"),
            critical_count.label("critical_count"),
            high_count.label("high_count"),
        )
        .where(live, SecurityAlert.agent_name.isnot(None))
        .group_by(SecurityAlert.agent_name)
        .order_by(risk_score.desc())
        .limit(10)
    )
    top_assets_result = await session.execute(top_assets_query)
    top_risky_assets = [
        TopRiskyAsset(
            asset=row[0] or "unknown",
            alert_count=row[1],
            risk_score=round(float(row[2] or 0), 1),
            critical_count=row[3] or 0,
            high_count=row[4] or 0,
        )
        for row in top_assets_result.all()
    ]

    # ── IOC Hits Today ─────────────────────────────────────────────
    ioc_result = await session.execute(
        select(func.count(IOCHitModel.id)).where(
            IOCHitModel.created_at >= today_start
        )
    )
    ioc_hits_today = ioc_result.scalar() or 0

    # ── Playbook Runs Today ────────────────────────────────────────
    playbook_result = await session.execute(
        select(func.count(PlaybookRunModel.id)).where(
            PlaybookRunModel.started_at >= today_start
        )
    )
    playbook_runs_today = playbook_result.scalar() or 0

    return DashboardStats(
        alerts_total=alerts_total,
        alerts_unresolved=alerts_unresolved,
        alerts_by_severity=alerts_by_severity,
        alerts_by_status=alerts_by_status,
        cases_open=cases_open,
        cases_overdue=cases_overdue,
        mttr_minutes=mttr_minutes,
        alerts_trend=alerts_trend,
        alerts_trend_by_severity=alerts_trend_by_severity,
        top_alert_sources=top_alert_sources,
        top_risky_assets=top_risky_assets,
        ioc_hits_today=ioc_hits_today,
        playbook_runs_today=playbook_runs_today,
    )

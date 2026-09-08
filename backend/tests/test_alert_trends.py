"""Integration tests for alert trends time series aggregation.

get_trends() is exercised against the real test database (SQLite in the
suite). The PostgreSQL expression set is the dialect twin of the SQLite one
and is verified against a real Postgres instance before release. Inserted
alerts cover hour/day/week buckets and assert Monday-based week bucketing.
"""

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select

backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

import models  # noqa: F401  (register all models before create_all)
from db.session import AsyncSessionLocal, init_db
from models.security_alert import SecurityAlert
from services.alerting.alert_lifecycle import AlertLifecycleService


@pytest.fixture
async def db_session():
    """Session bound to the test database; security_alerts cleaned up after."""
    await init_db()
    async with AsyncSessionLocal() as session:
        yield session
    async with AsyncSessionLocal() as session:
        for alert in await session.scalars(select(SecurityAlert)):
            await session.delete(alert)
        await session.commit()


async def _insert(session, created_at, severity, event_id):
    session.add(
        SecurityAlert(
            source="wazuh",
            external_event_id=event_id,
            event_type="test_event",
            severity=severity,
            title=f"trend test {event_id}",
            created_at=created_at,
        )
    )


async def test_hour_grouping_buckets_on_hour_start(db_session):
    base = datetime(2026, 3, 2, 14, 0, tzinfo=UTC)
    await _insert(db_session, base + timedelta(minutes=10), "critical", "h1")
    await _insert(db_session, base + timedelta(minutes=20), "high", "h2")
    await _insert(db_session, base + timedelta(hours=1, minutes=5), "critical", "h3")
    await db_session.commit()

    trends = await AlertLifecycleService(db_session).get_trends(
        start_date=base - timedelta(hours=1),
        end_date=base + timedelta(hours=3),
        interval="hour",
    )

    assert [(t.timestamp.hour, t.count) for t in trends] == [(14, 2), (15, 1)]
    assert all(t.timestamp.minute == 0 and t.timestamp.second == 0 for t in trends)
    first_bucket = next(t for t in trends if t.timestamp.hour == 14).by_severity
    assert first_bucket == {"critical": 1, "high": 1, "medium": 0, "low": 0, "info": 0}


async def test_day_grouping(db_session):
    day1 = datetime(2026, 3, 2, 9, 30, tzinfo=UTC)
    day2 = datetime(2026, 3, 3, 23, 10, tzinfo=UTC)
    await _insert(db_session, day1, "low", "d1")
    await _insert(db_session, day1 + timedelta(hours=2), "low", "d2")
    await _insert(db_session, day2, "info", "d3")
    await db_session.commit()

    trends = await AlertLifecycleService(db_session).get_trends(
        start_date=datetime(2026, 3, 1, tzinfo=UTC),
        end_date=datetime(2026, 3, 4, tzinfo=UTC),
        interval="day",
    )

    assert [(t.timestamp.day, t.count) for t in trends] == [(2, 2), (3, 1)]
    assert all(
        t.timestamp.hour == 0 and t.timestamp.minute == 0 and t.timestamp.second == 0
        for t in trends
    )


async def test_week_grouping_buckets_on_monday(db_session):
    # 2026-03-04 is a Wednesday; its week starts on Monday 2026-03-02.
    # 2026-03-08 (Sunday) belongs to the same week; 2026-03-09 starts the next.
    wednesday = datetime(2026, 3, 4, 12, 0, tzinfo=UTC)
    sunday = datetime(2026, 3, 8, 21, 0, tzinfo=UTC)
    next_monday = datetime(2026, 3, 9, 8, 0, tzinfo=UTC)
    await _insert(db_session, wednesday, "medium", "w1")
    await _insert(db_session, sunday, "high", "w2")
    await _insert(db_session, next_monday, "low", "w3")
    await db_session.commit()

    trends = await AlertLifecycleService(db_session).get_trends(
        start_date=datetime(2026, 3, 1, tzinfo=UTC),
        end_date=datetime(2026, 3, 15, tzinfo=UTC),
        interval="week",
    )

    def monday_of(d):
        return d - timedelta(days=d.weekday())

    expected = [(monday_of(wednesday.date()), 2), (monday_of(next_monday.date()), 1)]
    assert [(t.timestamp.date(), t.count) for t in trends] == expected
    assert all(t.timestamp.time().isoformat() == "00:00:00" for t in trends)


async def test_invalid_interval_raises(db_session):
    with pytest.raises(ValueError):
        await AlertLifecycleService(db_session).get_trends(interval="month")


async def test_empty_window_returns_no_trends(db_session):
    trends = await AlertLifecycleService(db_session).get_trends(
        start_date=datetime(2020, 1, 1, tzinfo=UTC),
        end_date=datetime(2020, 1, 2, tzinfo=UTC),
        interval="hour",
    )
    assert trends == []

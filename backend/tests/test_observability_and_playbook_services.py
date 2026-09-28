"""Tests for PerformanceMonitor and PlaybookImportExportService."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from models.playbook_definition import PlaybookDefinitionModel, PlaybookDefinitionStatus
from services.observability.performance_monitor import (
    PerformanceMetric,
    PerformanceMetricType,
    PerformanceMonitor,
    PerformanceReport,
)
from services.playbook.playbook_import_export_service import PlaybookImportExportService

# ── PerformanceMonitor Tests ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_performance_monitor_api_metrics():
    session = AsyncMock()
    monitor = PerformanceMonitor(session)

    mock_res = MagicMock()
    # method, path, count, avg_duration, max_duration, p95_duration
    mock_res.fetchall.return_value = [
        ("POST", "/api/v1/alerts", 50, 150.5, 300.0, 220.0),
        ("GET", "/api/v1/cases", 120, 85.0, 150.0, 95.0),
    ]
    session.execute = AsyncMock(return_value=mock_res)

    metrics = await monitor.collect_api_metrics(time_window_minutes=5)
    assert len(metrics) == 6
    types = [m.metric_type for m in metrics]
    assert PerformanceMetricType.API_RESPONSE_TIME in types
    assert PerformanceMetricType.API_THROUGHPUT in types


@pytest.mark.asyncio
async def test_performance_monitor_cache_and_db_metrics():
    session = AsyncMock()
    session.get_bind = MagicMock(return_value=None)
    monitor = PerformanceMonitor(session)

    # 1. Cache metrics
    cache_metrics = await monitor.collect_cache_metrics()
    assert len(cache_metrics) == 3
    assert all(
        m.metric_type == PerformanceMetricType.CACHE_HIT_RATE for m in cache_metrics
    )
    assert cache_metrics[0].value == 85.0

    # 2. Database metrics
    mock_res = MagicMock()
    mock_res.fetchall.return_value = [
        ("security_alerts", 150000),  # > 100000
        ("users", 10),
    ]
    session.execute = AsyncMock(return_value=mock_res)

    db_metrics = await monitor.collect_database_metrics(time_window_minutes=15)
    assert len(db_metrics) == 1
    assert db_metrics[0].metric_type == PerformanceMetricType.DATABASE_QUERY_TIME
    assert db_metrics[0].labels["table"] == "security_alerts"


@pytest.mark.asyncio
async def test_performance_monitor_generate_report():
    session = AsyncMock()
    monitor = PerformanceMonitor(session)

    # Mock all 3 collectors
    m1 = PerformanceMetric(
        metric_type=PerformanceMetricType.API_RESPONSE_TIME,
        value=550.0,  # slow response
        timestamp=datetime.now(),
        labels={"method": "GET", "path": "/slow", "statistic": "average"},
        source="audit_logs",
    )
    m2 = PerformanceMetric(
        metric_type=PerformanceMetricType.CACHE_HIT_RATE,
        value=65.0,  # low cache hit rate (<70)
        timestamp=datetime.now(),
        labels={"cache_name": "alert_cache"},
        source="cache_monitor",
    )
    m3 = PerformanceMetric(
        metric_type=PerformanceMetricType.DATABASE_QUERY_TIME,
        value=200000.0,
        timestamp=datetime.now(),
        labels={"table": "big_table", "issue": "large_table"},
        source="database_analysis",
    )

    with patch.object(
        monitor, "collect_api_metrics", new_callable=AsyncMock, return_value=[m1]
    ):
        with patch.object(
            monitor, "collect_cache_metrics", new_callable=AsyncMock, return_value=[m2]
        ):
            with patch.object(
                monitor,
                "collect_database_metrics",
                new_callable=AsyncMock,
                return_value=[m3],
            ):
                report = await monitor.generate_performance_report(
                    time_window_minutes=30
                )
                assert isinstance(report, PerformanceReport)
                assert len(report.metrics) == 3
                assert "api_metrics" in report.summary
                assert "cache_metrics" in report.summary
                assert len(report.recommendations) > 0


# ── PlaybookImportExportService Tests ──────────────────────────────────


@pytest.mark.asyncio
async def test_playbook_export_json_and_not_found():
    session = AsyncMock()
    service = PlaybookImportExportService(session)

    # 1. Not found
    mock_res_none = MagicMock()
    mock_res_none.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_res_none)

    with pytest.raises(ValueError) as exc:
        await service.export_definition("def-not-found", format="json")
    assert "not found" in str(exc.value)

    # 2. Success JSON export
    mock_def = PlaybookDefinitionModel(
        id="def-101",
        name="Auto Block IP",
        description="Extract IOCs and block malicious IP",
        version="1.0.0",
        status=PlaybookDefinitionStatus.PUBLISHED,
        current_version_no=1,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        created_by="user-admin",
        definition_json={
            "nodes": [
                {
                    "id": "start",
                    "type": "trigger",
                    "name": "Start",
                    "config": {},
                }
            ],
            "edges": [],
        },
    )
    mock_res_found = MagicMock()
    mock_res_found.scalar_one_or_none.return_value = mock_def
    session.execute = AsyncMock(return_value=mock_res_found)

    content, mime = await service.export_definition("def-101", format="json")
    assert mime == "application/json"
    parsed = json.loads(content)
    assert parsed["name"] == "Auto Block IP"
    assert parsed["version"] == "1.0.0"
    assert len(parsed["dag"]["nodes"]) == 1


@pytest.mark.asyncio
async def test_playbook_import_json_flow():
    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    service = PlaybookImportExportService(session)

    import_json_data = {
        "name": "Incident Response Playbook",
        "description": "Standard triage",
        "version": "1.2.0",
        "status": "draft",
        "current_version_no": 1,
        "created_at": datetime.now(UTC).isoformat(),
        "updated_at": datetime.now(UTC).isoformat(),
        "created_by_user_id": "analyst-1",
        "dag": {
            "nodes": [
                {
                    "id": "extract",
                    "type": "extract_iocs",
                    "name": "Extract IOCs",
                    "config": {},
                }
            ],
            "edges": [],
        },
    }

    # 1. Invalid JSON
    with pytest.raises(ValueError) as exc:
        await service.import_definition("not-valid-json {", format="json")
    assert "Invalid JSON" in str(exc.value)

    # 2. Missing required name
    with pytest.raises(ValueError) as exc:
        await service.import_definition(json.dumps({"dag": {}}), format="json")
    assert "Missing required field: name" in str(exc.value)

    # 3. Successful import with publish
    resp = await service.import_definition(
        json.dumps(import_json_data),
        format="json",
        publish=True,
        created_by_user_id="analyst-1",
    )
    assert resp.name == "Incident Response Playbook"
    assert resp.status == PlaybookDefinitionStatus.PUBLISHED
    session.add.assert_called_once()
    session.flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_playbook_replay_service():
    from models.playbook_run import PlaybookRunModel
    from services.playbook.playbook_replay_service import PlaybookReplayService

    session = AsyncMock()
    session.add = MagicMock()
    session.flush = AsyncMock()
    service = PlaybookReplayService(session)

    # 1. Replay original run
    orig_run = PlaybookRunModel(
        id="run-original-1",
        playbook_name="Block IP Playbook",
        playbook_version="1.0.0",
        mode="dry_run",
        status="success",
        created_by_user_id="analyst-bob",
        input_json={"target_ip": "1.2.3.4"},
        output_json={"blocked": True},
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        engine_version="2.0",
        execution_mode="dag",
        definition_id="def-1",
        failure_strategy="stop",
        input_context_json={"target_ip": "1.2.3.4"},
        context_json={},
        replay_of_run_id=None,
    )

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = orig_run
    session.execute = AsyncMock(return_value=mock_res)

    replay_resp = await service.replay_run(
        run_id="run-original-1",
        mode="apply",
        override_context={"target_ip": "5.6.7.8"},
        created_by_user_id="lead-alice",
    )
    assert replay_resp.original_run_id == "run-original-1"
    assert replay_resp.mode == "apply"
    assert replay_resp.status == "pending"
    session.add.assert_called()
    session.flush.assert_awaited()

    # 2. Replay run not found
    mock_res_none = MagicMock()
    mock_res_none.scalar_one_or_none.return_value = None
    session.execute = AsyncMock(return_value=mock_res_none)

    with pytest.raises(ValueError) as exc:
        await service.replay_run("run-nonexistent")
    assert "not found" in str(exc.value)

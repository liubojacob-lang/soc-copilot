"""
Comprehensive tests for Audit Archive Service, Audit Repository,
and Audit Log API router endpoints.
"""

from __future__ import annotations

import csv
import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from httpx import AsyncClient

from db.session import AsyncSessionLocal, init_db
from models.audit_log import AuditLogModel
from repositories.audit_repository import AuditRepository
from services.audit_archive_service import (
    AuditArchiveService,
    get_archive_service,
)


@pytest.fixture(autouse=True)
async def setup_database():
    await init_db()


# ─────────────────────────────────────────────────────────────
# 1. AuditArchiveService Unit Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_archive_service_lifecycle(tmp_path: Path):
    archive_dir = tmp_path / "audit_archives"
    service = AuditArchiveService(
        session_factory=AsyncSessionLocal,
        archive_dir=archive_dir,
        retention_days=30,
        archive_retention_days=180,
    )

    assert archive_dir.exists()

    # Seed an old audit log (45 days ago)
    old_date = datetime.now(UTC) - timedelta(days=45)
    async with AsyncSessionLocal() as session:
        log = AuditLogModel(
            user_id="analyst-1",
            action="alert:investigate",
            method="GET",
            path="/api/v1/alerts/123",
            status_code=200,
            target_type="alert",
            target_id="123",
            ip_address="10.0.0.1",
            user_agent="pytest-client",
            duration_ms=45,
            extra_json={"reason": "routine check"},
            created_at=old_date,
        )
        session.add(log)
        await session.commit()

    # 1. Archive logs
    stats = await service.archive_old_logs(days=30)
    assert stats["archived_count"] >= 1
    assert stats["files_created"] >= 1
    assert len(stats["errors"]) == 0

    # Verify compressed archive file exists
    archive_files = list(archive_dir.glob("audit_logs_*.json.gz"))
    assert len(archive_files) >= 1

    with gzip.open(archive_files[0], "rt", encoding="utf-8") as f:
        archived_data = json.load(f)
        assert "logs" in archived_data
        assert len(archived_data["logs"]) >= 1
        assert archived_data["logs"][0]["action"] == "alert:investigate"

    # 2. Check Archive Stats
    archive_stats = await service.get_archive_stats()
    assert archive_stats["archive_files"] >= 1
    assert archive_stats["total_size_bytes"] > 0
    assert archive_stats["oldest_archive"] is not None

    # 3. Export Logs (JSON)
    start_date = old_date - timedelta(days=5)
    end_date = datetime.now(UTC) + timedelta(days=1)
    export_json = await service.export_logs(start_date, end_date, format="json", include_archived=True)
    assert export_json.exists()
    with open(export_json, "r", encoding="utf-8") as f:
        exported = json.load(f)
        assert exported["total_count"] >= 1

    # 4. Export Logs (CSV)
    export_csv = await service.export_logs(start_date, end_date, format="csv", include_archived=True)
    assert export_csv.exists()
    with open(export_csv, "r", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)
        assert len(rows) >= 2  # Header + row

    # 5. Cleanup Archives older than 0 days (force purge for test)
    cleanup_stats = await service.cleanup_archived_files(retention_days=0)
    assert cleanup_stats["files_deleted"] >= 1
    assert cleanup_stats["space_freed_bytes"] > 0


def test_audit_archive_service_singleton():
    svc1 = get_archive_service(AsyncSessionLocal)
    svc2 = get_archive_service(AsyncSessionLocal)
    assert svc1 is svc2


# ─────────────────────────────────────────────────────────────
# 2. AuditRepository Unit Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_repository_crud_and_filters():
    async with AsyncSessionLocal() as session:
        repo = AuditRepository(session)

        # Create audit entries
        now = datetime.now(UTC)
        await repo.create(
            action="user:login_success",
            method="POST",
            path="/api/v1/auth/login",
            status_code=200,
            user_id="test-user-1",
            target_type="auth",
            ip_address="192.168.1.50",
            duration_ms=120,
            extra_json={"browser": "Firefox"},
        )
        await repo.create(
            action="user:login_failure",
            method="POST",
            path="/api/v1/auth/login",
            status_code=401,
            user_id="test-user-1",
            target_type="auth",
            ip_address="192.168.1.50",
            duration_ms=80,
            extra_json={"reason": "bad credentials"},
        )
        await repo.create(
            action="playbook:delete",
            method="DELETE",
            path="/api/v1/playbooks/pb-123",
            status_code=500,
            user_id="test-user-2",
            target_type="playbook",
            target_id="pb-123",
            ip_address="192.168.1.51",
            duration_ms=250,
            extra_json={},
        )
        await session.commit()

        # 1. Filter by wildcard action prefix (user:*)
        logs, total = await repo.list(action="user:*", limit=50)
        assert total >= 2
        assert all(l.action.startswith("user:") for l in logs)

        # 2. Filter by status_code="success" (2xx)
        success_logs, s_total = await repo.list(status_code="success", limit=50)
        assert s_total >= 1
        assert all(200 <= l.status_code < 300 for l in success_logs)

        # 3. Filter by status_code="4xx"
        client_err_logs, c_total = await repo.list(status_code="4xx", limit=50)
        assert c_total >= 1
        assert any(l.status_code == 401 for l in client_err_logs)

        # 4. Filter by status_code="error" (4xx + 5xx)
        err_logs, e_total = await repo.list(status_code="error", limit=50)
        assert e_total >= 2

        # 5. Query by target
        target_logs = await repo.get_by_target("playbook", "pb-123")
        assert len(target_logs) >= 1
        assert target_logs[0].target_id == "pb-123"


# ─────────────────────────────────────────────────────────────
# 3. Audit Log Router API Endpoints Tests
# ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_audit_logs_list_api(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/audit-logs?page=1&page_size=20")
    assert response.status_code == 200
    data = response.json()
    assert "total" in data
    assert "items" in data
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_audit_logs_stats_summary_api(auth_client: AsyncClient):
    response = await auth_client.get("/api/v1/audit-logs/stats/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "failed_requests" in data
    assert "last_24h_requests" in data
    assert "top_actions" in data
    assert isinstance(data["top_actions"], list)


@pytest.mark.asyncio
async def test_audit_logs_target_api(auth_client: AsyncClient):
    # Retrieve audit logs for a target
    response = await auth_client.get("/api/v1/audit-logs/target/playbook/pb-123")
    assert response.status_code in (200, 403)
    if response.status_code == 200:
        data = response.json()
        assert data["target_type"] == "playbook"
        assert "logs" in data


@pytest.mark.asyncio
async def test_audit_logs_cleanup_api(auth_client: AsyncClient):
    response = await auth_client.post("/api/v1/audit-logs/cleanup?days=90")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert "Deleted" in data["message"]

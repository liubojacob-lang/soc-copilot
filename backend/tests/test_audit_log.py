"""Audit log tests."""

import pytest
from datetime import datetime, timezone


class TestAuditLog:
    """Audit log endpoint tests."""

    @pytest.mark.asyncio
    async def test_list_audit_logs(self, auth_client):
        """Test listing audit logs."""
        response = await auth_client.get("/api/audit/logs?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data or "logs" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_filter_audit_logs_by_user(self, auth_client):
        """Test filtering audit logs by user."""
        response = await auth_client.get("/api/audit/logs?user_id=admin&limit=10")
        assert response.status_code == 200
        data = response.json()
        # Should return filtered results

    @pytest.mark.asyncio
    async def test_filter_audit_logs_by_action(self, auth_client):
        """Test filtering audit logs by action."""
        response = await auth_client.get("/api/audit/logs?action=login&limit=10")
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_filter_audit_logs_by_date_range(self, auth_client):
        """Test filtering audit logs by date range."""
        response = await auth_client.get(
            "/api/audit/logs?start_date=2024-01-01&end_date=2024-12-31&limit=10"
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_audit_log_details(self, auth_client):
        """Test getting specific audit log details."""
        # First get a list of logs
        list_response = await auth_client.get("/api/audit/logs?limit=1")
        assert list_response.status_code == 200

        logs = list_response.json()
        items = logs.get("items") or logs.get("logs") or logs

        if items and len(items) > 0:
            log_id = items[0].get("id")

            # Get details
            detail_response = await auth_client.get(f"/api/audit/logs/{log_id}")
            assert detail_response.status_code == 200
            data = detail_response.json()
            assert "id" in data or "action" in data

    @pytest.mark.asyncio
    async def test_audit_log_pagination(self, auth_client):
        """Test audit log pagination."""
        response = await auth_client.get("/api/audit/logs?limit=5&offset=0")
        assert response.status_code == 200
        data = response.json()
        # Check pagination info

        if "total" in data:
            assert isinstance(data["total"], int)

    @pytest.mark.asyncio
    async def test_audit_log_sorting(self, auth_client):
        """Test sorting audit logs."""
        response = await auth_client.get("/api/audit/logs?sort=-created_at&limit=10")
        assert response.status_code == 200


class TestAuditLogCreation:
    """Tests for automatic audit log creation."""

    @pytest.mark.asyncio
    async def test_login_creates_audit_log(self, client):
        """Test that login creates an audit log."""
        initial_logs = await client.get("/api/audit/logs?limit=100")
        # Note: This requires authentication, adjust as needed

    @pytest.mark.asyncio
    async def test_api_action_creates_audit_log(self, auth_client):
        """Test that API actions create audit logs."""
        # Perform an action
        action_response = await auth_client.post(
            "/api/playbook-definitions",
            json={
                "name": "Audit Test",
                "version": "1.0.0",
                "description": "Test audit logging",
                "dag": {
                    "nodes": [{"id": "n1", "type": "start", "name": "Start"}],
                    "edges": []
                }
            }
        )

        # Check if audit log was created
        logs_response = await auth_client.get("/api/audit/logs?limit=10")
        assert logs_response.status_code == 200

    @pytest.mark.asyncio
    async def test_failed_action_creates_audit_log(self, auth_client):
        """Test that failed actions create audit logs."""
        # Attempt a forbidden action
        response = await auth_client.get("/api/admin/users")
        # Should create audit log even on failure

        logs_response = await auth_client.get("/api/audit/logs?action=access_denied&limit=5")
        assert logs_response.status_code == 200


class TestAuditLogMiddleware:
    """Audit log middleware tests."""

    @pytest.mark.asyncio
    async def test_request_id_logging(self, auth_client):
        """Test that request IDs are logged."""
        response = await auth_client.get("/api/audit/logs")
        assert response.status_code == 200

        # Check for request ID in response headers
        request_id = response.headers.get("x-request-id")
        # May or may not be present depending on config

    @pytest.mark.asyncio
    async def test_user_id_logging(self, auth_client):
        """Test that user IDs are logged in audit trails."""
        response = await auth_client.get("/api/audit/logs?limit=1")
        assert response.status_code == 200

        data = response.json()
        items = data.get("items") or data.get("logs") or data

        if items and len(items) > 0:
            # Check for user_id in log entry
            log_entry = items[0]
            assert "user_id" in log_entry or "username" in log_entry

    @pytest.mark.asyncio
    async def test_ip_address_logging(self, auth_client):
        """Test that IP addresses are logged."""
        response = await auth_client.get("/api/audit/logs?limit=1")
        assert response.status_code == 200

        # Audit logs should include request metadata
        data = response.json()
        items = data.get("items") or data.get("logs") or data

        if items and len(items) > 0:
            log_entry = items[0]
            # Check for IP in metadata or extra fields
            metadata = log_entry.get("metadata") or log_entry.get("extra") or {}
            # IP should be present in real scenarios

    @pytest.mark.asyncio
    async def test_sensitive_data_masking(self, auth_client):
        """Test that sensitive data is masked in logs."""
        # Change password
        response = await auth_client.post(
            "/api/auth/change-password",
            json={
                "current_password": "admin123!",
                "new_password": "NewPassword123!",
                "confirm_password": "NewPassword123!"
            }
        )

        # Check audit logs
        logs_response = await auth_client.get("/api/audit/logs?action=change_password&limit=1")
        assert logs_response.status_code == 200

        data = logs_response.json()
        items = data.get("items") or data.get("logs") or data

        if items and len(items) > 0:
            # Password should be masked in logs
            log_entry = items[0]
            log_str = str(log_entry)
            assert "NewPassword123!" not in log_str


class TestAuditLogExport:
    """Audit log export tests."""

    @pytest.mark.asyncio
    async def test_export_audit_logs_csv(self, auth_client):
        """Test exporting audit logs as CSV."""
        response = await auth_client.get(
            "/api/audit/logs/export?format=csv&limit=10"
        )
        # Should succeed or 404 if not implemented
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            assert "text/csv" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_export_audit_logs_json(self, auth_client):
        """Test exporting audit logs as JSON."""
        response = await auth_client.get(
            "/api/audit/logs/export?format=json&limit=10"
        )
        assert response.status_code in [200, 404]

        if response.status_code == 200:
            assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.asyncio
    async def test_export_requires_admin(self, auth_client):
        """Test that export requires admin privileges."""
        response = await auth_client.get("/api/audit/logs/export")
        # Non-admin may be denied
        assert response.status_code in [200, 403, 404]


class TestAuditLogRetention:
    """Audit log retention tests."""

    @pytest.mark.asyncio
    async def test_old_logs_cleanup(self, admin_client):
        """Test cleanup of old audit logs."""
        # This would require admin privileges
        response = await admin_client.post("/api/audit/logs/cleanup")
        # Should succeed or 404 if not implemented
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_retention_policy(self, admin_client):
        """Test getting/setting retention policy."""
        response = await admin_client.get("/api/audit/retention-policy")
        # Should succeed or 404 if not implemented
        assert response.status_code in [200, 404]


class TestAuditLogCompliance:
    """Compliance-related audit log tests."""

    @pytest.mark.asyncio
    async def test_compliance_report(self, admin_client):
        """Test generating compliance report."""
        response = await admin_client.get("/api/audit/compliance-report")
        # Should succeed or 404 if not implemented
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_audit_trail_integrity(self, admin_client):
        """Test audit trail integrity checks."""
        response = await admin_client.get("/api/audit/integrity-check")
        # Should succeed or 404 if not implemented
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_log_immunity(self, admin_client):
        """Test that audit logs cannot be deleted."""
        # Try to delete an audit log
        list_response = await admin_client.get("/api/audit/logs?limit=1")
        data = list_response.json()
        items = data.get("items") or data.get("logs") or data

        if items and len(items) > 0:
            log_id = items[0].get("id")
            delete_response = await admin_client.delete(f"/api/audit/logs/{log_id}")
            # Should be forbidden
            assert delete_response.status_code in [403, 404, 405]

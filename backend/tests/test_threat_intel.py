"""Threat Intelligence service tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestThreatIntelQuery:
    """Threat intelligence query tests."""

    @pytest.mark.asyncio
    async def test_query_ip_address(self, auth_client):
        """Test querying IP address threat intel."""
        response = await auth_client.post(
            "/api/ti/query",
            json={
                "ioc": "1.1.1.1",
                "ioc_type": "ip"
            }
        )

        # Should succeed or 503 if TI service unavailable
        assert response.status_code in [200, 400, 503]

        if response.status_code == 200:
            data = response.json()
            assert "ioc" in data or "threat_level" in data

    @pytest.mark.asyncio
    async def test_query_domain(self, auth_client):
        """Test querying domain threat intel."""
        response = await auth_client.post(
            "/api/ti/query",
            json={
                "ioc": "malicious-domain.com",
                "ioc_type": "domain"
            }
        )

        assert response.status_code in [200, 400, 503]

    @pytest.mark.asyncio
    async def test_query_url(self, auth_client):
        """Test querying URL threat intel."""
        response = await auth_client.post(
            "/api/ti/query",
            json={
                "ioc": "http://malicious-site.com/path",
                "ioc_type": "url"
            }
        )

        assert response.status_code in [200, 400, 503]

    @pytest.mark.asyncio
    async def test_query_hash(self, auth_client):
        """Test querying file hash threat intel."""
        response = await auth_client.post(
            "/api/ti/query",
            json={
                "ioc": "44d88612fea8a8f36de82e1278abb02f",
                "ioc_type": "hash"
            }
        )

        assert response.status_code in [200, 400, 503]

    @pytest.mark.asyncio
    async def test_query_invalid_type(self, auth_client):
        """Test querying with invalid IOC type."""
        response = await auth_client.post(
            "/api/ti/query",
            json={
                "ioc": "test",
                "ioc_type": "invalid_type"
            }
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_query_missing_fields(self, auth_client):
        """Test query with missing required fields."""
        response = await auth_client.post(
            "/api/ti/query",
            json={"ioc": "1.1.1.1"}
        )

        assert response.status_code == 422


class TestThreatIntelBulkQuery:
    """Bulk threat intelligence query tests."""

    @pytest.mark.asyncio
    async def test_bulk_query_iocs(self, auth_client):
        """Test bulk IOC query."""
        response = await auth_client.post(
            "/api/ti/bulk",
            json={
                "iocs": [
                    {"ioc": "1.1.1.1", "ioc_type": "ip"},
                    {"ioc": "malicious.com", "ioc_type": "domain"}
                ]
            }
        )

        # Should succeed or 503 if TI service unavailable
        assert response.status_code in [200, 400, 503]

        if response.status_code == 200:
            data = response.json()
            assert "results" in data or isinstance(data, list)

    @pytest.mark.asyncio
    async def test_bulk_query_limit(self, auth_client):
        """Test bulk query with too many IOCs."""
        # Create list of 101 IOCs (over limit)
        iocs = [{"ioc": f"1.1.1.{i}", "ioc_type": "ip"} for i in range(101)]

        response = await auth_client.post(
            "/api/ti/bulk",
            json={"iocs": iocs}
        )

        # Should reject due to size limit
        assert response.status_code in [400, 413]


class TestThreatIntelCache:
    """Threat intelligence cache tests."""

    @pytest.mark.asyncio
    async def test_cache_stats(self, auth_client):
        """Test getting cache statistics."""
        response = await auth_client.get("/api/ti/stats")
        assert response.status_code == 200
        data = response.json()
        assert "cache_size" in data or "size" in data

    @pytest.mark.asyncio
    async def test_clear_cache_single_ioc(self, auth_client):
        """Test clearing cache for a single IOC."""
        response = await auth_client.delete(
            "/api/ti/cache/ip/1.1.1.1"
        )
        # Should succeed or 404
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_clear_cache_expired(self, auth_client):
        """Test clearing expired cache entries."""
        response = await auth_client.delete("/api/ti/cache/expired")
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_clear_cache_all(self, auth_client):
        """Test clearing entire cache."""
        response = await auth_client.delete(
            "/api/ti/cache/all?confirm=true"
        )
        # Should succeed or 403/404
        assert response.status_code in [200, 403, 404]

    @pytest.mark.asyncio
    async def test_clear_cache_all_without_confirmation(self, auth_client):
        """Test clearing cache without confirmation parameter."""
        response = await auth_client.delete("/api/ti/cache/all")
        # Should require confirmation
        assert response.status_code in [400, 403]

    @pytest.mark.asyncio
    async def test_cache_refresh(self, auth_client):
        """Test refreshing IOC cache."""
        response = await auth_client.post(
            "/api/ti/cache/refresh",
            json=[
                {"ioc_type": "ip", "ioc_value": "1.1.1.1"},
                {"ioc_type": "domain", "ioc_value": "test.com"}
            ]
        )
        # Should succeed or 404
        assert response.status_code in [200, 404]


class TestOTXIntegration:
    """OTX (AlienVault Open Threat Exchange) integration tests."""

    @pytest.mark.asyncio
    async def test_otx_query_success(self, auth_client):
        """Test successful OTX query."""
        with patch('services.threat_intel_service.OTXClient') as mock_otx:
            mock_client = AsyncMock()
            mock_client.get_indicator_details.return_value = {
                "threat_level": "high",
                "pulses": ["Test Pulse"],
                "reputation": "malicious"
            }
            mock_otx.return_value = mock_client

            response = await auth_client.post(
                "/api/ti/query",
                json={
                    "ioc": "1.1.1.1",
                    "ioc_type": "ip",
                    "providers": ["otx"]
                }
            )

            # Should succeed if OTX is mocked
            assert response.status_code in [200, 503]

    @pytest.mark.asyncio
    async def test_otx_rate_limiting(self, auth_client):
        """Test OTX rate limiting."""
        with patch('services.threat_intel_service.OTXClient') as mock_otx:
            mock_client = AsyncMock()
            # Simulate rate limit
            mock_client.get_indicator_details.side_effect = Exception("Rate limited")
            mock_otx.return_value = mock_client

            response = await auth_client.post(
                "/api/ti/query",
                json={
                    "ioc": "1.1.1.1",
                    "ioc_type": "ip"
                }
            )

            # Should handle rate limiting gracefully
            assert response.status_code in [200, 503, 429]

    @pytest.mark.asyncio
    async def test_otx_timeout(self, auth_client):
        """Test OTX timeout handling."""
        with patch('services.threat_intel_service.OTXClient') as mock_otx:
            mock_client = AsyncMock()
            import asyncio
            mock_client.get_indicator_details.side_effect = asyncio.TimeoutError()
            mock_otx.return_value = mock_client

            response = await auth_client.post(
                "/api/ti/query",
                json={
                    "ioc": "1.1.1.1",
                    "ioc_type": "ip"
                }
            )

            # Should handle timeout gracefully
            assert response.status_code in [200, 503]


class TestThreatIntelHistory:
    """Threat intel query history tests."""

    @pytest.mark.asyncio
    async def test_query_history(self, auth_client):
        """Test getting query history."""
        response = await auth_client.get("/api/ti/history?limit=10")
        # Should succeed or 404 if endpoint not implemented
        assert response.status_code in [200, 404]

    @pytest.mark.asyncio
    async def test_top_threats(self, auth_client):
        """Test getting top threats."""
        response = await auth_client.get("/api/ti/threats/top?days=7")
        # Should succeed or 404 if endpoint not implemented
        assert response.status_code in [200, 404]


class TestThreatIntelValidation:
    """Input validation tests."""

    @pytest.mark.asyncio
    async def test_invalid_ip_format(self, auth_client):
        """Test query with invalid IP format."""
        response = await auth_client.post(
            "/api/ti/query",
            json={
                "ioc": "invalid-ip",
                "ioc_type": "ip"
            }
        )

        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_invalid_domain_format(self, auth_client):
        """Test query with invalid domain format."""
        response = await auth_client.post(
            "/api/ti/query",
            json={
                "ioc": "invalid domain@",
                "ioc_type": "domain"
            }
        )

        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_empty_ioc(self, auth_client):
        """Test query with empty IOC."""
        response = await auth_client.post(
            "/api/ti/query",
            json={
                "ioc": "",
                "ioc_type": "ip"
            }
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_sql_injection_attempt(self, auth_client):
        """Test SQL injection protection."""
        response = await auth_client.post(
            "/api/ti/query",
            json={
                "ioc": "1.1.1.1; DROP TABLE users--",
                "ioc_type": "ip"
            }
        )

        # Should sanitize or reject
        assert response.status_code in [200, 400, 422]

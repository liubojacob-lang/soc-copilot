"""Unit tests for the VirusTotal integration service (HTTP fully mocked)."""

import base64
import secrets
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

import services.integration.virustotal_service as vt_module
from services.integration.virustotal_service import VirusTotalService

pytestmark = [pytest.mark.unit]


def make_settings(**overrides) -> SimpleNamespace:
    # Fake credentials generated at runtime — never real ones.
    defaults = {
        "virustotal_api_key": f"fake-{secrets.token_urlsafe(8)}",
        "virustotal_rate_limit_rpm": 4,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.fixture(autouse=True)
def reset_rate_limit_window():
    vt_module._last_request_times.clear()
    yield
    vt_module._last_request_times.clear()


@pytest.fixture
def default_settings(monkeypatch):
    settings = make_settings()
    monkeypatch.setattr(vt_module, "settings", settings)
    return settings


def make_service(session=None) -> VirusTotalService:
    return VirusTotalService(session=session, api_key=secrets.token_urlsafe(8))


def make_response(status_code=200, json_data=None, raise_exc=None) -> Mock:
    response = Mock(status_code=status_code)
    response.json.return_value = json_data if json_data is not None else {}
    if raise_exc is not None:
        response.raise_for_status.side_effect = raise_exc
    else:
        response.raise_for_status.return_value = None
    return response


def make_client(response: Mock) -> AsyncMock:
    client = AsyncMock()
    client.is_closed = False
    client.get = AsyncMock(return_value=response)
    client.post = AsyncMock(return_value=response)
    return client


def status_error(status_code: int) -> httpx.HTTPStatusError:
    return httpx.HTTPStatusError(
        f"HTTP {status_code}",
        request=Mock(),
        response=Mock(status_code=status_code),
    )


class TestServiceConfig:
    def test_enabled_with_api_key(self):
        assert make_service().is_enabled is True

    def test_disabled_without_api_key(self, monkeypatch):
        monkeypatch.setattr(vt_module, "settings", make_settings(virustotal_api_key=""))
        assert VirusTotalService().is_enabled is False

    async def test_close_closes_client(self):
        service = make_service()
        client = AsyncMock()
        client.is_closed = False
        service._client = client

        await service.close()

        client.aclose.assert_awaited_once()
        assert service._client is None


class TestGet:
    async def test_raises_when_not_configured(self, monkeypatch):
        monkeypatch.setattr(vt_module, "settings", make_settings(virustotal_api_key=""))
        service = VirusTotalService()
        with pytest.raises(RuntimeError, match="not configured"):
            await service._get("/ip_addresses/1.2.3.4")

    async def test_returns_json_on_success(self, default_settings):
        service = make_service()
        service._get_client = AsyncMock(
            return_value=make_client(make_response(json_data={"data": {}}))
        )

        assert await service._get("/ip_addresses/1.2.3.4") == {"data": {}}

    async def test_404_returns_not_found(self, default_settings):
        service = make_service()
        service._get_client = AsyncMock(
            return_value=make_client(make_response(raise_exc=status_error(404)))
        )

        assert await service._get("/files/abc") == {"not_found": True}

    async def test_403_raises_runtime_error(self, default_settings):
        service = make_service()
        service._get_client = AsyncMock(
            return_value=make_client(make_response(raise_exc=status_error(403)))
        )

        with pytest.raises(RuntimeError, match="invalid or lacks permission"):
            await service._get("/files/abc")

    async def test_other_http_errors_are_reraised(self, default_settings):
        service = make_service()
        service._get_client = AsyncMock(
            return_value=make_client(make_response(raise_exc=status_error(500)))
        )

        with pytest.raises(httpx.HTTPStatusError):
            await service._get("/files/abc")

    async def test_request_error_becomes_connection_error(self, default_settings):
        service = make_service()
        client = AsyncMock()
        client.is_closed = False
        client.get = AsyncMock(side_effect=httpx.ConnectError("down"))
        service._get_client = AsyncMock(return_value=client)

        with pytest.raises(ConnectionError, match="unreachable"):
            await service._get("/files/abc")

    async def test_429_sleeps_then_retries(self, monkeypatch, default_settings):
        import asyncio

        sleep_mock = AsyncMock()
        monkeypatch.setattr(asyncio, "sleep", sleep_mock)
        service = make_service()
        client = AsyncMock()
        client.is_closed = False
        client.get = AsyncMock(
            side_effect=[
                make_response(status_code=429, json_data={}),
                make_response(json_data={"data": {"id": "1.2.3.4"}}),
            ]
        )
        service._get_client = AsyncMock(return_value=client)

        result = await service._get("/ip_addresses/1.2.3.4")

        assert result == {"data": {"id": "1.2.3.4"}}
        sleep_mock.assert_awaited_once_with(60)
        assert client.get.await_count == 2


def vt_payload(stats, analysis_results=None, **attrs) -> dict:
    attributes = {"last_analysis_stats": stats, **attrs}
    if analysis_results is not None:
        attributes["last_analysis_results"] = analysis_results
    return {"data": {"id": "1.2.3.4", "attributes": attributes}}


class TestLookups:
    async def test_lookup_ip_malicious(self, default_settings):
        service = make_service()
        service._get = AsyncMock(
            return_value=vt_payload(
                {"malicious": 2, "suspicious": 1, "harmless": 90, "undetected": 0},
                {"engineA": {"category": "malicious", "result": "malware"}},
                country="US",
            )
        )

        result = await service.lookup_ip("1.2.3.4")

        assert result["verdict"] == "malicious"
        assert result["score"] == 3
        assert result["malicious_votes"] == 2
        assert result["total_votes"] == 93
        assert "malware" in result["tags"]
        assert result["cached"] is False
        service._get.assert_awaited_with("/ip_addresses/1.2.3.4")

    async def test_lookup_ip_clean(self, default_settings):
        service = make_service()
        service._get = AsyncMock(
            return_value=vt_payload({"malicious": 0, "suspicious": 0, "harmless": 80})
        )

        result = await service.lookup_ip("8.8.8.8")

        assert result["verdict"] == "clean"
        assert result["score"] == 0

    async def test_lookup_ip_unknown_with_empty_stats(self, default_settings):
        service = make_service()
        service._get = AsyncMock(return_value=vt_payload({}))

        result = await service.lookup_ip("0.0.0.0")

        assert result["verdict"] == "unknown"

    async def test_lookup_ip_degrades_when_api_fails(self, default_settings):
        service = make_service()
        service._get = AsyncMock(side_effect=httpx.ConnectError("down"))

        result = await service.lookup_ip("1.2.3.4")

        assert result["verdict"] == "unknown"
        assert result["degraded"] is True
        assert result["score"] == 0

    async def test_lookup_ip_returns_cached(self, default_settings):
        session = AsyncMock()
        session.execute.return_value = Mock(
            scalar_one_or_none=Mock(
                return_value=Mock(response_json={"verdict": "clean", "score": 1})
            )
        )
        service = VirusTotalService(session=session, api_key=secrets.token_urlsafe(8))

        result = await service.lookup_ip("1.2.3.4")

        assert result["cached"] is True
        assert result["verdict"] == "clean"

    async def test_lookup_domain_lowercases_value(self, default_settings):
        service = make_service()
        service._get = AsyncMock(return_value=vt_payload({"harmless": 5}))

        await service.lookup_domain("Evil.EXAMPLE")

        service._get.assert_awaited_with("/domains/evil.example")

    async def test_lookup_hash_lowercases_value(self, default_settings):
        service = make_service()
        service._get = AsyncMock(return_value=vt_payload({"harmless": 5}))

        await service.lookup_hash("ABC123")

        service._get.assert_awaited_with("/files/abc123")

    async def test_lookup_url_uses_base64url_id_without_padding(
        self, default_settings
    ):
        service = make_service()
        service._get = AsyncMock(
            return_value=vt_payload(
                {"harmless": 5}, title="Example Domain"
            )
        )

        url = "http://evil.example/path"
        result = await service.lookup_url(url)

        expected_id = (
            base64.urlsafe_b64encode(url.encode()).decode().rstrip("=")
        )
        service._get.assert_awaited_with(f"/urls/{expected_id}")
        assert "=" not in expected_id
        assert base64.urlsafe_b64decode(expected_id + "==").decode() == url
        assert result["title"] == "Example Domain"


class TestScanUrl:
    async def test_submits_url_for_scanning(self, default_settings):
        service = make_service()
        client = make_client(
            make_response(json_data={"data": {"id": "scan-123"}})
        )
        service._get_client = AsyncMock(return_value=client)

        result = await service.scan_url("http://evil.example")

        assert result["scan_id"] == "scan-123"
        assert result["status"] == "submitted"
        client.post.assert_awaited_once()

    async def test_rate_limited_scan_returns_error_dict(self, default_settings):
        service = make_service()
        client = make_client(make_response(raise_exc=status_error(429)))
        service._get_client = AsyncMock(return_value=client)

        result = await service.scan_url("http://evil.example")

        assert result["verdict"] == "error"
        assert "Rate limited" in result["error"]

    async def test_http_error_scan_returns_error_dict(self, default_settings):
        service = make_service()
        client = make_client(make_response(raise_exc=status_error(500)))
        service._get_client = AsyncMock(return_value=client)

        result = await service.scan_url("http://evil.example")

        assert result["verdict"] == "error"

    async def test_requires_api_key(self, monkeypatch):
        monkeypatch.setattr(vt_module, "settings", make_settings(virustotal_api_key=""))
        service = VirusTotalService()
        with pytest.raises(RuntimeError, match="not configured"):
            await service.scan_url("http://evil.example")


class TestBatchLookup:
    async def test_dispatch_and_unsupported_type(self, monkeypatch, default_settings):
        import asyncio

        monkeypatch.setattr(asyncio, "sleep", AsyncMock())
        service = make_service()
        service._get = AsyncMock(
            side_effect=[
                vt_payload({"harmless": 5}),
                vt_payload({"harmless": 5}),
                vt_payload({"harmless": 5}),
                vt_payload({"harmless": 5}),
            ]
        )

        results = await service.batch_lookup(
            [
                {"type": "IP", "value": "1.2.3.4"},
                {"type": "domain", "value": "a.example"},
                {"type": "hash", "value": "abc"},
                {"type": "weird", "value": "x"},
            ]
        )

        assert len(results) == 4
        assert results[0]["ioc_type"] == "ip"
        assert results[1]["ioc_type"] == "domain"
        assert results[2]["ioc_type"] == "hash"
        assert results[3]["verdict"] == "error"
        assert "Unsupported IOC type" in results[3]["error"]


class TestParsers:
    def setup_method(self):
        self.service = make_service()

    def test_suspicious_verdict_and_score(self):
        result = self.service._parse_ip_response(
            vt_payload(
                {"malicious": 0, "suspicious": 10, "harmless": 40, "undetected": 0}
            )
        )
        assert result["verdict"] == "suspicious"
        assert result["score"] == 20

    def test_file_parser_caps_threat_names(self):
        payload = vt_payload(
            {"harmless": 5},
            popular_threat_classification={
                "popular_threat_names": [f"name-{i}" for i in range(15)]
            },
        )
        result = self.service._parse_file_response(payload)
        assert len(result["popular_threat_names"]) == 10

    def test_url_parser_defaults(self):
        result = self.service._parse_url_response(vt_payload({}), "http://x")
        assert result["title"] == ""
        assert result["ioc_value"] == "http://x"
        assert result["provider"] == "virustotal"

    def test_engine_tags_deduplicated(self):
        payload = vt_payload(
            {"malicious": 2, "harmless": 10},
            {
                "engineA": {"category": "malicious", "result": "trojan.agent"},
                "engineB": {"category": "malicious", "result": "trojan.agent"},
                "engineC": {"category": "malicious", "result": ""},
                "engineD": {"category": "harmless", "result": "clean"},
            },
        )
        result = self.service._parse_ip_response(payload)
        assert result["tags"] == ["trojan.agent"]

    async def test_degraded_result_without_cache(self):
        self.service._db_session = None
        result = await self.service._degraded_result("ip", "1.2.3.4", False)
        assert result["degraded"] is True
        assert result["score"] == 0
        assert result["error"] == "VirusTotal API unavailable; no cached result"

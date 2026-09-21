"""Unit tests for the MISP integration service (HTTP fully mocked)."""

import secrets
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import httpx
import pytest

import services.integration.misp_service as misp_module
from services.integration.misp_service import MISPService

pytestmark = [pytest.mark.unit]


def make_settings(**overrides) -> SimpleNamespace:
    # Fake credentials generated at runtime — never real ones.
    defaults = {
        "misp_base_url": "http://misp.local/",
        "misp_api_key": f"fake-{secrets.token_urlsafe(8)}",
        "misp_verify_ssl": True,
        "misp_timeout_sec": 30,
    }
    defaults.update(overrides)
    return SimpleNamespace(**defaults)


@pytest.fixture(autouse=True)
def reset_rate_limit_window():
    misp_module._last_request_times.clear()
    yield
    misp_module._last_request_times.clear()


@pytest.fixture
def default_settings(monkeypatch):
    settings = make_settings()
    monkeypatch.setattr(misp_module, "settings", settings)
    return settings


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


class TestRateLimit:
    async def test_records_request_timestamps(self):
        for _ in range(3):
            await misp_module._rate_limit(10)
        assert len(misp_module._last_request_times) == 3

    async def test_sleeps_when_window_is_full(self, monkeypatch):
        import asyncio
        import time

        sleep_mock = AsyncMock()
        monkeypatch.setattr(asyncio, "sleep", sleep_mock)
        now = time.monotonic()
        misp_module._last_request_times.extend([now] * 10)

        await misp_module._rate_limit(10)

        sleep_mock.assert_awaited_once()
        assert sleep_mock.await_args.args[0] > 0


class TestServiceConfig:
    def test_enabled_with_explicit_credentials(self):
        service = MISPService(
            base_url="http://m.local", api_key=secrets.token_urlsafe(8)
        )
        assert service.is_enabled is True

    def test_disabled_without_configuration(self, monkeypatch):
        monkeypatch.setattr(misp_module, "settings", make_settings(misp_base_url=""))
        assert MISPService().is_enabled is False

    def test_disabled_without_api_key(self, monkeypatch):
        monkeypatch.setattr(misp_module, "settings", make_settings(misp_api_key=""))
        assert MISPService().is_enabled is False

    def test_base_url_trailing_slash_stripped(self):
        service = MISPService(
            base_url="http://m.local/", api_key=secrets.token_urlsafe(8)
        )
        assert service._base_url == "http://m.local"

    async def test_close_closes_client(self):
        service = MISPService(
            base_url="http://m.local", api_key=secrets.token_urlsafe(8)
        )
        client = AsyncMock()
        client.is_closed = False
        service._client = client

        await service.close()

        client.aclose.assert_awaited_once()
        assert service._client is None


class TestGet:
    async def test_raises_when_not_configured(self):
        service = MISPService(base_url="", api_key="")
        with pytest.raises(RuntimeError, match="not configured"):
            await service._get("/events")

    async def test_plain_dict_passthrough(self, default_settings):
        service = make_service_client()
        service._get_client = AsyncMock(
            return_value=make_client(make_response(json_data={"ok": True}))
        )

        result = await service._get("/events")

        assert result == {"ok": True}

    async def test_envelope_with_attribute_is_unwrapped(self, default_settings):
        service = make_service_client()
        service._get_client = AsyncMock(
            return_value=make_client(
                make_response(json_data={"response": {"Attribute": []}})
            )
        )

        result = await service._get("/attributes")

        assert result == {"Attribute": []}

    async def test_envelope_without_special_keys_kept(self, default_settings):
        service = make_service_client()
        service._get_client = AsyncMock(
            return_value=make_client(make_response(json_data={"response": [1, 2]}))
        )

        result = await service._get("/events")

        assert result == {"response": [1, 2]}

    async def test_404_returns_not_found(self, default_settings):
        service = make_service_client()
        service._get_client = AsyncMock(
            return_value=make_client(make_response(raise_exc=status_error(404)))
        )

        assert await service._get("/events/x") == {"not_found": True}

    @pytest.mark.parametrize("status_code", [401, 403])
    async def test_auth_errors_raise_runtime_error(self, default_settings, status_code):
        service = make_service_client()
        service._get_client = AsyncMock(
            return_value=make_client(make_response(raise_exc=status_error(status_code)))
        )

        with pytest.raises(RuntimeError, match="API key is invalid"):
            await service._get("/events")

    async def test_other_http_errors_are_reraised(self, default_settings):
        service = make_service_client()
        service._get_client = AsyncMock(
            return_value=make_client(make_response(raise_exc=status_error(500)))
        )

        with pytest.raises(httpx.HTTPStatusError):
            await service._get("/events")

    async def test_request_error_becomes_connection_error(self, default_settings):
        service = make_service_client()
        client = AsyncMock()
        client.is_closed = False
        client.get = AsyncMock(side_effect=httpx.ConnectError("down"))
        service._get_client = AsyncMock(return_value=client)

        with pytest.raises(ConnectionError, match="unreachable"):
            await service._get("/events")


class TestPost:
    async def test_raises_when_not_configured(self):
        service = MISPService(base_url="", api_key="")
        with pytest.raises(RuntimeError, match="not configured"):
            await service._post("/events")

    async def test_envelope_with_attribute_is_unwrapped(self, default_settings):
        service = make_service_client()
        service._get_client = AsyncMock(
            return_value=make_client(
                make_response(json_data={"response": {"Attribute": {}}})
            )
        )

        result = await service._post("/attributes/restSearch")

        assert result == {"Attribute": {}}

    async def test_http_status_error_is_reraised(self, default_settings):
        service = make_service_client()
        service._get_client = AsyncMock(
            return_value=make_client(make_response(raise_exc=status_error(500)))
        )

        with pytest.raises(httpx.HTTPStatusError):
            await service._post("/events/restSearch")

    async def test_request_error_becomes_connection_error(self, default_settings):
        service = make_service_client()
        client = AsyncMock()
        client.is_closed = False
        client.post = AsyncMock(side_effect=httpx.ConnectError("down"))
        service._get_client = AsyncMock(return_value=client)

        with pytest.raises(ConnectionError):
            await service._post("/events/restSearch")


def make_service_client(session=None) -> MISPService:
    """Configured MISPService; attach a mocked client via service._get_client."""
    return MISPService(
        session=session,
        base_url="http://m.local",
        api_key=secrets.token_urlsafe(8),
    )


class TestSearchIocs:
    async def test_parses_and_scores_results(self, default_settings):
        service = make_service_client()
        client = make_client(
            make_response(
                json_data={
                    "response": {
                        "Attribute": [
                            {
                                "id": "1",
                                "type": "ip-src",
                                "value": "1.2.3.4",
                                "to_ids": True,
                                "Tag": [{"name": "misp:tag"}],
                            },
                            {
                                "id": "2",
                                "type": "domain",
                                "value": "evil.example",
                                "to_ids": False,
                            },
                        ]
                    }
                }
            )
        )
        service._get_client = AsyncMock(return_value=client)

        result = await service.search_iocs(ioc_type="ip-src", ioc_value="1.2.3.4")

        assert result["total"] == 2
        assert result["verdict"] == "malicious"
        assert result["score"] == 50  # 1 of 2 attributes flagged to_ids
        assert "misp:tag" in result["tags"]
        client.post.assert_awaited_once()
        assert client.post.await_args.args[0] == "/attributes/restSearch"

    async def test_degrades_when_api_unreachable(self, default_settings):
        service = make_service_client()
        client = AsyncMock()
        client.is_closed = False
        client.post = AsyncMock(side_effect=httpx.ConnectError("down"))
        service._get_client = AsyncMock(return_value=client)

        result = await service.search_iocs()

        assert result["degraded"] is True
        assert result["verdict"] == "unknown"
        assert result["iocs"] == []

    async def test_returns_cached_result_for_exact_lookup(self, default_settings):
        session = AsyncMock()
        session.execute.return_value = Mock(
            scalar_one_or_none=Mock(
                return_value=Mock(response_json={"iocs": [], "total": 0})
            )
        )
        service = make_service_client(session=session)

        result = await service.search_iocs(ioc_type="ip-src", ioc_value="1.2.3.4")

        assert result["cached"] is True


class TestEvents:
    async def test_get_event_parses_response(self, default_settings):
        service = make_service_client()
        service._get = AsyncMock(
            return_value={
                "Event": {
                    "info": "Phishing campaign",
                    "date": "2026-01-01",
                    "threat_level_id": "3",
                    "published": True,
                    "Org": {"name": "CERT"},
                    "Tag": [{"name": "tlp:white"}],
                    "Attribute": [
                        {"type": "ip-src", "value": "1.2.3.4", "to_ids": True}
                    ],
                }
            }
        )

        result = await service.get_event("event-uuid")

        assert result["event_id"] == "event-uuid"
        assert result["info"] == "Phishing campaign"
        assert result["org"] == "CERT"
        assert result["tags"] == ["tlp:white"]
        assert result["attribute_count"] == 1
        assert result["attributes"][0]["value"] == "1.2.3.4"

    async def test_get_event_degrades_on_failure(self, default_settings):
        service = make_service_client()
        service._get = AsyncMock(side_effect=httpx.ConnectError("down"))

        result = await service.get_event("event-uuid")

        assert result["verdict"] == "error"
        assert result["degraded"] is True

    async def test_search_events_degrades_on_failure(self, default_settings):
        service = make_service_client()
        client = AsyncMock()
        client.is_closed = False
        client.post = AsyncMock(side_effect=httpx.ConnectError("down"))
        service._get_client = AsyncMock(return_value=client)

        result = await service.search_events(event_info="phishing")

        assert result["events"] == []
        assert result["degraded"] is True
        assert result["total"] == 0

    async def test_search_sightings_parses_list(self, default_settings):
        service = make_service_client()
        client = make_client(
            make_response(
                json_data={
                    "response": [
                        {
                            "id": "s1",
                            "attribute_id": "a1",
                            "event_id": "e1",
                            "source": "unit-test",
                            "type": "0",
                        },
                    ]
                }
            )
        )
        service._get_client = AsyncMock(return_value=client)

        result = await service.search_sightings("ip-src", "1.2.3.4")

        assert result["total"] == 1
        assert result["sightings"][0]["id"] == "s1"
        assert result["sightings"][0]["source"] == "unit-test"

    async def test_search_sightings_wraps_single_dict(self, default_settings):
        service = make_service_client()
        client = make_client(make_response(json_data={"Sighting": {"id": "s1"}}))
        service._get_client = AsyncMock(return_value=client)

        result = await service.search_sightings("ip-src", "1.2.3.4")

        assert result["total"] == 1

    async def test_search_sightings_degrades_on_failure(self, default_settings):
        service = make_service_client()
        client = AsyncMock()
        client.is_closed = False
        client.post = AsyncMock(side_effect=httpx.ConnectError("down"))
        service._get_client = AsyncMock(return_value=client)

        result = await service.search_sightings("ip-src", "1.2.3.4")

        assert result["degraded"] is True
        assert result["sightings"] == []


class TestBatchLookup:
    async def test_continues_after_error(self, monkeypatch, default_settings):
        import asyncio

        monkeypatch.setattr(asyncio, "sleep", AsyncMock())
        service = make_service_client()

        async def flaky_post(endpoint, json=None):
            if json.get("value") == "bad":
                raise httpx.ConnectError("down")
            return make_response(json_data={"response": {"Attribute": []}})

        client = AsyncMock()
        client.is_closed = False
        client.post = AsyncMock(side_effect=flaky_post)
        service._get_client = AsyncMock(return_value=client)

        results = await service.batch_lookup_iocs(
            [{"type": "ip-src", "value": "ok"}, {"type": "domain", "value": "bad"}]
        )

        assert len(results) == 2
        assert results[0]["total"] == 0
        # search_iocs swallows API errors internally and degrades instead
        assert results[1]["degraded"] is True
        assert results[1]["verdict"] == "unknown"


class TestParsers:
    def setup_method(self):
        self.service = make_service_client()

    def test_empty_results_are_unknown(self):
        result = self.service._parse_search_results({}, "attributes", "ip-src")
        assert result["verdict"] == "unknown"
        assert result["score"] == 0
        assert result["total"] == 0

    def test_ids_flag_drives_malicious_verdict(self):
        raw = {"Attribute": [{"to_ids": True}, {"to_ids": False}]}
        result = self.service._parse_search_results(raw, "attributes", "ip-src")
        assert result["verdict"] == "malicious"
        assert result["score"] == 50

    def test_attributes_without_ids_flag_are_suspicious(self):
        raw = {"Attribute": [{"value": "x"}]}
        result = self.service._parse_search_results(raw, "attributes", "ip-src")
        assert result["verdict"] == "suspicious"

    def test_tag_collection_deduplicates(self):
        raw = {"Attribute": [{"Tag": [{"name": "a"}, {"name": "a"}, {"name": "b"}]}]}
        result = self.service._parse_search_results(raw, "attributes", "ip-src")
        assert sorted(result["tags"]) == ["a", "b"]

    def test_normalize_attribute_defaults(self):
        parsed = self.service._normalize_attribute({}, "ip-dst")
        assert parsed["type"] == "ip-dst"
        assert parsed["to_ids"] is False
        assert parsed["tags"] == []

    async def test_degraded_result_without_cache(self):
        self.service._db_session = None
        result = await self.service._degraded_result("search", "ioc", False, None)
        assert result["degraded"] is True
        assert result["error"] == "MISP API unavailable; no cached result"

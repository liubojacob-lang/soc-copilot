"""Comprehensive unit tests for Playbook Executors and ExecutorFactory."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.playbook_executors.decision_executor import DecisionExecutor
from services.playbook_executors.executor_base import ExecutorContext
from services.playbook_executors.executor_factory import ExecutorFactory
from services.playbook_executors.extract_iocs_executor import ExtractIocsExecutor
from services.playbook_executors.http_request_executor import (
    is_private_ip,
    validate_url,
)
from services.playbook_executors.human_approval_executor import HumanApprovalExecutor
from services.playbook_executors.slack_webhook_executor import SlackWebhookExecutor
from services.playbook_executors.sleep_executor import SleepExecutor


def test_executor_factory():
    types = ExecutorFactory.list_types()
    assert "sleep" in types
    assert "decision" in types
    assert "extract_iocs" in types
    assert "http_request" in types
    assert "human_approval" in types
    assert "slack_webhook_notify" in types

    sleep_exec = ExecutorFactory.get_executor("sleep")
    assert isinstance(sleep_exec, SleepExecutor)

    with pytest.raises(ValueError) as exc:
        ExecutorFactory.get_executor("nonexistent_unknown_node")
    assert "No executor registered" in str(exc.value)


@pytest.mark.asyncio
async def test_sleep_executor():
    executor = SleepExecutor()
    ctx = ExecutorContext(
        run_id="run-1",
        node_id="node-1",
        node_def={"config": {"seconds": 0.01}},
        input_json={},
    )
    with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
        res = await executor.execute(ctx)
        assert res["status"] == "success"
        assert res["slept_seconds"] == 0.01
        mock_sleep.assert_awaited_once_with(0.01)


@pytest.mark.asyncio
async def test_decision_executor():
    executor = DecisionExecutor()

    # 1. No condition (default)
    ctx_default = ExecutorContext(
        run_id="run-1",
        node_id="dec-1",
        node_def={"config": {"branches": {"true": "node-2", "false": "node-3"}}},
        input_json={},
    )
    res_default = await executor.execute(ctx_default)
    assert res_default["status"] == "success"
    assert res_default["result"] == "default"

    # 2. Number comparisons: >, <, >=, <=, ==, !=
    cases = [
        ("count > 10", {"count": 15}, True),
        ("count > 10", {"count": 5}, False),
        ("count < 10", {"count": 5}, True),
        ("count >= 10", {"count": 10}, True),
        ("count <= 10", {"count": 10}, True),
        ("score == 100", {"score": 100}, True),
        ("score != 100", {"score": 50}, True),
        ("severity == critical", {"severity": "critical"}, True),
        ("severity == high", {"severity": "low"}, False),
        ("invalid", {"count": 1}, True),
    ]

    for cond, inp, expected in cases:
        ctx = ExecutorContext(
            run_id="run-1",
            node_id="dec-1",
            node_def={"config": {"condition": cond}},
            input_json=inp,
        )
        res = await executor.execute(ctx)
        assert (
            res["result"] == expected
        ), f"Failed for condition '{cond}' with input {inp}"


@pytest.mark.asyncio
async def test_extract_iocs_executor():
    executor = ExtractIocsExecutor()
    sample_text = (
        "Malicious connection to 198.51.100.24 and domain sub.bad-site.com. "
        "Also downloaded payload from https://evil.org/payload.exe. "
        "Attacker email phishing@attacker.net. "
        "MD5: e4d909c290d0fb1ca068ffaddf22cbd0 "
        "SHA256: e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    )
    ctx = ExecutorContext(
        run_id="run-1",
        node_id="ioc-1",
        node_def={},
        input_json={"text": sample_text},
    )
    res = await executor.execute(ctx)
    assert res["status"] == "success"
    iocs = res["iocs"]
    assert "198.51.100.24" in iocs["ips"]
    assert any("sub.bad-site.com" in d for d in iocs["domains"])
    assert any("https://evil.org/payload.exe" in u for u in iocs["urls"])
    assert "phishing@attacker.net" in iocs["emails"]
    assert any("e4d909c290d0fb1ca068ffaddf22cbd0" in h for h in iocs["hashes"])
    assert res["total_count"] > 0


def test_ssrf_helpers():
    # Private IPs
    assert is_private_ip("127.0.0.1") is True
    assert is_private_ip("10.0.0.1") is True
    assert is_private_ip("192.168.1.1") is True
    assert is_private_ip("172.16.0.1") is True
    assert is_private_ip("8.8.8.8") is False
    assert is_private_ip("invalid-ip") is False

    # URL Validation
    valid, err = validate_url("ftp://example.com/file")
    assert valid is False
    assert "Protocol 'ftp' is not allowed" in err

    valid, err = validate_url("http://127.0.0.1:8080/admin")
    assert valid is False
    assert "private" in err.lower()

    valid, err = validate_url("http:///missing-host")
    assert valid is False

    with patch(
        "services.playbook_executors.http_request_executor.resolve_hostname",
        return_value=["93.184.216.34"],
    ):
        valid, err = validate_url("https://example.com/api/v1")
        assert valid is True
        assert err == ""

    with patch(
        "services.playbook_executors.http_request_executor.resolve_hostname",
        return_value=["192.168.1.100"],
    ):
        valid, err = validate_url("https://internal.lan/secret")
        assert valid is False
        assert "private IP" in err


@pytest.mark.asyncio
async def test_slack_webhook_executor():
    executor = SlackWebhookExecutor()

    # 1. No webhook URL
    with patch.dict("os.environ", {}, clear=True):
        ctx_no_url = ExecutorContext(
            run_id="run-12345678901234567890",
            node_id="slack-1",
            node_def={"config": {}},
            input_json={"status": "failed"},
        )
        res_no_url = await executor.execute(ctx_no_url)
        assert res_no_url["status"] == "skipped"

    # 2. Webhook URL provided, successful send
    ctx_success = ExecutorContext(
        run_id="run-12345678901234567890",
        node_id="slack-1",
        node_def={
            "config": {
                "webhook_url": "https://hooks.slack.com/services/T00/B00/X00",
                "message_template": "Status: {{status}}",
                "include_output_fields": ["status", "count"],
            }
        },
        input_json={"status": "completed", "count": 42},
    )
    mock_resp = MagicMock()
    mock_resp.status_code = 200

    with patch(
        "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_resp
    ):
        res = await executor.execute(ctx_success)
        assert res["status"] == "success"
        assert res["message"] == "Notification sent"


@pytest.mark.asyncio
async def test_human_approval_executor():
    executor = HumanApprovalExecutor()
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.close = AsyncMock()

    ctx = ExecutorContext(
        run_id="run-app-1",
        node_id="node-app-1",
        node_def={
            "config": {
                "title": "Block IP Approval",
                "message": "Approve blocking 1.2.3.4?",
                "timeout_seconds": 3600,
            }
        },
        input_json={},
        user_id="analyst-bob",
    )

    with patch.object(executor, "_get_session", return_value=mock_session):
        with patch.object(
            executor, "_update_node_status", new_callable=AsyncMock
        ) as mock_upd:
            res = await executor.execute(ctx)
            assert res["status"] == "waiting_approval"
            assert res["title"] == "Block IP Approval"
            assert res["paused"] is True
            mock_session.flush.assert_awaited()
            mock_session.commit.assert_awaited()
            mock_upd.assert_awaited_once()

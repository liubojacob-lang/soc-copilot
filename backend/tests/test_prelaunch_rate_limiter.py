"""Pre-launch regression tests for the ``@rate_limit`` decorator.

``backend/middleware/rate_limiter.py`` was changed in the v0.9.4 batch (the
decorator now scans keyword arguments for a ``Request`` instance instead of
only looking at ``kwargs["request"]``) yet sits at ~34% coverage with no
dedicated test file. The decorator is the only brute-force protection in front
of ``POST /api/v1/auth/login`` (5 req/min outside development), so a silent
bypass is a security-relevant regression.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, Request, Response

from middleware.rate_limiter import rate_limit

# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def _scope(path="/api/v1/auth/login", client=("203.0.113.9", 54321)):
    return {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "root_path": "",
        "headers": [(b"host", b"localhost")],
        "client": client,
        "server": ("testserver", 80),
    }


def _request(**kwargs):
    return Request(_scope(**kwargs))


class _Patch:
    """Patch settingsenv + limiter for one test."""

    def __enter__(self):
        self.settings = patch(
            "middleware.rate_limiter.settings", MagicMock(environment="production")
        )
        self.get_ip = patch("middleware.rate_limiter.get_client_ip", return_value="203.0.113.9")
        self.get_limiter = patch("middleware.rate_limiter.get_rate_limiter")
        self.settings.start()
        self.get_ip.start()
        limiter_patch = self.get_limiter.start()
        self.limiter = MagicMock()
        self.limiter.is_allowed = AsyncMock(return_value=(True, {"limit": 5, "remaining": 4, "reset": 60}))
        limiter_patch.return_value = self.limiter
        return self

    def __exit__(self, *exc):
        self.get_limiter.stop()
        self.get_ip.stop()
        self.settings.stop()


# --------------------------------------------------------------------------- #
# Environment short-circuit
# --------------------------------------------------------------------------- #


class TestEnvironmentShortCircuit:
    async def test_test_environment_bypasses_limiter(self):
        calls = []

        @rate_limit(max_requests=1, window_seconds=60)
        async def endpoint(request: Request):
            calls.append(1)
            return Response("ok")

        with patch(
            "middleware.rate_limiter.settings", MagicMock(environment="test")
        ), patch("middleware.rate_limiter.get_rate_limiter") as get_limiter:
            await endpoint(request=_request())
            await endpoint(request=_request())

        assert len(calls) == 2
        get_limiter.assert_not_called()


# --------------------------------------------------------------------------- #
# Request extraction (the code changed in this release)
# --------------------------------------------------------------------------- #


class TestRequestExtraction:
    async def test_request_found_under_canonical_name(self):
        seen = {}

        @rate_limit(max_requests=5, window_seconds=60)
        async def endpoint(request: Request):
            return Response("ok")

        with _Patch() as p:
            await endpoint(request=_request())

        p.limiter.is_allowed.assert_awaited_once()
        seen["kwargs"] = p.limiter.is_allowed.await_args.kwargs
        assert seen["kwargs"]["endpoint"] == "/api/v1/auth/login"
        assert seen["kwargs"]["max_requests"] == 5

    async def test_request_found_under_non_canonical_kwarg(self):
        """v0.9.4 change: a Request under any kwarg name must still be limited."""

        @rate_limit(max_requests=5, window_seconds=60)
        async def endpoint(http_request: Request):
            return Response("ok")

        with _Patch() as p:
            await endpoint(http_request=_request())

        p.limiter.is_allowed.assert_awaited_once()

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "DEFECT QA-004: decorator only inspects kwargs, never *args — a Request "
            "passed positionally bypasses rate limiting entirely."
        ),
    )
    async def test_request_passed_positionally_is_still_limited(self):
        @rate_limit(max_requests=5, window_seconds=60)
        async def endpoint(req: Request):
            return Response("ok")

        with _Patch() as p:
            await endpoint(_request())

        p.limiter.is_allowed.assert_awaited_once()

    async def test_non_request_kwarg_bypasses_limiter(self):
        """Regression guard for the /analyze-alert renaming bug.

        Before v0.9.4 the decorator used ``kwargs.get("request")`` with a bare
        truthiness check; when the body model was named ``request`` the
        decorator tried to read ``.client`` off a Pydantic model.
        """

        @rate_limit(max_requests=5, window_seconds=60)
        async def endpoint(request):  # request is a Pydantic body, not a Request
            return Response("ok")

        with _Patch() as p:
            resp = await endpoint(request=MagicMock())

        assert resp.body == b"ok"
        p.limiter.is_allowed.assert_not_called()

    async def test_missing_request_bypasses_limiter(self):
        @rate_limit(max_requests=5, window_seconds=60)
        async def endpoint(payload=None):
            return Response("ok")

        with _Patch() as p:
            await endpoint()

        p.limiter.is_allowed.assert_not_called()


# --------------------------------------------------------------------------- #
# Limiter outcomes
# --------------------------------------------------------------------------- #


class TestLimiterOutcomes:
    async def test_over_limit_raises_429_with_headers(self):
        @rate_limit(max_requests=5, window_seconds=60)
        async def endpoint(request: Request):
            return Response("ok")

        with _Patch() as p:
            p.limiter.is_allowed = AsyncMock(
                return_value=(False, {"limit": 5, "remaining": 0, "reset": 30})
            )
            with pytest.raises(HTTPException) as exc:
                await endpoint(request=_request())

        assert exc.value.status_code == 429
        assert exc.value.headers["X-RateLimit-Limit"] == "5"
        assert exc.value.headers["Retry-After"] == "30"

    async def test_redis_unavailable_raises_503(self):
        @rate_limit(max_requests=5, window_seconds=60)
        async def endpoint(request: Request):
            return Response("ok")

        with _Patch() as p:
            p.limiter.is_allowed = AsyncMock(
                return_value=(
                    False,
                    {"limit": 5, "remaining": 0, "reset": 30, "redis_unavailable": True},
                )
            )
            with pytest.raises(HTTPException) as exc:
                await endpoint(request=_request())

        assert exc.value.status_code == 503

    async def test_allowed_response_gets_rate_limit_headers(self):
        @rate_limit(max_requests=5, window_seconds=60)
        async def endpoint(request: Request):
            return Response("ok")

        with _Patch() as p:
            resp = await endpoint(request=_request())

        assert resp.headers["X-RateLimit-Limit"] == "5"
        assert resp.headers["X-RateLimit-Remaining"] == "4"
        assert resp.headers["X-RateLimit-Reset"] == "60"

    async def test_requests_without_client_share_unknown_bucket(self):
        """DEFECT QA-005 (documented): ``request.client is None`` ⇒ identifier
        ``"unknown"``, so every such request shares one bucket."""

        @rate_limit(max_requests=5, window_seconds=60)
        async def endpoint(request: Request):
            return Response("ok")

        with _Patch() as p:
            await endpoint(request=_request(client=None))

        assert p.limiter.is_allowed.await_args.kwargs["identifier"] == "unknown"

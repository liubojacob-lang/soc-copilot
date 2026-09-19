"""Tests for runtime prompt resolution (T3.2).

Contract points:

1. An active registry row overrides the builtin template.
2. Missing row / blank content / registry outage all fall back to the
   builtin — the registry can never break the analysis path.
3. Environment mapping matches settings.environment → registry enum.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from services.prompt_resolution import (
    _ENV_MAPPING,
    _registry_environment,
    resolve_prompt,
)


def _factory_with_rows(rows):
    """resolve_prompt uses result.scalar_one_or_none(); mock accordingly."""
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=None)
    session.execute = AsyncMock(
        return_value=MagicMock(
            scalar_one_or_none=MagicMock(return_value=rows[0] if rows else None)
        )
    )
    return MagicMock(return_value=session)


def _row(content, version="v2"):
    row = MagicMock()
    row.content = content
    row.version = version
    return row


class TestResolvePrompt:
    @pytest.mark.asyncio
    async def test_active_registry_row_overrides_builtin(self):
        factory = _factory_with_rows([_row("CUSTOM TEMPLATE {raw_log}")])

        result = await resolve_prompt(
            "alert_analysis_user", "BUILTIN {raw_log}", session_factory=factory
        )

        assert result == "CUSTOM TEMPLATE {raw_log}"

    @pytest.mark.asyncio
    async def test_missing_row_falls_back_to_builtin(self):
        factory = _factory_with_rows([])

        result = await resolve_prompt(
            "alert_analysis_user", "BUILTIN", session_factory=factory
        )

        assert result == "BUILTIN"

    @pytest.mark.asyncio
    async def test_blank_content_falls_back_to_builtin(self):
        factory = _factory_with_rows([_row("   ")])

        result = await resolve_prompt(
            "alert_analysis_user", "BUILTIN", session_factory=factory
        )

        assert result == "BUILTIN"

    @pytest.mark.asyncio
    async def test_registry_outage_falls_back_to_builtin(self):
        factory = MagicMock(side_effect=RuntimeError("db down"))

        result = await resolve_prompt(
            "alert_analysis_user", "BUILTIN", session_factory=factory
        )

        assert result == "BUILTIN"


class TestEnvironmentMapping:
    def test_known_environments_map(self):
        from models.prompt_registry import PromptEnvironment

        assert _ENV_MAPPING["development"] is PromptEnvironment.DEV
        assert _ENV_MAPPING["test"] is PromptEnvironment.DEV
        assert _ENV_MAPPING["staging"] is PromptEnvironment.STAGING
        assert _ENV_MAPPING["production"] is PromptEnvironment.PROD

    def test_unknown_environment_defaults_to_dev(self):
        from models.prompt_registry import PromptEnvironment

        import core.config as config_mod

        original = config_mod.settings.environment
        config_mod.settings.environment = "weird-env"
        try:
            assert _registry_environment() is PromptEnvironment.DEV
        finally:
            config_mod.settings.environment = original

"""Facade for correlation execution.

This module exists as the new primary entry for DSL-based correlation while the
legacy `event_correlation_service.py` remains for backward compatibility.
"""

from __future__ import annotations

from typing import Any

from .rule_engine import RuleEngine
from .schemas import CorrelationRuleDSL


async def correlate_with_dsl(events: list[dict[str, Any]], rules: list[dict[str, Any]]) -> dict[str, Any]:
    engine = RuleEngine()
    dsl_rules = [CorrelationRuleDSL.model_validate(item) for item in rules]
    incidents = engine.execute(events, dsl_rules)
    return {
        "incidents": incidents,
        "execution_logs": [x.model_dump(mode="json") for x in engine.execution_logs],
    }

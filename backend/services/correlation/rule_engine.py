"""Correlation RuleEngine with window aggregation, dimensions and weighted scoring."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any

from core.metrics import observe_correlation_rule_hit

from .schemas import CorrelationRuleDSL, RuleExecutionLog


class RuleEngine:
    """Executes DSL-based correlation rules over event batches."""

    def __init__(self):
        self.execution_logs: list[RuleExecutionLog] = []

    def execute(
        self, events: list[dict[str, Any]], rules: list[CorrelationRuleDSL]
    ) -> list[dict[str, Any]]:
        incidents: list[dict[str, Any]] = []
        self.execution_logs.clear()

        normalized = [self._normalize_event(e) for e in events]
        for rule in rules:
            if not rule.enabled:
                continue

            windowed_groups = self._group_by_window_and_dimensions(
                normalized,
                rule.aggregation.window_seconds,
                rule.aggregation.dimensions,
            )

            for (window_start, dim_key), grouped_events in windowed_groups.items():
                matched = [
                    evt for evt in grouped_events if self._match_clause(evt, rule)
                ]
                raw_score = len(matched) * rule.weight
                threshold_hit = (
                    len(matched) >= rule.threshold.min_count
                    and raw_score >= rule.threshold.min_score
                )

                self.execution_logs.append(
                    RuleExecutionLog(
                        rule_id=rule.id,
                        rule_name=rule.name,
                        window_start=window_start,
                        window_end=window_start
                        + timedelta(seconds=rule.aggregation.window_seconds),
                        dimension_key=dim_key,
                        matched_count=len(matched),
                        score=raw_score,
                        triggered=threshold_hit,
                        reason=(
                            "threshold-met" if threshold_hit else "threshold-not-met"
                        ),
                    )
                )

                if threshold_hit:
                    tenant_id = (
                        str(matched[0].get("tenant_id", "default"))
                        if matched
                        else "default"
                    )
                    observe_correlation_rule_hit(rule.id, tenant_id)
                    incidents.append(
                        {
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "dimension_key": dim_key,
                            "window_start": window_start.isoformat(),
                            "window_end": (
                                window_start
                                + timedelta(seconds=rule.aggregation.window_seconds)
                            ).isoformat(),
                            "score": raw_score,
                            "matched_events": matched,
                            "event_count": len(matched),
                        }
                    )

        return incidents

    def dsl_example(self) -> dict[str, Any]:
        return {
            "id": "rule_failed_login_spike",
            "name": "Failed login spike by host+ip",
            "enabled": True,
            "weight": 2.5,
            "aggregation": {
                "window_seconds": 600,
                "dimensions": ["source_ip", "agent_name", "username"],
            },
            "clause": {
                "operator": "AND",
                "conditions": [
                    {
                        "field": "event_type",
                        "op": "in",
                        "value": ["auth_failed", "login_failed"],
                    },
                    {"field": "severity", "op": "in", "value": ["high", "critical"]},
                ],
            },
            "threshold": {"min_count": 3, "min_score": 6.0},
        }

    def _normalize_event(self, event: dict[str, Any]) -> dict[str, Any]:
        copied = dict(event)
        ts = copied.get("timestamp") or copied.get("created_at")
        if isinstance(ts, str):
            try:
                copied["_dt"] = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                copied["_dt"] = datetime.now(UTC)
        elif isinstance(ts, datetime):
            copied["_dt"] = ts
        else:
            copied["_dt"] = datetime.now(UTC)
        return copied

    def _group_by_window_and_dimensions(
        self,
        events: list[dict[str, Any]],
        window_seconds: int,
        dimensions: list[str],
    ) -> dict[tuple[datetime, str], list[dict[str, Any]]]:
        grouped: dict[tuple[datetime, str], list[dict[str, Any]]] = defaultdict(list)
        for event in events:
            dt = event["_dt"]
            bucket_seconds = int(dt.timestamp()) // window_seconds * window_seconds
            window_start = datetime.fromtimestamp(bucket_seconds, tz=UTC)
            dim_values = (
                [str(event.get(dim, "*")) for dim in dimensions]
                if dimensions
                else ["all"]
            )
            dim_key = "|".join(dim_values)
            grouped[(window_start, dim_key)].append(event)
        return grouped

    def _match_clause(self, event: dict[str, Any], rule: CorrelationRuleDSL) -> bool:
        results = [
            self._match_condition(event, cond.field, cond.op, cond.value)
            for cond in rule.clause.conditions
        ]
        if not results:
            return True
        return all(results) if rule.clause.operator == "AND" else any(results)

    def _match_condition(
        self, event: dict[str, Any], field: str, op: str, value: Any
    ) -> bool:
        actual = event.get(field)
        if op == "exists":
            return field in event and event.get(field) is not None
        if op == "eq":
            return actual == value
        if op == "ne":
            return actual != value
        if op == "in":
            return actual in (value or [])
        if op == "contains":
            return str(value) in str(actual)
        if op == "gt":
            return self._safe_num(actual) > self._safe_num(value)
        if op == "gte":
            return self._safe_num(actual) >= self._safe_num(value)
        if op == "lt":
            return self._safe_num(actual) < self._safe_num(value)
        if op == "lte":
            return self._safe_num(actual) <= self._safe_num(value)
        return False

    def _safe_num(self, value: Any) -> float:
        try:
            return float(value)
        except Exception:
            return 0.0

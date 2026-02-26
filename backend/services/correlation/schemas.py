"""Correlation rule DSL schemas."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RuleCondition(BaseModel):
    model_config = ConfigDict(extra="allow")

    field: str
    op: Literal["eq", "ne", "in", "gt", "gte", "lt", "lte", "contains", "exists"]
    value: Any = None


class RuleClause(BaseModel):
    model_config = ConfigDict(extra="allow")

    operator: Literal["AND", "OR"] = "AND"
    conditions: list[RuleCondition] = Field(default_factory=list)


class RuleThreshold(BaseModel):
    model_config = ConfigDict(extra="allow")

    min_count: int = 1
    min_score: float = 0.0


class RuleAggregation(BaseModel):
    model_config = ConfigDict(extra="allow")

    window_seconds: int = 300
    dimensions: list[str] = Field(default_factory=lambda: ["source_ip"])


class CorrelationRuleDSL(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    name: str
    enabled: bool = True
    weight: float = 1.0
    aggregation: RuleAggregation = Field(default_factory=RuleAggregation)
    clause: RuleClause = Field(default_factory=RuleClause)
    threshold: RuleThreshold = Field(default_factory=RuleThreshold)


class RuleExecutionLog(BaseModel):
    model_config = ConfigDict(extra="allow")

    rule_id: str
    rule_name: str
    window_start: datetime
    window_end: datetime
    dimension_key: str
    matched_count: int
    score: float
    triggered: bool
    reason: str = ""
    executed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

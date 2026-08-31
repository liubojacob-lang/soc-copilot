"""
Server-side Message Filter Models

This module defines the data models for server-side message filtering,
allowing users to control which messages they receive via WebSocket.

Filter Features:
- Severity level filtering (min/max severity)
- Event type filtering (whitelist/blacklist)
- Agent ID filtering
- Source IP filtering
- Aggregation control
"""

from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    """Security alert severity levels"""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

    @classmethod
    def get_order(cls, severity: "SeverityLevel") -> int:
        """Get numeric order for severity (lower = more severe)."""
        order = {
            cls.CRITICAL: 0,
            cls.HIGH: 1,
            cls.MEDIUM: 2,
            cls.LOW: 3,
            cls.INFO: 4,
        }
        return order.get(severity, 99)

    def __lt__(self, other):
        """Compare severities for sorting."""
        if isinstance(other, SeverityLevel):
            return self.get_order(self) < self.get_order(other)
        return NotImplemented


class FilterOperator(str, Enum):
    """Filter matching operators"""

    EQUALS = "equals"
    CONTAINS = "contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    IN = "in"


class StringFilter(BaseModel):
    """String filter with operator and value"""

    operator: FilterOperator = FilterOperator.EQUALS
    values: list[str] = Field(default_factory=list)
    case_sensitive: bool = False

    def match(self, text: str) -> bool:
        """Check if text matches this filter."""
        if not self.case_sensitive:
            text = text.lower()
            values = [v.lower() for v in self.values]

        if self.operator == FilterOperator.EQUALS:
            return text in values
        elif self.operator == FilterOperator.CONTAINS:
            return any(v in text for v in values)
        elif self.operator == FilterOperator.STARTS_WITH:
            return any(text.startswith(v) for v in values)
        elif self.operator == FilterOperator.ENDS_WITH:
            return any(text.endswith(v) for v in values)
        elif self.operator == FilterOperator.IN:
            return text in values
        elif self.operator == FilterOperator.REGEX:
            import re

            return any(re.search(v, text) for v in values)

        return False


class FilterRule(BaseModel):
    """
    Server-side message filter rule for WebSocket messages.

    Users can create multiple rules to control which messages they receive.
    Rules are evaluated in order, first matching rule wins.
    """

    id: str | None = None
    user_id: str

    # Rule metadata
    name: str = Field(default="My Filter")
    description: str = Field(default="")
    enabled: bool = Field(default=True)
    priority: int = Field(
        default=0, description="Higher priority rules evaluated first"
    )

    # Severity filter
    min_severity: SeverityLevel | None = None
    max_severity: SeverityLevel | None = None

    # Event type filter
    event_types: StringFilter | None = None

    # Agent filter
    agent_ids: StringFilter | None = None

    # Source IP filter
    source_ips: StringFilter | None = None

    # Content filter (search in full_log)
    content_search: StringFilter | None = None

    # Aggregation control
    enable_aggregation: bool = Field(default=True)

    # Rate limiting
    max_messages_per_minute: int | None = Field(
        default=None,
        description="Maximum messages to receive per minute (0 = unlimited)",
    )

    # Metadata
    created_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    last_triggered_at: str | None = None

    def matches(self, message_data: dict[str, Any]) -> bool:
        """
        Check if a message matches this filter rule.

        Args:
            message_data: Message data to check against this rule

        Returns:
            True if the message matches (should be sent), False otherwise
        """
        if not self.enabled:
            return False

        # Check severity
        severity = message_data.get("severity")
        if severity:
            try:
                severity_level = SeverityLevel(severity)

                if self.min_severity:
                    if severity_level < self.min_severity:
                        return False

                if self.max_severity:
                    if severity_level > self.max_severity:
                        return False
            except ValueError:
                pass  # Invalid severity, ignore

        # Check event type
        if self.event_types:
            event_type = message_data.get("event_type")
            if event_type:
                if not self.event_types.match(event_type):
                    return False

        # Check agent
        if self.agent_ids:
            agent = message_data.get("agent", {})
            agent_id = agent.get("id")
            if agent_id:
                if not self.agent_ids.match(agent_id):
                    return False

        # Check source IP
        if self.source_ips:
            source_ip = message_data.get("source_ip")
            if source_ip:
                if not self.source_ips.match(source_ip):
                    return False

        # Check content
        if self.content_search:
            full_log = message_data.get("full_log", "")
            if full_log:
                if not self.content_search.match(full_log):
                    return False

        # All checks passed
        return True

    class Config:
        json_schema_extra = {
            "example": {
                "id": "rule123",
                "user_id": "user456",
                "name": "High Severity Alerts Only",
                "description": "Only receive high and critical severity alerts",
                "enabled": True,
                "priority": 1,
                "min_severity": "high",
                "event_types": {
                    "operator": "in",
                    "values": ["malware", "ssh_bruteforce", "ransomware"],
                    "case_sensitive": False,
                },
                "enable_aggregation": True,
            }
        }


class FilterSet(BaseModel):
    """A collection of filter rules for a user"""

    user_id: str
    rules: list[FilterRule] = Field(default_factory=list)
    default_action: str = Field(
        default="allow", description="Default action if no rules match: allow or block"
    )
    updated_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())

    def get_active_rules(self) -> list[FilterRule]:
        """Get enabled rules sorted by priority (highest first)"""
        return [r for r in self.rules if r.enabled]

    def get_sorted_rules(self) -> list[FilterRule]:
        """Get enabled rules sorted by priority (highest first)"""
        active = self.get_active_rules()
        return sorted(active, key=lambda r: r.priority, reverse=True)

    def should_send_message(self, message_data: dict[str, Any]) -> bool:
        """
        Evaluate whether a message should be sent based on filter rules.

        Args:
            message_data: Message data to evaluate

        Returns:
            True if message should be sent, False otherwise
        """
        sorted_rules = self.get_sorted_rules()

        # If no rules, use default action
        if not sorted_rules:
            return self.default_action == "allow"

        # Check rules in priority order
        for rule in sorted_rules:
            if rule.matches(message_data):
                # Rule matched, check if it's an allow or block rule
                # For now, all rules are "allow if matches"
                return True

        # No rules matched, use default action
        return self.default_action == "allow"

    def add_rule(self, rule: FilterRule) -> FilterRule:
        """Add a rule to the filter set"""
        rule.id = f"rule_{datetime.now(UTC).timestamp()}"
        rule.created_at = datetime.now(UTC).isoformat()
        rule.updated_at = datetime.now(UTC).isoformat()
        self.rules.append(rule)
        self.updated_at = datetime.now(UTC).isoformat()
        return rule

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID"""
        for i, rule in enumerate(self.rules):
            if rule.id == rule_id:
                self.rules.pop(i)
                self.updated_at = datetime.now(UTC).isoformat()
                return True
        return False

    def update_rule(self, rule_id: str, updates: dict[str, Any]) -> FilterRule | None:
        """Update a rule by ID"""
        for rule in self.rules:
            if rule.id == rule_id:
                for key, value in updates.items():
                    setattr(rule, key, value)
                rule.updated_at = datetime.now(UTC).isoformat()
                self.updated_at = datetime.now(UTC).isoformat()
                return rule
        return None

    def get_rule(self, rule_id: str) -> FilterRule | None:
        """Get a rule by ID"""
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        return None


class FilterValidationResult(BaseModel):
    """Result of validating a message against filters"""

    user_id: str
    should_send: bool
    matched_rules: list[str] = Field(default_factory=list)
    rejected_by: str | None = Field(default=None)
    processing_time_ms: float = 0.0


class FilterStats(BaseModel):
    """Statistics for filter usage and performance"""

    user_id: str
    total_rules: int = 0
    active_rules: int = 0
    total_messages_evaluated: int = 0
    messages_allowed: int = 0
    messages_blocked: int = 0
    most_matched_rule: str | None = None
    avg_processing_time_ms: float = 0.0

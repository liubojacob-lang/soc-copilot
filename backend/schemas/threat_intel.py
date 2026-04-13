"""Schemas for threat intelligence."""

import ipaddress
import re
from enum import Enum

from pydantic import BaseModel, Field, field_validator

_DOMAIN_RE = re.compile(
    r"^[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9-]*[a-zA-Z0-9])?)*$"
)
_HASH_RE = re.compile(r"^[a-fA-F0-9]+$")


class IOCType(str, Enum):
    """IOC types supported for threat intel lookup."""

    ip = "ip"
    domain = "domain"
    url = "url"
    hash = "hash"


class Verdict(str, Enum):
    """Threat verdict levels."""

    benign = "benign"
    unknown = "unknown"
    suspicious = "suspicious"
    malicious = "malicious"


class ThreatIntelItem(BaseModel):
    """Single threat intelligence item.

    v0.4.1: Added skipped_reason field for compliance filtering.
    """

    ioc_type: str = Field(..., description="IOC type")
    ioc_value: str = Field(..., description="IOC value")
    verdict: Verdict = Field(..., description="Threat verdict")
    score: int = Field(ge=0, le=100, description="Threat score (0-100)")
    pulse_count: int = Field(default=0, description="Number of reports/pulses")
    tags: list[str] = Field(default_factory=list, description="Threat tags")
    references: list[str] = Field(default_factory=list, description="Reference URLs")
    cached: bool = Field(default=False, description="Whether from cache")
    skipped: bool = Field(default=False, description="Whether skipped due to limit/filter")
    skipped_reason: str | None = Field(
        None,
        description="Reason for skipping (e.g., 'private_ip', 'internal_domain', 'blocked_tld', 'rate_limit')",
    )


class ThreatIntelResponse(BaseModel):
    """Threat intelligence lookup response.

    v0.4.1: Added skipped_reason field.
    """

    request_id: str = Field(..., description="Request ID for tracing")
    provider: str = Field(default="otx", description="TI provider name")
    disabled: bool = Field(default=False, description="Whether external TI is disabled")
    cached: bool = Field(default=False, description="Whether result is from cache")
    degraded: bool = Field(default=False, description="Whether lookup was degraded")
    ioc_type: str = Field(..., description="IOC type")
    ioc_value: str = Field(..., description="IOC value")
    verdict: Verdict = Field(..., description="Threat verdict")
    score: int = Field(ge=0, le=100, description="Threat score (0-100)")
    pulse_count: int = Field(default=0, description="Number of reports/pulses")
    tags: list[str] = Field(default_factory=list, description="Threat tags")
    references: list[str] = Field(default_factory=list, description="Reference URLs")
    raw: dict = Field(default_factory=dict, description="Raw response from provider")
    error_reason: str | None = Field(None, description="Error message if lookup failed")
    skipped_reason: str | None = Field(
        None, description="Reason for skipping (e.g., 'private_ip', 'internal_domain')"
    )


class BulkThreatIntelRequestItem(BaseModel):
    """Single item in bulk threat intel lookup request."""

    ioc_type: str = Field(..., description="IOC type (ip/domain/url/hash)")
    ioc_value: str = Field(..., description="IOC value")

    @field_validator("ioc_type")
    @classmethod
    def validate_ioc_type(cls, v: str) -> str:
        valid = {e.value for e in IOCType}
        if v not in valid:
            raise ValueError(f"Invalid IOC type '{v}'. Must be one of: {', '.join(sorted(valid))}")
        return v

    @field_validator("ioc_value")
    @classmethod
    def validate_ioc_value(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("IOC value must not be empty")
        return v.strip()


class BulkThreatIntelRequest(BaseModel):
    """Bulk threat intel lookup request."""

    items: list[BulkThreatIntelRequestItem] = Field(
        ...,
        description="List of IOCs to lookup",
        min_length=1,
        max_length=50,
    )


class BulkThreatIntelResponse(BaseModel):
    """Bulk threat intel lookup response.

    v0.4.1: Added filtered_count and filtered_items fields.
    """

    request_id: str = Field(..., description="Request ID for tracing")
    provider: str = Field(default="otx", description="TI provider name")
    disabled: bool = Field(default=False, description="Whether external TI is disabled")
    results: list[ThreatIntelResponse] = Field(
        default_factory=list, description="List of lookup results"
    )
    skipped_count: int = Field(default=0, description="Number of IOCs skipped due to rate limiting")
    skipped_items: list[ThreatIntelItem] = Field(
        default_factory=list, description="List of IOCs skipped due to rate limiting"
    )
    # v0.4.1: New fields for compliance filtering
    filtered_count: int = Field(
        default=0, description="Number of IOCs filtered by compliance policy"
    )
    filtered_items: list[ThreatIntelItem] = Field(
        default_factory=list,
        description="List of IOCs filtered by compliance policy (not sent to external TI)",
    )


class ThreatIntelAnalysis(BaseModel):
    """Threat intelligence analysis for alert/timeline output.

    v0.4.1: Added filtered_items field for compliance-filtered IOCs.
    """

    provider: str = Field(default="otx", description="TI provider name")
    disabled: bool = Field(default=False, description="Whether external TI is disabled")
    degraded: bool = Field(default=False, description="Whether lookup was degraded")
    skipped: bool = Field(
        default=False, description="Whether some IOCs were skipped due to rate limiting"
    )
    items: list[ThreatIntelItem] = Field(
        default_factory=list, description="Threat intel results for IOCs"
    )
    # v0.4.1: New field for compliance-filtered IOCs
    filtered_items: list[ThreatIntelItem] = Field(
        default_factory=list,
        description="IOCs filtered by compliance policy (not sent to external TI)",
    )
    error_reason: str | None = Field(None, description="Error message if lookup failed")

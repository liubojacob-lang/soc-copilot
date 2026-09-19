"""Root cause analysis schemas (T2.4 minimal closed loop)."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# ---------------------------------------------------------------------------
# LLM output contract
# ---------------------------------------------------------------------------


class RootCauseLLMResult(BaseModel):
    """Schema the LLM must return for a root cause analysis.

    Deliberately loose (dicts passthrough) so prompt-format drift does not
    break parsing; the CoT structure lives in ``reasoning_steps`` and
    ``evidence_chain`` as free dictionaries.
    """

    model_config = ConfigDict(protected_namespaces=(), extra="ignore")

    root_cause_category: str = Field(
        description="misconfiguration | attack | failure | human_error | false_positive | unknown"
    )
    root_cause_subcategory: str | None = None
    confidence: float = Field(ge=0.0, le=1.0, default=0.5)
    reasoning_steps: list[dict] = Field(default_factory=list)
    evidence_chain: list[dict] = Field(default_factory=list)
    verification_steps: list[str] = Field(default_factory=list)
    suggested_remediation: str | None = None
    remediation_priority: str = "medium"


# ---------------------------------------------------------------------------
# API payloads
# ---------------------------------------------------------------------------


class RootCauseAnalysisResponse(BaseModel):
    """A persisted root cause analysis record."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    alert_id: str
    root_cause_category: str
    root_cause_subcategory: str | None
    confidence: float
    reasoning_steps: list[dict]
    evidence_chain: list[dict]
    verification_steps: list[str]
    suggested_remediation: str | None
    remediation_priority: str
    ai_model: str
    analysis_duration_ms: float | None
    human_verified: bool
    human_feedback: str | None
    feedback_category: str | None
    created_at: str


class RootCauseAnalysisListResponse(BaseModel):
    items: list[RootCauseAnalysisResponse]
    total: int


class RootCauseFeedbackRequest(BaseModel):
    verdict: Literal["accurate", "partially_accurate", "inaccurate"]
    comment: str | None = Field(None, max_length=2000)

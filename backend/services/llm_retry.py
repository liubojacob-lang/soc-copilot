"""LLM retry service with schema validation and degraded mode."""

import asyncio
import json
import uuid
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from core.config import settings
from core.logger import get_logger
from services.ai_service_enhanced import EnhancedAIService

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


class AlertLLMExtraction(BaseModel):
    """Concise schema for LLM structured extraction during alert analysis."""

    model_config = ConfigDict(protected_namespaces=())

    event_type: str = Field(
        default="unknown",
        description="Security event type: scan, bruteforce, malware, c2, phishing, abnormal_login, lateral_movement, data_exfil, unknown",
    )
    severity: str = Field(
        default="medium", description="Severity level: high, medium, low"
    )
    attack_pattern: str | None = Field(
        default=None,
        description="Identified attack pattern or technique (e.g. DNS Tunneling, T1059)",
    )
    summary: str = Field(..., description="Comprehensive security incident summary")
    confidence: int | float = Field(
        default=85, description="Confidence score between 0 and 100"
    )
    evidence_points: list[str] = Field(
        default_factory=list, description="Key evidence points supporting analysis"
    )
    recommended_actions: list[Any] = Field(
        default_factory=list,
        description="Recommended remediation and containment actions",
    )
    users: list[str] = Field(default_factory=list, description="Involved user accounts")
    hosts: list[str] = Field(default_factory=list, description="Involved hosts/devices")
    processes: list[str] = Field(default_factory=list, description="Involved processes")
    escalation_needed: bool = Field(
        default=False, description="Whether human escalation is required"
    )


class LLMRetryService:
    """LLM service with automatic retry and degraded mode fallback."""

    MAX_RETRIES = 2

    def __init__(self) -> None:
        """Initialize LLM retry service."""
        self.ai_service = EnhancedAIService()

    def _generate_request_id(self) -> str:
        """Generate unique request ID."""
        return str(uuid.uuid4())[:8]

    def _create_correction_prompt(
        self, error_message: str, attempted_output: str
    ) -> str:
        """Generate correction prompt for retry."""
        return f"""

The previous output failed validation with this error:
{error_message}

Please correct your response. Ensure:
1. All required fields are present
2. All values match the expected types
3. Enums use only valid values
4. Arrays and objects are properly formatted
5. Return ONLY valid JSON, no markdown code blocks

Previous attempt was:
{attempted_output[:500]}

Please provide the corrected JSON response:"""

    # NOTE: _build_heuristic_alert_response() was removed (T1.1).
    # It generated fabricated forensic evidence (DNS rate "8-12/s", entropy 4.2,
    # hardcoded domain "0xcd10e1.tech", confidence 88-92) that was
    # indistinguishable from real AI analysis output, creating a patient-safety
    # class risk for SOC analysts acting on false data.
    # Degraded mode now uses the minimal response defined in _create_degraded_response().

    def _create_degraded_response(
        self, response_class: type[T], error_reason: str, prompt: str = ""
    ) -> dict[str, Any]:
        """Create minimal degraded response.

        Args:
            response_class: Expected response class
            error_reason: Reason for degradation
            prompt: Optional prompt text for heuristic analysis

        Returns:
            Minimal valid response dictionary
        """
        base_response = {
            "request_id": self._generate_request_id(),
            "degraded": True,
            "error_reason": error_reason,
        }

        # Module-specific degraded responses
        class_name = response_class.__name__

        if "Alert" in class_name or "Analyzer" in class_name:
            # T1.1: Always use minimal degraded response. No fabricated evidence.
            # The prompt parameter is intentionally ignored here to prevent
            # heuristic hallucination of forensic data.
            base_response.update(
                {
                    "event_type": "unknown",
                    # Schema-valid placeholders: Severity/confidence are required
                    # fields, so degraded mode reports "medium"/0 rather than
                    # crashing validation. The degraded flag + summary carry the
                    # "unassessed" semantics.
                    "severity": "medium",
                    "confidence": 0,
                    "attack_pattern": None,
                    "iocs": {"ips": [], "domains": [], "urls": [], "hashes": []},
                    "iocs_local": {"ips": [], "domains": [], "urls": [], "hashes": []},
                    "iocs_llm": {"ips": [], "domains": [], "urls": [], "hashes": []},
                    "ioc_count": {
                        "ips": 0,
                        "domains": 0,
                        "urls": 0,
                        "hashes": 0,
                        "total": 0,
                    },
                    "entities": {"users": [], "hosts": [], "processes": []},
                    "summary": "[AI 分析不可用] AI 服务暂时不可用，无法完成本次研判。请人工审查原始告警日志并进行人工处置。",
                    "evidence_points": [],
                    "recommended_actions": [
                        {
                            "action": "人工审查告警",
                            "priority": "medium",
                            "details": "AI 分析服务当前不可用，请人工核对原始日志并进行处置。",
                            "description": "AI 分析服务当前不可用，请人工核对原始日志并进行处置。",
                            "verification": "完成人工研判后更新告警状态。",
                        }
                    ],
                    "escalation_needed": False,
                    "impact_analysis": {
                        "affected_assets": [],
                        "business_impact": "Unavailable — AI analysis degraded",
                        "risk_score": 0,
                        "severity": "low",
                        "containment_priority": [],
                        "recommended_next_queries": [],
                    },
                    "threat_intel": {
                        "provider": "otx",
                        "disabled": False,
                        "degraded": True,
                        "skipped": True,
                        "items": [],
                        "error_reason": "AI provider unavailable",
                    },
                }
            )

        elif "Timeline" in class_name:
            base_response.update(
                {
                    "timeline": [],
                    "suspicious_top5": [],
                    "next_steps": [
                        "Manual timeline reconstruction required",
                        "Consider alternative analysis methods",
                        "Review raw logs directly",
                    ],
                    "iocs": {"ips": [], "domains": [], "urls": [], "hashes": []},
                    "iocs_local": {"ips": [], "domains": [], "urls": [], "hashes": []},
                    "iocs_llm": {"ips": [], "domains": [], "urls": [], "hashes": []},
                    "ioc_count": {
                        "ips": 0,
                        "domains": 0,
                        "urls": 0,
                        "hashes": 0,
                        "total": 0,
                    },
                    "impact_analysis": {
                        "affected_assets": [],
                        "business_impact": "Unable to perform impact analysis in degraded mode",
                        "risk_score": 0,
                        "severity": "low",
                        "containment_priority": [],
                        "recommended_next_queries": [],
                    },
                    "threat_intel": {
                        "provider": "otx",
                        "disabled": False,
                        "degraded": True,
                        "skipped": False,
                        "items": [],
                        "error_reason": "Unable to perform threat intel lookup in degraded mode",
                    },
                }
            )

        elif "Report" in class_name:
            base_response.update(
                {
                    "ticket_template": "# Incident Report\n\n"
                    "**Status**: Automated generation failed\n\n"
                    "Manual report creation required.",
                    "daily_report_template": "# Daily Security Report\n\n"
                    "Automated generation failed.",
                    "postmortem_template": "# Postmortem Report\n\n"
                    "Automated generation failed.",
                }
            )

        return base_response

    def _validate_safely(
        self, response_class: type[T], data: dict[str, Any]
    ) -> tuple[T | None, str | None]:
        """Safely validate response, returning None with error if failed.

        Args:
            response_class: Pydantic model class
            data: Dictionary to validate

        Returns:
            Tuple of (validated_instance or None, error_message or None)
        """
        try:
            return response_class.model_validate(data), None
        except ValidationError as e:
            error_details = e.errors()
            formatted_errors = []
            for error in error_details:
                loc = " -> ".join(str(x) for x in error["loc"])
                formatted_errors.append(f"{loc}: {error['msg']}")
            return None, "; ".join(formatted_errors)
        except Exception as e:
            return None, str(e)

    def _assemble_alert_response(
        self,
        extracted: AlertLLMExtraction,
        response_class: type[T],
        extracted_iocs: dict[str, list[str]] | None = None,
    ) -> Any:
        """Assemble a full AlertAnalysisResponse from concise LLM extraction."""
        from schemas.alert import EventType, RecommendedAction, Severity

        raw_event_type = (extracted.event_type or "unknown").lower()
        try:
            event_type = EventType(raw_event_type)
        except ValueError:
            matched = False
            for et in EventType:
                if et.value in raw_event_type:
                    event_type = et
                    matched = True
                    break
            if not matched:
                event_type = EventType.unknown

        raw_sev = (extracted.severity or "medium").lower()
        try:
            severity = Severity(raw_sev)
        except ValueError:
            severity = (
                Severity.high
                if "high" in raw_sev
                else Severity.low if "low" in raw_sev else Severity.medium
            )

        conf = (
            int(extracted.confidence * 100)
            if 0 <= extracted.confidence <= 1.0
            else int(extracted.confidence)
        )
        conf = max(0, min(100, conf))

        actions = []
        for a in extracted.recommended_actions:
            if isinstance(a, dict):
                act_name = a.get("action") or a.get("title") or "安全排查措施"
                prio = (a.get("priority") or "medium").lower()
                details = a.get("details") or a.get("description") or act_name
                verif = a.get("verification") or "核查处置状态及告警消除情况"
                auto = bool(a.get("automated", False))
                actions.append(
                    RecommendedAction(
                        action=act_name,
                        priority=prio,
                        details=details,
                        description=details,
                        verification=verif,
                        automated=auto,
                    )
                )
            elif isinstance(a, str):
                actions.append(
                    RecommendedAction(
                        action=a,
                        priority="medium",
                        details=a,
                        description=a,
                        verification="核查处置状态",
                        automated=False,
                    )
                )

        if not actions:
            actions = [
                RecommendedAction(
                    action="排查受影响主机行为与网络连接",
                    priority="high",
                    details="检查涉事资产网络流量并确认是否存在恶意连接。",
                    description="检查涉事资产网络流量并确认是否存在恶意连接。",
                    verification="核实涉事资产网络行为恢复正常。",
                    automated=False,
                )
            ]

        local_iocs_dict = extracted_iocs or {
            "ips": [],
            "domains": [],
            "urls": [],
            "hashes": [],
        }
        ips = local_iocs_dict.get("ips", [])
        domains = local_iocs_dict.get("domains", [])
        urls = local_iocs_dict.get("urls", [])
        hashes = local_iocs_dict.get("hashes", [])

        assembled_data = {
            "event_type": event_type,
            "severity": severity,
            "attack_pattern": extracted.attack_pattern or "安全异常行为",
            "confidence": conf,
            "summary": extracted.summary,
            "evidence_points": extracted.evidence_points or ["事件已命中规则检测"],
            "recommended_actions": [a.model_dump() for a in actions],
            "entities": {
                "users": extracted.users,
                "hosts": extracted.hosts,
                "processes": extracted.processes,
            },
            "escalation_needed": extracted.escalation_needed,
            "iocs": local_iocs_dict,
            "iocs_local": local_iocs_dict,
            "iocs_llm": {"ips": [], "domains": [], "urls": [], "hashes": []},
            "ioc_count": {
                "ips": len(ips),
                "domains": len(domains),
                "urls": len(urls),
                "hashes": len(hashes),
                "total": len(ips) + len(domains) + len(urls) + len(hashes),
            },
            "impact_analysis": {
                "affected_assets": [],
                "business_impact": f"已完成深度大模型研判（{extracted.summary[:40]}...）",
                "risk_score": conf,
                "severity": severity,
                "containment_priority": [],
                "recommended_next_queries": (
                    [f'domain == "{domains[0]}"'] if domains else []
                ),
            },
            "threat_intel": {
                "provider": "otx",
                "disabled": False,
                "degraded": False,
                "skipped": False,
                "items": [],
                "error_reason": None,
            },
        }
        return response_class.model_validate(assembled_data)

    async def generate_structured(
        self,
        prompt: str,
        response_class: type[T] | None = None,
        extracted_iocs: dict[str, list[str]] | None = None,
    ) -> tuple[T | str, str, bool]:
        """Generate structured response with retry and degraded fallback.

        Args:
            prompt: The prompt to send to LLM
            response_class: Pydantic model for response validation. When
                ``None``, free-form text generation is used (no schema
                coercion) — suitable for task types like CHAT_COMPLETION
                that do not map to a fixed schema.
            extracted_iocs: Pre-extracted IOCs to include

        Returns:
            Tuple of (validated_response, model_used, was_degraded). When
            ``response_class`` is None, the first element is the raw model
            text.
        """
        request_id = self._generate_request_id()

        # ---- Free-form path: no schema, no validation, no degraded payload ----
        if response_class is None:
            return await self._generate_freeform(prompt, request_id)

        last_error = ""
        last_attempt = ""

        for attempt in range(self.MAX_RETRIES + 1):
            try:
                if attempt > 0:
                    logger.warning(
                        f"Retry attempt {attempt}/{self.MAX_RETRIES} "
                        f"for request {request_id}"
                    )
                    # Add correction prompt
                    correction = self._create_correction_prompt(
                        last_error, last_attempt
                    )
                    prompt = prompt + "\n" + correction

                is_alert_response = (
                    getattr(response_class, "__name__", "") == "AlertAnalysisResponse"
                )
                target_model = (
                    AlertLLMExtraction if is_alert_response else response_class
                )

                # Generate response
                raw_output = await self.ai_service.generate_structured(
                    prompt=prompt,
                    response_model=target_model,
                )
                model_used = self.ai_service.get_model_name()

                if is_alert_response and isinstance(raw_output, AlertLLMExtraction):
                    raw_output = self._assemble_alert_response(
                        raw_output, response_class, extracted_iocs
                    )

                # Validate response
                validated, error = self._validate_safely(response_class, raw_output)

                if validated is not None:
                    # Add metadata
                    validated_dict = validated.model_dump()
                    validated_dict["request_id"] = request_id
                    validated_dict["model_used"] = model_used
                    validated_dict["degraded"] = False

                    # Recreate with metadata
                    final_response = response_class.model_validate(validated_dict)

                    logger.info(
                        f"Successfully generated response for request {request_id}, "
                        f"model: {model_used}"
                    )
                    return final_response, model_used, False

                # Validation failed
                last_error = error or "Unknown validation error"
                last_attempt = json.dumps(raw_output, default=str)[:500]

                if attempt < self.MAX_RETRIES:
                    logger.warning(
                        f"Validation failed for request {request_id}: {last_error}"
                    )
                    continue

            except Exception as e:
                last_error = str(e)
                logger.error(f"Error generating response: {last_error}")

                if attempt < self.MAX_RETRIES:
                    continue

        # All retries failed - create degraded response
        logger.warning(
            f"All retries failed for request {request_id}, using degraded mode"
        )

        degraded_data = self._create_degraded_response(
            response_class, last_error, prompt=prompt
        )
        degraded_data["request_id"] = request_id
        degraded_data["model_used"] = (
            f"{settings.ai_provider} (启发式安全引擎)"
            if not self.ai_service._initialized
            else settings.ai_provider
        )

        # Try to validate degraded response
        try:
            degraded_response = response_class.model_validate(degraded_data)
            return degraded_response, settings.ai_provider, True
        except ValidationError as e:
            # The degraded payload must always satisfy the response schema; a
            # miss here is a programming error in _create_degraded_response,
            # not a runtime condition to paper over.
            logger.error(
                f"Degraded payload failed schema validation for "
                f"{response_class.__name__}: {e!s}"
            )
            raise ValueError(
                f"Degraded response does not satisfy {response_class.__name__}"
            ) from e

    async def _generate_freeform(
        self, prompt: str, request_id: str
    ) -> tuple[str, str, bool]:
        """Free-form generation: retry on error, no schema validation.

        Used when ``response_class`` is None. Returns the raw model text plus
        metadata; ``was_degraded`` is True only if every retry failed.
        """
        last_error = ""
        for attempt in range(self.MAX_RETRIES + 1):
            try:
                content = await self.ai_service.generate(prompt)
                model_used = self.ai_service.get_model_name()
                logger.info(
                    f"Generated free-form response for request {request_id}, "
                    f"model: {model_used}"
                )
                return content, model_used, False
            except Exception as e:
                last_error = str(e)
                logger.error(
                    f"Free-form generation error (attempt {attempt}): {last_error}"
                )
                if attempt < self.MAX_RETRIES:
                    await self._backoff(attempt)
                    continue

        # All retries failed — return an empty string rather than raising so
        # callers (task queue) can still persist a terminal record.
        logger.warning(f"Free-form generation exhausted for {request_id}: {last_error}")
        return "", self.ai_service.get_model_name(), True

    async def _backoff(self, attempt: int) -> None:
        """Exponential backoff between free-form retries."""
        await asyncio.sleep(0.5 * (attempt + 1))


# Singleton instance
_llm_retry_service: LLMRetryService | None = None


def get_llm_retry_service() -> LLMRetryService:
    """Get or create LLM retry service singleton."""
    global _llm_retry_service
    if _llm_retry_service is None:
        _llm_retry_service = LLMRetryService()
    return _llm_retry_service

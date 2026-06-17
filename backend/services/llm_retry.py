"""LLM retry service with schema validation and degraded mode."""

import asyncio
import json
import uuid
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from core.config import settings
from core.logger import get_logger
from services.ai_service_enhanced import EnhancedAIService

logger = get_logger(__name__)
T = TypeVar("T", bound=BaseModel)


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

    def _create_degraded_response(
        self, response_class: type[T], error_reason: str
    ) -> dict[str, Any]:
        """Create minimal degraded response.

        Args:
            response_class: Expected response class
            error_reason: Reason for degradation

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
            base_response.update(
                {
                    "event_type": "unknown",
                    "severity": "low",
                    "confidence": 0,
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
                    "summary": "Unable to analyze due to LLM output validation failure. "
                    "Please try again or provide clearer input.",
                    "evidence_points": [
                        "LLM output validation failed",
                        "Local IOC extraction may still be available",
                    ],
                    "recommended_actions": [
                        {
                            "action": "Manual review required",
                            "priority": "high",
                            "details": "Automated analysis failed. Manual investigation required.",
                            "verification": "Review logs manually and correlate with other events.",
                        }
                    ],
                    "escalation_needed": False,
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

                # Generate response
                raw_output = await self.ai_service.generate_structured(
                    prompt=prompt,
                    response_model=response_class,
                )
                model_used = self.ai_service.get_model_name()

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

        degraded_data = self._create_degraded_response(response_class, last_error)
        degraded_data["request_id"] = request_id
        degraded_data["model_used"] = settings.ai_provider

        # Try to validate degraded response
        try:
            degraded_response = response_class.model_validate(degraded_data)
            return degraded_response, settings.ai_provider, True
        except ValidationError:
            # If even degraded fails, return minimal response
            return (
                response_class.model_validate(
                    {
                        **degraded_data,
                        "degraded": True,
                    }
                ),
                settings.ai_provider,
                True,
            )

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
        logger.warning(
            f"Free-form generation exhausted for {request_id}: {last_error}"
        )
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

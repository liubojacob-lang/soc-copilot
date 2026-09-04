"""
Enhanced AI Service for SOC Copilot - Phase 2
Adds RAG (Retrieval Augmented Generation) and advanced AI capabilities
"""

import asyncio
import json
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from core.config import settings
from core.logger import get_logger
from core.prompt_sanitizer import (
    sanitize_alert_data,
    sanitize_json_for_prompt,
    sanitize_prompt_input,
)
from services.ai_providers import LLMFactory, LLMProvider
from services.ai_utils import clean_json_content
from utils.circuit_breaker import CircuitBreaker, CircuitBreakerOpenException

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


class AIAnalysisResult(BaseModel):
    """Result of AI analysis."""

    summary: str
    root_cause: str
    recommendations: list[str]
    confidence: float
    severity_assessment: str | None = None
    attack_techniques: list[str] | None = None


class NaturalLanguageQueryResult(BaseModel):
    """Natural language query result."""

    intent: str
    parameters: dict[str, Any]
    filter_criteria: dict[str, Any]
    response: str
    sql_query: str | None = None


class PlaybookRecommendation(BaseModel):
    """Playbook recommendation."""

    playbook_id: str
    playbook_name: str
    confidence: float
    reason: str
    estimated_time: str | None = None


class EnhancedAIService:
    """Enhanced AI service with RAG capabilities."""

    def __init__(self):
        self.max_retries = getattr(settings, "max_retries", 3)
        self.provider = getattr(settings, "ai_provider", "zhipu").lower()
        self.llm: LLMProvider | None = None
        self._initialized = False
        self.circuit_breaker = CircuitBreaker(
            name="llm_provider",
            failure_threshold=5,
            recovery_timeout=30.0,
        )

        # Initialize LLM provider
        self._init_llm()

    def _init_llm(self):
        """Initialize LLM provider."""
        try:
            self.llm = LLMFactory.create_from_config()
            if self.llm:
                self._initialized = True
                logger.info(f"Enhanced AI service initialized with {self.provider}")
            else:
                logger.warning("No LLM provider available")
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")

    def get_model_name(self) -> str:
        """Return the model identifier currently in use.

        Falls back to the configured provider name when no concrete provider
        is initialized (e.g. degraded mode / missing API key). This keeps
        downstream consumers (LLMRetryService, audit metadata) working even
        when the LLM itself is unavailable.
        """
        if self.llm is not None and getattr(self.llm, "model", None):
            return self.llm.model
        return getattr(settings, "ai_provider", "unknown")

    async def generate(
        self,
        prompt: str,
        system_prompt: str = "You are a cybersecurity expert assistant.",
        temperature: float = 0.7,
    ) -> str:
        """Generate a plain-text completion for the given prompt.

        Unlike ``generate_structured`` (which enforces a JSON schema), this is
        the escape hatch for task types that produce free-form text
        (e.g. CHAT_COMPLETION, REPORT_GENERATION). Returns the raw model
        output as a string.
        """
        if not self.llm:
            raise ValueError("AI service not initialized")

        content = await self.circuit_breaker.call(
            self.llm.chat_completion,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt},
            ],
            temperature=temperature,
        )
        return content

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[T],
        system_prompt: str = "You are a cybersecurity expert assistant.",
    ) -> T:
        """Generate structured response using AI."""
        if not self.llm:
            raise ValueError("AI service not initialized")

        schema = response_model.model_json_schema()

        full_prompt = f"""You must respond with valid JSON only. No markdown, no explanations.

JSON Schema:
{json.dumps(schema, indent=2, ensure_ascii=False)}

User Input:
{prompt}

Respond with JSON that matches the schema above:"""

        content = None
        for attempt in range(self.max_retries + 1):
            try:
                content = await self.circuit_breaker.call(
                    self.llm.chat_completion,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": full_prompt},
                    ],
                    temperature=0.1,
                )

                # Clean and parse the content
                content = clean_json_content(content)
                data = json.loads(content)

                # Type coercion for integer fields
                if "properties" in schema:
                    for field_name, field_def in schema["properties"].items():
                        if field_name in data and isinstance(field_def, dict):
                            field_type = field_def.get("type")
                            # Handle anyOf (optional fields) - get the first non-null type
                            if field_type is None and "anyOf" in field_def:
                                for anyof_item in field_def["anyOf"]:
                                    if anyof_item.get("type") != "null":
                                        field_type = anyof_item.get("type")
                                        break

                            if field_type == "integer" and isinstance(
                                data[field_name], float
                            ):
                                data[field_name] = int(data[field_name])
                            elif field_type == "array" and not isinstance(
                                data[field_name], list
                            ):
                                data[field_name] = []

                return response_model(**data)

            except (ValidationError, json.JSONDecodeError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {e!s}")
                if attempt == self.max_retries:
                    error_msg = f"Failed to parse content: {content[:500] if content else 'empty'}..."
                    logger.error(error_msg)
                    raise ValueError(
                        f"Failed to get valid JSON after {self.max_retries + 1} attempts"
                    )
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"AI service error: {e!s}")
                raise

        raise RuntimeError("Unexpected end of generate_structured")

    async def analyze_alert_with_rag(
        self, alert_data: dict[str, Any], use_rag: bool = True
    ) -> AIAnalysisResult:
        """
        Analyze alert using AI with optional RAG enhancement.

        Args:
            alert_data: Alert information
            use_rag: Whether to use RAG for context enhancement

        Returns:
            AI analysis result
        """
        if not self.llm:
            raise ValueError("AI service not available")

        try:
            # Sanitize alert data to prevent prompt injection
            safe_alert = sanitize_alert_data(alert_data)

            # Build base prompt
            alert_summary = f"""
Alert: {safe_alert.get("title", "N/A")}
Description: {safe_alert.get("description", "N/A")}
Severity: {safe_alert.get("severity", "unknown")}
Source: {safe_alert.get("source", "N/A")}
Type: {safe_alert.get("alert_type", "N/A")}
"""

            # RAG context: vector search is not yet wired (see roadmap);
            # keep the placeholder so the prompt template stays intact.
            rag_context = ""

            system_prompt = """You are an expert SOC analyst. Analyze this security alert and provide:
1. Concise summary
2. Root cause analysis
3. Specific, actionable recommendations
4. Confidence level (0.0-1.0)
5. Severity assessment (if different from provided)
6. MITRE ATT&CK techniques (if applicable)"""

            user_prompt = f"""{alert_summary}

{rag_context}

Respond in JSON format with these fields:
- summary (string)
- root_cause (string)
- recommendations (array of strings)
- confidence (float)
- severity_assessment (string, optional)
- attack_techniques (array of strings, optional)"""

            return await self.generate_structured(
                prompt=user_prompt,
                response_model=AIAnalysisResult,
                system_prompt=system_prompt,
            )

        except Exception as e:
            logger.warning(
                f"LLM analysis unavailable or circuit open ({e}), activating rule-based fallback"
            )
            return self._rule_based_fallback_analysis(alert_data, reason=str(e))

    def _rule_based_fallback_analysis(
        self, alert_data: dict[str, Any], reason: str = ""
    ) -> AIAnalysisResult:
        """Rule-based heuristic fallback analysis when LLM service is unavailable or circuit is open."""
        title = alert_data.get("title", "Security Alert")
        description = alert_data.get("description", "")
        severity = alert_data.get("severity", "medium").lower()
        src_ip = alert_data.get("source_ip") or "unknown"
        alert_type = alert_data.get("alert_type") or "unknown"

        recommendations = [
            f"Inspect network traffic and connections associated with source {src_ip}.",
            "Check endpoint detection and response (EDR) telemetry for process anomalies.",
            "Re-trigger AI deep analysis once LLM upstream service recovers.",
        ]
        techniques = []
        low_context = f"{title} {description}".lower()
        if "scan" in low_context or "recon" in low_context:
            techniques.append("T1046 - Network Service Discovery")
        if "brute" in low_context or "login" in low_context or "auth" in low_context:
            techniques.append("T1110 - Brute Force")
        if "malware" in low_context or "trojan" in low_context or "virus" in low_context:
            techniques.append("T1204 - User Execution")
        if "privilege" in low_context or "escalat" in low_context:
            techniques.append("T1068 - Exploitation for Privilege Escalation")

        return AIAnalysisResult(
            summary=f"[Degraded Mode] Analyzed '{title}' using heuristic rules. External AI engine is currently degraded.",
            root_cause=f"Heuristic signature evaluation for {alert_type}: {reason or 'LLM service fast-fail/circuit open'}.",
            recommendations=recommendations,
            confidence=0.6,
            severity_assessment=severity,
            attack_techniques=techniques,
        )

    async def natural_language_query(
        self, query: str, user_context: dict[str, Any] | None = None
    ) -> NaturalLanguageQueryResult:
        """
        Process natural language query and convert to structured intent.

        Examples:
        - "Show me high severity alerts from yesterday"
        - "What's the status of playbook run XYZ?"
        - "Analyze IP 192.168.1.100"
        """
        if not self.llm:
            raise ValueError("AI service not available")

        try:
            system_prompt = """You are SOC Copilot's query parser. Convert natural language to structured intent.

Supported intents:
- list_alerts: List/filter alerts
- get_alert: Get specific alert
- list_playbooks: List playbooks
- get_playbook: Get playbook details
- run_playbook: Execute a playbook
- list_playbook_runs: List playbook execution history
- get_playbook_run: Get playbook run status
- analyze_entity: Analyze IP, domain, hash, etc.
- create_playbook: Create a new playbook
- get_statistics: Get SOC metrics
- help: General help

Parse the query and extract:
1. Intent
2. Parameters (time ranges, filters, entities)
3. Filter criteria for database queries
4. Natural language acknowledgment"""

            user_prompt = f"Query: {sanitize_prompt_input(query)}"
            if user_context:
                user_prompt += f"\nUser: {user_context.get('username', 'unknown')}"
                user_prompt += f"\nRole: {user_context.get('role', 'unknown')}"

            result = await self.generate_structured(
                prompt=user_prompt,
                response_model=NaturalLanguageQueryResult,
                system_prompt=system_prompt,
            )

            logger.info(f"Natural language query result: intent={result.intent}")
            return result

        except Exception as e:
            logger.error(f"Error processing natural language query: {e}")
            return NaturalLanguageQueryResult(
                intent="unknown",
                parameters={},
                filter_criteria={},
                response=f"I'm sorry, I couldn't understand your query: {e!s}",
            )

    async def recommend_playbooks(
        self, alert_data: dict[str, Any], available_playbooks: list[dict[str, Any]]
    ) -> list[PlaybookRecommendation]:
        """
        Recommend playbooks based on alert characteristics.

        Args:
            alert_data: Alert information
            available_playbooks: List of available playbooks

        Returns:
            Ranked list of recommendations
        """
        if not self.llm or not available_playbooks:
            return []

        try:
            system_prompt = """You are a playbook recommendation engine. Given an alert and available playbooks,
recommend the most suitable ones. Consider alert type, severity, and playbook capabilities.

Respond with an array of recommendations, each with:
- playbook_id (string)
- playbook_name (string)
- confidence (float, 0-1)
- reason (string)
- estimated_time (string, optional, e.g., "5 minutes")"""

            user_prompt = f"""Alert:
{sanitize_json_for_prompt(alert_data)}

Available Playbooks ({len(available_playbooks)}):
{sanitize_json_for_prompt(available_playbooks[:10])}

Provide your recommendations:"""

            response = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,
            )

            # Parse response
            content = clean_json_content(response)
            data = json.loads(content)

            if isinstance(data, list):
                return [PlaybookRecommendation(**item) for item in data]
            elif isinstance(data, dict) and "recommendations" in data:
                return [
                    PlaybookRecommendation(**item) for item in data["recommendations"]
                ]
            else:
                return []

        except Exception as e:
            logger.error(f"Error recommending playbooks: {e}")
            return []

    async def chat(
        self,
        message: str,
        conversation_history: list[dict[str, str]] | None = None,
        model_id: str | None = None,
        model_provider: str | None = None,
    ) -> str:
        """
        Chat with AI assistant (non-streaming response).

        Args:
            message: User message
            conversation_history: Previous messages
            model_id: Specific model ID to use (optional)
            model_provider: Provider type for the model (optional)

        Returns:
            Complete response string
        """
        # Use specified model/provider if provided
        llm = self.llm
        if model_id and model_provider:
            try:
                llm = LLMFactory.create_provider_for_model(model_id, model_provider)
                logger.info(f"Using model {model_id} from provider {model_provider}")
            except Exception as e:
                logger.error(f"Failed to create provider for model {model_id}: {e}")
                if not self.llm:
                    return "I'm sorry, but the AI assistant is currently unavailable."
                llm = self.llm

        if not llm:
            return "I'm sorry, but the AI assistant is currently unavailable."

        try:
            system_prompt = """You are SOC Copilot, an AI assistant for security operations.
Help SOC analysts with alert analysis, investigations, playbook creation, and security questions.
Be concise, professional, and helpful."""

            messages = [{"role": "system", "content": system_prompt}]

            if conversation_history:
                messages.extend(
                    conversation_history[-10:]
                )  # Keep last 10 messages for context

            messages.append({"role": "user", "content": message})

            # Get complete response
            response = await llm.chat_completion(
                messages=messages,
                model=model_id,
                temperature=0.5,
                max_tokens=4096,
            )

            logger.info(f"Chat response length: {len(response)} chars")
            return response

        except Exception as e:
            logger.error(f"Error in chat: {e}")
            return f"I'm sorry, I encountered an error: {e!s}"

    async def generate_investigation_report(
        self, alert_id: str, investigation_data: dict[str, Any]
    ) -> str:
        """
        Generate investigation report in Markdown format.

        Args:
            alert_id: Alert ID
            investigation_data: Investigation findings

        Returns:
            Markdown report
        """
        if not self.llm:
            return "AI service not available for report generation."

        try:
            system_prompt = """You are a senior SOC analyst writing an investigation report.
Generate a professional Markdown report with:
- Executive Summary
- Alert Details
- Investigation Timeline
- Findings
- Recommendations
- Conclusion"""

            user_prompt = f"""Generate an investigation report for:
Alert ID: {sanitize_prompt_input(alert_id)}

Investigation Data:
{sanitize_json_for_prompt(investigation_data)}

Format the report in Markdown."""

            report = await self.llm.chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.4,
                max_tokens=3000,
            )

            return report

        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return f"Error generating report: {e!s}"


# Global service instance
_enhanced_ai_service: EnhancedAIService | None = None


def get_enhanced_ai_service() -> EnhancedAIService:
    """Get or create global enhanced AI service instance."""
    global _enhanced_ai_service
    if _enhanced_ai_service is None:
        _enhanced_ai_service = EnhancedAIService()
    return _enhanced_ai_service


# -------- Extension Interfaces --------


class IncidentAnalysisRequest(BaseModel):
    incident_id: str
    title: str
    summary: str
    indicators: list[str] = []
    raw_events: list[dict] = []


class IncidentAnalysisResult(BaseModel):
    incident_id: str
    risk_score: float
    root_cause: str
    recommendations: list[str] = []
    confidence: float = 0.0


class AIIncidentAnalyzer:
    """Adapter interface for future LLM-backed incident analysis providers."""

    async def analyze_incident(
        self, request: IncidentAnalysisRequest
    ) -> IncidentAnalysisResult:
        raise NotImplementedError


class VectorStoreProvider:
    """Extension point for vector DB integrations (pgvector/milvus/faiss/etc)."""

    async def upsert_documents(self, namespace: str, documents: list[dict]) -> None:
        raise NotImplementedError

    async def similarity_search(
        self, namespace: str, query: str, top_k: int = 5
    ) -> list[dict]:
        raise NotImplementedError

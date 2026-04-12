"""
Enhanced AI Service for SOC Copilot - Phase 2
Adds RAG (Retrieval Augmented Generation) and advanced AI capabilities
"""

import asyncio
import json
import re
from typing import Any, TypeVar

from pydantic import BaseModel, ValidationError

from core.config import settings
from core.logger import get_logger
from services.ai_providers import LLMFactory, LLMProvider
from services.vector_store import get_vector_store

logger = get_logger(__name__)

T = TypeVar("T", bound=BaseModel)


def clean_json_content(content: str) -> str:
    """Clean AI response content for valid JSON parsing."""
    content = content.strip()

    # Find JSON content - might be wrapped in ```json ... ``` or ``` ... ```
    if content.startswith("```"):
        end_marker = content.find("```", 3)
        if end_marker != -1:
            content = content[3:end_marker].strip()
        else:
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1].strip()

        # Remove json language identifier if present
        if content.startswith("json"):
            content = content[4:].strip()

    # Remove control characters that could break JSON parsing
    content = re.sub(r"[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]", "", content)

    return content


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
                content = await self.llm.chat_completion(
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
            # Build base prompt
            alert_summary = f"""
Alert: {alert_data.get("title", "N/A")}
Description: {alert_data.get("description", "N/A")}
Severity: {alert_data.get("severity", "unknown")}
Source: {alert_data.get("source", "N/A")}
Type: {alert_data.get("alert_type", "N/A")}
"""

            # Add RAG context if enabled
            rag_context = ""
            if use_rag:
                try:
                    vector_store = await get_vector_store()
                    # Search for similar historical alerts
                    query_text = f"{alert_data.get('title', '')} {alert_data.get('description', '')}"
                    # Note: In real implementation, you'd generate embedding for the query
                    # For now, we'll skip the vector search and use text-based similarity

                    rag_context = """
Consider similar historical cases and best practices in your analysis.
"""
                except Exception as e:
                    logger.warning(f"RAG search failed: {e}")

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
            logger.error(f"Error analyzing alert: {e}")
            return AIAnalysisResult(
                summary="Analysis failed",
                root_cause=str(e),
                recommendations=["Please review the alert manually"],
                confidence=0.0,
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

            user_prompt = f"Query: {query}"
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
{json.dumps(alert_data, indent=2)}

Available Playbooks ({len(available_playbooks)}):
{json.dumps(available_playbooks[:10], indent=2)}  # Limit to 10 for token efficiency

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
Alert ID: {alert_id}

Investigation Data:
{json.dumps(investigation_data, indent=2, default=str)}

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


# Backwards compatibility
ai_service = get_enhanced_ai_service()

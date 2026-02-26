import json
import asyncio
import re
from typing import Type, TypeVar
from pydantic import BaseModel, ValidationError
from core import get_settings, setup_logger
import httpx

logger = setup_logger(__name__)
settings = get_settings()
T = TypeVar("T", bound=BaseModel)


def clean_json_content(content: str) -> str:
    """Clean AI response content for valid JSON parsing."""
    # Remove markdown code blocks
    content = content.strip()

    # Find JSON content - might be wrapped in ```json ... ``` or ``` ... ```
    if content.startswith("```"):
        # Find the end of the first code block
        end_marker = content.find("```", 3)
        if end_marker != -1:
            content = content[3:end_marker].strip()
        else:
            # Fallback: split and take second part
            parts = content.split("```")
            if len(parts) >= 2:
                content = parts[1].strip()

        # Remove json language identifier if present
        if content.startswith("json"):
            content = content[4:].strip()

    # Remove control characters that could break JSON parsing
    # Keep \n, \r, \t as they might be part of JSON string escapes
    content = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F]', '', content)

    return content


class AIService:
    def __init__(self):
        self.max_retries = settings.max_retries
        self.provider = settings.ai_provider.lower()

        if self.provider == "zhipu":
            self.api_key = settings.zhipu_api_key
            self.base_url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            self.model = "glm-4-plus"  # Changed from glm-4-flash to glm-4-plus
        else:  # anthropic
            from anthropic import AsyncAnthropic
            self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            self.model = "claude-3-5-sonnet-20241022"

    def get_model_name(self) -> str:
        """Get the name of the model being used."""
        return f"{self.provider}:{self.model}"

    async def generate_structured(
        self,
        prompt: str,
        response_model: Type[T],
        system_prompt: str = "You are a cybersecurity expert assistant.",
    ) -> T:
        schema = response_model.model_json_schema()

        full_prompt = f"""You must respond with valid JSON only. No markdown, no explanations.

JSON Schema:
{json.dumps(schema, indent=2, ensure_ascii=False)}

User Input:
{prompt}

Respond with JSON that matches the schema above:"""

        for attempt in range(self.max_retries + 1):
            try:
                if self.provider == "zhipu":
                    content = await self._call_zhipu(system_prompt, full_prompt)
                else:
                    content = await self._call_anthropic(system_prompt, full_prompt)

                # Clean and parse the content
                content = clean_json_content(content)
                data = json.loads(content)

                # Type coercion: ensure integer fields are actually integers
                # This handles cases where LLM returns floats for int fields
                schema = response_model.model_json_schema()
                if "properties" in schema:
                    for field_name, field_def in schema["properties"].items():
                        if field_name in data:
                            if field_def.get("type") == "integer" and isinstance(data[field_name], float):
                                data[field_name] = int(data[field_name])
                            elif field_def.get("type") == "array" and not isinstance(data[field_name], list):
                                data[field_name] = []

                return response_model(**data)

            except (ValidationError, json.JSONDecodeError) as e:
                logger.warning(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt == self.max_retries:
                    # Log the problematic content for debugging
                    logger.error(f"Failed to parse content: {content[:500]}...")
                    raise ValueError(
                        f"Failed to get valid JSON after {self.max_retries + 1} attempts. "
                        f"Last error: {str(e)}"
                    )
                await asyncio.sleep(0.5)
            except Exception as e:
                logger.error(f"AI service error: {str(e)}")
                raise

    async def _call_zhipu(self, system_prompt: str, user_prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.1,
            "max_tokens": 2048,  # Reduced from 4096 for faster response
        }

        async with httpx.AsyncClient(timeout=90.0) as client:  # Increased timeout
            response = await client.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]

    async def _call_anthropic(self, system_prompt: str, user_prompt: str) -> str:
        response = await self.client.messages.create(
            model=self.model,
            max_tokens=2048,  # Reduced from 4096 for faster response
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
            temperature=0.2,
        )
        return response.content[0].text


ai_service = AIService()


# -------- P2 Extension Interfaces (backward-compatible additions) --------
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

    async def analyze_incident(self, request: IncidentAnalysisRequest) -> IncidentAnalysisResult:
        raise NotImplementedError


class VectorStoreProvider:
    """Extension point for vector DB integrations (pgvector/milvus/faiss/etc)."""

    async def upsert_documents(self, namespace: str, documents: list[dict]) -> None:
        raise NotImplementedError

    async def similarity_search(self, namespace: str, query: str, top_k: int = 5) -> list[dict]:
        raise NotImplementedError

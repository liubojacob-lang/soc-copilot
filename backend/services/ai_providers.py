"""
AI Service Module - SOC Copilot AI Assistant
Provides intelligent analysis and recommendations using LLM
"""

import json
import logging
from typing import Any, Dict, List, Optional, AsyncGenerator
from datetime import datetime
from dataclasses import dataclass

import httpx
from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AIAnalysisResult:
    """Result of AI analysis."""

    summary: str
    root_cause: str
    recommendations: List[str]
    confidence: float
    related_cases: List[Dict[str, Any]]
    suggested_playbooks: List[str]


@dataclass
class NaturalLanguageQuery:
    """Natural language query result."""

    query: str
    intent: str
    parameters: Dict[str, Any]
    sql_or_filter: Optional[str]
    response: str


class LLMProvider:
    """Base class for LLM providers."""

    def __init__(self, api_key: str, base_url: Optional[str] = None):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Generate chat completion."""
        raise NotImplementedError

    async def embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
        raise NotImplementedError


class ZhipuAIProvider(LLMProvider):
    """Zhipu AI (智谱AI) provider."""

    def __init__(self, api_key: str):
        super().__init__(api_key, "https://open.bigmodel.cn/api/paas/v4")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "glm-4",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Generate chat completion using Zhipu AI."""
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Zhipu AI API error: {e}")
            raise

    async def embedding(self, text: str) -> List[float]:
        """Generate embedding using Zhipu AI."""
        try:
            response = await self.client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": "embedding-2", "input": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Zhipu AI embedding error: {e}")
            raise


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.anthropic.com")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "claude-3-opus-20240229",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Generate chat completion using Claude."""
        try:
            # Convert messages to Claude format
            system_msg = ""
            user_messages = []

            for msg in messages:
                if msg["role"] == "system":
                    system_msg = msg["content"]
                else:
                    user_messages.append(msg)

            response = await self.client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "system": system_msg,
                    "messages": user_messages,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["content"][0]["text"]
        except Exception as e:
            logger.error(f"Claude API error: {e}")
            raise

    async def embedding(self, text: str) -> List[float]:
        """Claude doesn't have embedding API, use OpenAI fallback."""
        raise NotImplementedError("Use OpenAI for embeddings with Claude")


class OpenAIProvider(LLMProvider):
    """OpenAI provider."""

    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.openai.com/v1")

    async def chat_completion(
        self,
        messages: List[Dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2000,
    ) -> str:
        """Generate chat completion using OpenAI."""
        try:
            response = await self.client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def embedding(
        self, text: str, model: str = "text-embedding-ada-002"
    ) -> List[float]:
        """Generate embedding using OpenAI."""
        try:
            response = await self.client.post(
                f"{self.base_url}/embeddings",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={"model": model, "input": text},
            )
            response.raise_for_status()
            data = response.json()
            return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            raise


class LLMFactory:
    """Factory for creating LLM providers."""

    @staticmethod
    def create_provider(provider_type: str, api_key: str) -> LLMProvider:
        """Create LLM provider based on type."""
        providers = {
            "zhipu": ZhipuAIProvider,
            "claude": ClaudeProvider,
            "openai": OpenAIProvider,
        }

        provider_class = providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_type}")

        return provider_class(api_key)

    @staticmethod
    def create_from_config() -> Optional[LLMProvider]:
        """Create provider from configuration."""
        ai_provider = getattr(settings, "AI_PROVIDER", "zhipu")

        if ai_provider == "zhipu":
            api_key = getattr(settings, "ZHIPU_API_KEY", None)
            if api_key:
                return ZhipuAIProvider(api_key)
        elif ai_provider == "claude":
            api_key = getattr(settings, "ANTHROPIC_API_KEY", None)
            if api_key:
                return ClaudeProvider(api_key)
        elif ai_provider == "openai":
            api_key = getattr(settings, "OPENAI_API_KEY", None)
            if api_key:
                return OpenAIProvider(api_key)

        logger.warning(f"No API key found for provider: {ai_provider}")
        return None

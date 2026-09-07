"""
AI Service Module - SOC Copilot AI Assistant
Provides intelligent analysis and recommendations using LLM
"""

import httpx

from core.config import settings
from core.http_client import get_http_client
from core.logger import get_logger

logger = get_logger(__name__)


class LLMProvider:
    """Base class for LLM providers."""

    def __init__(self, api_key: str, base_url: str | None = None):
        self.api_key = api_key
        self.base_url = base_url
        self._client: httpx.AsyncClient | None = None

    @property
    def client(self) -> httpx.AsyncClient:
        """Get the shared HTTP client."""
        return get_http_client()

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float | None = None,
    ) -> str:
        """Generate chat completion."""
        raise NotImplementedError

    async def embedding(self, text: str) -> list[float]:
        """Generate embedding for text."""
        raise NotImplementedError


class ZhipuAIProvider(LLMProvider):
    """Zhipu AI (智谱AI) provider."""

    def __init__(self, api_key: str, model: str = "glm-4"):
        super().__init__(api_key, "https://open.bigmodel.cn/api/paas/v4")
        self.model = model

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float | None = None,
    ) -> str:
        """Generate chat completion using Zhipu AI."""
        try:
            actual_model = self.model if (not model or model.lower() == "auto") else model

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
            payload = {
                "model": actual_model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            if timeout:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                    )
            else:
                response = await self.client.post(
                    f"{self.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Zhipu AI API error: {e}")
            raise

    async def embedding(self, text: str) -> list[float]:
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
        messages: list[dict[str, str]],
        model: str = "claude-3-opus-20240229",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float | None = None,
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

            # Use custom timeout if provided
            client = self.client
            if timeout:
                client = httpx.AsyncClient(timeout=timeout)

            response = await client.post(
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

    async def embedding(self, text: str) -> list[float]:
        """Claude doesn't have embedding API, use OpenAI fallback."""
        raise NotImplementedError("Use OpenAI for embeddings with Claude")


class OpenAIProvider(LLMProvider):
    """OpenAI provider."""

    def __init__(self, api_key: str):
        super().__init__(api_key, "https://api.openai.com/v1")

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float | None = None,
    ) -> str:
        """Generate chat completion using OpenAI."""
        try:
            # Use custom timeout if provided
            client = self.client
            if timeout:
                client = httpx.AsyncClient(timeout=timeout)

            response = await client.post(
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
    ) -> list[float]:
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


class OpenRouterProvider(LLMProvider):
    """OpenRouter provider (access to multiple LLMs including Kimi models)."""

    def __init__(self, api_key: str, model: str = "moonshotai/kimi-k2.5"):
        # Use NVIDIA API endpoint instead of OpenRouter to avoid 502 errors
        super().__init__(api_key, "https://integrate.api.nvidia.com/v1")
        self.model = model

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float | None = None,
    ) -> str:
        """Generate chat completion using OpenRouter."""
        try:
            # Use provided model or default from initialization
            actual_model = model or self.model

            # Use custom timeout if provided
            client = self.client
            if timeout:
                client = httpx.AsyncClient(timeout=timeout)

            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": actual_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"OpenRouter API error: {e}")
            raise

    async def embedding(
        self, text: str, model: str = "openai/text-embedding-ada-002"
    ) -> list[float]:
        """Generate embedding using OpenRouter."""
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
            logger.error(f"OpenRouter embedding error: {e}")
            raise


class MoonshotAIProvider(LLMProvider):
    """Moonshot AI (Kimi) provider (OpenAI-compatible)."""

    def __init__(self, api_key: str, model: str = "moonshot-v1-8k"):
        # Moonshot AI API endpoint
        super().__init__(api_key, "https://api.moonshot.cn/v1")
        self.model = model

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float | None = None,
    ) -> str:
        """Generate chat completion using Moonshot AI (Kimi)."""
        try:
            # Use provided model or default from initialization
            actual_model = model or self.model

            # Use custom timeout if provided
            client = self.client
            if timeout:
                client = httpx.AsyncClient(timeout=timeout)

            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": actual_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"Moonshot AI API error: {e}")
            raise

    async def embedding(
        self, text: str, model: str = "moonshot-embedding"
    ) -> list[float]:
        """Generate embedding using Moonshot AI."""
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
            logger.error(f"Moonshot AI embedding error: {e}")
            raise


class NVIDIAProvider(LLMProvider):
    """NVIDIA AI Foundation Models provider (OpenAI-compatible)."""

    def __init__(self, api_key: str, model: str = "meta/llama-3.2-11b-vision-instruct"):
        # NVIDIA API endpoint
        super().__init__(api_key, "https://integrate.api.nvidia.com/v1")
        self.model = model

    async def chat_completion(
        self,
        messages: list[dict[str, str]],
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = 4096,
        timeout: float | None = None,
    ) -> str:
        """Generate chat completion using NVIDIA API."""
        try:
            # Use provided model or default from initialization
            actual_model = self.model if (not model or model.lower() == "auto") else model

            # Use custom timeout if provided
            client = self.client
            if timeout:
                client = httpx.AsyncClient(timeout=timeout)

            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": actual_model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            response.raise_for_status()
            data = response.json()
            choice = data["choices"][0]
            msg = choice.get("message", {})
            return msg.get("content") or msg.get("reasoning_content") or ""
        except Exception as e:
            logger.error(f"NVIDIA API error: {e}")
            raise

    async def embedding(
        self, text: str, model: str = "nvidia/nv-embedqa-e5-v5"
    ) -> list[float]:
        """Generate embedding using NVIDIA API."""
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
            logger.error(f"NVIDIA embedding error: {e}")
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
            "nvidia": NVIDIAProvider,
            "moonshot": MoonshotAIProvider,
            "openrouter": OpenRouterProvider,
        }

        provider_class = providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_type}")

        return provider_class(api_key)

    @staticmethod
    def create_provider_for_model(model_id: str, provider_type: str) -> LLMProvider:
        """Create LLM provider for a specific model."""
        from core.config import settings

        # Map provider type to API key setting
        provider_key_map = {
            "anthropic": ("anthropic_api_key", None),
            "zhipu": ("zhipu_api_key", "zhipu_model"),
            "openai": ("openai_api_key", None),
            "nvidia": ("nvidia_api_key", "nvidia_model"),
            "moonshot": ("moonshot_api_key", "moonshot_model"),
            "openrouter": ("openrouter_api_key", "openrouter_model"),
        }

        if provider_type.lower() == "auto" or model_id.lower() == "auto":
            from services.ai_service_enhanced import get_enhanced_ai_service

            svc = get_enhanced_ai_service()
            m_id, p_type, _ = svc.resolve_auto_model("")
            return LLMFactory.create_provider_for_model(m_id, p_type)

        if provider_type.lower() not in provider_key_map:
            raise ValueError(f"Unknown provider: {provider_type}")

        key_setting, model_setting = provider_key_map[provider_type.lower()]
        api_key = getattr(settings, key_setting, None)

        if not api_key:
            raise ValueError(f"No API key configured for provider: {provider_type}")

        # Create provider with model if needed
        providers = {
            "anthropic": ClaudeProvider,
            "zhipu": ZhipuAIProvider,
            "openai": OpenAIProvider,
            "nvidia": NVIDIAProvider,
            "moonshot": MoonshotAIProvider,
            "openrouter": OpenRouterProvider,
        }

        provider_class = providers.get(provider_type.lower())
        if not provider_class:
            raise ValueError(f"Unknown provider: {provider_type}")

        # Some providers need model in constructor
        if provider_type.lower() in ["zhipu", "nvidia", "moonshot", "openrouter"]:
            return provider_class(api_key, model_id)
        else:
            return provider_class(api_key)

    @staticmethod
    def create_from_config() -> LLMProvider | None:
        """Create provider from configuration."""
        ai_provider = getattr(settings, "ai_provider", "zhipu")

        if ai_provider == "zhipu":
            api_key = getattr(settings, "zhipu_api_key", None)
            if api_key:
                zhipu_model = getattr(settings, "zhipu_model", "glm-4")
                return ZhipuAIProvider(api_key, zhipu_model)
        elif ai_provider == "claude":
            api_key = getattr(settings, "anthropic_api_key", None)
            if api_key:
                return ClaudeProvider(api_key)
        elif ai_provider == "openai":
            api_key = getattr(settings, "openai_api_key", None)
            if api_key:
                return OpenAIProvider(api_key)
        elif ai_provider == "nvidia":
            api_key = getattr(settings, "nvidia_api_key", None)
            if api_key:
                nvidia_model = getattr(
                    settings, "nvidia_model", "meta/llama-3.2-11b-vision-instruct"
                )
                return NVIDIAProvider(api_key, nvidia_model)
        elif ai_provider == "moonshot":
            api_key = getattr(settings, "moonshot_api_key", None)
            if api_key:
                moonshot_model = getattr(settings, "moonshot_model", "moonshot-v1-8k")
                return MoonshotAIProvider(api_key, moonshot_model)
        elif ai_provider == "openrouter":
            api_key = getattr(settings, "openrouter_api_key", None)
            if api_key:
                openrouter_model = getattr(
                    settings, "openrouter_model", "moonshotai/kimi-k2.5"
                )
                return OpenRouterProvider(api_key, openrouter_model)

        logger.warning(f"No API key found for provider: {ai_provider}")
        return None

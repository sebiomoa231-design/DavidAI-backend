"""
AI Router (Section 7, 26, 27) -- the heart of v0.8.

Loads all configured providers, ranks them by health/priority, tries each
in order until one succeeds, and falls back automatically. Never lets a
provider failure crash the app.
"""
from typing import Dict, List, Optional

from david.config.settings import get_settings
from david.providers.base import BaseProvider, ProviderResponse
from david.providers.gemini import GeminiProvider
from david.providers.groq import GroqProvider
from david.providers.huggingface import HuggingFaceProvider
from david.providers.openrouter import OpenRouterProvider
from david.providers.cerebras import CerebrasProvider
from david.providers.sambanova import SambaNovaProvider
from david.router.cache import response_cache
from david.router.metrics import router_metrics
from david.utils.logger import get_logger

logger = get_logger("david.router")


class AIRouter:
    def __init__(self):
        settings = get_settings()

        self.providers: Dict[str, BaseProvider] = {
            "gemini": GeminiProvider(settings.GEMINI_API_KEY, settings.GEMINI_MODEL),
            "groq": GroqProvider(settings.GROQ_API_KEY, settings.GROQ_MODEL),
            "huggingface": HuggingFaceProvider(settings.HUGGINGFACE_API_KEY, settings.HUGGINGFACE_MODEL),
            "openrouter": OpenRouterProvider(settings.OPENROUTER_API_KEY, settings.OPENROUTER_MODEL),
            "cerebras": CerebrasProvider(settings.CEREBRAS_API_KEY, settings.CEREBRAS_MODEL),
            "sambanova": SambaNovaProvider(settings.SAMBANOVA_API_KEY, settings.SAMBANOVA_MODEL),
        }
        self.priority: List[str] = settings.provider_priority_list
        self.mode = settings.ROUTER_MODE  # auto | manual | smart

        # Smart-routing preference table (Section 27). Task type -> ordered
        # provider preference. Falls back to self.priority if task_type is
        # unknown or the preferred provider is unavailable.
        self.task_type_preference: Dict[str, List[str]] = {
            "reasoning": ["gemini", "openrouter", "groq"],
            "fast": ["groq", "cerebras", "sambanova"],
            "large_context": ["openrouter", "gemini"],
            "fallback": ["huggingface"],
        }

    def _candidate_order(self, task_type: Optional[str] = None, manual_provider: Optional[str] = None) -> List[str]:
        if manual_provider:
            return [manual_provider]

        if self.mode == "smart" and task_type and task_type in self.task_type_preference:
            preferred = self.task_type_preference[task_type]
            remainder = [p for p in self.priority if p not in preferred]
            return preferred + remainder

        return list(self.priority)

    def get_provider(self, name: str) -> Optional[BaseProvider]:
        return self.providers.get(name)

    async def health_snapshot(self) -> Dict[str, dict]:
        snapshot = {}
        for name, provider in self.providers.items():
            snapshot[name] = {
                "available": provider.available,
                "has_key": bool(provider.api_key),
                "online": provider.health.online,
                "latency_ms": provider.health.latency_ms,
                "last_error": provider.health.last_error,
                "failure_count": provider.health.failure_count,
                "success_count": provider.health.success_count,
            }
        return snapshot

    async def chat(
        self,
        messages: List[Dict[str, str]],
        task_type: Optional[str] = None,
        manual_provider: Optional[str] = None,
        use_cache: bool = True,
        **kwargs,
    ) -> ProviderResponse:
        router_metrics.total_requests += 1

        cache_key = "".join(m.get("content", "") for m in messages)
        if use_cache:
            cached = response_cache.get(cache_key)
            if cached is not None:
                router_metrics.cache_hits += 1
                logger.info("router cache hit")
                return ProviderResponse(
                    provider="cache", model="cache", text=cached, raw=None,
                    latency_ms=0.0, success=True,
                )

        order = self._candidate_order(task_type=task_type, manual_provider=manual_provider)
        attempted = []

        for provider_name in order:
            provider = self.providers.get(provider_name)
            if provider is None or not provider.available:
                continue

            attempted.append(provider_name)
            logger.info(f"router trying provider: {provider_name}")
            response = await provider.chat(messages, **kwargs)

            router_metrics.record_attempt(provider_name, response.success, response.total_tokens)

            if response.success:
                router_metrics.successes += 1
                router_metrics.last_provider_used = provider_name
                router_metrics.prompt_tokens += response.prompt_tokens
                router_metrics.completion_tokens += response.completion_tokens
                if len(attempted) > 1:
                    router_metrics.fallbacks += 1
                if use_cache and response.text:
                    response_cache.set(cache_key, response.text)
                return response

            logger.warning(f"provider {provider_name} failed, trying next candidate")

        router_metrics.failures += 1
        logger.error(f"all providers failed or unavailable. attempted={attempted}")
        return ProviderResponse(
            provider="none",
            model="none",
            text=(
                "I couldn't reach any AI provider right now. "
                "All configured providers are either missing API keys or are currently failing. "
                "Please check your .env configuration or try again shortly."
            ),
            raw={"attempted": attempted},
            latency_ms=0.0,
            success=False,
            error="all_providers_failed",
        )


ai_router = AIRouter()

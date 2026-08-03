"""
Common provider interface (Section 6 & 25).

Every provider (Gemini, Groq, HuggingFace, OpenRouter, Cerebras, SambaNova)
implements this same interface so the router can treat them interchangeably.
"""
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

import httpx

from david.utils.logger import get_logger

logger = get_logger("david.providers")


@dataclass
class ProviderResponse:
    provider: str
    model: str
    text: str
    raw: Any
    latency_ms: float
    success: bool
    error: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


@dataclass
class ProviderHealth:
    online: bool = True
    latency_ms: float = 0.0
    last_error: Optional[str] = None
    failure_count: int = 0
    success_count: int = 0
    cooldown_until: float = 0.0


class BaseProvider(ABC):
    name: str = "base"

    def __init__(self, api_key: str, model: str, timeout: float = 30.0):
        self.api_key = api_key
        self.model = model
        self.timeout = timeout
        self.health = ProviderHealth()

    @property
    def available(self) -> bool:
        """True if the provider has credentials and isn't in a cooldown window."""
        if not self.api_key:
            return False
        if self.health.cooldown_until and time.time() < self.health.cooldown_until:
            return False
        return True

    def _record_success(self, latency_ms: float) -> None:
        self.health.online = True
        self.health.latency_ms = latency_ms
        self.health.last_error = None
        self.health.success_count += 1
        self.health.cooldown_until = 0.0

    def _record_failure(self, error: str) -> None:
        self.health.online = False
        self.health.last_error = error
        self.health.failure_count += 1
        # Exponential-ish cooldown: back off harder after repeated failures.
        cooldown_seconds = min(60 * self.health.failure_count, 600)
        self.health.cooldown_until = time.time() + cooldown_seconds
        logger.warning(f"[{self.name}] failure recorded, cooldown {cooldown_seconds}s")

    async def health_check(self) -> ProviderHealth:
        """Cheap availability check. Subclasses may override with a real ping."""
        self.health.online = bool(self.api_key)
        return self.health

    @abstractmethod
    async def chat(self, messages: List[Dict[str, str]], **kwargs) -> ProviderResponse:
        ...

    async def _post_json(self, url: str, headers: Dict[str, str], json_body: Dict[str, Any]) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(url, headers=headers, json=json_body)
            resp.raise_for_status()
            return resp.json()

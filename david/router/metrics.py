"""Router metrics tracking (Section 7)."""
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class RouterMetrics:
    total_requests: int = 0
    successes: int = 0
    failures: int = 0
    fallbacks: int = 0
    cache_hits: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    last_provider_used: str = ""
    provider_usage_counts: Dict[str, int] = field(default_factory=dict)
    provider_token_counts: Dict[str, int] = field(default_factory=dict)
    provider_failures: Dict[str, int] = field(default_factory=dict)

    def record_attempt(self, provider: str, success: bool, tokens: int = 0) -> None:
        self.provider_usage_counts[provider] = self.provider_usage_counts.get(provider, 0) + 1
        if success:
            self.provider_token_counts[provider] = self.provider_token_counts.get(provider, 0) + tokens
        else:
            self.provider_failures[provider] = self.provider_failures.get(provider, 0) + 1

    def as_dict(self) -> dict:
        return {
            "total_requests": self.total_requests,
            "successes": self.successes,
            "failures": self.failures,
            "fallbacks": self.fallbacks,
            "cache_hits": self.cache_hits,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "last_provider_used": self.last_provider_used,
            "provider_usage_counts": self.provider_usage_counts,
            "provider_token_counts": self.provider_token_counts,
            "provider_failures": self.provider_failures,
        }


router_metrics = RouterMetrics()

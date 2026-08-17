"""Embedding abstractions for semantic memory search.

The current backend has no configured embedding provider. This module therefore
returns an explicit unavailable result and lets lexical/metadata retrieval
continue. A real provider can be injected later without changing callers.
"""
from typing import Any, Optional, Protocol, Sequence


class EmbeddingProvider(Protocol):
    name: str

    async def embed(self, text: str) -> Optional[Sequence[float]]:
        ...


class UnavailableEmbeddingProvider:
    name = "unavailable"

    async def embed(self, text: str) -> Optional[Sequence[float]]:
        return None


class EmbeddingService:
    def __init__(self, provider: Optional[EmbeddingProvider] = None):
        self.provider = provider or UnavailableEmbeddingProvider()

    async def embed(self, text: str) -> Optional[Sequence[float]]:
        return await self.provider.embed(text)

    @property
    def available(self) -> bool:
        return self.provider.name != "unavailable"

    def health(self) -> dict[str, Any]:
        return {"available": self.available, "provider": self.provider.name}

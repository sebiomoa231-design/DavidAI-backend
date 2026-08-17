"""Simple in-memory prompt/response cache (Section 7)."""
import time
from typing import Optional

from david.utils.helpers import hash_text

_DEFAULT_TTL_SECONDS = 600


class ResponseCache:
    def __init__(self, ttl_seconds: int = _DEFAULT_TTL_SECONDS):
        self.ttl_seconds = ttl_seconds
        self._store: dict[str, tuple[float, str]] = {}

    def _key(self, prompt: str) -> str:
        return hash_text(prompt)

    def get(self, prompt: str) -> Optional[str]:
        key = self._key(prompt)
        entry = self._store.get(key)
        if not entry:
            return None
        timestamp, value = entry
        if time.time() - timestamp > self.ttl_seconds:
            del self._store[key]
            return None
        return value

    def set(self, prompt: str, response_text: str) -> None:
        self._store[self._key(prompt)] = (time.time(), response_text)

    def clear(self) -> None:
        self._store.clear()


response_cache = ResponseCache()

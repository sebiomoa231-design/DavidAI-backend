"""
Memory engine (Section 8).

Handles storage and retrieval across memory types: short-term, working,
long-term, project, decision, knowledge, preference, task, conversation.

Relevance scoring here is intentionally simple (keyword overlap) so it works
with zero external dependencies. It can later be swapped for embeddings
without changing the public interface (add / search / update / forget).
"""
import re
from typing import List, Optional

from david.database.json_store import JSONStore
from david.utils.helpers import new_id, now_iso
from david.utils.logger import get_logger

logger = get_logger("david.memory")

VALID_TYPES = {
    "short_term",
    "working",
    "long_term",
    "project",
    "decision",
    "knowledge",
    "preference",
    "task",
    "conversation",
}

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "or",
    "in", "on", "for", "with", "i", "you", "it", "this", "that", "my", "me",
}


def _tokenize(text: str) -> set:
    words = re.findall(r"[a-zA-Z0-9']+", text.lower())
    return {w for w in words if w not in _STOPWORDS and len(w) > 1}


class MemoryEngine:
    def __init__(self):
        self.store = JSONStore("memories")

    def add(
        self,
        content: str,
        memory_type: str = "long_term",
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source: str = "user",
    ) -> dict:
        memory_type = memory_type if memory_type in VALID_TYPES else "long_term"

        # Deduplication: skip near-identical existing memories for this user.
        existing = self.store.find(
            lambda m: m.get("user_id") == user_id and m.get("content", "").strip().lower() == content.strip().lower()
        )
        if existing:
            logger.info("duplicate memory skipped")
            return existing[0]

        record = {
            "id": new_id("mem"),
            "content": content,
            "type": memory_type,
            "user_id": user_id,
            "project_id": project_id,
            "tags": tags or [],
            "source": source,
            "created_at": now_iso(),
            "updated_at": now_iso(),
        }
        self.store.add(record)
        return record

    def search(self, query: str, user_id: Optional[str] = None, limit: int = 10) -> List[dict]:
        """Keyword-overlap relevance search. Returns highest-scoring memories first."""
        query_tokens = _tokenize(query)
        if not query_tokens:
            return []

        candidates = self.store.find(lambda m: user_id is None or m.get("user_id") == user_id)

        scored = []
        for m in candidates:
            content_tokens = _tokenize(m.get("content", ""))
            overlap = len(query_tokens & content_tokens)
            if overlap > 0:
                scored.append((overlap, m))

        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [m for _, m in scored[:limit]]

    def get(self, memory_id: str) -> Optional[dict]:
        return self.store.get(memory_id)

    def all(self, user_id: Optional[str] = None) -> List[dict]:
        if user_id is None:
            return self.store.all()
        return self.store.find(lambda m: m.get("user_id") == user_id)

    def update(self, memory_id: str, content: Optional[str] = None, tags: Optional[List[str]] = None) -> Optional[dict]:
        patch = {"updated_at": now_iso()}
        if content is not None:
            patch["content"] = content
        if tags is not None:
            patch["tags"] = tags
        return self.store.update(memory_id, patch)

    def forget(self, memory_id: str) -> bool:
        return self.store.delete(memory_id)

    def count(self, user_id: Optional[str] = None) -> int:
        return len(self.all(user_id))


memory_engine = MemoryEngine()

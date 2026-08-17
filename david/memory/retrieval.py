"""Hybrid memory retrieval and relevance ranking."""
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Set

from david.memory.embeddings import EmbeddingService
from david.memory.models import SOURCE_AUTHORITY
from david.memory.repository import MemoryRepository

_STOPWORDS = {
    "the", "a", "an", "is", "are", "was", "were", "to", "of", "and", "or",
    "in", "on", "for", "with", "i", "you", "it", "this", "that", "my", "me",
    "we", "our", "what", "how", "why", "when", "continue", "please",
}


def tokenize(text: str) -> Set[str]:
    tokens = set()
    for word in re.findall(r"[a-zA-Z0-9][a-zA-Z0-9'_-]+", (text or "").lower()):
        if word in _STOPWORDS or len(word) <= 1:
            continue
        # Conservative normalization improves recall when no embedding provider
        # is configured, without pretending this is full semantic search.
        if word in {"preferred", "prefers", "preferences"}:
            word = "prefer"
        elif word.endswith("ies") and len(word) > 4:
            word = word[:-3] + "y"
        elif word.endswith("ing") and len(word) > 5:
            word = word[:-3]
        elif word.endswith("ed") and len(word) > 4:
            word = word[:-2]
        tokens.add(word)
    return tokens


def lexical_similarity(query: Set[str], content: Set[str]) -> float:
    if not query or not content:
        return 0.0
    overlap = len(query & content)
    return min(1.0, overlap / max(1, len(query))) * 0.7 + min(1.0, overlap / max(1, len(content))) * 0.3


def recency_score(value: Optional[str]) -> float:
    if not value:
        return 0.0
    try:
        timestamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (datetime.now(timezone.utc) - timestamp).total_seconds() / 86400)
        return math.exp(-age_days / 45.0)
    except (TypeError, ValueError):
        return 0.0


@dataclass
class RetrievalQuery:
    text: str
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    conversation_id: Optional[str] = None
    memory_types: Optional[Set[str]] = None
    include_history: bool = False
    limit: int = 10


class MemoryRetriever:
    def __init__(self, repository: MemoryRepository, embeddings: Optional[EmbeddingService] = None):
        self.repository = repository
        self.embeddings = embeddings or EmbeddingService()
        self.weights = {
            "lexical": 0.36,
            "project": 0.18,
            "task": 0.14,
            "conversation": 0.14,
            "importance": 0.07,
            "confidence": 0.05,
            "recency": 0.04,
            "authority": 0.02,
        }

    def _candidate_filter(self, query: RetrievalQuery):
        allowed_status = {"active", "pending_review", "conflicted"}
        if query.include_history:
            allowed_status |= {"superseded", "archived"}

        def predicate(memory: Dict[str, Any]) -> bool:
            if query.user_id is not None and memory.get("user_id") != query.user_id:
                return False
            if memory.get("status") not in allowed_status:
                return False
            if query.memory_types and memory.get("memory_type") not in query.memory_types:
                return False
            return True
        return predicate

    def retrieve(self, query: RetrievalQuery) -> List[Dict[str, Any]]:
        query_tokens = tokenize(query.text)
        candidates = self.repository.list(self._candidate_filter(query))
        scored: List[Dict[str, Any]] = []
        for memory in candidates:
            content_tokens = tokenize(memory.get("content", ""))
            lexical = lexical_similarity(query_tokens, content_tokens)
            exact_scope = 1.0 if query.project_id and memory.get("project_id") == query.project_id else 0.0
            task_scope = 1.0 if query.task_id and memory.get("task_id") == query.task_id else 0.0
            conversation_scope = 1.0 if query.conversation_id and memory.get("conversation_id") == query.conversation_id else 0.0
            # Project/task/conversation records are still discoverable when the
            # caller has no exact ID, but exact IDs receive the strongest bonus.
            if lexical <= 0 and not (exact_scope or task_scope or conversation_scope):
                continue
            importance = float(memory.get("importance", 0.6))
            confidence = float(memory.get("confidence", 0.8))
            recency = recency_score(memory.get("updated_at") or memory.get("created_at"))
            authority = SOURCE_AUTHORITY.get(memory.get("source", ""), 0.5)
            score = (
                self.weights["lexical"] * lexical
                + self.weights["project"] * exact_scope
                + self.weights["task"] * task_scope
                + self.weights["conversation"] * conversation_scope
                + self.weights["importance"] * importance
                + self.weights["confidence"] * confidence
                + self.weights["recency"] * recency
                + self.weights["authority"] * authority
            )
            item = dict(memory)
            item["relevance_score"] = round(score, 6)
            item["retrieval_signals"] = {
                "lexical": round(lexical, 4), "project_match": bool(exact_scope),
                "task_match": bool(task_scope), "conversation_match": bool(conversation_scope),
                "recency": round(recency, 4), "source_authority": authority,
            }
            scored.append(item)

        # Stable deterministic ordering: score, importance, recency, creation order.
        scored.sort(key=lambda item: (
            item.get("relevance_score", 0), item.get("importance", 0),
            item.get("updated_at", ""), item.get("id", ""),
        ), reverse=True)
        unique: List[Dict[str, Any]] = []
        seen: Set[str] = set()
        for item in scored:
            key = re.sub(r"\W+", " ", item.get("content", "").lower()).strip()
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
            if len(unique) >= max(1, min(query.limit, 100)):
                break
        return unique

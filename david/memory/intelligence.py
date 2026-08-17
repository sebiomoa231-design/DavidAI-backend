"""Decision support for safe memory writes and lifecycle transitions."""
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

from david.memory.models import MemoryInput, SOURCE_AUTHORITY
from david.memory.privacy import PrivacyAssessment, assess_memory_text, is_explicit_memory_command
from david.memory.repository import MemoryRepository
from david.memory.retrieval import lexical_similarity, tokenize


@dataclass
class MemoryDecision:
    action: str
    reason: str
    duplicate_id: Optional[str] = None
    conflict_ids: List[str] = None

    def __post_init__(self):
        if self.conflict_ids is None:
            self.conflict_ids = []


def normalized_text(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", (value or "").lower()))


def _subject_value(text: str) -> Optional[tuple[str, str]]:
    """Extract a conservative subject/value pair for configuration conflicts."""
    patterns = (
        r"(?i)^(?P<subject>.+?)\s+(?:uses|is|are|prefers|selected|deploys|runs on|stores)\s+(?P<value>.+?)\.?$",
        r"(?i)^(?P<subject>[^:=]{2,})\s*[:=]\s*(?P<value>.+?)\.?$",
    )
    for pattern in patterns:
        match = re.match(pattern, (text or "").strip())
        if match:
            return normalized_text(match.group("subject")), normalized_text(match.group("value"))
    return None


class MemoryDecisionEngine:
    def __init__(self, repository: MemoryRepository):
        self.repository = repository
        self.duplicate_threshold = 0.82
        self.related_threshold = 0.35
        self.conflict_threshold = 0.35

    def validate(self, memory: MemoryInput) -> PrivacyAssessment:
        if not memory.content or len(memory.content.strip()) < 2:
            return PrivacyAssessment(False, "memory content is empty or too short")
        if len(memory.content) > 20_000:
            return PrivacyAssessment(False, "memory content exceeds the safe maximum length")
        return assess_memory_text(memory.content)

    def _same_scope(self, incoming: MemoryInput, existing: Dict[str, Any]) -> bool:
        return (
            incoming.user_id == existing.get("user_id")
            and incoming.project_id == existing.get("project_id")
            and incoming.task_id == existing.get("task_id")
            and incoming.conversation_id == existing.get("conversation_id")
            and incoming.memory_type == existing.get("memory_type")
        )

    def _similar_records(self, incoming: MemoryInput) -> List[Dict[str, Any]]:
        incoming_tokens = tokenize(incoming.content)
        records = self.repository.list(lambda m: m.get("user_id") == incoming.user_id and m.get("status") not in {"deleted", "archived"})
        scored = []
        for record in records:
            if not self._same_scope(incoming, record):
                continue
            score = lexical_similarity(incoming_tokens, tokenize(record.get("content", "")))
            if normalized_text(incoming.content) == normalized_text(record.get("content", "")):
                score = 1.0
            if score >= self.related_threshold:
                scored.append((score, record))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [record for _, record in scored[:20]]

    def _is_conflict(self, incoming: MemoryInput, existing: Dict[str, Any]) -> bool:
        if existing.get("status") in {"deleted", "archived", "superseded"} or not self._same_scope(incoming, existing):
            return False
        incoming_pair = _subject_value(incoming.content)
        existing_pair = _subject_value(existing.get("content", ""))
        if not incoming_pair or not existing_pair:
            return False
        incoming_subject, incoming_value = incoming_pair
        existing_subject, existing_value = existing_pair
        subject_similarity = lexical_similarity(tokenize(incoming_subject), tokenize(existing_subject))
        return subject_similarity >= self.conflict_threshold and incoming_value != existing_value

    def decide(self, incoming: MemoryInput) -> MemoryDecision:
        assessment = self.validate(incoming)
        if not assessment.allowed:
            return MemoryDecision("reject", assessment.reason or "privacy validation failed")
        similar = self._similar_records(incoming)
        if similar:
            top = similar[0]
            similarity = lexical_similarity(tokenize(incoming.content), tokenize(top.get("content", "")))
            if normalized_text(incoming.content) == normalized_text(top.get("content", "")) or similarity >= self.duplicate_threshold:
                return MemoryDecision("reinforce", "substantially equivalent memory already exists", duplicate_id=top.get("id"))
        conflicts = [record.get("id") for record in similar if self._is_conflict(incoming, record)]
        if conflicts:
            incoming_authority = SOURCE_AUTHORITY.get(incoming.source, 0.5)
            existing_records = [record for record in similar if record.get("id") in conflicts]
            strongest = max((SOURCE_AUTHORITY.get(record.get("source", ""), 0.5) for record in existing_records), default=0.0)
            if incoming.explicit or incoming_authority > strongest + 0.05:
                return MemoryDecision("supersede", "newer or more authoritative information replaces conflicting current knowledge", conflict_ids=conflicts)
            if incoming_authority < strongest - 0.05:
                return MemoryDecision("review", "conflicting knowledge has stronger existing provenance", conflict_ids=conflicts)
            return MemoryDecision("conflict", "equally authoritative current knowledge conflicts", conflict_ids=conflicts)
        return MemoryDecision("create", "new scoped knowledge is sufficiently distinct")

    def should_write_chat(self, message: str, response: Optional[str] = None) -> bool:
        text = (message or "").strip()
        if len(text) < 12 or text.lower() in {"ok", "okay", "thanks", "thank you", "hi", "hello"}:
            return False
        if is_explicit_memory_command(text):
            return True
        # Chat exchanges are durable only when they contain a decision,
        # preference, correction, stable fact, or meaningful outcome.
        durable_markers = re.compile(r"(?i)\b(prefer(?:red|ence|ences)?|always|never|decided|decision|use(?:s|d|ing)?|switched|remember|goal|project|task|architecture|deployment|configured|correct|instead|from now on)\b")
        return bool(durable_markers.search(text)) or bool(response and durable_markers.search(response))

    def classify_chat(self, message: str) -> Dict[str, Any]:
        lower = (message or "").lower()
        if re.search(r"\b(prefer(?:red|ence|ences)?|always|never|from now on)\b", lower):
            return {"memory_type": "personal", "importance": 0.78}
        if re.search(r"\b(decided|decision)\b", lower):
            return {"memory_type": "decision", "importance": 0.82}
        if re.search(r"\b(project|architecture|backend|frontend|deployment|database)\b", lower):
            return {"memory_type": "project", "importance": 0.72}
        if re.search(r"\b(task|worked on|implemented|fixed|failed)\b", lower):
            return {"memory_type": "task", "importance": 0.68}
        return {"memory_type": "conversation", "importance": 0.55}

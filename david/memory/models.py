"""Domain models and canonical values for David's durable memory system."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

MEMORY_TYPES = {
    "personal", "project", "task", "conversation", "decision", "learning",
    "system", "asset", "workflow", "short_term", "working", "long_term",
    "knowledge", "preference",
}

SOURCES = {
    "user_explicit", "user_confirmed", "user_conversation", "system",
    "system_state", "ai_inference", "external_source", "tool_result",
    "verified_tool_result", "project_event", "task_event", "workflow_result",
    "chat", "user",
}

STATUSES = {"active", "superseded", "archived", "deleted", "conflicted", "pending_review"}

TYPE_ALIASES = {
    "PERSONAL": "personal", "PROJECT": "project", "TASK": "task",
    "CONVERSATION": "conversation", "DECISION": "decision", "LEARNING": "learning",
    "SYSTEM": "system", "ASSET": "asset", "WORKFLOW": "workflow",
    "LONG_TERM": "long_term", "SHORT_TERM": "short_term", "WORKING": "working",
    "KNOWLEDGE": "knowledge", "PREFERENCE": "preference",
}

SOURCE_ALIASES = {
    "USER_EXPLICIT": "user_explicit", "USER_CONFIRMED": "user_confirmed",
    "USER_CONVERSATION": "user_conversation", "SYSTEM": "system",
    "SYSTEM_STATE": "system_state", "AI_INFERENCE": "ai_inference",
    "EXTERNAL_SOURCE": "external_source", "TOOL_RESULT": "tool_result",
    "VERIFIED_TOOL_RESULT": "verified_tool_result", "PROJECT_EVENT": "project_event",
    "TASK_EVENT": "task_event", "WORKFLOW_RESULT": "workflow_result",
    "user": "user_conversation", "chat": "user_conversation",
}

SOURCE_AUTHORITY = {
    "ai_inference": 0.35,
    "external_source": 0.55,
    "user_conversation": 0.65,
    "user": 0.65,
    "tool_result": 0.75,
    "verified_tool_result": 0.82,
    "system": 0.85,
    "system_state": 0.88,
    "user_confirmed": 0.92,
    "user_explicit": 1.0,
    "project_event": 0.78,
    "task_event": 0.78,
    "workflow_result": 0.78,
}


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def canonical_type(value: Optional[str]) -> str:
    value = (value or "long_term").strip()
    return TYPE_ALIASES.get(value, value.lower() if value.lower() in MEMORY_TYPES else "long_term")


def canonical_source(value: Optional[str]) -> str:
    value = (value or "user_conversation").strip()
    return SOURCE_ALIASES.get(value, value.lower() if value.lower() in SOURCES else "user_conversation")


def clamp_score(value: Any, default: float) -> float:
    try:
        return max(0.0, min(1.0, float(value)))
    except (TypeError, ValueError):
        return default


def normalize_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """Upgrade a legacy JSON record in memory without deleting any fields."""
    now = utc_now()
    record = dict(record)
    record.setdefault("memory_type", canonical_type(record.get("type")))
    record["memory_type"] = canonical_type(record.get("memory_type"))
    record.setdefault("type", record["memory_type"])
    record.setdefault("source", "user_conversation")
    record["source"] = canonical_source(record.get("source"))
    record.setdefault("confidence", 0.8)
    record["confidence"] = clamp_score(record.get("confidence"), 0.8)
    record.setdefault("importance", 0.6)
    record["importance"] = clamp_score(record.get("importance"), 0.6)
    record.setdefault("status", "active")
    if record.get("status") not in STATUSES:
        record["status"] = "active"
    record.setdefault("created_at", now)
    record.setdefault("updated_at", record["created_at"])
    record.setdefault("last_accessed_at", None)
    record.setdefault("user_scope", record.get("user_id"))
    record.setdefault("task_id", None)
    record.setdefault("conversation_id", None)
    record.setdefault("metadata", {})
    record.setdefault("provenance", [])
    record.setdefault("version", 1)
    record.setdefault("supersedes_id", None)
    record.setdefault("canonical_id", record.get("id"))
    record.setdefault("tags", [])
    return record


@dataclass
class MemoryInput:
    content: str
    memory_type: str = "long_term"
    source: str = "user_conversation"
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    conversation_id: Optional[str] = None
    confidence: float = 0.8
    importance: float = 0.6
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    explicit: bool = False

    def normalized(self) -> "MemoryInput":
        return MemoryInput(
            content=self.content.strip(),
            memory_type=canonical_type(self.memory_type),
            source=canonical_source("user_explicit" if self.explicit else self.source),
            user_id=self.user_id,
            project_id=self.project_id,
            task_id=self.task_id,
            conversation_id=self.conversation_id,
            confidence=clamp_score(self.confidence, 0.8),
            importance=clamp_score(self.importance, 0.6),
            tags=list(dict.fromkeys(self.tags or [])),
            metadata=dict(self.metadata or {}),
            explicit=self.explicit,
        )

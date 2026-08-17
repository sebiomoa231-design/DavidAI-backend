"""Backward-compatible facade for the production MemoryService.

Existing callers can continue using add/search/get/all/update/forget while all
operations now pass through the same lifecycle, privacy, audit, and retrieval
logic used by the new APIs and AI Core.
"""
from typing import Any, Dict, List, Optional

from david.memory.service import memory_service

VALID_TYPES = {
    "short_term", "working", "long_term", "project", "decision", "knowledge",
    "preference", "task", "conversation", "personal", "learning", "system",
    "asset", "workflow",
}


class MemoryEngine:
    def __init__(self):
        self.service = memory_service
        self.store = self.service.repository.store

    def add(
        self, content: str, memory_type: str = "long_term", user_id: Optional[str] = None,
        project_id: Optional[str] = None, tags: Optional[List[str]] = None,
        source: str = "user_conversation", task_id: Optional[str] = None,
        conversation_id: Optional[str] = None, confidence: float = 0.8,
        importance: float = 0.6, metadata: Optional[Dict[str, Any]] = None,
        explicit: bool = False,
    ) -> dict:
        return self.service.remember(
            content=content, memory_type=memory_type, user_id=user_id,
            project_id=project_id, task_id=task_id, conversation_id=conversation_id,
            tags=tags, source=source, confidence=confidence, importance=importance,
            metadata=metadata, explicit=explicit,
        )

    def search(self, query: str, user_id: Optional[str] = None, limit: int = 10,
               project_id: Optional[str] = None, task_id: Optional[str] = None,
               conversation_id: Optional[str] = None, include_history: bool = False) -> List[dict]:
        return self.service.search_memories(
            query=query, user_id=user_id, project_id=project_id, task_id=task_id,
            conversation_id=conversation_id, limit=limit, include_history=include_history,
        )

    def get(self, memory_id: str) -> Optional[dict]:
        return self.service.get_memory(memory_id)

    def all(self, user_id: Optional[str] = None, include_deleted: bool = False) -> List[dict]:
        return self.service.get_memories(user_id=user_id, include_deleted=include_deleted)

    def update(self, memory_id: str, content: Optional[str] = None, tags: Optional[List[str]] = None,
               confidence: Optional[float] = None, importance: Optional[float] = None,
               status: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> Optional[dict]:
        return self.service.update_memory(
            memory_id, content=content, tags=tags, confidence=confidence,
            importance=importance, status=status, metadata=metadata,
        )

    def forget(self, memory_id: str, user_id: Optional[str] = None) -> bool:
        return self.service.delete_memory(memory_id, user_id=user_id)

    def archive(self, memory_id: str, user_id: Optional[str] = None) -> Optional[dict]:
        return self.service.archive_memory(memory_id, user_id=user_id)

    def count(self, user_id: Optional[str] = None) -> int:
        return self.service.repository.count(user_id=user_id)


memory_engine = MemoryEngine()

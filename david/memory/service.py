"""Authoritative memory service used by AI Core, routes, and planning systems."""
from typing import Any, Dict, List, Optional

from david.memory.context import MemoryContext, MemoryContextService
from david.memory.embeddings import EmbeddingService
from david.memory.intelligence import MemoryDecisionEngine
from david.memory.maintenance import MemoryMaintenance
from david.memory.models import MemoryInput, canonical_source, canonical_type, utc_now
from david.memory.repository import MemoryRepository
from david.memory.retrieval import MemoryRetriever, RetrievalQuery
from david.utils.helpers import new_id
from david.utils.logger import get_logger

logger = get_logger("david.memory.service")


class MemoryService:
    def __init__(self, repository: Optional[MemoryRepository] = None):
        self.repository = repository or MemoryRepository()
        self.retriever = MemoryRetriever(self.repository, EmbeddingService())
        self.context_service = MemoryContextService(self.retriever)
        self.decision_engine = MemoryDecisionEngine(self.repository)
        self.maintenance = MemoryMaintenance(self.repository)

    def _record_from_input(self, incoming: MemoryInput, status: str = "active", **extra: Any) -> Dict[str, Any]:
        incoming = incoming.normalized()
        now = utc_now()
        record = {
            "id": new_id("mem"),
            "content": incoming.content,
            "memory_type": incoming.memory_type,
            "type": incoming.memory_type,
            "source": incoming.source,
            "confidence": incoming.confidence,
            "importance": incoming.importance,
            "created_at": now,
            "updated_at": now,
            "last_accessed_at": None,
            "status": status,
            "user_id": incoming.user_id,
            "user_scope": incoming.user_id,
            "project_id": incoming.project_id,
            "task_id": incoming.task_id,
            "conversation_id": incoming.conversation_id,
            "tags": incoming.tags,
            "metadata": incoming.metadata,
            "provenance": [],
            "version": 1,
            "canonical_id": None,
            "supersedes_id": None,
        }
        record.update(extra)
        record["canonical_id"] = record.get("canonical_id") or record["id"]
        return record

    def create_memory(self, incoming: MemoryInput, *, force: bool = False) -> Dict[str, Any]:
        incoming = incoming.normalized()
        decision = self.decision_engine.decide(incoming)
        if decision.action == "reject":
            raise ValueError(decision.reason)
        if decision.action == "reinforce" and decision.duplicate_id and not force:
            existing = self.repository.get(decision.duplicate_id)
            if not existing:
                raise ValueError("duplicate target memory no longer exists")
            source_strength = 0.04 if incoming.source in {"user_explicit", "user_confirmed", "verified_tool_result"} else 0.01
            patch = {
                "confidence": min(1.0, max(existing.get("confidence", 0.8), incoming.confidence) + source_strength),
                "importance": max(existing.get("importance", 0.6), incoming.importance),
                "last_accessed_at": utc_now(),
                "provenance": list(existing.get("provenance", [])) + [{"source": incoming.source, "at": utc_now(), "metadata": incoming.metadata}],
                "version": int(existing.get("version", 1)) + 1,
            }
            updated = self.repository.update(decision.duplicate_id, patch)
            self.repository.audit("reinforced", decision.duplicate_id, incoming.user_id, {"reason": decision.reason})
            return updated or existing

        if decision.action == "review":
            status = "pending_review"
        elif decision.action == "conflict":
            status = "conflicted"
        else:
            status = "active"

        record = self._record_from_input(incoming, status=status)
        if decision.action in {"supersede", "conflict", "review"}:
            record["metadata"] = dict(record.get("metadata", {}), conflict_ids=decision.conflict_ids)
        created = self.repository.add(record)
        self.repository.audit("created" if decision.action == "create" else decision.action, created["id"], incoming.user_id, {
            "reason": decision.reason, "conflict_ids": decision.conflict_ids,
        })
        if decision.action == "supersede":
            for old_id in decision.conflict_ids:
                self.repository.update(old_id, {
                    "status": "superseded", "superseded_by": created["id"],
                    "version": int((self.repository.get(old_id) or {}).get("version", 1)) + 1,
                })
                self.repository.audit("superseded", old_id, incoming.user_id, {"superseded_by": created["id"]})
            created["supersedes_id"] = decision.conflict_ids[0] if decision.conflict_ids else None
            self.repository.update(created["id"], {"supersedes_id": created["supersedes_id"]})
            created = self.repository.get(created["id"]) or created
        return created

    def remember(
        self,
        content: str,
        memory_type: str = "long_term",
        user_id: Optional[str] = None,
        project_id: Optional[str] = None,
        task_id: Optional[str] = None,
        conversation_id: Optional[str] = None,
        tags: Optional[List[str]] = None,
        source: str = "user_conversation",
        confidence: float = 0.8,
        importance: float = 0.6,
        metadata: Optional[Dict[str, Any]] = None,
        explicit: bool = False,
    ) -> Dict[str, Any]:
        return self.create_memory(MemoryInput(
            content=content, memory_type=memory_type, source=source,
            user_id=user_id, project_id=project_id, task_id=task_id,
            conversation_id=conversation_id, tags=tags or [], confidence=confidence,
            importance=importance, metadata=metadata or {}, explicit=explicit,
        ))

    def get_memory(self, memory_id: str, *, touch: bool = False) -> Optional[Dict[str, Any]]:
        memory = self.repository.get(memory_id)
        if memory and touch and memory.get("status") != "deleted":
            return self.repository.update(memory_id, {"last_accessed_at": utc_now()})
        return memory

    def get_memories(self, user_id: Optional[str] = None, include_deleted: bool = False, limit: int = 100,
                     memory_type: Optional[str] = None, project_id: Optional[str] = None,
                     task_id: Optional[str] = None, conversation_id: Optional[str] = None,
                     status: Optional[str] = None, min_importance: Optional[float] = None,
                     min_confidence: Optional[float] = None) -> List[Dict[str, Any]]:
        records = self.repository.list(lambda m: (
            (user_id is None or m.get("user_id") == user_id)
            and (include_deleted or m.get("status") != "deleted")
            and (memory_type is None or m.get("memory_type") == canonical_type(memory_type))
            and (project_id is None or m.get("project_id") == project_id)
            and (task_id is None or m.get("task_id") == task_id)
            and (conversation_id is None or m.get("conversation_id") == conversation_id)
            and (status is None or m.get("status") == status)
            and (min_importance is None or float(m.get("importance", 0.0)) >= min_importance)
            and (min_confidence is None or float(m.get("confidence", 0.0)) >= min_confidence)
        ))
        records.sort(key=lambda m: (m.get("updated_at", ""), m.get("id", "")), reverse=True)
        return records[: max(1, min(limit, 500))]

    def list_memories_page(self, *, user_id: Optional[str] = None, page: int = 1, page_size: int = 100,
                           include_deleted: bool = False, **filters: Any) -> Dict[str, Any]:
        page = max(1, int(page))
        page_size = max(1, min(int(page_size), 500))
        all_records = self.get_memories(user_id=user_id, include_deleted=include_deleted, limit=500, **filters)
        start = (page - 1) * page_size
        items = all_records[start:start + page_size]
        return {"items": items, "page": page, "page_size": page_size, "has_more": start + page_size < len(all_records), "total_returnable": min(len(all_records), 500)}

    def update_memory(self, memory_id: str, *, content: Optional[str] = None, tags: Optional[List[str]] = None,
                      confidence: Optional[float] = None, importance: Optional[float] = None,
                      status: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None,
                      source: Optional[str] = None, reason: str = "manual correction") -> Optional[Dict[str, Any]]:
        current = self.repository.get(memory_id)
        if not current:
            return None
        patch: Dict[str, Any] = {"version": int(current.get("version", 1)) + 1}
        if content is not None:
            assessment = self.decision_engine.validate(MemoryInput(content=content))
            if not assessment.allowed:
                raise ValueError(assessment.reason or "memory content rejected")
            history = list(current.get("version_history", []))
            history.append({"content": current.get("content"), "version": current.get("version", 1), "updated_at": current.get("updated_at")})
            patch.update({"content": content.strip(), "version_history": history})
        if tags is not None:
            patch["tags"] = tags
        if confidence is not None:
            patch["confidence"] = max(0.0, min(1.0, float(confidence)))
        if importance is not None:
            patch["importance"] = max(0.0, min(1.0, float(importance)))
        if status is not None:
            patch["status"] = status
        if metadata is not None:
            patch["metadata"] = metadata
        if source is not None:
            patch["source"] = canonical_source(source)
        updated = self.repository.update(memory_id, patch)
        self.repository.audit("updated", memory_id, current.get("user_id"), {"reason": reason, "fields": sorted(patch.keys())})
        return updated

    def delete_memory(self, memory_id: str, user_id: Optional[str] = None) -> bool:
        current = self.repository.get(memory_id)
        if not current or (user_id is not None and current.get("user_id") != user_id):
            return False
        deleted = self.repository.soft_delete(memory_id)
        if deleted:
            self.repository.audit("deleted", memory_id, user_id, {"soft_delete": True})
        return bool(deleted)

    def restore_memory(self, memory_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        restored = self.maintenance.restore(memory_id, user_id)
        return restored

    def consolidate_memories(self, canonical_id: str, duplicate_id: str, user_id: str, reason: str = "safe duplicate consolidation") -> Optional[Dict[str, Any]]:
        return self.maintenance.consolidate(canonical_id, duplicate_id, user_id, reason=reason)

    def maintenance_scan(self, user_id: Optional[str] = None, stale_after_days: int = 365) -> Dict[str, Any]:
        return self.maintenance.scan(user_id=user_id, stale_after_days=stale_after_days)

    def archive_memory(self, memory_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        current = self.repository.get(memory_id)
        if not current or (user_id is not None and current.get("user_id") != user_id):
            return None
        updated = self.repository.update(memory_id, {"status": "archived"})
        if updated:
            self.repository.audit("archived", memory_id, user_id, {})
        return updated

    def search_memories(self, query: str, user_id: Optional[str] = None, project_id: Optional[str] = None,
                        task_id: Optional[str] = None, conversation_id: Optional[str] = None,
                        limit: int = 10, include_history: bool = False) -> List[Dict[str, Any]]:
        return self.retriever.retrieve(RetrievalQuery(
            text=query, user_id=user_id, project_id=project_id, task_id=task_id,
            conversation_id=conversation_id, limit=limit, include_history=include_history,
        ))

    def build_context(self, *args, **kwargs) -> MemoryContext:
        return self.context_service.assemble(*args, **kwargs)

    def health(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        records = self.get_memories(user_id=user_id, include_deleted=True, limit=500)
        counts: Dict[str, int] = {}
        for record in records:
            counts[record.get("status", "unknown")] = counts.get(record.get("status", "unknown"), 0) + 1
        return {
            "count": len(records), "status_counts": counts,
            "embedding": self.retriever.embeddings.health(),
            "audit_events": len(self.repository.audit_store.all()),
        }

    def migrate_legacy_records(self) -> int:
        return self.repository.migrate_legacy_records()


memory_service = MemoryService()

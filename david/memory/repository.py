"""Persistence boundary for the memory domain.

JSONStore remains the active storage implementation in this repository. The
repository keeps that decision isolated so a future SQL/Supabase adapter can be
introduced without changing MemoryService or the AI Core.
"""
from typing import Any, Callable, Dict, List, Optional

from david.database.json_store import JSONStore
from david.memory.models import normalize_record, utc_now
from david.utils.helpers import new_id


class MemoryRepository:
    def __init__(self, store: Optional[JSONStore] = None, audit_store: Optional[JSONStore] = None):
        self.store = store or JSONStore("memories")
        self.audit_store = audit_store or JSONStore("memory_audit")

    def _normalize(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return normalize_record(record)

    def add(self, record: Dict[str, Any]) -> Dict[str, Any]:
        return self.store.add(self._normalize(record))

    def get(self, memory_id: str) -> Optional[Dict[str, Any]]:
        record = self.store.get(memory_id)
        return self._normalize(record) if record else None

    def list(self, predicate: Optional[Callable[[Dict[str, Any]], bool]] = None) -> List[Dict[str, Any]]:
        records = [self._normalize(record) for record in self.store.all()]
        if predicate:
            records = [record for record in records if predicate(record)]
        return records

    def update(self, memory_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        patch = dict(patch)
        patch["updated_at"] = utc_now()
        if "memory_type" in patch:
            patch["type"] = patch["memory_type"]
        record = self.store.update(memory_id, patch)
        return self._normalize(record) if record else None

    def soft_delete(self, memory_id: str) -> Optional[Dict[str, Any]]:
        return self.update(memory_id, {"status": "deleted", "deleted_at": utc_now()})

    def audit(self, event_type: str, memory_id: Optional[str], user_id: Optional[str], details: Dict[str, Any]) -> Dict[str, Any]:
        event = {
            "id": new_id("maudit"),
            "event_type": event_type,
            "memory_id": memory_id,
            "user_id": user_id,
            "details": details,
            "created_at": utc_now(),
        }
        self.audit_store.add(event)
        return event

    def count(self, user_id: Optional[str] = None, include_deleted: bool = False) -> int:
        return len(self.list(lambda m: (user_id is None or m.get("user_id") == user_id) and (include_deleted or m.get("status") != "deleted")))

    def migrate_legacy_records(self) -> int:
        """Persist canonical fields for legacy records without deleting data."""
        changed = 0
        for record in self.store.all():
            normalized = self._normalize(record)
            if normalized != record:
                self.store.update(record.get("id"), normalized)
                changed += 1
        return changed

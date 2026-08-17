from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from david.memory.models import SOURCE_AUTHORITY, normalize_record, utc_now
from david.memory.repository import MemoryRepository
from david.memory.retrieval import lexical_similarity, tokenize


class MemoryMaintenance:
    """Non-destructive diagnostics and explicitly authorized lifecycle repairs."""

    def __init__(self, repository: MemoryRepository):
        self.repository = repository

    def scan(self, user_id: Optional[str] = None, stale_after_days: int = 365) -> Dict[str, Any]:
        records = self.repository.list(lambda item: user_id is None or item.get("user_id") == user_id)
        malformed = []
        stale = []
        unresolved_conflicts = []
        duplicate_candidates = []
        now = datetime.now(timezone.utc)
        for raw in records:
            record = normalize_record(raw)
            if not record.get("id") or not record.get("content") or not record.get("user_id"):
                malformed.append(record.get("id"))
            if record.get("status") == "conflicted":
                unresolved_conflicts.append(record.get("id"))
            try:
                updated = datetime.fromisoformat(record.get("updated_at", "").replace("Z", "+00:00"))
                if updated.tzinfo is None:
                    updated = updated.replace(tzinfo=timezone.utc)
                if (now - updated).days >= stale_after_days and record.get("status") == "active":
                    stale.append(record.get("id"))
            except (TypeError, ValueError):
                malformed.append(record.get("id"))

        active = [r for r in records if r.get("status") == "active"]
        for index, left in enumerate(active):
            for right in active[index + 1:]:
                if (left.get("user_id"), left.get("project_id"), left.get("task_id"), left.get("conversation_id"), left.get("memory_type")) != (right.get("user_id"), right.get("project_id"), right.get("task_id"), right.get("conversation_id"), right.get("memory_type")):
                    continue
                similarity = lexical_similarity(tokenize(left.get("content", "")), tokenize(right.get("content", "")))
                if similarity >= 0.82:
                    duplicate_candidates.append({"left_id": left.get("id"), "right_id": right.get("id"), "similarity": round(similarity, 4)})

        return {
            "available": True,
            "records_scanned": len(records),
            "malformed_ids": malformed,
            "stale_ids": stale,
            "unresolved_conflict_ids": unresolved_conflicts,
            "duplicate_candidates": duplicate_candidates[:100],
            "safe_repairs_applied": 0,
            "scanned_at": utc_now(),
        }

    def restore(self, memory_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        current = self.repository.get(memory_id)
        if not current or current.get("user_id") != user_id or current.get("status") != "deleted":
            return None
        restored = self.repository.update(memory_id, {"status": "active", "deleted_at": None, "restored_at": utc_now()})
        if restored:
            self.repository.audit("restored", memory_id, user_id, {"from_status": "deleted"})
        return restored

    def consolidate(self, canonical_id: str, duplicate_id: str, user_id: str, reason: str = "safe duplicate consolidation") -> Optional[Dict[str, Any]]:
        canonical = self.repository.get(canonical_id)
        duplicate = self.repository.get(duplicate_id)
        if not canonical or not duplicate or canonical.get("user_id") != user_id or duplicate.get("user_id") != user_id:
            return None
        same_scope = all(canonical.get(key) == duplicate.get(key) for key in ("project_id", "task_id", "conversation_id", "memory_type"))
        similarity = lexical_similarity(tokenize(canonical.get("content", "")), tokenize(duplicate.get("content", "")))
        if not same_scope or similarity < 0.82 or canonical.get("status") != "active" or duplicate.get("status") != "active":
            return None
        winner = canonical
        if (SOURCE_AUTHORITY.get(duplicate.get("source", ""), 0.5), duplicate.get("confidence", 0.0), duplicate.get("importance", 0.0)) > (SOURCE_AUTHORITY.get(canonical.get("source", ""), 0.5), canonical.get("confidence", 0.0), canonical.get("importance", 0.0)):
            winner = duplicate
        loser_id = duplicate_id if winner["id"] == canonical_id else canonical_id
        winner_id = winner["id"]
        provenance = list(winner.get("provenance", [])) + list(duplicate.get("provenance", [])) + [{"memory_id": loser_id, "source": duplicate.get("source"), "at": utc_now(), "reason": reason}]
        merged = self.repository.update(winner_id, {
            "confidence": max(float(canonical.get("confidence", 0.8)), float(duplicate.get("confidence", 0.8))),
            "importance": max(float(canonical.get("importance", 0.6)), float(duplicate.get("importance", 0.6))),
            "tags": list(dict.fromkeys(list(canonical.get("tags", [])) + list(duplicate.get("tags", [])))),
            "provenance": provenance,
            "version": int(winner.get("version", 1)) + 1,
        })
        self.repository.update(loser_id, {"status": "superseded", "canonical_id": winner_id, "superseded_by": winner_id, "version": int((self.repository.get(loser_id) or {}).get("version", 1)) + 1})
        self.repository.audit("merged", winner_id, user_id, {"merged_memory_id": loser_id, "reason": reason})
        return merged

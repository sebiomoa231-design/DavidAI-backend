"""Decision engine (Section 10) -- records decisions with reasoning, and
mirrors important ones into long-term memory."""
from typing import List, Optional

from david.database.json_store import JSONStore
from david.utils.helpers import new_id, now_iso
from david.memory.memory_engine import memory_engine

store = JSONStore("decisions")


def record_decision(decision: str, reason: str, project_id: Optional[str] = None, remember: bool = True) -> dict:
    entry = {
        "id": new_id("dec"),
        "decision": decision,
        "reason": reason,
        "project_id": project_id,
        "created_at": now_iso(),
    }
    store.add(entry)

    if remember:
        memory_engine.add(
            content=f"Decision: {decision} -- Reason: {reason}",
            memory_type="decision",
            project_id=project_id,
            source="decision_engine",
        )
    return entry


def list_decisions(project_id: Optional[str] = None) -> List[dict]:
    if project_id is None:
        return store.all()
    return store.find(lambda d: d.get("project_id") == project_id)

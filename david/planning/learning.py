"""Learning engine (Section 10) -- records signal/outcome/confidence so
David can remember what worked and what failed."""
from typing import List, Optional

from david.database.json_store import JSONStore
from david.utils.helpers import new_id, now_iso

store = JSONStore("learning")


def record_learning(signal: str, outcome: str, confidence: float = 0.5) -> dict:
    entry = {
        "id": new_id("learn"),
        "signal": signal,
        "outcome": outcome,
        "confidence": max(0.0, min(1.0, confidence)),
        "created_at": now_iso(),
    }
    store.add(entry)
    return entry


def list_learning(limit: Optional[int] = None) -> List[dict]:
    records = store.all()
    records.sort(key=lambda r: r.get("created_at", ""), reverse=True)
    return records[:limit] if limit else records

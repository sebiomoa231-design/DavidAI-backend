"""
Lightweight JSON-backed data store.

This is the v0.7 persistence layer. Every collection (memories, projects,
tasks, learning, decisions, conversations, users, uploads...) is a JSON file
under /data. A thread lock protects read-modify-write cycles.

The store deliberately exposes a small, generic interface so it can later be
swapped for SQLite/Postgres (see database/models.py) without touching the
engines that use it (memory, planning, etc).
"""
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from david.config.settings import get_settings
from david.utils.logger import get_logger

logger = get_logger("david.database")

_locks: Dict[str, threading.Lock] = {}
_locks_guard = threading.Lock()


def _lock_for(name: str) -> threading.Lock:
    with _locks_guard:
        if name not in _locks:
            _locks[name] = threading.Lock()
        return _locks[name]


class JSONStore:
    """A single JSON-file-backed collection of dict records, keyed by 'id'."""

    def __init__(self, collection: str):
        settings = get_settings()
        self.collection = collection
        self.path: Path = settings.DATA_DIR / f"{collection}.json"
        self.lock = _lock_for(collection)
        if not self.path.exists():
            self._write([])

    def _read(self) -> List[Dict[str, Any]]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                content = f.read().strip()
                return json.loads(content) if content else []
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.warning(f"[{self.collection}] store unreadable ({e}); resetting to empty list")
            return []

    def _write(self, records: List[Dict[str, Any]]) -> None:
        tmp_path = self.path.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)
        tmp_path.replace(self.path)

    def all(self) -> List[Dict[str, Any]]:
        with self.lock:
            return self._read()

    def get(self, record_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            for r in self._read():
                if r.get("id") == record_id:
                    return r
        return None

    def add(self, record: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            records = self._read()
            records.append(record)
            self._write(records)
        return record

    def update(self, record_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        with self.lock:
            records = self._read()
            for r in records:
                if r.get("id") == record_id:
                    r.update(patch)
                    self._write(records)
                    return r
        return None

    def delete(self, record_id: str) -> bool:
        with self.lock:
            records = self._read()
            new_records = [r for r in records if r.get("id") != record_id]
            if len(new_records) == len(records):
                return False
            self._write(new_records)
            return True

    def find(self, predicate) -> List[Dict[str, Any]]:
        with self.lock:
            return [r for r in self._read() if predicate(r)]

    def clear(self) -> None:
        with self.lock:
            self._write([])

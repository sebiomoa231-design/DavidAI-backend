"""
Small shared helper utilities used across David AI modules.
"""
import uuid
import time
import hashlib
from datetime import datetime, timezone


def new_id(prefix: str = "") -> str:
    """Generate a short unique id, optionally prefixed (e.g. 'proj_ab12cd34')."""
    raw = uuid.uuid4().hex[:12]
    return f"{prefix}_{raw}" if prefix else raw


def now_iso() -> str:
    """Current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


def now_ts() -> float:
    """Current epoch timestamp (for latency / duration math)."""
    return time.time()


def hash_text(text: str) -> str:
    """Stable hash used for cache keys (prompt/response caching)."""
    return hashlib.sha256(text.strip().lower().encode("utf-8")).hexdigest()

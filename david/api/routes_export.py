"""Export endpoint (Section 23) -- dumps all David data as one JSON payload."""
from fastapi import APIRouter, Depends

from david.database.json_store import JSONStore
from david.security.auth import get_current_user
from david.security.workspace import scope_user_id

router = APIRouter(tags=["export"])

COLLECTIONS = [
    "memories", "projects", "tasks", "learning", "decisions",
    "conversations", "users", "uploads", "notes",
]


@router.get("/api/export")
async def export_all(current_user: dict = Depends(get_current_user)):
    user_id = scope_user_id(current_user, None)

    data = {}
    for name in COLLECTIONS:
        records = JSONStore(name).all()
        if user_id is not None:
            if name == "users":
                data[name] = [r for r in records if r.get("id") == user_id]
            else:
                data[name] = [r for r in records if r.get("user_id") == user_id]
        else:
            data[name] = records
    return data

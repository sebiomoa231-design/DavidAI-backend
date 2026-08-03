
"""Built-in notes plugin -- simple persistent quick-notes."""
from fastapi import HTTPException

from david.database.json_store import JSONStore
from david.utils.helpers import new_id, now_iso

store = JSONStore("notes")


def run(action: str = "list", content: str = "", note_id: str = "", user_id: str = None) -> dict:
    if action == "add":
        note = {"id": new_id("note"), "content": content, "user_id": user_id, "created_at": now_iso()}
        store.add(note)
        return note
    if action == "list":
        if user_id:
            return {"notes": store.find(lambda n: n.get("user_id") == user_id)}
        return {"notes": store.find(lambda n: n.get("user_id") is None)}
    if action == "delete":
        matches = store.find(lambda n: n.get("id") == note_id)
        if not matches:
            return {"deleted": False}
        note = matches[0]
        if note.get("user_id") not in (None, user_id):
            raise HTTPException(status_code=403, detail="You cannot delete another user's note")
        return {"deleted": store.delete(note_id)}
    raise ValueError(f"Unknown action '{action}'")

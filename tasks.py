
"""Task management (Section 9)."""
from typing import List, Optional

from david.database.json_store import JSONStore
from david.utils.helpers import new_id, now_iso
from david.planning import projects as projects_module

store = JSONStore("tasks")

VALID_STATUSES = {"pending", "running", "completed", "blocked", "cancelled"}


def create_task(
    title: str,
    project_id: Optional[str] = None,
    notes: str = "",
    priority: Optional[str] = None,
    due_date: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict:
    task = {
        "id": new_id("task"),
        "user_id": user_id,
        "title": title,
        "project_id": project_id,
        "notes": notes,
        "status": "pending",
        "priority": priority,
        "due_date": due_date,
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    store.add(task)
    if project_id:
        projects_module.link_task(project_id, task["id"])
    return task


def list_tasks(project_id: Optional[str] = None, status: Optional[str] = None, user_id: Optional[str] = None) -> List[dict]:
    def predicate(t: dict) -> bool:
        if user_id is not None and t.get("user_id") != user_id:
            return False
        if project_id is not None and t.get("project_id") != project_id:
            return False
        if status is not None and t.get("status") != status:
            return False
        return True
    return store.find(predicate)


def get_task(task_id: str) -> Optional[dict]:
    return store.get(task_id)


def update_task_status(task_id: str, status: str) -> Optional[dict]:
    status = status.strip().lower()
    if status not in VALID_STATUSES:
        raise ValueError(f"Invalid status '{status}'. Must be one of {sorted(VALID_STATUSES)}")
    return store.update(task_id, {"status": status, "updated_at": now_iso()})

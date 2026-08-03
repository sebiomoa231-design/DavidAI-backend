"""Project management (Section 9)."""
from typing import List, Optional

from david.database.json_store import JSONStore
from david.utils.helpers import new_id, now_iso

store = JSONStore("projects")


def create_project(name: str, description: str = "", goals: Optional[List[str]] = None, user_id: Optional[str] = None) -> dict:
    project = {
        "id": new_id("proj"),
        "user_id": user_id,
        "name": name,
        "description": description,
        "goals": goals or [],
        "decisions": [],
        "milestones": [],
        "blockers": [],
        "linked_tasks": [],
        "linked_conversations": [],
        "linked_files": [],
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    store.add(project)
    return project


def list_projects(user_id: Optional[str] = None) -> List[dict]:
    if user_id is None:
        return store.all()
    return store.find(lambda p: p.get("user_id") == user_id)


def get_project(project_id: str) -> Optional[dict]:
    return store.get(project_id)


def update_project(project_id: str, **fields) -> Optional[dict]:
    fields["updated_at"] = now_iso()
    return store.update(project_id, fields)


def link_task(project_id: str, task_id: str) -> Optional[dict]:
    project = store.get(project_id)
    if not project:
        return None
    linked = project.get("linked_tasks", [])
    if task_id not in linked:
        linked.append(task_id)
    return store.update(project_id, {"linked_tasks": linked, "updated_at": now_iso()})

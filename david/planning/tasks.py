"""Task management with durable task-event memory integration."""
from typing import List, Optional

from david.database.json_store import JSONStore
from david.memory.service import memory_service
from david.utils.helpers import new_id, now_iso
from david.planning import projects as projects_module

store = JSONStore("tasks")
VALID_STATUSES = {"pending", "running", "completed", "blocked", "cancelled"}


def create_task(
    title: str, project_id: Optional[str] = None, notes: str = "",
    priority: Optional[str] = None, due_date: Optional[str] = None,
    user_id: Optional[str] = None,
) -> dict:
    task = {
        "id": new_id("task"), "user_id": user_id, "title": title,
        "project_id": project_id, "notes": notes, "status": "pending",
        "priority": priority, "due_date": due_date, "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    store.add(task)
    if project_id:
        projects_module.link_task(project_id, task["id"])
    try:
        memory_service.remember(
            content=f"Task created: {title}", memory_type="task", user_id=user_id,
            project_id=project_id, task_id=task["id"], source="task_event",
            confidence=0.86, importance=0.62, metadata={"event": "created"},
        )
    except ValueError:
        pass
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
    updated = store.update(task_id, {"status": status, "updated_at": now_iso()})
    if updated:
        try:
            memory_service.remember(
                content=f"Task '{updated.get('title', task_id)}' status changed to {status}.",
                memory_type="task", user_id=updated.get("user_id"), project_id=updated.get("project_id"),
                task_id=task_id, source="task_event", confidence=0.9,
                importance=0.7 if status in {"blocked", "completed"} else 0.58,
                metadata={"event": "status_changed", "status": status},
            )
        except ValueError:
            pass
    return updated


DEFAULT_AGENTIC_CAPABILITIES = [
    "agentic_execution",
    "multi_step_execution",
]


async def execute_task(
    task_id: str,
    user_id: Optional[str] = None,
    provider: Optional[str] = None,
    required_capabilities: Optional[List[str]] = None,
    provider_options: Optional[dict] = None,
) -> dict:
    """Execute a planned task through David's AI Core.

    The import is intentionally local because AI Core already imports the task
    module for status and context information. Manus is selected automatically
    when agentic capabilities are required, while the router retains fallback
    providers if Manus is unavailable or fails.
    """
    task = get_task(task_id)
    if task is None:
        raise ValueError("Task not found")
    if user_id is not None and task.get("user_id") != user_id:
        raise PermissionError("Task does not belong to the current workspace")

    from david.core.david import handle_chat

    update_task_status(task_id, "running")
    prompt = task.get("title", "")
    notes = task.get("notes", "")
    if notes:
        prompt += f"\n\nTask notes:\n{notes}"

    options = dict(provider_options or {})
    capabilities = required_capabilities or DEFAULT_AGENTIC_CAPABILITIES
    response = await handle_chat(
        message=prompt,
        user_id=task.get("user_id"),
        project_id=task.get("project_id"),
        task_id=task_id,
        task_type="agentic" if provider == "manus" or capabilities else "reasoning",
        manual_provider=provider,
        required_capabilities=capabilities,
        provider_options=options,
        remember=True,
    )
    update_task_status(task_id, "completed" if response.get("success") else "blocked")
    return {"task": get_task(task_id), "execution": response}

"""Task endpoints (Section 9, 23)."""
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from david.planning import tasks as tasks_module
from david.planning import projects as projects_module
from david.security.auth import get_current_user
from david.security.workspace import ensure_owner, scope_user_id

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    title: str
    project_id: Optional[str] = None
    notes: str = ""
    priority: Optional[str] = None
    due_date: Optional[str] = None
    user_id: Optional[str] = None


@router.get("")
async def list_tasks(
    project_id: Optional[str] = None,
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user),
):
    scoped_user_id = scope_user_id(current_user, None)
    return tasks_module.list_tasks(project_id=project_id, status=status, user_id=scoped_user_id)


@router.post("")
async def create_task(payload: TaskCreate, current_user: dict = Depends(get_current_user)):
    scoped_user_id = scope_user_id(current_user, payload.user_id)

    if payload.project_id:
        project = projects_module.get_project(payload.project_id)
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")
        ensure_owner(project, current_user, resource_name="project")

    return tasks_module.create_task(
        title=payload.title,
        project_id=payload.project_id,
        notes=payload.notes,
        priority=payload.priority,
        due_date=payload.due_date,
        user_id=scoped_user_id,
    )


@router.post("/{task_id}/status/{status}")
async def update_task_status(task_id: str, status: str, current_user: dict = Depends(get_current_user)):
    task = tasks_module.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    ensure_owner(task, current_user, resource_name="task")
    try:
        updated = tasks_module.update_task_status(task_id, status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return updated

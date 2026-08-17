"""Project endpoints (Section 9, 23)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from david.planning import projects as projects_module
from david.security.auth import get_current_user
from david.security.workspace import ensure_owner, scope_user_id

router = APIRouter(prefix="/api/projects", tags=["projects"])


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    goals: Optional[List[str]] = None
    user_id: Optional[str] = None


@router.get("")
async def list_projects(user_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    scoped_user_id = scope_user_id(current_user, user_id)
    return projects_module.list_projects(user_id=scoped_user_id)


@router.post("")
async def create_project(payload: ProjectCreate, current_user: dict = Depends(get_current_user)):
    scoped_user_id = scope_user_id(current_user, payload.user_id)
    return projects_module.create_project(
        name=payload.name, description=payload.description, goals=payload.goals, user_id=scoped_user_id
    )


@router.get("/{project_id}")
async def get_project(project_id: str, current_user: dict = Depends(get_current_user)):
    project = projects_module.get_project(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    ensure_owner(project, current_user, resource_name="project")
    return project

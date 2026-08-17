from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from david.core.david import IDENTITY, handle_chat
from david.config.settings import get_settings
from david.core.owner import get_owner_profile
from david.memory.memory_engine import memory_engine
from david.memory.service import memory_service
from david.planning import projects as projects_module
from david.planning import tasks as tasks_module
from david.router.ai_router import ai_router
from david.security.auth import get_current_user_optional
from david.security.workspace import scope_user_id

router = APIRouter(tags=["core"])


@router.get("/api/health")
async def health():
    embedding = memory_service.retriever.embeddings.health()
    return {
        "status": "ok",
        "service": "david-ai-backend",
        "version": get_settings().APP_VERSION,
        "memory": {
            "status": "ok",
            "persistence": "json_store",
            "embedding_status": embedding.get("status", "unknown"),
        },
    }


@router.get("/api/status")
async def status(current_user: Optional[dict] = Depends(get_current_user_optional)):
    scoped_user_id = scope_user_id(current_user, None)
    return {
        "status": "online",
        "workspace_user_id": scoped_user_id,
        "private_mode": True,
        "owner": get_owner_profile(),
        "memory_count": memory_engine.count(user_id=scoped_user_id),
        "memory_health": memory_service.health(user_id=scoped_user_id),
        "project_count": len(projects_module.list_projects(user_id=scoped_user_id)),
        "task_count": len(tasks_module.list_tasks(user_id=scoped_user_id)),
        "providers": await ai_router.health_snapshot(),
    }


@router.get("/api/identity")
async def identity():
    return IDENTITY


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    conversation_id: Optional[str] = None
    task_type: Optional[str] = None
    provider: Optional[str] = None
    remember: bool = True
    recent_context: Optional[list[str]] = None


@router.post("/api/chat")
async def chat(payload: ChatRequest, current_user: Optional[dict] = Depends(get_current_user_optional)):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    scoped_user_id = scope_user_id(current_user, payload.user_id)
    return await handle_chat(
        message=payload.message, user_id=scoped_user_id, project_id=payload.project_id,
        task_id=payload.task_id, conversation_id=payload.conversation_id,
        task_type=payload.task_type, manual_provider=payload.provider,
        remember=payload.remember, recent_context=payload.recent_context,
    )

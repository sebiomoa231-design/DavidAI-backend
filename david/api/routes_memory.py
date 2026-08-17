from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from david.memory.memory_engine import memory_engine
from david.memory.service import memory_service
from david.security.auth import get_current_user
from david.security.workspace import ensure_owner, scope_user_id

router = APIRouter(prefix="/api/memories", tags=["memory"])


class MemoryCreate(BaseModel):
    content: str = Field(min_length=2, max_length=20000)
    type: str = "long_term"
    memory_type: Optional[str] = None
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    conversation_id: Optional[str] = None
    tags: Optional[List[str]] = None
    source: str = "user_explicit"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    importance: float = Field(default=0.6, ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    explicit: bool = True

    @field_validator("content")
    @classmethod
    def strip_content(cls, value: str) -> str:
        return value.strip()


class MemoryUpdate(BaseModel):
    content: Optional[str] = Field(default=None, min_length=2, max_length=20000)
    tags: Optional[List[str]] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    importance: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    status: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    reason: str = "manual correction"


class MemoryRestoreRequest(BaseModel):
    reason: str = "user-requested restoration"


class MemoryConsolidateRequest(BaseModel):
    duplicate_id: str = Field(min_length=1, max_length=200)
    reason: str = "safe duplicate consolidation"


class MemoryContextRequest(BaseModel):
    message: str = Field(min_length=1, max_length=20000)
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    task_id: Optional[str] = None
    conversation_id: Optional[str] = None
    recent_context: Optional[List[str]] = None
    limit: int = Field(default=8, ge=1, le=50)
    budget_tokens: int = Field(default=1800, ge=100, le=12000)


def _memory_type(payload: MemoryCreate) -> str:
    return payload.memory_type or payload.type


@router.get("")
async def list_memories(
    user_id: Optional[str] = None,
    include_deleted: bool = False,
    page: int = Query(default=1, ge=1, le=10000),
    page_size: int = Query(default=100, ge=1, le=500),
    memory_type: Optional[str] = None,
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    status: Optional[str] = None,
    min_importance: Optional[float] = Query(default=None, ge=0.0, le=1.0),
    min_confidence: Optional[float] = Query(default=None, ge=0.0, le=1.0),
    current_user: dict = Depends(get_current_user),
):
    scoped_user_id = scope_user_id(current_user, user_id)
    return memory_service.list_memories_page(
        user_id=scoped_user_id, page=page, page_size=page_size, include_deleted=include_deleted,
        memory_type=memory_type, project_id=project_id, task_id=task_id,
        conversation_id=conversation_id, status=status, min_importance=min_importance,
        min_confidence=min_confidence,
    )


@router.post("")
async def create_memory(payload: MemoryCreate, current_user: dict = Depends(get_current_user)):
    scoped_user_id = scope_user_id(current_user, payload.user_id)
    try:
        return memory_service.remember(
            content=payload.content, memory_type=_memory_type(payload), user_id=scoped_user_id,
            project_id=payload.project_id, task_id=payload.task_id,
            conversation_id=payload.conversation_id, tags=payload.tags,
            source=payload.source, confidence=payload.confidence, importance=payload.importance,
            metadata=payload.metadata, explicit=payload.explicit,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/search")
async def search_memories(
    q: str,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    task_id: Optional[str] = None,
    conversation_id: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=100),
    include_history: bool = False,
    current_user: dict = Depends(get_current_user),
):
    scoped_user_id = scope_user_id(current_user, user_id)
    return memory_service.search_memories(
        query=q, user_id=scoped_user_id, project_id=project_id, task_id=task_id,
        conversation_id=conversation_id, limit=limit, include_history=include_history,
    )


@router.get("/health")
async def memory_health(current_user: dict = Depends(get_current_user)):
    return memory_service.health(user_id=scope_user_id(current_user, None))


@router.post("/context")
async def build_memory_context(payload: MemoryContextRequest, current_user: dict = Depends(get_current_user)):
    scoped_user_id = scope_user_id(current_user, payload.user_id)
    context = memory_service.build_context(
        message=payload.message, user_id=scoped_user_id, project_id=payload.project_id,
        task_id=payload.task_id, conversation_id=payload.conversation_id,
        recent_context=payload.recent_context, limit=payload.limit, budget_tokens=payload.budget_tokens,
    )
    return {**context.to_dict(), "prompt": context.prompt, "memories": context.memories}


@router.post("/maintenance/scan")
async def scan_memory_health(
    stale_after_days: int = Query(default=365, ge=1, le=3650),
    current_user: dict = Depends(get_current_user),
):
    return memory_service.maintenance_scan(user_id=scope_user_id(current_user, None), stale_after_days=stale_after_days)


@router.get("/{memory_id}/history")
async def memory_history(memory_id: str, current_user: dict = Depends(get_current_user)):
    memory = memory_service.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    ensure_owner(memory, current_user, resource_name="memory")
    events = [event for event in memory_service.repository.audit_store.all() if event.get("memory_id") == memory_id]
    return {"id": memory_id, "version": memory.get("version", 1), "version_history": memory.get("version_history", []), "audit_events": events[-100:]}


@router.post("/{memory_id}/restore")
async def restore_memory(memory_id: str, payload: MemoryRestoreRequest, current_user: dict = Depends(get_current_user)):
    memory = memory_service.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    ensure_owner(memory, current_user, resource_name="memory")
    restored = memory_service.restore_memory(memory_id, current_user["id"])
    if not restored:
        raise HTTPException(status_code=409, detail="Memory is not eligible for restoration")
    return restored


@router.post("/{memory_id}/consolidate")
async def consolidate_memory(memory_id: str, payload: MemoryConsolidateRequest, current_user: dict = Depends(get_current_user)):
    memory = memory_service.get_memory(memory_id)
    duplicate = memory_service.get_memory(payload.duplicate_id)
    if not memory or not duplicate:
        raise HTTPException(status_code=404, detail="Memory not found")
    ensure_owner(memory, current_user, resource_name="memory")
    ensure_owner(duplicate, current_user, resource_name="memory")
    merged = memory_service.consolidate_memories(memory_id, payload.duplicate_id, current_user["id"], reason=payload.reason)
    if not merged:
        raise HTTPException(status_code=409, detail="Memories are not safe consolidation candidates")
    return merged


@router.get("/{memory_id}")
async def get_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    memory = memory_service.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    ensure_owner(memory, current_user, resource_name="memory")
    return memory


@router.patch("/{memory_id}")
async def update_memory(memory_id: str, payload: MemoryUpdate, current_user: dict = Depends(get_current_user)):
    memory = memory_service.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    ensure_owner(memory, current_user, resource_name="memory")
    try:
        updated = memory_service.update_memory(
            memory_id, content=payload.content, tags=payload.tags, confidence=payload.confidence,
            importance=payload.importance, status=payload.status, metadata=payload.metadata,
            reason=payload.reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Memory not found")
    return updated


@router.post("/{memory_id}/archive")
async def archive_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    memory = memory_service.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    ensure_owner(memory, current_user, resource_name="memory")
    archived = memory_service.archive_memory(memory_id, user_id=memory.get("user_id"))
    if not archived:
        raise HTTPException(status_code=404, detail="Memory not found")
    return archived


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    memory = memory_service.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    ensure_owner(memory, current_user, resource_name="memory")
    ok = memory_service.delete_memory(memory_id, user_id=memory.get("user_id"))
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True, "soft_deleted": True, "id": memory_id}

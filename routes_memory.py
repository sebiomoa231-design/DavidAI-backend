"""Memory endpoints (Section 8, 23)."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from david.memory.memory_engine import memory_engine
from david.security.auth import get_current_user
from david.security.workspace import ensure_owner, scope_user_id

router = APIRouter(prefix="/api/memories", tags=["memory"])


class MemoryCreate(BaseModel):
    content: str
    type: str = "long_term"
    user_id: Optional[str] = None
    project_id: Optional[str] = None
    tags: Optional[List[str]] = None


@router.get("")
async def list_memories(user_id: Optional[str] = None, current_user: dict = Depends(get_current_user)):
    scoped_user_id = scope_user_id(current_user, user_id)
    return memory_engine.all(user_id=scoped_user_id)


@router.post("")
async def create_memory(payload: MemoryCreate, current_user: dict = Depends(get_current_user)):
    scoped_user_id = scope_user_id(current_user, payload.user_id)
    return memory_engine.add(
        content=payload.content,
        memory_type=payload.type,
        user_id=scoped_user_id,
        project_id=payload.project_id,
        tags=payload.tags,
    )


@router.get("/search")
async def search_memories(q: str, user_id: Optional[str] = None, limit: int = 10, current_user: dict = Depends(get_current_user)):
    scoped_user_id = scope_user_id(current_user, user_id)
    return memory_engine.search(query=q, user_id=scoped_user_id, limit=limit)


@router.delete("/{memory_id}")
async def delete_memory(memory_id: str, current_user: dict = Depends(get_current_user)):
    memory = memory_engine.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    ensure_owner(memory, current_user, resource_name="memory")
    ok = memory_engine.forget(memory_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True}

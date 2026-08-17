"""Learning + decision endpoints (Section 10, 23)."""
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from david.planning import learning as learning_module
from david.planning import decisions as decisions_module

router = APIRouter(tags=["learning"])


class LearningCreate(BaseModel):
    signal: str
    outcome: str
    confidence: float = 0.5


@router.get("/api/learning")
async def list_learning(limit: Optional[int] = None):
    return learning_module.list_learning(limit=limit)


@router.post("/api/learning")
async def create_learning(payload: LearningCreate):
    return learning_module.record_learning(
        signal=payload.signal, outcome=payload.outcome, confidence=payload.confidence
    )


class DecisionCreate(BaseModel):
    decision: str
    reason: str
    project_id: Optional[str] = None
    remember: bool = True


@router.get("/api/decisions")
async def list_decisions(project_id: Optional[str] = None):
    return decisions_module.list_decisions(project_id=project_id)


@router.post("/api/decisions")
async def create_decision(payload: DecisionCreate):
    return decisions_module.record_decision(
        decision=payload.decision, reason=payload.reason,
        project_id=payload.project_id, remember=payload.remember,
    )

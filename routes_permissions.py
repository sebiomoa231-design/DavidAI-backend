"""Planning/permission endpoints (Section 11, 23)."""
from fastapi import APIRouter

from david.security.permissions import PermissionRequest, evaluate_permission

router = APIRouter(tags=["permissions"])


@router.post("/api/authorize")
async def authorize(payload: PermissionRequest):
    return evaluate_permission(payload)


@router.post("/api/plan")
async def plan(payload: dict):
    """
    Lightweight planning endpoint: given a goal, break it into a simple
    checklist. This is intentionally simple in v0.7 -- richer multi-step
    automation planning arrives in v1.4.
    """
    goal = payload.get("goal", "").strip()
    if not goal:
        return {"steps": []}
    return {
        "goal": goal,
        "steps": [
            f"Clarify the outcome of: {goal}",
            "Check memory/projects for related context",
            "Identify any sensitive actions requiring permission",
            "Execute using the best available provider/tool",
            "Record the outcome as a decision or learning entry",
        ],
    }

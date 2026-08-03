"""Router/provider status endpoints (Section 7, 23)."""
from fastapi import APIRouter

from david.router.ai_router import ai_router
from david.router.metrics import router_metrics

router = APIRouter(tags=["router"])


@router.get("/api/providers")
async def get_providers():
    return await ai_router.health_snapshot()


@router.get("/api/router/status")
async def router_status():
    return {
        "mode": ai_router.mode,
        "priority": ai_router.priority,
        "providers": await ai_router.health_snapshot(),
    }


@router.get("/api/router/metrics")
async def router_metrics_endpoint():
    return router_metrics.as_dict()

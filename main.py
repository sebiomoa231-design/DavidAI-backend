"""
David AI -- FastAPI application entrypoint.

Wires together every route group described in the master handoff
(Section 23 / 31) and mounts the minimal dashboard (Section 21).
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from david.api import (
    routes_auth,
    routes_core,
    routes_export,
    routes_learning,
    routes_memory,
    routes_permissions,
    routes_plugins,
    routes_projects,
    routes_providers,
    routes_research,
    routes_tasks,
    routes_uploads,
    routes_vision,
    routes_voice,
    routes_capabilities,
)
from david.config.settings import get_settings
from david.utils.logger import get_logger

settings = get_settings()
logger = get_logger("david.main")

DASHBOARD_DIR = Path(__file__).resolve().parent / "david" / "web" / "dashboard_static"


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"David AI starting up (env={settings.ENV})")
    yield
    logger.info("David AI shutting down")


app = FastAPI(
    title="David AI",
    description="David is the orchestrator, not the model. A modular personal AI platform.",
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.ENV == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Route groups (Section 31 API endpoint map) ---
app.include_router(routes_core.router)
app.include_router(routes_memory.router)
app.include_router(routes_projects.router)
app.include_router(routes_tasks.router)
app.include_router(routes_learning.router)
app.include_router(routes_permissions.router)
app.include_router(routes_auth.router)
app.include_router(routes_plugins.router)
app.include_router(routes_uploads.router)
app.include_router(routes_providers.router)
app.include_router(routes_research.router)
app.include_router(routes_voice.router)
app.include_router(routes_vision.router)
app.include_router(routes_export.router)
app.include_router(routes_capabilities.router)

# --- Minimal dashboard (Section 21) ---
app.mount("/dashboard", StaticFiles(directory=str(DASHBOARD_DIR), html=True), name="dashboard")


@app.get("/")
async def root():
    return {
        "message": "David AI is online.",
        "dashboard": "/dashboard",
        "docs": "/docs",
        "health": "/api/health",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=(settings.ENV == "development"))

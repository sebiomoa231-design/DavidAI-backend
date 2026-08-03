"""Research / web intelligence endpoints (Section 16, 23)."""
from fastapi import APIRouter

from david.web import research

router = APIRouter(prefix="/api/research", tags=["research"])


@router.get("/search")
async def search(q: str):
    return await research.web_search(q)


@router.get("/fetch")
async def fetch(url: str):
    return await research.fetch_url(url)

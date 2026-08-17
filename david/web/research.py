"""
Web intelligence / research engine (Section 16, v0.9).

Provides URL fetching + basic readability extraction so David can summarize
pages and cite sources. Uses httpx + BeautifulSoup; no headless browser.
Fails cleanly and never executes remote scripts.
"""
from typing import Optional

import httpx
from bs4 import BeautifulSoup

from david.utils.logger import get_logger

logger = get_logger("david.research")

_HEADERS = {"User-Agent": "DavidAI-Research/1.0 (+https://david.local)"}


async def fetch_url(url: str, timeout: float = 15.0) -> dict:
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True, headers=_HEADERS) as client:
            resp = await client.get(url)
            resp.raise_for_status()
    except Exception as e:
        logger.error(f"fetch_url failed for {url}: {e}")
        return {"success": False, "url": url, "error": str(e)}

    soup = BeautifulSoup(resp.text, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    title = soup.title.string.strip() if soup.title and soup.title.string else ""
    text = " ".join(soup.get_text(separator=" ").split())

    return {
        "success": True,
        "url": url,
        "title": title,
        "text": text[:20000],  # cap extracted text for sanity
        "length": len(text),
    }


async def web_search(query: str) -> dict:
    """
    Placeholder search interface. Wire this up to a real search API
    (e.g. Bing/SerpAPI/Brave Search) by setting a SEARCH_API_KEY in .env
    and implementing the request here -- kept provider-agnostic so any
    search backend can be dropped in without touching callers.
    """
    logger.info(f"web_search called (no search backend configured): {query}")
    return {
        "success": False,
        "query": query,
        "results": [],
        "error": "No search backend configured yet. Add a SEARCH_API_KEY and implement the request in david/web/research.py",
    }

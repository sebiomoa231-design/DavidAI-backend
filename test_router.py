import pytest

from david.router.ai_router import ai_router


@pytest.mark.asyncio
async def test_router_returns_graceful_error_with_no_keys():
    response = await ai_router.chat(messages=[{"role": "user", "content": "hello"}], use_cache=False)
    assert response.success in (True, False)
    assert isinstance(response.text, str)


def test_health_snapshot_shape():
    import asyncio
    snapshot = asyncio.run(ai_router.health_snapshot())
    assert "gemini" in snapshot
    assert "groq" in snapshot
    assert "huggingface" in snapshot
    assert "openrouter" in snapshot
    assert "cerebras" in snapshot
    assert "sambanova" in snapshot

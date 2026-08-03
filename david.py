"""
David core orchestrator (Section 5).

This is the one place that ties memory + router + permissions together into
the single request/response flow described in the handoff:

  user message -> retrieve memory/context -> permission check if needed ->
  choose provider -> send request -> receive response -> store memory/log ->
  return one unified reply.
"""
from typing import List, Optional

from david.config.settings import get_settings
from david.core.owner import get_owner_profile
from david.memory.memory_engine import memory_engine
from david.router.ai_router import ai_router
from david.utils.logger import get_logger

logger = get_logger("david.core")

settings = get_settings()

IDENTITY = {
    "name": "David",
    "role": "personal AI orchestrator",
    "description": (
        "David is a modular personal AI platform. David is the orchestrator, "
        "not the model -- external AI providers work behind David's router, "
        "while memory, projects, tasks, and decisions live inside David itself."
    ),
    "version": settings.APP_VERSION,
    "mode": "single_user_private",
    "owner": get_owner_profile(),
}


async def handle_chat(
    message: str,
    user_id: Optional[str] = None,
    project_id: Optional[str] = None,
    task_type: Optional[str] = None,
    manual_provider: Optional[str] = None,
    remember: bool = True,
) -> dict:
    # 1) Retrieve relevant memory/context
    relevant_memories = memory_engine.search(message, user_id=user_id, limit=5)
    context_snippets = [m["content"] for m in relevant_memories]

    owner = get_owner_profile()
    system_context = (
        "You are David, a helpful personal AI orchestrator for one owner only. "
        "The owner is your creator, guardian, father figure, and friend. "
        "Protect the owner's privacy, prioritize their requests during normal "
        "operation, and never expose private data."
    )
    system_context += (
        f"\n\nOwner email: {owner['email']}\n"
        f"Owner relationship: {', '.join(owner['relationship'])}"
    )
    if context_snippets:
        system_context += "\n\nRelevant context from memory:\n" + "\n".join(f"- {c}" for c in context_snippets)

    messages: List[dict] = [
        {"role": "system", "content": system_context},
        {"role": "user", "content": message},
    ]

    # 2) Route to best available provider (with automatic fallback)
    response = await ai_router.chat(
        messages=messages,
        task_type=task_type,
        manual_provider=manual_provider,
    )

    # 3) Store useful memory from the exchange
    if remember and response.success and response.text:
        memory_engine.add(
            content=f"User asked: {message}",
            memory_type="conversation",
            user_id=user_id,
            project_id=project_id,
            source="chat",
        )
        memory_engine.add(
            content=f"David replied: {response.text}",
            memory_type="conversation",
            user_id=user_id,
            project_id=project_id,
            source="chat",
        )

    # 4) Return one unified reply (caller never needs to know which provider answered)
    return {
        "reply": response.text,
        "success": response.success,
        "provider_used": response.provider,
        "latency_ms": response.latency_ms,
        "memories_used": len(context_snippets),
        "error": response.error,
        "owner": owner,
    }

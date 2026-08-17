"""Tool manager (Section 20) -- routes tool requests, enforces permissions,
logs execution, isolates tool failures."""
from typing import Any, Callable, Dict

from david.security.permissions import PermissionRequest, evaluate_permission, PermissionDecision
from david.utils.logger import get_logger

logger = get_logger("david.tools")

_registry: Dict[str, Callable[..., Any]] = {}


def register_tool(name: str, fn: Callable[..., Any], category: str = "general") -> None:
    _registry[name] = {"fn": fn, "category": category}


def list_tools() -> list:
    return [{"name": name, "category": meta["category"]} for name, meta in _registry.items()]


def run_tool(name: str, confirmed: bool = False, **kwargs) -> dict:
    if name not in _registry:
        return {"success": False, "error": f"Tool '{name}' not found"}

    meta = _registry[name]
    permission = evaluate_permission(
        PermissionRequest(action=name, category=meta["category"], confirmed=confirmed)
    )

    if permission.decision == PermissionDecision.DENY:
        return {"success": False, "error": "Denied", "reason": permission.reason}
    if permission.decision == PermissionDecision.ASK:
        return {"success": False, "needs_confirmation": True, "reason": permission.reason}

    try:
        result = meta["fn"](**kwargs)
        return {"success": True, "result": result}
    except Exception as e:
        logger.error(f"tool '{name}' failed: {e}")
        return {"success": False, "error": str(e)}

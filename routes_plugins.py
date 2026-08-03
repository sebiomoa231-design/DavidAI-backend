"""Plugin endpoints (Section 19, 23)."""
from fastapi import APIRouter, Depends, HTTPException

from david.plugins.plugin_manager import list_plugins, run_plugin
from david.security.auth import get_current_user
from david.security.workspace import scope_user_id

router = APIRouter(prefix="/api/plugins", tags=["plugins"])


@router.get("")
async def get_plugins(current_user: dict = Depends(get_current_user)):
    return {"plugins": list_plugins(), "owner": current_user["email"]}


@router.post("/{plugin_name}/run")
async def run_plugin_endpoint(plugin_name: str, payload: dict = None, current_user: dict = Depends(get_current_user)):
    data = dict(payload or {})
    data["user_id"] = scope_user_id(current_user, data.get("user_id"))
    return run_plugin(plugin_name, **data)

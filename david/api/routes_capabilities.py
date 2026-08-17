from fastapi import APIRouter, Depends

from david.capabilities.registry import list_capabilities
from david.security.auth import get_current_user_optional
from david.core.owner import get_owner_profile

router = APIRouter(prefix="/api/capabilities", tags=["capabilities"])


@router.get("")
async def capabilities(current_user: dict | None = Depends(get_current_user_optional)):
    return {
        "owner": get_owner_profile(),
        "private_mode": True,
        "capabilities": list_capabilities(),
        "authenticated": current_user is not None,
    }

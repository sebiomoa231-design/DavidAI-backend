from __future__ import annotations

from david.config.settings import get_settings

def get_owner_profile() -> dict:
    settings = get_settings()
    return {
        "email": settings.OWNER_EMAIL.lower(),
        "display_name": settings.OWNER_DISPLAY_NAME,
        "relationship": settings.OWNER_RELATIONSHIP.split(", "),
        "mode": "single_user_private",
        "privacy": "private_workspace",
    }

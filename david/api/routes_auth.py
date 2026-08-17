"""Auth endpoints (single-user owner-only mode)."""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, field_validator

from david.config.settings import get_settings
from david.security.auth import (
    authenticate_user,
    create_access_token,
    get_current_user,
    register_user,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    password: str
    display_name: str = ""

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v


class LoginRequest(BaseModel):
    email: str
    password: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        v = v.strip().lower()
        if "@" not in v or "." not in v.split("@")[-1]:
            raise ValueError("Invalid email address")
        return v


@router.post("/register")
async def register(payload: RegisterRequest):
    settings = get_settings()
    if payload.email.strip().lower() != settings.OWNER_EMAIL.lower():
        raise HTTPException(
            status_code=403,
            detail="This David AI instance is private. Only the owner may register or sign in.",
        )
    user = register_user(payload.email, payload.password, payload.display_name)
    token = create_access_token(user["id"], user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"],
            "role": user.get("role", "owner"),
            "private_workspace": True,
        },
        "owner": {
            "email": settings.OWNER_EMAIL.lower(),
            "display_name": settings.OWNER_DISPLAY_NAME,
            "relationship": settings.OWNER_RELATIONSHIP,
        },
    }


@router.post("/login")
async def login(payload: LoginRequest):
    settings = get_settings()
    if payload.email.strip().lower() != settings.OWNER_EMAIL.lower():
        raise HTTPException(
            status_code=403,
            detail="This David AI instance is private. Only the owner may access it.",
        )
    user = authenticate_user(payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = create_access_token(user["id"], user["email"])
    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "email": user["email"],
            "display_name": user["display_name"],
            "role": user.get("role", "owner"),
            "private_workspace": True,
        },
        "owner": {
            "email": settings.OWNER_EMAIL.lower(),
            "display_name": settings.OWNER_DISPLAY_NAME,
            "relationship": settings.OWNER_RELATIONSHIP,
        },
    }


@router.get("/me")
async def me(current_user: dict = Depends(get_current_user)):
    settings = get_settings()
    current_user["owner"] = {
        "email": settings.OWNER_EMAIL.lower(),
        "display_name": settings.OWNER_DISPLAY_NAME,
        "relationship": settings.OWNER_RELATIONSHIP,
    }
    return current_user

"""Authentication: single-user owner-only registration/login, password hashing,
and bearer tokens. Passwords are hashed with PBKDF2-HMAC-SHA256 (stdlib only).
Tokens are signed JWTs. Nothing secret is ever logged.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from david.config.settings import get_settings
from david.database.json_store import JSONStore
from david.utils.helpers import new_id, now_iso
from david.utils.logger import get_logger

logger = get_logger("david.auth")
bearer_scheme = HTTPBearer(auto_error=False)
users_store = JSONStore("users")

_PBKDF2_ITERATIONS = 120_000
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _encode_hash(algorithm: str, iterations: int, salt: bytes, dk: bytes) -> str:
    return "$".join(
        [
            algorithm,
            str(iterations),
            base64.urlsafe_b64encode(salt).decode("ascii"),
            base64.urlsafe_b64encode(dk).decode("ascii"),
        ]
    )


def _decode_hash(encoded: str) -> tuple[str, int, bytes, bytes]:
    algorithm, iterations_s, salt_b64, dk_b64 = encoded.split("$", 3)
    return (
        algorithm,
        int(iterations_s),
        base64.urlsafe_b64decode(salt_b64.encode("ascii")),
        base64.urlsafe_b64decode(dk_b64.encode("ascii")),
    )


def _owner_email() -> str:
    return get_settings().OWNER_EMAIL.lower().strip()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return _encode_hash("pbkdf2_sha256", _PBKDF2_ITERATIONS, salt, dk)


def verify_password(password: str, hashed: str) -> bool:
    try:
        algorithm, iterations, salt, stored_dk = _decode_hash(hashed)
    except Exception:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    calc = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(calc, stored_dk)


def _validate_email(email: str) -> str:
    email = email.strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Invalid email address")
    return email


def _ensure_owner_email(email: str) -> str:
    email = _validate_email(email)
    owner = _owner_email()
    if email != owner:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This David AI instance is private. Only the owner may access it.",
        )
    return email


def create_access_token(user_id: str, email: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": user_id, "email": email, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        logger.info("token expired")
        return None
    except jwt.InvalidTokenError:
        logger.info("invalid token presented")
        return None


def register_user(email: str, password: str, display_name: str = "") -> dict:
    email = _ensure_owner_email(email)
    existing = users_store.find(lambda u: u.get("email") == email)
    if existing:
        user = existing[0]
        if verify_password(password, user["hashed_password"]):
            return user
        raise HTTPException(status_code=409, detail="Owner account already exists. Use the owner password.")

    user = {
        "id": new_id("user"),
        "email": email,
        "hashed_password": hash_password(password),
        "display_name": display_name or get_settings().OWNER_DISPLAY_NAME,
        "created_at": now_iso(),
        "role": "owner",
        "private_workspace": True,
    }
    users_store.add(user)
    logger.info(f"registered owner account: {user['id']}")
    return user


def authenticate_user(email: str, password: str) -> Optional[dict]:
    email = _ensure_owner_email(email)
    matches = users_store.find(lambda u: u.get("email") == email)
    if not matches:
        return None
    user = matches[0]
    if not verify_password(password, user["hashed_password"]):
        return None
    return user


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing bearer token")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user = users_store.get(payload.get("sub"))
    if user is None:
        raise HTTPException(status_code=401, detail="User no longer exists")

    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user.get("display_name"),
        "role": user.get("role", "owner"),
        "private_workspace": True,
    }


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[dict]:
    if credentials is None:
        return None
    payload = decode_access_token(credentials.credentials)
    if payload is None:
        return None
    user = users_store.get(payload.get("sub"))
    if user is None:
        return None
    return {
        "id": user["id"],
        "email": user["email"],
        "display_name": user.get("display_name"),
        "role": user.get("role", "owner"),
        "private_workspace": True,
    }

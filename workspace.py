
"""Workspace ownership helpers for David.

These helpers keep each logged-in user's workspace private by ensuring that
records are filtered by owner and that one user cannot access another user's
data.
"""
from __future__ import annotations

from fastapi import HTTPException


def effective_user_id(user: dict | None) -> str | None:
    return user["id"] if user else None


def is_owned_by(record: dict, user: dict | None) -> bool:
    owner_id = record.get("user_id")
    current_user_id = effective_user_id(user)
    if current_user_id is None:
        return owner_id in (None, "")
    return owner_id == current_user_id


def ensure_owner(record: dict, user: dict | None, resource_name: str = "resource") -> None:
    if not is_owned_by(record, user):
        raise HTTPException(status_code=403, detail=f"You do not have access to this {resource_name}")


def scope_records(records: list[dict], user: dict | None) -> list[dict]:
    current_user_id = effective_user_id(user)
    if current_user_id is None:
        return records
    return [r for r in records if r.get("user_id") == current_user_id]


def scope_user_id(user: dict | None, requested_user_id: str | None = None) -> str | None:
    current_user_id = effective_user_id(user)
    return current_user_id if current_user_id is not None else requested_user_id

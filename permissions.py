"""
Permission / authorization engine (Section 11).

Sensitive action categories require explicit confirmation before David
executes them. This module answers: allow | ask | deny.
"""
from enum import Enum
from typing import Optional

from pydantic import BaseModel

from david.utils.logger import get_logger

logger = get_logger("david.permissions")


class PermissionDecision(str, Enum):
    ALLOW = "allow"
    ASK = "ask"
    DENY = "deny"


# Categories that always require confirmation before execution.
SENSITIVE_CATEGORIES = {
    "delete",
    "purchase",
    "send",
    "publish",
    "account_change",
    "security_change",
    "external_action",
    "financial_action",
    "credential_action",
}

# Categories that are always blocked outright in this build.
BLOCKED_CATEGORIES: set[str] = set()


class PermissionRequest(BaseModel):
    action: str
    category: str
    confirmed: bool = False
    details: Optional[str] = None


class PermissionResult(BaseModel):
    decision: PermissionDecision
    reason: str


def evaluate_permission(request: PermissionRequest) -> PermissionResult:
    category = request.category.strip().lower()

    if category in BLOCKED_CATEGORIES:
        return PermissionResult(decision=PermissionDecision.DENY, reason="Category is blocked")

    if category in SENSITIVE_CATEGORIES and not request.confirmed:
        return PermissionResult(
            decision=PermissionDecision.ASK,
            reason=f"'{category}' actions require explicit confirmation before David executes them.",
        )

    return PermissionResult(decision=PermissionDecision.ALLOW, reason="Action is not sensitive, or was confirmed")

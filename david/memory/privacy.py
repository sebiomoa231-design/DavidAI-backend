"""Privacy controls for durable memory and model context.

Secrets are rejected rather than stored. Memory text is always framed as
untrusted data before it reaches an AI provider; it can never add instructions
or system messages to the provider request.
"""
import re
from dataclasses import dataclass
from typing import Optional

SECRET_PATTERNS = (
    re.compile(r"(?i)\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"(?i)\b(?:api[_ -]?key|access[_ -]?token|refresh[_ -]?token|password|passwd|secret)\s*[:=]\s*[^\s]+"),
    re.compile(r"(?i)\b(?:ghp|github_pat|xoxb|xoxp|AIza)[A-Za-z0-9_-]{12,}\b"),
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)\b(?:postgres|postgresql|mysql)://[^\s]+:[^\s]+@"),
)

INJECTION_PATTERNS = (
    re.compile(r"(?i)ignore\s+(?:all\s+)?previous instructions"),
    re.compile(r"(?i)system\s+message\s*:"),
    re.compile(r"(?i)developer\s+message\s*:"),
    re.compile(r"(?i)you\s+are\s+now\s+(?:a|an)\s+"),
    re.compile(r"(?i)reveal\s+(?:the|your)\s+(?:system|developer|hidden)\s+prompt"),
)

@dataclass(frozen=True)
class PrivacyAssessment:
    allowed: bool
    reason: Optional[str] = None
    contains_secret: bool = False
    contains_injection: bool = False


def assess_memory_text(content: str) -> PrivacyAssessment:
    text = content or ""
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        return PrivacyAssessment(False, "sensitive credential material is not eligible for memory", True, False)
    injection = any(pattern.search(text) for pattern in INJECTION_PATTERNS)
    if injection:
        return PrivacyAssessment(True, "instruction-like text will be stored only as untrusted data", False, True)
    return PrivacyAssessment(True)


def redact_for_provider(content: str) -> str:
    """Return a safe, explicitly untrusted representation for model context."""
    assessment = assess_memory_text(content)
    if assessment.contains_secret:
        return "[PRIVATE MEMORY REDACTED]"
    return content.replace("\x00", "").strip()


def is_explicit_memory_command(text: str) -> bool:
    return bool(re.search(r"(?i)\b(?:remember|save|don't forget|do not forget)\b", text or ""))


def is_forget_command(text: str) -> bool:
    return bool(re.search(r"(?i)\b(?:forget|delete|remove|don't remember|do not remember)\b", text or ""))

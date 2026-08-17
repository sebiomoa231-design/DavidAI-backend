"""
Centralized logging for David AI.
Never logs secrets (API keys, passwords, tokens).
"""
import logging
import sys
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_DIR.mkdir(exist_ok=True)

REDACT_KEYS = {"api_key", "apikey", "password", "token", "secret", "authorization"}


def _redact(msg: str) -> str:
    lowered = msg.lower()
    for key in REDACT_KEYS:
        if key in lowered:
            return "[REDACTED LOG - possible secret content suppressed]"
    return msg


class RedactingFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = _redact(str(record.msg))
        return True


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)

    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
    )

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(RedactingFilter())

    file_handler = logging.FileHandler(LOG_DIR / "david.log")
    file_handler.setFormatter(formatter)
    file_handler.addFilter(RedactingFilter())

    logger.addHandler(stream_handler)
    logger.addHandler(file_handler)

    return logger

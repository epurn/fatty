"""Structured logging configured to never emit secrets or personal data.

Logs are emitted as single-line JSON so they are machine-parseable, and a
redaction filter scrubs any log record field whose name looks sensitive (tokens,
secrets, keys, passwords, authorization headers, cookies). This redaction posture
is a security-sensitive convention later stories inherit: prefer request/event
IDs over personal values, and never attach raw prompts, provider keys, or food
history to log records.
"""

from __future__ import annotations

import json
import logging
import re
import sys
from typing import Any

#: Placeholder substituted for the value of any sensitive log field.
REDACTED = "[REDACTED]"

#: Field names matching this pattern are redacted before formatting.
_SENSITIVE_KEY = re.compile(
    r"(secret|token|password|passwd|api[_-]?key|access[_-]?key|authorization|auth|cookie|key)",
    re.IGNORECASE,
)

#: Standard ``LogRecord`` attributes that are never treated as extra fields.
_RESERVED = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class RedactionFilter(logging.Filter):
    """Redact sensitive ``extra`` fields in place before they are formatted."""

    def filter(self, record: logging.LogRecord) -> bool:
        for key in list(record.__dict__):
            if key in _RESERVED:
                continue
            if _SENSITIVE_KEY.search(key):
                record.__dict__[key] = REDACTED
        return True


class JsonFormatter(logging.Formatter):
    """Render a log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for key, value in record.__dict__.items():
            if key in _RESERVED or key.startswith("_"):
                continue
            payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging(level: str) -> None:
    """Install the JSON formatter and redaction filter on the root logger."""

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RedactionFilter())

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

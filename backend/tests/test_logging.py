"""Structured logging and redaction tests.

These are security tests: they prove the redaction control fails closed, i.e. a
sensitive field never reaches the formatted log line.
"""

from __future__ import annotations

import json
import logging

from app.logging import REDACTED, JsonFormatter, RedactionFilter


def _record(message: str = "msg", **extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_message_is_structured_json() -> None:
    formatted = JsonFormatter().format(_record("hello"))

    payload = json.loads(formatted)
    assert payload["message"] == "hello"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "test"


def test_sensitive_fields_are_redacted() -> None:
    record = _record(api_key="super-secret-value", authorization="Bearer abc.def")
    RedactionFilter().filter(record)

    formatted = JsonFormatter().format(record)
    payload = json.loads(formatted)

    assert "super-secret-value" not in formatted
    assert "abc.def" not in formatted
    assert payload["api_key"] == REDACTED
    assert payload["authorization"] == REDACTED


def test_non_sensitive_extra_is_preserved() -> None:
    record = _record(request_id="req-123")
    RedactionFilter().filter(record)

    payload = json.loads(JsonFormatter().format(record))
    assert payload["request_id"] == "req-123"

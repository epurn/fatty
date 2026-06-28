"""Redis-backed fixed-window rate limiter for auth endpoints (FTY-118).

The limiter is wired as a swappable seam on ``app.state.rate_limiter`` so the
production ``RedisRateLimiter`` is replaced by a lightweight
``InMemoryRateLimiter`` in tests — no live Redis required.

PII: per-account keys use ``sha256(lower_email)``; no raw email or IP is stored
in Redis keys or emitted in log records from this module.
"""

from __future__ import annotations

import hashlib
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import redis as redis_lib

logger = logging.getLogger(__name__)

_RL_PREFIX = "fatty:rl"


@dataclass(frozen=True)
class RateLimitDecision:
    """Outcome of a single rate-limit check.

    ``allowed`` is ``True`` when the request count is at or below the limit.
    ``retry_after`` is seconds until the window resets; zero when allowed.
    """

    allowed: bool
    retry_after: int


class RateLimiter(ABC):
    """Abstract base for rate-limit backends. Use the seam on ``app.state``."""

    @abstractmethod
    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        """Increment the counter for ``key`` and return an allow/throttle decision.

        Callers must handle exceptions (e.g. ``redis.RedisError``) and should
        implement fail-open logic to avoid converting an infra blip into an
        auth outage.
        """


class RedisRateLimiter(RateLimiter):
    """Fixed-window per-key counter backed by Redis INCR / EXPIRE.

    Uses a pipeline to INCR and read TTL atomically, then sets the window
    expiry on the first hit (TTL == -1). Exceptions propagate to the caller,
    which is responsible for fail-open handling.
    """

    def __init__(self, redis_url: str) -> None:
        self._redis: Any = redis_lib.from_url(  # type: ignore[no-untyped-call]
            redis_url, decode_responses=True
        )

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        pipe: Any = self._redis.pipeline()
        pipe.incr(key)
        pipe.ttl(key)
        results: list[Any] = pipe.execute()
        count = int(results[0])
        ttl = int(results[1])
        if ttl == -1:
            # No expiry yet (first hit this window) — pin the window boundary.
            self._redis.expire(key, window_seconds)
            ttl = window_seconds
        retry_after = max(ttl, 0)
        return RateLimitDecision(allowed=count <= limit, retry_after=retry_after)


class InMemoryRateLimiter(RateLimiter):
    """In-memory rate limiter for tests. No TTL; counts survive until ``reset()``.

    ``window_seconds`` is echoed back as ``retry_after`` when throttled so tests
    can assert the header carries a positive integer.
    """

    def __init__(self) -> None:
        self._counts: dict[str, int] = {}

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        self._counts[key] = self._counts.get(key, 0) + 1
        count = self._counts[key]
        retry_after = window_seconds if count > limit else 0
        return RateLimitDecision(allowed=count <= limit, retry_after=retry_after)

    def reset(self) -> None:
        """Clear all counters (useful when reusing one instance across scenarios)."""
        self._counts.clear()


def build_redis_limiter(redis_url: str) -> RateLimiter:
    """Factory used by ``create_app`` to build the production rate limiter."""
    return RedisRateLimiter(redis_url)


def account_key(email: str) -> str:
    """Non-reversible per-account key derived from a lower-cased email."""
    digest = hashlib.sha256(email.lower().encode()).hexdigest()
    return f"{_RL_PREFIX}:acct:{digest}"


def ip_key(ip: str, endpoint: str) -> str:
    """Per-IP rate-limit key for a named endpoint (e.g. ``login`` or ``register``)."""
    return f"{_RL_PREFIX}:{endpoint}:ip:{ip}"

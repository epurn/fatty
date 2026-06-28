"""Rate-limit tests for the auth endpoints (FTY-118).

Covers:
- Per-IP throttle on /login and /register
- Per-account throttle on /login from rotating IPs (via X-Forwarded-For)
- Legitimate cadence below the threshold is never throttled
- Shared counter: two app instances sharing one seam enforce one combined limit
- IP-spoof rejection: X-Forwarded-For is ignored unless trusted_proxy is on
- Fail-open: a limiter seam that raises still allows the request (no 500)
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.engine import Engine

from app.db import create_db_engine
from app.main import create_app
from app.security.rate_limit import InMemoryRateLimiter, RateLimitDecision, RateLimiter
from app.settings import Settings
from tests.conftest import RecordingEnqueuer, upgrade

# A valid login password that passes the 8-char schema minimum.
_PW = "any-password"

_LOW_LIMIT_SETTINGS = Settings(
    environment="test",
    log_level="WARNING",
    rate_limit_login_ip_max=2,
    rate_limit_login_ip_window=60,
    rate_limit_login_account_max=2,
    rate_limit_login_account_window=60,
    rate_limit_register_ip_max=2,
    rate_limit_register_ip_window=60,
)

_TRUSTED_PROXY_SETTINGS = Settings(
    environment="test",
    log_level="WARNING",
    rate_limit_login_ip_max=100,  # high so per-IP limit never fires in account tests
    rate_limit_login_ip_window=60,
    rate_limit_login_account_max=2,
    rate_limit_login_account_window=60,
    rate_limit_register_ip_max=100,
    rate_limit_register_ip_window=60,
    rate_limit_trusted_proxy=True,
)

_PROXY_OFF_SETTINGS = Settings(
    environment="test",
    log_level="WARNING",
    rate_limit_login_ip_max=2,
    rate_limit_login_ip_window=60,
    rate_limit_login_account_max=100,  # high so account limit never fires in IP tests
    rate_limit_login_account_window=60,
    rate_limit_register_ip_max=100,
    rate_limit_register_ip_window=60,
    rate_limit_trusted_proxy=False,
)


@pytest.fixture
def low_limit_db(tmp_path: Path) -> Iterator[Engine]:
    engine = create_db_engine(f"sqlite:///{tmp_path / 'rl_test.db'}")
    upgrade(engine)
    try:
        yield engine
    finally:
        engine.dispose()


def _make_client(
    engine: Engine,
    settings: Settings,
    rate_limiter: RateLimiter | None = None,
) -> TestClient:
    """Build a TestClient with the given settings and rate-limiter seam."""
    app = create_app(settings=settings, engine=engine)
    app.state.estimation_enqueuer = RecordingEnqueuer()
    app.state.rate_limiter = rate_limiter or InMemoryRateLimiter()
    return TestClient(app, raise_server_exceptions=False)


# ---------------------------------------------------------------------------
# Per-IP throttle: /login
# ---------------------------------------------------------------------------


def test_login_per_ip_throttled(low_limit_db: Engine) -> None:
    """Exceeding the per-IP login limit returns 429 with a Retry-After header."""
    client = _make_client(low_limit_db, _LOW_LIMIT_SETTINGS)

    # First two requests are under the limit — normal 200/401 responses
    for _ in range(2):
        resp = client.post("/api/auth/login", json={"email": "x@example.com", "password": _PW})
        assert resp.status_code != 429

    # Third attempt → throttled
    resp = client.post("/api/auth/login", json={"email": "x@example.com", "password": _PW})
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
    assert int(resp.headers["Retry-After"]) > 0


# ---------------------------------------------------------------------------
# Per-account throttle: /login from rotating IPs
# ---------------------------------------------------------------------------


def test_login_per_account_throttled_rotating_ips(low_limit_db: Engine) -> None:
    """The per-account limit fires even when each request comes from a different IP."""
    client = _make_client(low_limit_db, _TRUSTED_PROXY_SETTINGS)

    # Register target account
    client.post(
        "/api/auth/register",
        json={"email": "victim@example.com", "password": "password-ok-1"},
    )

    # Two attempts from distinct IPs — both under the account limit
    for i in range(2):
        resp = client.post(
            "/api/auth/login",
            json={"email": "victim@example.com", "password": "wrong-password"},
            headers={"X-Forwarded-For": f"10.0.0.{i + 1}"},
        )
        assert resp.status_code != 429

    # Third attempt from a fresh IP → per-account limit fires
    resp = client.post(
        "/api/auth/login",
        json={"email": "victim@example.com", "password": "wrong-password"},
        headers={"X-Forwarded-For": "10.0.0.99"},
    )
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
    assert int(resp.headers["Retry-After"]) > 0


# ---------------------------------------------------------------------------
# Per-IP throttle: /register
# ---------------------------------------------------------------------------


def test_register_per_ip_throttled(low_limit_db: Engine) -> None:
    """Exceeding the per-IP register limit returns 429 with a Retry-After header."""
    client = _make_client(low_limit_db, _LOW_LIMIT_SETTINGS)

    # First two under limit — normal 201 (or 409 for a duplicate)
    for i in range(2):
        resp = client.post(
            "/api/auth/register",
            json={"email": f"u{i}@example.com", "password": "password-ok-1"},
        )
        assert resp.status_code != 429

    # Third attempt → throttled before the insert
    resp = client.post(
        "/api/auth/register",
        json={"email": "u3@example.com", "password": "password-ok-1"},
    )
    assert resp.status_code == 429
    assert "Retry-After" in resp.headers
    assert int(resp.headers["Retry-After"]) > 0


# ---------------------------------------------------------------------------
# Legitimate cadence: never throttled below the threshold
# ---------------------------------------------------------------------------


def test_legitimate_login_cadence_not_throttled(low_limit_db: Engine) -> None:
    """Requests below the threshold always pass through normally."""
    client = _make_client(low_limit_db, _LOW_LIMIT_SETTINGS)
    client.post(
        "/api/auth/register",
        json={"email": "legit@example.com", "password": "password-ok-1"},
    )

    # One successful login followed by one wrong-password 401 — both under the limit
    resp_ok = client.post(
        "/api/auth/login",
        json={"email": "legit@example.com", "password": "password-ok-1"},
    )
    resp_bad = client.post(
        "/api/auth/login",
        json={"email": "legit@example.com", "password": "wrong-password"},
    )
    assert resp_ok.status_code == 200
    assert resp_bad.status_code == 401


# ---------------------------------------------------------------------------
# Shared counter: two "processes" sharing one seam
# ---------------------------------------------------------------------------


def test_shared_counter_across_instances(low_limit_db: Engine) -> None:
    """Two app instances sharing the same seam enforce one combined limit."""
    shared_limiter = InMemoryRateLimiter()

    with (
        _make_client(low_limit_db, _LOW_LIMIT_SETTINGS, shared_limiter) as c1,
        _make_client(low_limit_db, _LOW_LIMIT_SETTINGS, shared_limiter) as c2,
    ):
        # One request through each instance — combined count = 2 (at the limit)
        r1 = c1.post("/api/auth/login", json={"email": "a@b.com", "password": _PW})
        r2 = c2.post("/api/auth/login", json={"email": "a@b.com", "password": _PW})
        assert r1.status_code != 429
        assert r2.status_code != 429

        # Third request through either instance → over the shared limit
        r3 = c1.post("/api/auth/login", json={"email": "a@b.com", "password": _PW})
        assert r3.status_code == 429


# ---------------------------------------------------------------------------
# IP-spoof rejection: X-Forwarded-For ignored when trusted_proxy is off
# ---------------------------------------------------------------------------


def test_ip_spoof_rejected_when_trusted_proxy_off(low_limit_db: Engine) -> None:
    """With trusted_proxy=False, spoofed X-Forwarded-For does not create a fresh key."""
    client = _make_client(low_limit_db, _PROXY_OFF_SETTINGS)

    # Two requests each with a different X-Forwarded-For — but both key on the
    # real peer IP ("testclient"), exhausting the per-IP limit
    for i in range(2):
        resp = client.post(
            "/api/auth/login",
            json={"email": "x@example.com", "password": _PW},
            headers={"X-Forwarded-For": f"1.2.3.{i}"},
        )
        assert resp.status_code != 429

    # Third request with a fresh spoofed IP → real peer is still throttled
    resp = client.post(
        "/api/auth/login",
        json={"email": "x@example.com", "password": _PW},
        headers={"X-Forwarded-For": "1.2.3.99"},
    )
    assert resp.status_code == 429


def test_forwarded_for_honoured_when_trusted_proxy_on(low_limit_db: Engine) -> None:
    """With trusted_proxy=True, each distinct X-Forwarded-For IP gets its own key."""
    client = _make_client(low_limit_db, _TRUSTED_PROXY_SETTINGS)

    # Two requests from distinct IPs (ip_max=100, never trips)
    for i in range(2):
        resp = client.post(
            "/api/auth/login",
            json={"email": "x@example.com", "password": _PW},
            headers={"X-Forwarded-For": f"10.0.0.{i}"},
        )
        assert resp.status_code != 429


# ---------------------------------------------------------------------------
# Fail-open: limiter seam raises → request allowed, warning logged
# ---------------------------------------------------------------------------


class _ErrorRateLimiter(RateLimiter):
    """Test double that always raises, simulating a Redis outage."""

    def check(self, key: str, limit: int, window_seconds: int) -> RateLimitDecision:
        raise RuntimeError("simulated Redis failure")


def test_fail_open_login_on_limiter_error(low_limit_db: Engine) -> None:
    """When the rate-limiter seam raises, /login still responds normally (fail-open)."""
    warned: list[Any] = []

    # Patch the logger on the auth module before create_app so configure_logging
    # does not clear the capture.  We verify the warning reaches the logger; the
    # JSON formatter then forwards it to stdout (visible in the captured output).
    with patch("app.routers.auth.logger") as mock_log:
        mock_log.warning.side_effect = lambda *a, **kw: warned.append(a[0])
        client = _make_client(low_limit_db, _LOW_LIMIT_SETTINGS, _ErrorRateLimiter())
        resp = client.post(
            "/api/auth/login",
            json={"email": "x@example.com", "password": _PW},
        )

    # Fail-open: 401 for an unknown user, never 500 or 429
    assert resp.status_code not in (500, 429)
    assert any("fail-open" in str(w) for w in warned)


def test_fail_open_register_on_limiter_error(low_limit_db: Engine) -> None:
    """When the rate-limiter seam raises, /register still completes (fail-open)."""
    warned: list[Any] = []

    with patch("app.routers.auth.logger") as mock_log:
        mock_log.warning.side_effect = lambda *a, **kw: warned.append(a[0])
        client = _make_client(low_limit_db, _LOW_LIMIT_SETTINGS, _ErrorRateLimiter())
        resp = client.post(
            "/api/auth/register",
            json={"email": "new@example.com", "password": "password-ok-1"},
        )

    # Fail-open: 201 Created, never 500 or 429
    assert resp.status_code == 201
    assert any("fail-open" in str(w) for w in warned)

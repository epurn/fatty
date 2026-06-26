"""Health service.

Trivial today, but routes delegate here from the outset so the route layer stays
a thin HTTP boundary as real readiness checks (database, queue) are added later.
"""

from __future__ import annotations

from app.schemas.health import HealthStatus


def check_health() -> HealthStatus:
    """Return the current service health status."""

    return HealthStatus(status="ok")

"""Health check route."""

from __future__ import annotations

from fastapi import APIRouter

from app.schemas.health import HealthStatus
from app.services import health as health_service

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthStatus)
def healthz() -> HealthStatus:
    """Liveness probe: returns HTTP 200 with a typed status body."""

    return health_service.check_health()

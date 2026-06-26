"""Health endpoint boundary models."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class HealthStatus(BaseModel):
    """Response body for ``GET /healthz``.

    The shape (``{"status": "ok"}``) and path are a contract relied on by infra
    healthchecks (FTY-011) and later stories; changes here are contract changes.
    """

    status: Literal["ok"] = "ok"

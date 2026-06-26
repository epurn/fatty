"""FastAPI application factory.

``create_app`` validates settings, configures structured logging, and wires the
routers. Importing ``app`` builds the application from the process environment.
"""

from __future__ import annotations

import logging

from fastapi import FastAPI

from app.logging import configure_logging
from app.routers import health
from app.settings import Settings, load_settings

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application.

    Settings are validated here (or passed in by tests); invalid environment
    configuration raises ``ValidationError`` before the app starts serving.
    """

    settings = settings or load_settings()
    configure_logging(settings.log_level)

    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.include_router(health.router)

    # No secrets/personal data here: only the non-sensitive environment label.
    logger.info("backend application initialized", extra={"environment": settings.environment})
    return app


app = create_app()

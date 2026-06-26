"""Run the backend with uvicorn: ``python -m app``."""

from __future__ import annotations

import uvicorn

from app.settings import load_settings


def main() -> None:
    settings = load_settings()
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, log_config=None)


if __name__ == "__main__":
    main()

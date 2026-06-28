"""Regression tests for Alembic database-URL resolution (FTY-085).

The compose ``migrate`` service runs ``alembic upgrade head`` against the shipped
default DSN, a bare ``postgresql://`` URL. SQLAlchemy would default that scheme to
the psycopg2 dialect, which this project does not ship (it standardizes on
``psycopg[binary]`` v3), so first boot used to die with ``ModuleNotFoundError: No
module named 'psycopg2'``. ``alembic/env.py`` must resolve the URL through the
same :func:`app.db._normalize_url` the application runtime uses so the migration
path binds the installed psycopg v3 driver.

These tests drive the *real* ``env.py`` through Alembic's command machinery (so a
future edit that drops the normalization is caught) and assert the URL handed to
both the offline and online migration paths selects ``postgresql+psycopg`` for a
bare ``postgresql://`` input while leaving SQLite untouched.
"""

from __future__ import annotations

import pytest
import sqlalchemy

from alembic import command, context
from app import settings as settings_module
from app.settings import Settings
from tests.conftest import alembic_config

_BARE_POSTGRES_URL = "postgresql://fatty:fatty@db:5432/fatty"
_QUALIFIED_POSTGRES_URL = "postgresql+psycopg://fatty:fatty@db:5432/fatty"
_SQLITE_URL = "sqlite:///./untouched.db"


class _StopMigration(Exception):
    """Sentinel raised once the resolved URL is captured to abort the run early."""


def _force_settings(monkeypatch: pytest.MonkeyPatch, database_url: str) -> None:
    """Make ``env.py``'s ``load_settings()`` return ``database_url``.

    ``env.py`` does ``from app.settings import load_settings`` on every fresh exec,
    so patching the attribute on :mod:`app.settings` is picked up by the next
    Alembic command without touching real environment variables.
    """

    def _fake_load_settings(*_args: object, **_kwargs: object) -> Settings:
        return Settings(environment="test", database_url=database_url)

    monkeypatch.setattr(settings_module, "load_settings", _fake_load_settings)


def _capture_offline_url(monkeypatch: pytest.MonkeyPatch, database_url: str) -> str:
    """Resolve ``database_url`` through the real offline migration path."""

    _force_settings(monkeypatch, database_url)
    captured: dict[str, str] = {}

    def _record_configure(**kwargs: object) -> None:
        captured["url"] = str(kwargs["url"])
        raise _StopMigration

    monkeypatch.setattr(context, "configure", _record_configure)

    cfg = alembic_config()
    with pytest.raises(_StopMigration):
        command.upgrade(cfg, "head", sql=True)
    return captured["url"]


def _capture_online_url(monkeypatch: pytest.MonkeyPatch, database_url: str) -> str:
    """Resolve ``database_url`` through the real online (engine) migration path."""

    _force_settings(monkeypatch, database_url)
    captured: dict[str, str] = {}

    def _record_engine(configuration: dict[str, str], *_args: object, **_kwargs: object) -> object:
        captured["url"] = configuration["sqlalchemy.url"]
        raise _StopMigration

    monkeypatch.setattr(sqlalchemy, "engine_from_config", _record_engine)

    cfg = alembic_config()
    with pytest.raises(_StopMigration):
        command.upgrade(cfg, "head")
    return captured["url"]


def test_offline_resolver_binds_psycopg_v3(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _capture_offline_url(monkeypatch, _BARE_POSTGRES_URL) == _QUALIFIED_POSTGRES_URL


def test_online_resolver_binds_psycopg_v3(monkeypatch: pytest.MonkeyPatch) -> None:
    assert _capture_online_url(monkeypatch, _BARE_POSTGRES_URL) == _QUALIFIED_POSTGRES_URL


def test_resolver_leaves_qualified_postgres_url_unchanged(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Idempotent: an already-qualified psycopg v3 URL must not be double-rewritten.
    assert _capture_offline_url(monkeypatch, _QUALIFIED_POSTGRES_URL) == _QUALIFIED_POSTGRES_URL


def test_resolver_leaves_sqlite_url_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    # SQLite-backed migrations/tests must keep working untouched.
    assert _capture_offline_url(monkeypatch, _SQLITE_URL) == _SQLITE_URL

"""Settings validation tests."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.settings import Settings, load_settings


def test_defaults() -> None:
    settings = Settings()

    assert settings.app_name == "fatty-backend"
    assert settings.environment == "development"
    assert settings.log_level == "INFO"
    assert settings.host == "127.0.0.1"
    assert settings.port == 8000


def test_load_from_env_overrides_defaults() -> None:
    settings = load_settings(
        {"FATTY_ENVIRONMENT": "production", "FATTY_LOG_LEVEL": "ERROR", "FATTY_PORT": "9001"}
    )

    assert settings.environment == "production"
    assert settings.log_level == "ERROR"
    assert settings.port == 9001


def test_invalid_environment_fails_clearly() -> None:
    with pytest.raises(ValidationError):
        Settings(environment="staging")  # type: ignore[arg-type]


def test_invalid_log_level_from_env_fails() -> None:
    with pytest.raises(ValidationError):
        load_settings({"FATTY_LOG_LEVEL": "verbose"})


def test_out_of_range_port_fails() -> None:
    with pytest.raises(ValidationError):
        load_settings({"FATTY_PORT": "70000"})


def test_unknown_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        Settings(unexpected="value")  # type: ignore[call-arg]

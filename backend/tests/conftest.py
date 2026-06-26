"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings


@pytest.fixture
def client() -> Iterator[TestClient]:
    app = create_app(Settings(environment="test", log_level="WARNING"))
    with TestClient(app) as test_client:
        yield test_client

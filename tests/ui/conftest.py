"""Shared pytest fixtures for UI API tests."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def app():
    from aidb_locator.ui.server import build_app
    return build_app()


@pytest.fixture
def client(app):
    return TestClient(app)

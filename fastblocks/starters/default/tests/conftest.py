"""Pytest fixtures for the scaffolded app.

# req: REQ-P2-B1-001, REQ-P2-B1-005
"""
from __future__ import annotations

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def app():
    """Import the ASGI app from main."""
    from main import app as fastblocks_app

    return fastblocks_app


@pytest.fixture
def client(app):
    """Starlette TestClient wrapping the app."""
    return TestClient(app)

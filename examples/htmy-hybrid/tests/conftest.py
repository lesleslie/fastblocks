"""Pytest fixtures for the htmy-hybrid app.

# req: REQ-P2-B3-001
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

# Make ``main`` importable regardless of pytest's rootdir discovery —
# the htmy-hybrid app lives at ``examples/htmy-hybrid/main.py`` and the
# tests need to import it via ``from main import app``.
_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))


@pytest.fixture
def app():
    """Import the ASGI app from main."""
    from main import app as fastblocks_app

    return fastblocks_app


@pytest.fixture
def client(app):
    """Starlette TestClient wrapping the app."""
    return TestClient(app)

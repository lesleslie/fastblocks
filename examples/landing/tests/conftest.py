"""Pytest fixtures for the landing-page app.

# req: REQ-P2-B2-001
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

# Make ``landing_app`` importable regardless of pytest's rootdir discovery —
# the landing app lives at ``examples/landing/landing_app.py`` and the tests
# need to import it via ``from landing_app import app``.
_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))


@pytest.fixture
def app():
    """Import the ASGI app from main."""
    from landing_app import app as fastblocks_app

    return fastblocks_app


@pytest.fixture
def client(app):
    """Starlette TestClient wrapping the app."""
    return TestClient(app)

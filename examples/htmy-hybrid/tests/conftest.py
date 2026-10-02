"""Pytest fixtures for the htmy-hybrid app.

# req: REQ-P2-B3-001
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

# Make ``htmy_hybrid_app`` importable regardless of pytest's rootdir discovery —
# the htmy-hybrid app lives at ``examples/htmy-hybrid/htmy_hybrid_app.py`` and
# the tests need to import it via ``from htmy_hybrid_app import app``.
_APP_ROOT = Path(__file__).resolve().parent.parent
if str(_APP_ROOT) not in sys.path:
    sys.path.insert(0, str(_APP_ROOT))


@pytest.fixture
def app():
    """Import the ASGI app from htmy_hybrid_app."""
    from htmy_hybrid_app import app as fastblocks_app

    return fastblocks_app


@pytest.fixture
def client(app):
    """Starlette TestClient wrapping the app."""
    return TestClient(app)

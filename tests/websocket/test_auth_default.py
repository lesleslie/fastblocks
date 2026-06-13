"""Tests for fastblocks.websocket.auth default for AUTH_ENABLED.

Phase 1.1.b: ``AUTH_ENABLED`` defaults to ``True``; an explicit
``FASTBLOCKS_AUTH_ENABLED=false`` opt-out is the only way to disable.
"""

from __future__ import annotations

import importlib
import sys

import pytest

# This module imports fastblocks.websocket.auth, which transitively imports
# from mcp_common.websocket (the stub provided by tests/conftest.py).
pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.mark.unit
class TestAuthEnabledDefault:
    def test_auth_enabled_defaults_to_true(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Without ``FASTBLOCKS_AUTH_ENABLED`` set, auth must be on."""
        monkeypatch.delenv("FASTBLOCKS_AUTH_ENABLED", raising=False)
        monkeypatch.setenv("FASTBLOCKS_JWT_SECRET", "a-real-secret-32-bytes-long-xx")

        # Drop cached auth module so the env vars re-read.
        saved_auth = sys.modules.pop("fastblocks.websocket.auth", None)
        saved_pkg = sys.modules.pop("fastblocks.websocket", None)
        try:
            mod = importlib.import_module("fastblocks.websocket.auth")
        finally:
            if saved_auth is not None:
                sys.modules["fastblocks.websocket.auth"] = saved_auth
            if saved_pkg is not None:
                sys.modules["fastblocks.websocket"] = saved_pkg

        assert mod.AUTH_ENABLED is True, (
            "AUTH_ENABLED must default to True; the only opt-out is the "
            "explicit FASTBLOCKS_AUTH_ENABLED=false env var."
        )

    def test_auth_disabled_with_explicit_opt_out(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Setting ``FASTBLOCKS_AUTH_ENABLED=false`` is the documented off-switch."""
        monkeypatch.setenv("FASTBLOCKS_AUTH_ENABLED", "false")
        monkeypatch.setenv("FASTBLOCKS_JWT_SECRET", "a-real-secret-32-bytes-long-xx")

        saved_auth = sys.modules.pop("fastblocks.websocket.auth", None)
        saved_pkg = sys.modules.pop("fastblocks.websocket", None)
        try:
            mod = importlib.import_module("fastblocks.websocket.auth")
        finally:
            if saved_auth is not None:
                sys.modules["fastblocks.websocket.auth"] = saved_auth
            if saved_pkg is not None:
                sys.modules["fastblocks.websocket"] = saved_pkg

        assert mod.AUTH_ENABLED is False

"""Tests for fastblocks.websocket.auth.

Phase 1.1.a: refuse to start with the dev fallback JWT secret in any
non-test process. ``pytest.MonkeyPatch`` (or more precisely, pytest being
in ``sys.modules``) is the test exemption — the runtime check fires only
when no test runner is active.
"""

from __future__ import annotations

import importlib
import sys

import pytest

# This module imports fastblocks.websocket.auth, which transitively imports
# from mcp_common.websocket (the stub provided by tests/conftest.py).
pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.mark.unit
class TestJWTSecretRequired:
    def test_refuses_to_start_with_default_secret(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """A non-test process must fail if ``FASTBLOCKS_JWT_SECRET`` is the dev fallback.

        We simulate a non-test process by removing ``pytest`` from
        ``sys.modules`` (since the production guard keys off that), then
        re-import the auth module to trigger the module-level check.
        """
        # Remove JWT secret from the environment.
        monkeypatch.delenv("FASTBLOCKS_JWT_SECRET", raising=False)

        # Simulate a non-test process: drop pytest from sys.modules.
        saved_pytest = sys.modules.pop("pytest", None)
        # Also clear out the already-loaded auth module so the
        # module-level guard runs again.
        saved_auth = sys.modules.pop("fastblocks.websocket.auth", None)
        saved_pkg = sys.modules.pop("fastblocks.websocket", None)
        try:
            with pytest.raises((RuntimeError, ValueError)):
                importlib.import_module("fastblocks.websocket.auth")
        finally:
            # Restore modules so other tests in the same session keep
            # working.
            if saved_pytest is not None:
                sys.modules["pytest"] = saved_pytest
            if saved_auth is not None:
                sys.modules["fastblocks.websocket.auth"] = saved_auth
            if saved_pkg is not None:
                sys.modules["fastblocks.websocket"] = saved_pkg

    def test_passes_when_secret_is_set(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Setting ``FASTBLOCKS_JWT_SECRET`` to a real value lets import succeed."""
        monkeypatch.setenv("FASTBLOCKS_JWT_SECRET", "a-real-secret-32-bytes-long-xx")

        # Drop the cached module so the guard re-runs.
        saved_auth = sys.modules.pop("fastblocks.websocket.auth", None)
        saved_pkg = sys.modules.pop("fastblocks.websocket", None)
        try:
            importlib.import_module("fastblocks.websocket.auth")
        finally:
            if saved_auth is not None:
                sys.modules["fastblocks.websocket.auth"] = saved_auth
            if saved_pkg is not None:
                sys.modules["fastblocks.websocket"] = saved_pkg

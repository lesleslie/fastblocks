"""Tests for fastblocks.websocket.auth default for AUTH_ENABLED.

Phase 1.1.b: ``AUTH_ENABLED`` defaults to ``True``; an explicit
``FASTBLOCKS_AUTH_ENABLED=false`` opt-out is the only way to disable.

Phase 3.0: these tests run ``import fastblocks.websocket.auth`` in a
fresh subprocess (same pattern as ``test_auth.py``) so the production
behaviour is exercised in a genuine non-test process. The previous
implementation mutated ``sys.modules`` in the parent to simulate a
non-test process; that raced with sibling tests under xdist, per
``conftest-sysmodules-pollution-pattern``.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

# Subprocess body: import the auth module and print AUTH_ENABLED.
# Unlike test_auth.py, AUTH_ENABLED here is set at module-load time
# from FASTBLOCKS_AUTH_ENABLED, so a successful import is required to
# observe the value at all.
_IMPORT_SCRIPT = (
    "import fastblocks.websocket.auth as m\n"
    "print('AUTH_ENABLED:', m.AUTH_ENABLED)\n"
)


def _import_in_subprocess(env_overrides: dict[str, str | None]) -> subprocess.CompletedProcess:
    """Run ``import fastblocks.websocket.auth`` in a fresh Python process.

    ``PYTEST_CURRENT_TEST`` is always stripped so the guard sees a
    non-test environment; the supplied overrides are applied on top.
    """
    env = {k: v for k, v in os.environ.items() if k != "PYTEST_CURRENT_TEST"}
    for key, value in env_overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value

    return subprocess.run(
        [sys.executable, "-c", _IMPORT_SCRIPT],
        env=env,
        capture_output=True,
        text=True,
    )


@pytest.mark.unit
class TestAuthEnabledDefault:
    def test_auth_enabled_defaults_to_true(self) -> None:
        """Without ``FASTBLOCKS_AUTH_ENABLED`` set, auth must be on."""
        result = _import_in_subprocess(
            {
                "FASTBLOCKS_AUTH_ENABLED": None,
                "FASTBLOCKS_JWT_SECRET": "a-real-secret-32-bytes-long-xx",
            }
        )

        assert result.returncode == 0, (
            f"Expected import to succeed; got returncode={result.returncode}. "
            f"stderr={result.stderr!r}"
        )
        assert "AUTH_ENABLED: True" in result.stdout

    def test_auth_disabled_with_explicit_opt_out(self) -> None:
        """Setting ``FASTBLOCKS_AUTH_ENABLED=false`` is the documented off-switch."""
        result = _import_in_subprocess(
            {
                "FASTBLOCKS_AUTH_ENABLED": "false",
                "FASTBLOCKS_JWT_SECRET": "a-real-secret-32-bytes-long-xx",
            }
        )

        assert result.returncode == 0, (
            f"Expected import to succeed; got returncode={result.returncode}. "
            f"stderr={result.stderr!r}"
        )
        assert "AUTH_ENABLED: False" in result.stdout

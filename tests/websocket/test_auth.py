"""Tests for fastblocks.websocket.auth.

Phase 1.1.a: refuse to start with the dev fallback JWT secret in any
non-test process. ``pytest.MonkeyPatch`` (or more precisely, pytest being
in ``sys.modules``) is the test exemption — the runtime check fires only
when no test runner is active.

Phase 3.0: these tests now run ``import fastblocks.websocket.auth`` in a
fresh subprocess so the production guard logic is exercised in a
genuine non-test process — without mutating ``sys.modules`` in the
parent (which raced with sibling tests under xdist, per the memory
note ``conftest-sysmodules-pollution-pattern``). Each subprocess
starts with a clean ``sys.modules``, so no test can leak a cached
``pytest`` entry to the guard predicate.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

# Subprocess body: import the auth module (which fires the module-level
# guard) and print AUTH_ENABLED on stdout. If the guard raises, Python
# writes the traceback to stderr and exits non-zero.
_IMPORT_SCRIPT = (
    "import fastblocks.websocket.auth as m\n"
    "print('AUTH_ENABLED:', m.AUTH_ENABLED)\n"
)


def _import_in_subprocess(env_overrides: dict[str, str | None]) -> subprocess.CompletedProcess:
    """Run ``import fastblocks.websocket.auth`` in a fresh Python process.

    Args:
        env_overrides: dict mapping env-var name to its desired value
            (``str`` to set, ``None`` to unset). The subprocess inherits
            the parent's environment with three changes:
            ``PYTEST_CURRENT_TEST`` is always stripped (so the guard's
            "is this a test process?" predicate sees a non-test
            environment), the overrides are applied, and any parent-set
            ``FASTBLOCKS_AUTH_ENABLED`` is stripped. The latter matters
            because ``tests/test_websocket_auth.py`` and
            ``tests/unit/test_websocket_auth.py`` mutate
            ``os.environ["FASTBLOCKS_AUTH_ENABLED"]`` directly (no
            ``monkeypatch``), which leaks into the subprocess and makes
            ``auth.AUTH_ENABLED`` resolve to whatever the most recent
            sibling test set. Stripping here keeps these tests
            order-independent even under xdist.
    """
    strip = {"PYTEST_CURRENT_TEST", "FASTBLOCKS_AUTH_ENABLED"}
    env = {k: v for k, v in os.environ.items() if k not in strip}
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
class TestJWTSecretRequired:
    def test_refuses_to_start_with_default_secret(self) -> None:
        """A non-test process must fail if ``FASTBLOCKS_JWT_SECRET`` is the dev fallback."""
        result = _import_in_subprocess({"FASTBLOCKS_JWT_SECRET": None})

        assert result.returncode != 0, (
            f"Expected non-zero exit when JWT secret is the dev fallback; "
            f"got returncode={result.returncode}. "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )
        assert "RuntimeError" in result.stderr
        assert "dev fallback" in result.stderr

    def test_passes_when_secret_is_set(self) -> None:
        """Setting ``FASTBLOCKS_JWT_SECRET`` to a real value lets import succeed."""
        result = _import_in_subprocess(
            {"FASTBLOCKS_JWT_SECRET": "a-real-secret-32-bytes-long-xx"}
        )

        assert result.returncode == 0, (
            f"Expected import to succeed when JWT secret is set; "
            f"got returncode={result.returncode}. stderr={result.stderr!r}"
        )
        assert "AUTH_ENABLED: True" in result.stdout

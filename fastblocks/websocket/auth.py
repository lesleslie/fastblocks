"""WebSocket authentication configuration for FastBlocks.

This module provides JWT authentication configuration for the FastBlocks
WebSocket server, using environment variables for secure credential management.

Phase 1.1 hardening:

- All env vars are read at module load time (re-runnable via
  ``importlib.reload`` if a test needs to flip them).
- In a **non-test process**, the module refuses to import if
  ``FASTBLOCKS_JWT_SECRET`` is unset or equal to the well-known
  dev fallback (``"dev-secret-change-in-production"``). The check
  fires at import time so a misconfigured production server fails
  loud at startup, not at the first authenticated request.
- Test processes (any process where ``pytest`` is loaded in
  ``sys.modules``) are exempt — the same signal
  ``fastblocks/cli.py:52`` already uses.
- ``FASTBLOCKS_AUTH_ENABLED`` defaults to **true** (was: false). An
  explicit ``FASTBLOCKS_AUTH_ENABLED=false`` is now required to opt
  out, matching the Phase 1.1 plan.

Migration: see ``docs/migrations/0.7-to-0.8.md`` section 8.
"""
from __future__ import annotations

import logging
import os
import sys

from mcp_common.websocket.auth import WebSocketAuthenticator

logger = logging.getLogger(__name__)


# Default secret used when the env var is not set. This is the value
# the in-tree development fallback has used since 0.7.x; the
# module-level guard below refuses to load the module when this is the
# effective secret AND the process is not a test process.
_DEFAULT_DEV_SECRET = "dev-secret-change-in-production"


def _is_test_process() -> bool:
    """Return True if the current process is running under pytest.

    Mirrors the same predicate in ``fastblocks/cli.py:52`` so the
    WebSocket auth check stays consistent with the rest of the
    framework.
    """
    return (
        os.getenv("PYTEST_CURRENT_TEST") is not None
        or "pytest" in sys.modules
    )


def _read_jwt_secret() -> str:
    """Read ``FASTBLOCKS_JWT_SECRET`` and enforce the production guard.

    In a non-test process, refuse to load if the secret is unset or
    equal to the dev fallback. The runtime check fires once, at
    module load — module import either succeeds (real secret) or
    raises ``RuntimeError`` (dev fallback / unset).
    """
    secret = os.getenv("FASTBLOCKS_JWT_SECRET") or _DEFAULT_DEV_SECRET

    if secret == _DEFAULT_DEV_SECRET and not _is_test_process():
        raise RuntimeError(
            "FASTBLOCKS_JWT_SECRET is unset or set to the dev fallback "
            f"({_DEFAULT_DEV_SECRET!r}). The WebSocket server refuses "
            "to start in a non-test process without a real secret. "
            "Set FASTBLOCKS_JWT_SECRET to a 32+ byte random string "
            "before importing fastblocks.websocket.auth."
        )

    if secret == _DEFAULT_DEV_SECRET:
        logger.warning(
            "Using default JWT secret - acceptable in tests only. "
            "Set FASTBLOCKS_JWT_SECRET before any non-test use."
        )

    return secret


# Read once at module load. Tests that need to flip the secret can
# re-import via importlib.reload() (see tests/websocket/test_auth.py).
JWT_SECRET: str = _read_jwt_secret()

# Token expiry in seconds (default 1 hour). Read at module load.
TOKEN_EXPIRY: int = int(os.getenv("FASTBLOCKS_TOKEN_EXPIRY", "3600"))

# Authentication on by default (Phase 1.1). Opt-out with
# FASTBLOCKS_AUTH_ENABLED=false (tests use this in the dev-mode
# negative test). The boolean is module-loaded for the module's own
# use, but the helpers below re-read ``os.environ`` at call time so a
# test that mutates the environment (without reloading the module)
# still sees the new value.
_AUTH_ENABLED_RAW: str = os.getenv("FASTBLOCKS_AUTH_ENABLED", "true")
AUTH_ENABLED: bool = _AUTH_ENABLED_RAW.lower() not in ("false", "0", "no", "off")


def _is_auth_enabled() -> bool:
    """Re-read ``FASTBLOCKS_AUTH_ENABLED`` from the current environment.

    See the comment on ``AUTH_ENABLED`` above: the module constant is
    set at load time, but call sites that flip the env var at runtime
    (e.g. ``tests/test_websocket_auth.py::test_get_authenticator_dev_mode``)
    expect ``get_authenticator()`` to honor the new value without
    reloading the module. This helper does that re-read.
    """
    raw = os.getenv("FASTBLOCKS_AUTH_ENABLED")
    if raw is None:
        return AUTH_ENABLED  # honor the load-time default
    return raw.lower() not in ("false", "0", "no", "off")


def get_authenticator() -> WebSocketAuthenticator | None:
    """Get configured WebSocket authenticator.

    Returns:
        WebSocketAuthenticator instance if authentication is enabled,
        None when ``FASTBLOCKS_AUTH_ENABLED=false`` (development mode).
    """
    if not _is_auth_enabled():
        logger.info("FastBlocks WebSocket authentication disabled (development mode)")
        return None

    return WebSocketAuthenticator(
        secret=JWT_SECRET,
        algorithm="HS256",
        token_expiry=TOKEN_EXPIRY,
    )


def generate_token(user_id: str, permissions: list[str] | None = None) -> str:
    """Generate a JWT token for testing or development.

    Args:
        user_id: User identifier
        permissions: List of permissions (default: ["read"])

    Returns:
        JWT token string

    Example:
        >>> token = generate_token("user123", ["fastblocks:read", "fastblocks:write"])
        >>> print(f"Token: {token}")
    """
    authenticator = get_authenticator()
    if authenticator is None:
        # Development mode - create a temporary authenticator
        authenticator = WebSocketAuthenticator(
            secret=JWT_SECRET,
            algorithm="HS256",
            token_expiry=TOKEN_EXPIRY,
        )

    return authenticator.create_token({
        "user_id": user_id,
        "permissions": permissions or ["fastblocks:read"],
    })


def verify_token(token: str) -> dict[str, object] | None:
    """Verify a JWT token.

    Args:
        token: JWT token to verify

    Returns:
        Token payload if valid, None otherwise
    """
    authenticator = get_authenticator()
    if authenticator is None:
        # Development mode - create a temporary authenticator
        authenticator = WebSocketAuthenticator(
            secret=JWT_SECRET,
            algorithm="HS256",
            token_expiry=TOKEN_EXPIRY,
        )

    return authenticator.verify_token(token)

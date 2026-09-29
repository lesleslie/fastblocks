"""D6: assert default security headers are set on every response.

Per security-auditor BL1: VALUE-shape assertions, not just presence. A CSP
of ``default-src 'unsafe-inline' *`` passes a presence check. This file
pins the value contract: no ``'unsafe-inline'`` / ``'unsafe-eval'`` in
CSP (unless nonce-protected), HSTS ``max-age >= 31536000``, X-Frame-
Options ``DENY``/``SAMEORIGIN``, X-Content-Type-Options ``nosniff``, and
a safe Referrer-Policy value.

The brief's ``FastBlocks()`` + ``app.user_middleware`` sketch had to be
reality-adapted: ``SecureHeadersMiddleware`` is registered as a SYSTEM
middleware by ``MiddlewareStackManager`` (not a user middleware), and
the FastBlocks kwarg is ``config=`` (not ``enable_csrf=``). We follow
the established pattern from ``test_middleware_security_headers.py``:
construct a ``MiddlewareStackManager(config=...)`` directly, build the
stack, wrap a minimal ASGI app, send a real request through TestClient,
and assert headers / middleware composition.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from starlette.responses import PlainTextResponse
from starlette.testclient import TestClient


def _make_config(deployed: bool = False) -> MagicMock:
    cfg = MagicMock()
    cfg.deployed = deployed
    cfg.debug = MagicMock(production=False)
    cfg.app = MagicMock()
    cfg.app.secret_key.get_secret_value.return_value = "x" * 32
    cfg.app.token_id = "_fb_"
    cfg.app.security_headers_strict = True
    return cfg


@pytest.fixture
def app_with_secure_stack():
    """Build a FastBlocks-style app with the full default middleware stack.

    Uses the same wiring as production (``MiddlewareStackManager.build_stack``)
    so the test exercises the real stack composition path.
    """
    from fastblocks.middleware import (
        MiddlewareStackManager,
        SecureHeadersMiddleware,
    )

    cfg = _make_config(deployed=False)
    mgr = MiddlewareStackManager(config=cfg)
    mgr.initialize()
    stack = mgr.build_stack()

    async def home(scope, receive, send):  # noqa: ARG001
        await send(
            {"type": "http.response.start", "status": 200, "headers": []},
        )
        await send({"type": "http.response.body", "body": b"ok"})

    # Wrap innermost first so the stack applies outermost last.
    wrapped = home
    for mw in reversed(stack):
        cls = getattr(mw, "cls", mw)
        kwargs = dict(getattr(mw, "kwargs", {}))
        wrapped = cls(wrapped, **kwargs)

    # Stash for the middleware-in-stack assertion.
    wrapped._fb_test_stack_classes = [
        getattr(getattr(m, "cls", m), "__name__", str(m)) for m in stack
    ]
    return wrapped


@pytest.fixture
def client(app_with_secure_stack):
    return TestClient(app_with_secure_stack)


def test_csp_header_present_and_safe(client):
    """CSP must include ``default-src`` and not allow unsafe-inline/eval."""
    r = client.get("/")
    csp = next(
        (v for k, v in r.headers.items() if k.lower() == "content-security-policy"),
        None,
    )
    assert csp is not None, "D6: Content-Security-Policy header missing"
    assert "default-src" in csp, f"D6: CSP missing default-src: {csp!r}"
    assert "'unsafe-inline'" not in csp or "nonce-" in csp, (
        f"D6: CSP allows 'unsafe-inline' without nonce: {csp!r}"
    )
    assert "'unsafe-eval'" not in csp, f"D6: CSP allows 'unsafe-eval': {csp!r}"


def test_hsts_header_present_and_long_enough(client):
    """HSTS max-age must be >= 31536000 (1 year OWASP minimum)."""
    import re

    r = client.get("/")
    hsts = r.headers.get("strict-transport-security", "")
    assert hsts, "D6: Strict-Transport-Security header missing"
    match = re.search(r"max-age=(\d+)", hsts)
    assert match, f"D6: HSTS missing max-age: {hsts!r}"
    max_age = int(match.group(1))
    assert max_age >= 31_536_000, (
        f"D6: HSTS max-age={max_age} < 31536000 (1 year minimum): {hsts!r}"
    )


def test_x_frame_options_deny_or_sameorigin(client):
    r = client.get("/")
    xfo = r.headers.get("x-frame-options", "")
    assert xfo.upper() in {"DENY", "SAMEORIGIN"}, (
        f"D6: X-Frame-Options must be DENY or SAMEORIGIN (got: {xfo!r})"
    )


def test_x_content_type_options_nosniff(client):
    r = client.get("/")
    assert r.headers.get("x-content-type-options", "").lower() == "nosniff", (
        "D6: X-Content-Type-Options must be 'nosniff'"
    )


def test_referrer_policy_safe(client):
    r = client.get("/")
    rp = r.headers.get("referrer-policy", "").lower()
    safe = {
        "no-referrer",
        "same-origin",
        "strict-origin",
        "strict-origin-when-cross-origin",
        "no-referrer-when-downgrade",
    }
    assert rp in safe, f"D6: Referrer-Policy {rp!r} is not in the safe set {safe}"


def test_app_has_secure_headers_middleware_in_stack(app_with_secure_stack):
    """Per security-auditor IMP7: the test must exercise the production
    middleware path, not just check response headers (which could come
    from an uncontrolled source)."""

    classes = app_with_secure_stack._fb_test_stack_classes
    assert "SecureHeadersMiddleware" in classes, (
        f"D6: SecureHeadersMiddleware not in stack (got: {classes})"
    )


def test_secure_headers_middleware_class_importable():
    """Smoke: the production middleware class is still importable."""
    from fastblocks.middleware import SecureHeadersMiddleware

    assert SecureHeadersMiddleware.__name__ == "SecureHeadersMiddleware"

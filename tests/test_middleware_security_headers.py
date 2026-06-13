"""Phase 1.4: Security headers + CSRF default-on.

Lives in a separate file from ``test_middleware.py`` because the
existing ``TestMiddleware`` class mutates ``sys.modules`` to inject a
mock ``fastblocks.middleware`` module, and the import system will
return that cached mock to subsequent tests in the same xdist worker.
This file imports the real module via top-level imports, so it must
be loaded before any test that polls ``sys.modules`` with a mock.
"""

from __future__ import annotations

import asyncio
import typing as t
from http.cookies import SimpleCookie
from unittest.mock import MagicMock

import pytest
from starlette_csrf.middleware import CSRFMiddleware
from fastblocks.middleware import (
    MiddlewarePosition,
    MiddlewareStackManager,
    SecureHeadersMiddleware,
    secure_headers,
)


def _make_config(deployed: bool = False) -> MagicMock:
    cfg = MagicMock()
    cfg.deployed = deployed
    cfg.debug = MagicMock(production=False)
    cfg.app = MagicMock()
    cfg.app.secret_key.get_secret_value.return_value = "x" * 32
    cfg.app.token_id = "_fb_"
    return cfg


@pytest.mark.unit
def test_security_headers_strict_defaults_to_true() -> None:
    """``security_headers_strict`` is a default-on secure setting."""
    from fastblocks.applications import FastBlocksSettings

    assert getattr(FastBlocksSettings, "security_headers_strict", None) is True


@pytest.mark.unit
def test_security_headers_strict_subclass_override() -> None:
    """Subclasses may opt out of strict headers by setting False."""
    from fastblocks.applications import FastBlocksSettings

    class LooseSettings(FastBlocksSettings):
        security_headers_strict = False

    assert LooseSettings.security_headers_strict is False
    # Default stays True on the base
    assert FastBlocksSettings.security_headers_strict is True


@pytest.mark.unit
def test_security_headers_registered_in_dev_mode() -> None:
    mgr = MiddlewareStackManager(config=_make_config(deployed=False))
    mgr.initialize()

    assert MiddlewarePosition.SECURITY_HEADERS in mgr._middleware_registry
    assert (
        mgr._middleware_registry[MiddlewarePosition.SECURITY_HEADERS]
        is SecureHeadersMiddleware
    )


@pytest.mark.unit
def test_csrf_registered_in_dev_mode() -> None:
    mgr = MiddlewareStackManager(config=_make_config(deployed=False))
    mgr.initialize()

    assert MiddlewarePosition.CSRF in mgr._middleware_registry
    assert mgr._middleware_registry[MiddlewarePosition.CSRF] is CSRFMiddleware


@pytest.mark.unit
def test_security_headers_strict_false_omits_security_headers() -> None:
    """``security_headers_strict=False`` on the FastBlocksSettings subclass must opt the application out of strict security headers, regardless of the ``deployed`` toggle."""
    from fastblocks.applications import FastBlocksSettings

    class LooseAppSettings(FastBlocksSettings):
        name: str = "fastblocks"
        token_id: str = "_fb_"
        security_headers_strict: bool = False

    class _Secret:
        def get_secret_value(self) -> str:
            return "x" * 32

    loose = LooseAppSettings()
    loose.secret_key = _Secret()  # type: ignore[attr-defined]
    cfg = _make_config(deployed=True)
    cfg.app = loose

    mgr = MiddlewareStackManager(config=cfg)
    mgr.initialize()

    assert MiddlewarePosition.SECURITY_HEADERS not in mgr._middleware_registry


@pytest.mark.unit
def test_build_stack_includes_security_headers_in_dev() -> None:
    mgr = MiddlewareStackManager(config=_make_config(deployed=False))
    stack = mgr.build_stack()
    classes = [mw.cls for mw in stack]
    assert SecureHeadersMiddleware in classes


@pytest.mark.unit
def test_build_stack_includes_csrf_in_dev() -> None:
    mgr = MiddlewareStackManager(config=_make_config(deployed=False))
    stack = mgr.build_stack()
    classes = [mw.cls for mw in stack]
    assert CSRFMiddleware in classes


@pytest.mark.unit
def test_security_headers_emit_csp_xfo_xcto() -> None:
    """``SecureHeadersMiddleware`` should emit real CSP / XFO / XCTO values (not an empty mapping). The previous default of ``Secure()`` produced no headers, so this test guards the default-on secure behavior."""
    headers = dict(secure_headers.headers)
    assert "Content-Security-Policy" in headers
    assert "X-Frame-Options" in headers
    assert "X-Content-Type-Options" in headers
    assert headers["X-Frame-Options"].upper() in {"DENY", "SAMEORIGIN"}
    assert headers["X-Content-Type-Options"].lower() == "nosniff"


@pytest.mark.unit
def test_csrf_cookie_set_in_response() -> None:
    """Driving a request through the dev stack should produce a CSRF cookie in the response."""
    mgr = MiddlewareStackManager(config=_make_config(deployed=False))
    mgr.initialize()
    csrf_options = mgr._middleware_options[MiddlewarePosition.CSRF]

    async def app(scope, receive, send):  # noqa: ARG001
        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [],
            }
        )
        await send({"type": "http.response.body", "body": b"ok"})

    wrapped = SecureHeadersMiddleware(
        CSRFMiddleware(
            app,
            secret=csrf_options["secret"],
            cookie_name=csrf_options["cookie_name"],
            cookie_secure=csrf_options["cookie_secure"],
        )
    )

    cookies: list[str] = []
    status_seen: dict[str, int] = {}

    async def send(message: dict[str, t.Any]) -> None:
        if message["type"] == "http.response.start":
            status_seen["status"] = message["status"]
            for k, v in message.get("headers", []):
                if k == b"set-cookie":
                    cookies.append(v.decode("latin-1"))

    async def receive() -> dict[str, t.Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    scope: dict[str, t.Any] = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
    }

    asyncio.run(wrapped(scope, receive, send))

    assert status_seen.get("status") == 200
    joined = "\n".join(cookies)
    parsed = SimpleCookie()
    parsed.load(joined)
    assert len(parsed) >= 1, f"No cookies set: {cookies!r}"

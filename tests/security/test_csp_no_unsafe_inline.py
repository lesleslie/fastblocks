"""F1.5-D6-T1: CSP ``style-src`` must not allow ``'unsafe-inline'``.

Path A from the Phase 1.5 plan: ``SecureHeadersMiddleware`` overrides the
``secure`` library default (which sets ``style-src 'self' https:
'unsafe-inline'``) and rebuilds the CSP with a per-request nonce --
``style-src 'self' https: 'nonce-...'``. ``'unsafe-inline'`` must NOT
appear in the emitted header.

This file complements the broader D6 contract in
``tests/middleware/test_security_headers.py`` with a single-purpose
check that pins the value shape of ``style-src`` specifically.

The middleware-level assertion lives in ``test_security_headers.py``;
this file adds nonce-shape coverage plus the helper-side guard
(``inline_css(nonce)`` emits the matching attribute).
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
def client():
    """Build a real FastBlocks-style app with the default middleware stack."""
    from fastblocks.middleware import MiddlewareStackManager

    cfg = _make_config(deployed=False)
    mgr = MiddlewareStackManager(config=cfg)
    mgr.initialize()
    stack = mgr.build_stack()

    async def home(scope, receive, send):  # noqa: ARG001
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})

    # Wrap innermost first so the stack applies outermost last.
    wrapped = home
    for mw in reversed(stack):
        cls = getattr(mw, "cls", mw)
        kwargs = dict(getattr(mw, "kwargs", {}))
        wrapped = cls(wrapped, **kwargs)

    return TestClient(wrapped)


def test_csp_style_src_excludes_unsafe_inline(client):
    """``style-src`` must not allow ``'unsafe-inline'`` (F1.5-D6-T1)."""
    r = client.get("/")
    csp = next(
        (v for k, v in r.headers.items() if k.lower() == "content-security-policy"),
        None,
    )
    assert csp is not None, "Content-Security-Policy header missing"

    # Extract the style-src directive.
    directives = [d.strip() for d in csp.split(";") if d.strip()]
    style_src = next((d for d in directives if d.startswith("style-src ")), "")
    assert style_src, f"style-src directive missing in CSP: {csp!r}"
    assert "'unsafe-inline'" not in style_src, (
        f"F1.5-D6-T1: style-src allows 'unsafe-inline': {style_src!r}"
    )


def test_csp_includes_nonce(client):
    """``SecureHeadersMiddleware`` must inject a nonce into style-src."""
    r = client.get("/")
    csp = next(
        (v for k, v in r.headers.items() if k.lower() == "content-security-policy"),
        None,
    )
    assert csp is not None
    assert "nonce-" in csp, f"F1.5-D6-T1: CSP missing nonce source: {csp!r}"


def test_csp_nonce_varies_per_request(client):
    """Two requests get distinct nonces (no accidental caching)."""
    r1 = client.get("/")
    r2 = client.get("/")

    def _nonce(csp: str) -> str:
        for directive in csp.split(";"):
            directive = directive.strip()
            if directive.startswith("style-src ") or directive.startswith(
                "script-src "
            ):
                for token in directive.split():
                    if token.startswith("'nonce-"):
                        return token
        return ""

    csp1 = next(
        (v for k, v in r1.headers.items() if k.lower() == "content-security-policy"),
        "",
    )
    csp2 = next(
        (v for k, v in r2.headers.items() if k.lower() == "content-security-policy"),
        "",
    )
    n1 = _nonce(csp1)
    n2 = _nonce(csp2)
    assert n1, "first CSP missing nonce"
    assert n2, "second CSP missing nonce"
    assert n1 != n2, f"F1.5-D6-T1: nonce reused across requests: {n1!r}"


def test_inline_css_emits_nonce_when_provided():
    """``inline_css(nonce)`` must emit ``<style nonce="...">``."""
    from fastblocks.adapters.templates.htmy_components.adapter import inline_css

    out = inline_css("abc123")
    # SafeHTML wraps the string; check the underlying HTML.
    html = str(out)
    assert 'nonce="abc123"' in html, (
        f"inline_css(nonce) did not emit nonce attribute: {html[:80]!r}"
    )
    assert html.startswith("<style nonce="), html[:80]


def test_inline_css_no_nonce_omits_attribute():
    """Without a nonce, ``inline_css()`` emits a bare ``<style>`` (legacy CSP compat)."""
    from fastblocks.adapters.templates.htmy_components.adapter import inline_css

    out = inline_css()
    html = str(out)
    assert "<style>" in html, html[:80]
    assert "nonce=" not in html, html[:80]


def test_build_nonce_csp_strips_unsafe_inline():
    """``build_nonce_csp`` unit-level: drops ``'unsafe-inline'`` from style-src."""
    from fastblocks.middleware import build_nonce_csp

    library_csp = (
        "default-src 'self'; style-src 'self' https: 'unsafe-inline'; "
        "script-src 'self'; img-src 'self' data:"
    )
    out = build_nonce_csp("noncevalue", library_csp)
    assert "'unsafe-inline'" not in out, out
    assert "'nonce-noncevalue'" in out, out

    # Every other directive preserved verbatim.
    assert "default-src 'self'" in out, out
    assert "img-src 'self' data:" in out, out


def test_build_nonce_csp_empty_nonce_passes_through():
    """When nonce is empty, ``build_nonce_csp`` returns the library CSP unchanged."""
    from fastblocks.middleware import build_nonce_csp

    library_csp = "style-src 'self' https: 'unsafe-inline'; script-src 'self'"
    out = build_nonce_csp("", library_csp)
    assert out == library_csp


def test_inline_js_emits_nonce_when_provided():
    """``inline_js(nonce)`` must emit ``<script type="module" nonce="...">``."""
    from fastblocks.adapters.templates.htmy_components.adapter import inline_js

    out = inline_js("xyz789")
    html = str(out)
    assert 'nonce="xyz789"' in html, html[:80]
    assert html.startswith('<script type="module" nonce="'), html[:80]


def test_template_globals_inline_resolvers_are_callables():
    """The inline globals are callables so they can resolve the request nonce at render time."""
    from fastblocks.adapters.templates.htmy_components.adapter import (
        template_globals,
    )

    gl = template_globals()
    assert callable(gl["fastblocks_ui_css_inline"]), (
        "fastblocks_ui_css_inline must be a callable (Jinja globals don't auto-call)"
    )
    assert callable(gl["fastblocks_ui_js_inline"]), (
        "fastblocks_ui_js_inline must be a callable (Jinja globals don't auto-call)"
    )

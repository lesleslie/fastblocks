"""D4: pin the four HTMX response headers the framework claims to emit.

Each helper (``htmx_trigger``, ``htmx_redirect``, ``htmx_refresh``,
``htmx_push_url``) returns an ``HtmxResponse`` whose ``_set_htmx_headers``
writes a specific response header. This test drives the helpers
through a real FastBlocks app + Starlette ``TestClient`` so we exercise
the full ASGI pipeline (not just unit-level response construction).

Per Task 7 brief constraint B: the actual emitted key for push URL is
``HX-Push-Url`` (mixed-case ``Url``), NOT ``HX-Push-URL``. The assertion
here matches ``fastblocks/htmx.py:308`` verbatim.

Per reality check: Starlette does NOT expose a ``route`` decorator —
only ``add_route(path, endpoint, methods=[...])``. The brief's
``@a.route(...)`` sketch was reality-adapted to ``a.add_route(...)``.
"""
from __future__ import annotations

import pytest
from fastblocks.applications import FastBlocks
from fastblocks.htmx import (
    htmx_push_url,
    htmx_redirect,
    htmx_refresh,
    htmx_trigger,
)
from starlette.testclient import TestClient


@pytest.fixture
def app():
    a = FastBlocks()

    async def trigger(request):  # noqa: ARG001
        return htmx_trigger("evt")

    async def redirect(request):  # noqa: ARG001
        return htmx_redirect("/loc")

    async def refresh(request):  # noqa: ARG001
        return htmx_refresh()

    async def push(request):  # noqa: ARG001
        return htmx_push_url("/pushed")

    a.add_route("/trigger", trigger)
    a.add_route("/redirect", redirect)
    a.add_route("/refresh", refresh)
    a.add_route("/push", push)

    return a


@pytest.fixture
def client(app):
    return TestClient(app)


def test_hx_trigger_header_emitted(client):
    """``htmx_trigger`` emits ``HX-Trigger`` with the event name."""
    r = client.get("/trigger")
    assert r.status_code == 200, (
        f"D4: trigger endpoint returned {r.status_code}, expected 200"
    )
    assert r.headers.get("HX-Trigger") == "evt", (
        f"D4: HX-Trigger header wrong "
        f"(got={r.headers.get('HX-Trigger')!r}, expected 'evt')"
    )


def test_hx_redirect_header_emitted(client):
    """``htmx_redirect`` emits ``HX-Redirect`` with the target URL."""
    r = client.get("/redirect")
    assert r.status_code == 200, (
        f"D4: redirect endpoint returned {r.status_code}, expected 200"
    )
    assert r.headers.get("HX-Redirect") == "/loc", (
        f"D4: HX-Redirect header wrong "
        f"(got={r.headers.get('HX-Redirect')!r}, expected '/loc')"
    )


def test_hx_refresh_header_emitted(client):
    """``htmx_refresh`` emits ``HX-Refresh: true`` (full page refresh)."""
    r = client.get("/refresh")
    assert r.status_code == 200, (
        f"D4: refresh endpoint returned {r.status_code}, expected 200"
    )
    assert r.headers.get("HX-Refresh") == "true", (
        f"D4: HX-Refresh header wrong "
        f"(got={r.headers.get('HX-Refresh')!r}, expected 'true')"
    )


def test_hx_push_url_header_emitted(client):
    """``htmx_push_url`` emits ``HX-Push-Url`` (NOT ``HX-Push-URL``).

    Per ``fastblocks/htmx.py:308``, the actual emitted response header
    key is ``HX-Push-Url`` (mixed-case ``Url``). Brief constraint B
    pins this casing verbatim.
    """
    r = client.get("/push")
    assert r.status_code == 200, (
        f"D4: push endpoint returned {r.status_code}, expected 200"
    )
    assert r.headers.get("HX-Push-Url") == "/pushed", (
        f"D4: HX-Push-Url header wrong "
        f"(got={r.headers.get('HX-Push-Url')!r}, expected '/pushed')"
    )

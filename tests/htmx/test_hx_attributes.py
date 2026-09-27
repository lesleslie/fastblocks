"""D4: tests for hx-* attribute handling at the framework level.

These tests assert that hx-* attributes on requests are recognized
and that the response pipeline produces the expected HTMX semantics.

Per reality check: Starlette does NOT expose a ``route`` decorator —
only ``add_route(path, endpoint, methods=[...])``. The brief's
``@a.route(...)`` sketch was reality-adapted to ``a.add_route(...)``.
All routes are registered inside the fixture (rather than at test
time, per the brief's ``test_hx_current_url_propagated`` sketch) —
the fixture pattern keeps the route registration colocated with the
test setup and avoids the brief's known inconsistency of defining
routes after the ``app`` fixture has already been constructed.

The full ASGI pipeline is exercised via Starlette ``TestClient`` so we
verify the headers survive middleware (HtmxMiddleware, etc.) and the
final response layer, not just the helper constructors.
"""
from __future__ import annotations

import pytest
from fastblocks.applications import FastBlocks
from fastblocks.htmx import htmx_redirect, htmx_trigger
from starlette.responses import HTMLResponse, PlainTextResponse
from starlette.testclient import TestClient


@pytest.fixture
def app():
    a = FastBlocks()

    async def partial(request):  # noqa: ARG001
        return HTMLResponse("<div>partial</div>")

    async def trigger(request):  # noqa: ARG001
        return htmx_trigger("server-event")

    async def redirect(request):  # noqa: ARG001
        return htmx_redirect("/new-location")

    async def echo_current_url(request):
        return PlainTextResponse(request.headers.get("HX-Current-URL", ""))

    a.add_route("/partial", partial)
    a.add_route("/trigger-server-event", trigger, methods=["POST"])
    a.add_route("/redirect", redirect)
    # Registered in the fixture (not at test time) — fixes the brief's
    # known route-after-fixture inconsistency.
    a.add_route("/echo-current-url", echo_current_url)

    return a


@pytest.fixture
def client(app):
    return TestClient(app)


def test_hx_get_request_recognized(client):
    """``HX-Request: true`` on the request signals HTMX-driven fetch.

    The endpoint returns 200 regardless of HTMX-ness (a non-HTMX
    client gets the same partial). What we pin here is the request
    layer's acceptance — no middleware drops the request because
    the HX-Request header is present.
    """
    r = client.get("/partial", headers={"HX-Request": "true"})
    assert r.status_code == 200, (
        f"D4: HX-Request GET returned {r.status_code}, expected 200"
    )


def test_hx_target_response(client):
    """``HX-Trigger`` server-sent event surfaces in response header.

    When a route returns ``htmx_trigger("server-event")``, the
    response must carry ``HX-Trigger: server-event`` so the browser-
    side HTMX runtime fires the matching event listener.
    """
    r = client.post(
        "/trigger-server-event",
        headers={"HX-Request": "true"},
    )
    assert r.status_code == 200, (
        f"D4: trigger endpoint returned {r.status_code}, expected 200"
    )
    assert r.headers.get("HX-Trigger") == "server-event", (
        f"D4: HX-Trigger header wrong "
        f"(got={r.headers.get('HX-Trigger')!r}, expected 'server-event')"
    )


def test_hx_redirect_response(client):
    """``HX-Redirect`` header instructs client to navigate.

    Pin the URL value (not just header presence) — the redirect
    target is the contract.
    """
    r = client.get("/redirect", headers={"HX-Request": "true"})
    assert r.status_code == 200, (
        f"D4: redirect endpoint returned {r.status_code}, expected 200"
    )
    assert r.headers.get("HX-Redirect") == "/new-location", (
        f"D4: HX-Redirect header wrong "
        f"(got={r.headers.get('HX-Redirect')!r}, expected '/new-location')"
    )


def test_hx_current_url_propagated(client):
    """``HX-Current-URL`` on request reaches the route handler as a header.

    Per htmx.org: HTMX sends ``HX-Current-URL`` on every request so
    the server can know the page the user is currently viewing. The
    framework must propagate it through to the route handler —
    middleware (HtmxMiddleware, etc.) must not strip it.

    Route is registered in the fixture (see app fixture docstring) to
    fix the brief's known route-after-fixture inconsistency.
    """
    r = client.get(
        "/echo-current-url",
        headers={
            "HX-Request": "true",
            "HX-Current-URL": "https://example.com/page",
        },
    )
    assert r.status_code == 200, (
        f"D4: echo-current-url returned {r.status_code}, expected 200"
    )
    assert r.text == "https://example.com/page", (
        f"D4: HX-Current-URL not propagated to route handler "
        f"(got: {r.text!r})"
    )

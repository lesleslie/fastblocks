"""F1.5-D4-T1: assert ``/demo`` emits ``HX-Trigger`` header on HTMX swap.

The landing ``/demo`` endpoint serves an HTMX fragment when the request
carries ``HX-Request: true``. Beyond the body swap, the route should
emit an ``HX-Trigger`` response header so client-side listeners can
fire on ``demo-search-completed`` with the query payload. This test
pins that contract end-to-end through a real Starlette ``TestClient``.

The app is bootstrapped from ``examples/landing/landing_app.py`` so the test
exercises the actual route handler, not a synthetic stand-in. To keep
the test independent of pytest's working directory, we ``chdir`` into
the example's root before importing the app — Oneiric's settings
loader resolves ``settings/app.yaml`` from CWD.

# req: REQ-P2-B2-001
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from starlette.testclient import TestClient

_EXAMPLES_LANDING = (
    Path(__file__).resolve().parents[2] / "examples" / "landing"
)


@pytest.fixture
def landing_app(monkeypatch: pytest.MonkeyPatch):
    """Import the real landing FastBlocks app with Oneiric settings."""
    monkeypatch.chdir(_EXAMPLES_LANDING)
    if str(_EXAMPLES_LANDING) not in sys.path:
        sys.path.insert(0, str(_EXAMPLES_LANDING))
    # Reload the module fresh so any prior import (e.g. from a sibling
    # test) does not leak cached adapter state into this test.
    for name in list(sys.modules):
        if name == "landing_app" or name.startswith("landing_app."):
            monkeypatch.delitem(sys.modules, name)
    from landing_app import app

    return app


@pytest.fixture
def client(landing_app):
    """Starlette TestClient wrapping the landing demo app."""
    return TestClient(landing_app)


def test_demo_swap_emits_hx_trigger_header(client) -> None:
    """``/demo`` HTMX swap emits ``HX-Trigger`` with the query payload."""
    response = client.get("/demo?q=test", headers={"HX-Request": "true"})

    assert response.status_code == 200, (
        f"F1.5-D4-T1: /demo returned {response.status_code}, expected 200"
    )
    assert "HX-Trigger" in response.headers, (
        "F1.5-D4-T1: HX-Trigger header missing from /demo swap response. "
        "Per the integration contract, HTMX fragments must emit "
        "demo-search-completed via HX-Trigger so client-side listeners can "
        f"observe the swap. Response headers: {dict(response.headers)!r}"
    )


def test_demo_swap_hx_trigger_payload_is_json(client) -> None:
    """``HX-Trigger`` body is a JSON object keyed by event name."""
    response = client.get("/demo?q=test", headers={"HX-Request": "true"})

    raw = response.headers.get("HX-Trigger")
    assert raw is not None, "F1.5-D4-T1: HX-Trigger missing (see other test)"
    payload = json.loads(raw)
    assert "demo-search-completed" in payload, (
        "F1.5-D4-T1: HX-Trigger payload missing 'demo-search-completed' "
        f"event key (got keys={list(payload)!r})"
    )
    assert payload["demo-search-completed"].get("query") == "test", (
        "F1.5-D4-T1: HX-Trigger payload should carry the echoed query "
        f"(got query={payload['demo-search-completed'].get('query')!r})"
    )


def test_demo_full_page_does_not_emit_hx_trigger(client) -> None:
    """Non-HTMX GET to ``/demo`` does NOT emit ``HX-Trigger``.

    The trigger event is meaningful only on the HTMX fragment response.
    On a full-page load there is no swap listener to fire it, so emitting
    the header would be noise.
    """
    response = client.get("/demo?q=test")

    assert response.status_code == 200
    assert "HX-Trigger" not in response.headers, (
        "F1.5-D4-T1: HX-Trigger leaked into the full-page response. "
        "Only the HTMX swap (HX-Request: true) should emit it. "
        f"Headers: {dict(response.headers)!r}"
    )

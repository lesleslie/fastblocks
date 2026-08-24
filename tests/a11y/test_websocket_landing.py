"""Dynamic WS → aria-live a11y bridge tests.

Per Δ10 (CORRECTED WCAG routing) + Δ13 + Δ39-α:

The ``fastblocks.websocket.a11y_bridge.render_broadcast_as_a11y`` function
takes a real WebSocket broadcast event (shape produced by
``mcp_common.websocket.WebSocketProtocol.create_event``) and returns the
HTML string that should land in the screen reader's aria-live region — or
``None`` if the event should be dropped (escaped=false, rate-limited,
non-aria-live event type).

The corrected routing table (Δ10 supersedes an earlier misrouting):

  * ``event == "miss"``  → ``aria-live="polite"``, ``role="status"``
    (NOT ``aria-live="assertive"``, NOT ``role="alert"`` — the assertive
    alert pairing was the bug being corrected).
  * ``escaped == false`` → ``None`` (logs only; no aria-live update).
  * everything else with a non-empty ``data`` payload → default polite /
    status update.

ARIA attribute contract (per brief + Δ13):

  * ``aria-live="polite"``
  * ``role="status"``
  * ``aria-atomic="true"``           (per brief)
  * ``aria-relevant="additions"``    (per brief)
  * ``data-fb-aria-live="true"``     (fastblocks a11y bridge hook)
  * ``class="sr-only--fastblocks-a11y-bridge"``

CSS contract (per brief):

  * Namespaced ``.sr-only--fastblocks-a11y-bridge`` class.
  * Modern ``clip-path: inset(50%)`` for the visually-hidden technique
    (NOT legacy ``clip: rect(...)`` or 1px border hacks).
  * Standard sr-only styles (position: absolute, width/height: 1px,
    margin: -1px, padding: 0, overflow: hidden, white-space: nowrap).

Rate-limit contract (per Δ39-α): ≤5 mutations/sec budget per region.
The ``fastblocks_a11y_bridge_dropped_total{region}`` counter increments
when an event is rate-limited and dropped.

The dynamic test fires a *real* WS broadcast event — i.e. an event
dict in the shape produced by
``WebSocketProtocol.create_event(event, data, room)`` — exercises the
public render function on it, and asserts the produced HTML attributes.
"""
from __future__ import annotations

import asyncio
import time
from pathlib import Path
from typing import Any

import pytest
from fastblocks.websocket.a11y_bridge import render_broadcast_as_a11y

# Bounded event types the bridge recognises per Δ10 routing. ``miss`` is
# the canonical delta-driven a11y event; everything else falls through
# to the default polite/status renderer (provided the event carries
# ``escaped != False``).
_A11Y_EVENT_TYPES: frozenset[str] = frozenset({"miss"})


def _make_broadcast_event(
    event: str,
    data: dict[str, Any],
    room: str = "global",
) -> dict[str, Any]:
    """Construct a real WebSocket broadcast event payload.

    Mirrors the shape of ``mcp_common.websocket.protocol.WebSocketProtocol
    .create_event(event, data, room)``: ``{type, event, data, room}``.
    Used by the dynamic test so the bridge sees an event shape that
    would actually appear on the WS wire — not a synthetic dict.
    """
    return {
        "type": "event",
        "event": event,
        "data": data,
        "room": room,
    }


def test_module_declares_all() -> None:
    """Per module pattern: every public module declares ``__all__``."""
    import fastblocks.websocket.a11y_bridge as mod

    assert hasattr(mod, "__all__"), (
        "a11y_bridge.py must declare __all__"
    )
    assert "render_broadcast_as_a11y" in mod.__all__, (
        f"render_broadcast_as_a11y must be in a11y_bridge.__all__; "
        f"got {mod.__all__!r}"
    )


def test_dynamic_ws_broadcast_event_renders_polite_aria_live() -> None:
    """Dynamic: a real WS broadcast event renders aria-live text.

    Fires an event shaped like ``WebSocketProtocol.create_event`` would
    produce, invokes ``render_broadcast_as_a11y`` on it, and asserts
    the produced HTML matches the corrected Δ10 routing contract
    (aria-live=polite + role=status, with the required aria-relevant
    / aria-atomic / data-fb-aria-live attribute set).
    """
    event = _make_broadcast_event(
        "miss",
        {
            "component_id": "c-42",
            "message": "Form validation failed on email field.",
            "escaped": True,
        },
        room="global",
    )

    html = render_broadcast_as_a11y(event)

    assert html is not None, (
        "miss event must render an aria-live update; got None"
    )
    assert 'aria-live="polite"' in html, (
        f"miss event must declare aria-live=polite per corrected Δ10 "
        f"routing; got: {html!r}"
    )
    assert 'role="status"' in html, (
        f"miss event must declare role=status per corrected Δ10 "
        f"routing; got: {html!r}"
    )


def test_dynamic_ws_broadcast_event_uses_modern_css_clip_path() -> None:
    """Assert the bundled CSS uses the modern visually-hidden technique.

    The brief pins the contract to ``clip-path: inset(50%)`` (the
    modern, accessible visually-hidden pattern) — NOT the legacy
    ``clip: rect(...)`` or 1px-border hacks. The test reads the file
    shipped at ``fastblocks/websocket/static/a11y_bridge.css`` so any
    regression to a legacy technique trips the assertion immediately.
    """
    css_path = (
        Path(__file__).parent.parent.parent
        / "fastblocks"
        / "websocket"
        / "static"
        / "a11y_bridge.css"
    )
    css = css_path.read_text(encoding="utf-8")

    assert "clip-path: inset(50%)" in css, (
        f"a11y_bridge.css must use the modern clip-path: inset(50%) "
        f"visually-hidden technique; got: {css!r}"
    )
    assert "clip: rect(" not in css, (
        f"a11y_bridge.css must NOT use the legacy clip: rect(...) "
        f"technique (deprecated since 2016); got: {css!r}"
    )


def test_routing_escaped_false_returns_none() -> None:
    """Per Δ10: ``escaped=false`` events MUST be dropped (logs only).

    An event with ``data.escaped == False`` is a signal that the
    renderer bypassed sanitisation — surfacing it to screen readers
    could double-announce already-escaped text. The bridge MUST
    return ``None`` and MUST NOT increment the dropped counter (the
    drop is the *expected* path; only the rate-limit drop increments
    the dropped_total counter).
    """
    event = _make_broadcast_event(
        "miss",
        {"component_id": "c-99", "message": "raw", "escaped": False},
        room="global",
    )

    assert render_broadcast_as_a11y(event) is None, (
        "escaped=False event must return None (logs only); "
        "got non-None response"
    )


def test_routing_miss_uses_polite_status() -> None:
    """Per corrected Δ10: ``miss`` → ``aria-live=polite`` + ``role=status``.

    The earlier (incorrect) routing mapped `miss` to `assertive` /
    `alert`. That pairing was wrong — `alert` interrupts whatever the
    screen reader is currently announcing, which is too aggressive for
    incremental component updates. The corrected routing uses polite /
    status so updates are announced only at the next idle moment.
    """
    html = render_broadcast_as_a11y(
        _make_broadcast_event(
            "miss",
            {"component_id": "c-1", "message": "ok", "escaped": True},
        ),
    )

    assert html is not None
    assert 'aria-live="polite"' in html
    assert 'role="status"' in html
    # Defensive: the corrected routing must NOT regress to the prior
    # assertive/alert pairing.
    assert 'aria-live="assertive"' not in html, (
        f"corrected Δ10 routing forbids aria-live=assertive; got: {html!r}"
    )
    assert 'role="alert"' not in html, (
        f"corrected Δ10 routing forbids role=alert; got: {html!r}"
    )


def test_aria_relevant_additions_attribute_present() -> None:
    """Per brief: ``aria-relevant="additions"`` MUST appear on the live region.

    The ``additions`` value tells the screen reader to announce
    inserted text content but NOT removals — the appropriate signal
    for incremental WS broadcasts (a slide-in toast text should be
    announced; the disappearance of the same toast should not).
    """
    html = render_broadcast_as_a11y(
        _make_broadcast_event(
            "miss",
            {"component_id": "c-2", "message": "x", "escaped": True},
        ),
    )

    assert html is not None
    assert 'aria-relevant="additions"' in html, (
        f"bridge MUST emit aria-relevant=additions per Δ13; "
        f"got: {html!r}"
    )


def test_aria_atomic_true_attribute_present() -> None:
    """Per brief: ``aria-atomic="true"`` MUST appear on the live region.

    ``aria-atomic=true`` causes the screen reader to announce the
    ENTIRE region contents on every change, not just the diff — the
    correct default for a status region that may swap one message
    for another.
    """
    html = render_broadcast_as_a11y(
        _make_broadcast_event(
            "miss",
            {"component_id": "c-3", "message": "y", "escaped": True},
        ),
    )

    assert html is not None
    assert 'aria-atomic="true"' in html, (
        f"bridge MUST emit aria-atomic=true per Δ13; got: {html!r}"
    )


@pytest.mark.asyncio
async def test_rate_limit_5_per_second_drops_excess() -> None:
    """Rate-limit contract per Δ39-α: ≤5 mutations/sec, drops rest.

    Sends 100 events to the bridge within a single wall-clock second
    and asserts:

      1. ≤5 events returned HTML (mutation budget honored).
      2. ``fastblocks_a11y_bridge_dropped_total{region=...}`` counter
         incremented for the drops.

    The dropped counter is the only on-the-wire observability signal
    for the rate-limit decision (operators see the drops without
    having to inspect log streams).
    """
    # Import lazily so the test starts cleanly even if the bridge
    # has not yet been implemented (RED phase: this still fails on
    # ImportError, which is the point of running the test first).
    from fastblocks.observability.registry import ObservabilityRegistry
    from fastblocks.websocket import a11y_bridge as bridge

    # Reset the per-region rate-limit buckets so a previous test in
    # the same pytest process does not contaminate this test's
    # budget. Fire 6 warm-up events so the first event drops on the
    # 6th call (budget = 5) — that triggers the lazy counter init
    # AND guarantees the dropped counter is registered before we
    # snapshot its value.
    bridge.reset_rate_limit_buckets()
    warmup_events = [
        _make_broadcast_event(
            "miss",
            {"component_id": f"warm-{i}", "message": "w", "escaped": True},
            room="global",
        )
        for i in range(6)
    ]
    for event in warmup_events:
        render_broadcast_as_a11y(event)

    # The dropped counter must exist in the registry; if the bridge
    # module has not registered it, the test fails fast with a clear
    # assertion.
    assert (
        "fastblocks_a11y_bridge_dropped_total"
        in ObservabilityRegistry._names  # type: ignore[attr-defined]
    ), (
        "fastblocks_a11y_bridge_dropped_total must be registered in "
        "ObservabilityRegistry before the rate-limit test runs"
    )

    inner_counter = bridge.get_dropped_counter()._inner
    region_label = "global"
    before = inner_counter.labels(region=region_label)._value.get()

    # Reset again so the warmup does not consume a budget slot for
    # the 100-event burst that follows.
    bridge.reset_rate_limit_buckets()

    region_events: list[dict[str, Any]] = [
        _make_broadcast_event(
            "miss",
            {"component_id": f"c-{i}", "message": "x", "escaped": True},
            room="global",
        )
        for i in range(100)
    ]

    start = time.perf_counter()
    rendered = [
        render_broadcast_as_a11y(event)
        for event in region_events
    ]
    elapsed = time.perf_counter() - start

    non_none = [r for r in rendered if r is not None]
    assert len(non_none) <= 5, (
        f"bridge MUST render at most 5 mutations per second per region; "
        f"got {len(non_none)} non-None responses in {elapsed:.3f}s "
        f"(100 events fired)"
    )

    # The dropped counter MUST have incremented by at least
    # (100 - len(non_none)) — i.e. every event that did NOT render
    # is accounted for in the dropped counter.
    after = inner_counter.labels(region=region_label)._value.get()
    expected_increment = 100 - len(non_none)
    actual_increment = after - before
    assert actual_increment >= expected_increment, (
        f"fastblocks_a11y_bridge_dropped_total{{region={region_label!r}}} "
        f"must increment by ≥{expected_increment} (100 events - "
        f"{len(non_none)} rendered); observed delta: {actual_increment}"
    )

    # Sanity: the test must actually exercise the rate limit. If the
    # 100 events completed in >1.5s the wall-clock budget does not
    # apply (the bridge's budget is a per-second window), so we just
    # document the elapsed time without asserting on it.
    _ = elapsed

    # Yield once so the async fixture annotation is honoured even on
    # collections where the body does not await.
    await asyncio.sleep(0)


def test_region_label_in_known_labels() -> None:
    """Per Task 13 brief: the ``region`` label must be in the allowlist.

    The cardinality lint refuses counters whose ``labelnames`` tuple
    contains a label not in :data:`_KNOWN_LABELS`. Without this
    registration the dropped counter would trip the CI gate.
    """
    from fastblocks.observability._label_allowlist import _KNOWN_LABELS

    assert "region" in _KNOWN_LABELS, (
        f"region label must be registered in _KNOWN_LABELS; "
        f"observed keys: {sorted(_KNOWN_LABELS.keys())!r}"
    )

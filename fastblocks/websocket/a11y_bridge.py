"""WebSocket → aria-live accessibility bridge for FastBlocks.

Per Δ10 (CORRECTED WCAG routing) + Δ13 + Δ39-α:

The ``render_broadcast_as_a11y`` function converts a WebSocket broadcast
event into an HTML payload suitable for an ARIA live region on the
client. The client injects the returned HTML into a
``<div role="status" aria-live="polite" aria-atomic="true"
data-fb-aria-live="true" aria-relevant="additions"
class="sr-only--fastblocks-a11y-bridge">`` element and assistive
technologies announce the text content.

CORRECTED WCAG routing (Δ10 supersedes the prior misrouting)
-------------------------------------------------------------

The earlier (incorrect) routing paired ``miss`` with
``aria-live="assertive"`` + ``role="alert"``. That pairing was wrong:
``alert`` interrupts whatever the screen reader is currently
announcing, which is too aggressive for incremental component
updates — a brief validation hint should wait until the next idle
moment, not interrupt a reading user's progress message. The corrected
routing uses the polite/status pairing:

  * ``event == "miss"``  → ``aria-live="polite"`` + ``role="status"``
    (NOT assertive/alert).
  * ``data.escaped == False`` → ``None`` (logs only; the renderer
    bypassed sanitisation, so re-surfacing the text to assistive
    tech would double-announce already-escaped content).

The routing table is deliberately narrow: the bridge accepts the
two-state ``miss`` / fallback-to-polite pair so future event types
inherit the polite default without bypassing the WCAG contract.

Rate-limit budget (Δ39-α)
-------------------------

The bridge enforces a per-region mutation budget of ≤5 renders per
wall-clock second. When an event would exceed the budget the bridge
emits ``fastblocks_a11y_bridge_dropped_total{region=...}`` and
returns ``None``. The dropped counter is the only on-the-wire
observability signal for the rate-limit decision; operators see the
drops without having to grep logs.

The budget is a per-region sliding window: each region maintains its
own timestamp list of the last 5 mutations. An event is rendered
when its arrival would NOT cause the region to exceed 5 renders in
the last 1.0 seconds.

CSS contract
------------

The companion ``fastblocks/websocket/static/a11y_bridge.css`` provides
the visually-hidden stylesheet that hides the live region from sighted
users while keeping it readable by assistive tech. The CSS uses the
modern ``clip-path: inset(50%)`` pattern (NOT the legacy ``clip:
rect(...)`` or 1px-border hacks).
"""
from __future__ import annotations

import time
from html import escape
from threading import Lock
from typing import Any

from fastblocks.observability.counters import Counter
from fastblocks.observability.loggers import get_logger

# Mutable per-process state guarded by ``_REGION_LOCK``. Tests that
# need a deterministic mutation budget should reset the buckets
# (or use the ``reset_rate_limit_buckets()`` helper) before firing.
_REGION_LOCK: Lock = Lock()

# Wall-clock budget: render at most 5 mutations per region per 1.0s.
_MUTATIONS_PER_SECOND: int = 5
_WINDOW_SECONDS: float = 1.0

__all__ = [
    "get_dropped_counter",
    "render_broadcast_as_a11y",
    "reset_rate_limit_buckets",
]


def _init_drop_counter() -> Counter:
    """Lazily initialise the dropped counter for the bridge.

    Per Task 12's sentry_bridge lazy-init pattern: a module-level
    Counter would crash on pytest module reloads (``import-mode=importlib``
    reloads test modules per test, blowing away ``sys.modules`` and
    re-executing the bridge module body, which would re-raise the
    prometheus_client ``Duplicated timeseries`` ValueError on the
    second registration. Lazy init runs exactly once per process
    and survives module reloads because the cached reference lives
    on the module dictionary (``a11y_bridge._DROPPED_COUNTER``).
    """
    return Counter(
        "fastblocks_a11y_bridge_dropped_total",
        "Number of a11y_bridge events dropped due to the per-region "
        "rate-limit budget (5 mutations/second).",
        labelnames=("region",),
    )


def _ensure_drop_counter_loaded() -> Counter:
    """Module-dictionary cache pattern (matches sentry_bridge)."""
    global _DROPPED_COUNTER  # ty: ignore[unresolved-global]
    try:
        return _DROPPED_COUNTER  # type: ignore[name-defined]
    except NameError:
        _DROPPED_COUNTER = _init_drop_counter()
        return _DROPPED_COUNTER


def get_dropped_counter() -> Counter:
    """Return the lazily-initialised dropped-events counter.

    Public accessor (mirrors the lazy pattern of
    ``sentry_bridge._get_disabled_counter()``). Forces the prometheus
    client ``Counter`` to construct on first call so test surfaces
    that need to read the counter's labelled children do not have to
    fire a warm-up event just to trigger init.

    The Counter is cached on the module dictionary (``a11y_bridge
    ._DROPPED_COUNTER``) so subsequent calls return the same object —
    matches the idempotency contract of every other Counter wrapper
    in the codebase.
    """
    return _ensure_drop_counter_loaded()


def _normalise_region(room: Any) -> str:
    """Map a WS event's ``room`` field to one of the bounded label values.

    The dropped counter's ``region`` label is bounded by
    ``fastblocks.observability._label_allowlist.WebsocketRegion`` to
    the four canonical rooms the FastBlocks WS server emits
    (``ui:<id>`` collapses to ``ui``, ``component:<id>`` to
    ``component``, ``state``, ``global``). Any non-string or
    out-of-set value falls back to ``global`` so a malformed event
    cannot blow up the label cardinality.
    """
    if not isinstance(room, str):
        return "global"
    if room.startswith("ui:"):
        return "ui"
    if room.startswith("component:"):
        return "component"
    if room == "state":
        return "state"
    if room == "global":
        return "global"
    return "global"


def _consume_budget(region: str) -> bool:
    """Decide whether ``region`` may consume one of its mutation slots.

    Returns ``True`` if the mutation is within budget (and records the
    timestamp so the budget window slides), ``False`` otherwise. The
    per-region timestamp list is bounded to ``_MUTATIONS_PER_SECOND``
    entries; the oldest entry is evicted on each call so the window
    slides correctly across seconds.
    """
    now = time.perf_counter()
    bucket = _REGION_BUCKETS.setdefault(region, [])
    with _REGION_LOCK:
        # Drop expired entries first; any timestamp older than the
        # 1.0s window no longer counts against the budget.
        cutoff = now - _WINDOW_SECONDS
        while bucket and bucket[0] < cutoff:
            bucket.pop(0)
        if len(bucket) >= _MUTATIONS_PER_SECOND:
            return False
        bucket.append(now)
        return True


def reset_rate_limit_buckets() -> None:
    """Clear all per-region rate-limit buckets.

    Test-only helper: pytest tests that fire >5 events in a single
    wall-clock second would otherwise have a contaminated budget for
    the next test in the same process. Exposed via ``__all__`` so
    the test surface stays consistent with the public API.
    """
    with _REGION_LOCK:
        _REGION_BUCKETS.clear()


# Per-region timestamp buckets. Populated lazily on the first event
# for a given region; cleared by ``reset_rate_limit_buckets()``.
_REGION_BUCKETS: dict[str, list[float]] = {}


def _extract_message(data: Any) -> str:
    """Extract the human-readable message from a WS event's ``data`` payload.

    Bridges the contract between ``FastblocksWebSocketServer
    .broadcast_*`` (which always sets ``data.message`` for status
    updates) and the ARIA live region. Defensive against missing
    ``message`` keys — returns an empty string rather than raising,
    so a malformed event surfaces as a silent no-op rather than a
    crash.
    """
    if not isinstance(data, dict):
        return ""
    message = data.get("message")
    if isinstance(message, str):
        return message
    return ""


def render_broadcast_as_a11y(event: dict[str, Any]) -> str | None:
    """Render a WS broadcast event as an aria-live region update.

    Per the corrected Δ10 routing table:

      * ``event.event == "miss"`` with ``data.escaped != False`` →
        ``<div role="status" aria-live="polite" aria-atomic="true"
        data-fb-aria-live="true" aria-relevant="additions"
        class="sr-only--fastblocks-a11y-bridge">{message}</div>``.
      * ``event.event == "miss"`` with ``data.escaped == False`` →
        ``None`` (logs only; the renderer bypassed sanitisation so
        re-surfacing the text would double-announce).
      * Any other event type with a non-empty payload → the same
        polite/status update (future event types inherit the safe
        default rather than bypassing the WCAG contract).
      * Events exceeding the per-region 5/sec budget → ``None`` AND
        ``fastblocks_a11y_bridge_dropped_total{region=...}`` increments.

    Parameters
    ----------
    event : dict[str, Any]
        A WebSocket broadcast event in the shape produced by
        ``mcp_common.websocket.WebSocketProtocol.create_event(event,
        data, room)``: ``{type, event, data, room}``.

    Returns:
    -------
    str | None
        The HTML string to inject into the live region, or ``None``
        when the event should be dropped (escaped=false, no payload,
        or rate-limited).
    """
    if not isinstance(event, dict):
        return None

    data = event.get("data")
    if not isinstance(data, dict):
        return None

    # Per Δ10: ``escaped=false`` means the renderer bypassed
    # sanitisation, so re-surfacing the text to assistive tech would
    # double-announce already-escaped content. Drop (log only).
    escaped = data.get("escaped", True)
    if escaped is False:
        # structlog reserves the ``event`` kwarg as the log-event
        # name, so the WS event type is forwarded as ``ws_event``
        # instead of clashing with the structlog convention.
        get_logger("fastblocks.websocket.a11y_bridge").debug(
            "a11y_bridge_dropped_escaped_false",
            ws_event=event.get("event"),
            component_id=data.get("component_id"),
        )
        return None

    message = _extract_message(data)
    if not message:
        return None

    region = _normalise_region(event.get("room"))

    # Rate-limit gate. The dropped counter increments BEFORE the
    # early-return so the observability signal survives the drop.
    if not _consume_budget(region):
        _ensure_drop_counter_loaded().inc(1.0, region=region)
        # structlog reserves ``event`` for the log-event name; the
        # WS event type is forwarded as ``ws_event`` to avoid the
        # ``got multiple values for argument 'event'`` TypeError
        # ``BoundLogger._proxy_to_logger`` raises when the call has
        # both a positional event name and a kwarg named ``event``.
        get_logger("fastblocks.websocket.a11y_bridge").debug(
            "a11y_bridge_dropped_rate_limit",
            region=region,
            ws_event=event.get("event"),
        )
        return None

    # Corrected Δ10 routing: polite + status (NOT assertive + alert).
    # ``aria-atomic=true`` re-reads the entire region on every
    # change; ``aria-relevant=additions`` announces inserts but not
    # removals. ``data-fb-aria-live=true`` is the fastblocks-side
    # hook so client-side tooling can target the live region.
    safe_message = escape(message, quote=True)
    return (
        f'<div role="status" aria-live="polite" aria-atomic="true" '
        f'data-fb-aria-live="true" aria-relevant="additions" '
        f'class="sr-only--fastblocks-a11y-bridge">{safe_message}</div>'
    )

"""Task 8 — MCP tool observability bridge.

Per Δ37: ``instrument_tool(tool_name, func)`` wraps an MCP tool
function so every invocation emits:

  * Counter  ``fastblocks_mcp_tool_invocations_total``
              labels: ``(tool_name, status)`` — status ∈ {"ok", "error"}
  * Histogram ``fastblocks_mcp_tool_duration_seconds``
              labels: ``(tool_name,)``
              buckets: latency-tuned tuples (seconds)

Per Δ49: ``func.__wrapped_by_instrument_tool__ = True`` after wrapping;
the marker is checked on entry so double-wrap is a no-op (idempotency).

Wraps BOTH registration paths:
  - ``fastblocks/mcp/server.py`` → calls ``register_fastblocks_tools``
    which iterates the 7-tool dict and calls ``register(name)(func)``.
    That call site becomes ``register(name)(instrument_tool(name, func))``.
  - ``fastblocks/mcp/capabilities.py`` → 7 more ``server.tool(name, ...)``
    calls in the per-capability ``register_*_capability`` functions.
    Each gets the same ``register(name)(instrument_tool(name, func))``
    shape.

``tool_name`` is the registered MCP name (string). It may differ from
``func.__name__`` — never read the latter for the metric label, always
use the passed ``tool_name`` argument.
"""
from __future__ import annotations

import functools
import time
from collections.abc import Callable
from typing import Any

from fastblocks.observability.counters import Counter, Histogram
from fastblocks.observability.loggers import get_logger

__all__ = [
    "instrument_tool",
]

_logger = get_logger("fastblocks.mcp.observability")

# Latency buckets tuned for in-process MCP tool calls (milliseconds
# to single-digit seconds). Exposed as a module-level constant so tests
# can reference the same buckets the production wrapper uses.
_DURATION_BUCKETS: tuple[float, ...] = (
    0.001,
    0.005,
    0.01,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
)


def _build_metrics() -> tuple[Counter, Histogram]:
    """Construct the canonical Counter + Histogram for MCP tools.

    Centralized so a test that imports ``instrument_tool`` triggers the
    same registration path the production wrappers use.

    Both Counter and Histogram self-register their names with
    ``ObservabilityRegistry`` via ``__init__`` (Wave 6 Task 5). Name
    collisions surface as ``MetricNameCollisionError`` — same posture
    for both metric types.
    """
    invocations = Counter(
        "fastblocks_mcp_tool_invocations_total",
        "MCP tool invocation counts",
        ("tool_name", "tool_status"),
    )
    duration = Histogram(
        "fastblocks_mcp_tool_duration_seconds",
        "MCP tool duration histogram",
        ("tool_name",),
        _DURATION_BUCKETS,
    )
    return invocations, duration


_INVOCATIONS_COUNTER, _DURATION_HISTOGRAM = _build_metrics()


def instrument_tool(
    tool_name: str,
    func: Callable[..., Any],
) -> Callable[..., Any]:
    """Wrap ``func`` so every invocation emits Counter + Histogram.

    Per Δ49: if ``func.__wrapped_by_instrument_tool__`` is True, return
    ``func`` unchanged. The marker is set on the wrapper after the
    first call so re-wrapping is idempotent (Δ47 compatibility).

    Per Δ37: ``tool_name`` is the canonical MCP tool name (string).
    Do NOT read ``func.__name__`` for the metric label — aliases must
    preserve the registered name.

    The wrapper preserves ``func``'s metadata (``__name__``, ``__doc__``,
    ``__wrapped__``) via ``functools.wraps`` so introspection tools see
    the original function. The idempotency marker is attached to the
    wrapper itself.
    """
    # Idempotency guard (Δ49): if the function is already wrapped,
    # return it as-is. Avoids double-emission when callers (or our
    # own server.py / capabilities.py wiring) attempt to wrap twice.
    if getattr(func, "__wrapped_by_instrument_tool__", False):
        return func

    @functools.wraps(func)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.monotonic()
        status = "ok"
        try:
            return await func(*args, **kwargs)
        except Exception:
            status = "error"
            raise
        finally:
            elapsed = time.monotonic() - start
            try:
                _INVOCATIONS_COUNTER.inc(tool_name=tool_name, tool_status=status)
                _DURATION_HISTOGRAM.observe(elapsed, tool_name=tool_name)
            except Exception:
                # Per the wrapper's transparency contract: metric
                # emission failures must NEVER mask a tool caller's
                # result (Δ37). Log at debug and proceed; the caller
                # sees the original return value or exception.
                _logger.debug(
                    "mcp_tool_metric_emission_failed",
                    tool_name=tool_name,
                    tool_status=status,
                    exc_info=True,
                )

    # Δ49: idempotency marker — checked on entry to ``instrument_tool``.
    wrapper.__wrapped_by_instrument_tool__ = True  # type: ignore[attr-defined]  # ty: ignore[unresolved-attribute]
    return wrapper

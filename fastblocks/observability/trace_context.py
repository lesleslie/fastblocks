"""Trace context propagation.

Per ADR 0013 Decision 17: structlog's `merge_contextvars` reads
exclusively from stdlib `contextvars` storage (ContextVars whose
names start with `STRUCTLOG_KEY_PREFIX`); `bind_contextvars`
writes to those ContextVars. Raw `ContextVar.set()` writes to
unrelated ContextVars are invisible to `merge_contextvars`.

The public API does BOTH:
  1. `set(ctx)` writes to `_current_trace` (the typed, internal
     ContextVar that consumers can read directly via `get()`).
  2. `bind_contextvars(**asdict(ctx))` writes to structlog's
     ContextVars so the next log line carries trace_id/span_id
     automatically.

Returns a `Token` from the typed `set` so callers can pair with
`reset(token)` for token-safe de-allocation.
"""
from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass

import structlog


@dataclass(frozen=True)
class TraceContext:
    """Immutable snapshot of an active trace span."""

    trace_id: str
    span_id: str
    parent_span_id: str | None = None


_current_trace: ContextVar[TraceContext | None] = ContextVar(
    "fastblocks_trace", default=None,
)


def get() -> TraceContext | None:
    """Return the currently-active trace context, or None."""
    return _current_trace.get()


def set(ctx: TraceContext) -> Token:
    """Set the active trace context.

    Both writes happen:
    - The internal ContextVar (typed, retrievable via `get()`).
    - structlog's per-thread contextvars (via `bind_contextvars`),
      so `merge_contextvars` makes the trace_id/span_id visible
      to log emission without a custom processor.

    Returns a `Token` from the raw ContextVar.set so callers
    can pair with `reset(token)` for token-safe de-allocation.
    """
    token = _current_trace.set(ctx)
    structlog.contextvars.bind_contextvars(
        trace_id=ctx.trace_id,
        span_id=ctx.span_id,
        parent_span_id=ctx.parent_span_id,
    )
    return token


def reset(token: Token) -> None:
    """Reset the typed ContextVar to its prior value and clear structlog's."""
    _current_trace.reset(token)
    structlog.contextvars.unbind_contextvars(
        "trace_id", "span_id", "parent_span_id",
    )


# Module-public names re-exported via __init__.py
set_trace_context = set
reset_trace_context = reset
get_trace_context = get
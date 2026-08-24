"""Task 11 — OtelMiddleware: OUTERMOST HTTP middleware via Starlette reverse.

Per Δ45/Δ48 + P1-5: ``OtelMiddleware`` is the OUTERMOST HTTP middleware
on a FastBlocks application. Starlette reverses ``user_middleware`` when
building the ASGI chain (the LAST registered entry becomes the OUTERMOST
wrapper), so this middleware MUST be registered via ``app.add_middleware(
OtelMiddleware)`` AFTER every other ``app.add_middleware(...)`` call.

Per Task 11 brief (binding requirements):

  * Inherits from Starlette's ``BaseHTTPMiddleware`` (high-level API).
  * On entry (``dispatch``):
      - Starts an OTel span via ``get_tracer("fastblocks.observability").
        start_as_current_span("http.request")``.
      - Reads the active ``SpanContext`` and formats ``trace_id`` /
        ``span_id`` as hex strings via ``opentelemetry.trace.
        format_trace_id`` / ``format_span_id``.
      - Calls ``trace_context.set(TraceContext(...))`` to bind the
        trace into the typed ``_current_trace`` ContextVar.
      - Saves the returned ``Token`` for the ``finally`` block.
  * On exit (``finally`` block):
      - Sets ``http.status_code`` on the active span.
      - Always calls ``trace_context.reset(token)`` to clear the binding
        so the next request does not inherit the prior trace context.
  * Per P1-5: the ``trace_context.reset(token)`` call is wrapped in
    try/except; on failure, ``fastblocks_otel_middleware_reset_failed_total{
    reason}`` is incremented where ``reason`` is the exception class
    name. The Literal ``ErrorReason`` in ``_label_allowlist`` bounds
    the cardinality of the ``reason`` label.

Why ``BaseHTTPMiddleware`` (not pure ASGI): Starlette's
``BaseHTTPMiddleware`` provides the high-level ``dispatch(self,
request, call_next)`` shape so we can integrate with the OTel
``start_as_current_span`` context manager idiomatically. Pure ASGI
would require manual ``__aenter__`` / ``__aexit__`` plumbing and lose
the readable ``with span: ...`` form.
"""
from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp
from fastblocks.observability.counters import Counter
from fastblocks.observability.loggers import get_logger
from fastblocks.observability.trace_context import (
    TraceContext,
    reset_trace_context,
    set_trace_context,
)

if TYPE_CHECKING:
    from contextvars import Token

    from opentelemetry.trace import Span


# Per P1-5: ``fastblocks_otel_middleware_reset_failed_total{reason}``.
# ``reason`` is bounded to ``ErrorReason`` in
# ``fastblocks.observability._label_allowlist``; the counter only
# fires from inside the ``finally`` block's try/except so the labelled
# child only ever sees the exception class names ``reset()`` can
# actually emit (RuntimeError, OSError, ValueError, TypeError, Exception).
# Module-level so the per-process state survives across multiple
# FastBlocksApp instances within the same pytest process — matches
# the /metrics dispatch counter pattern (Task 9).
_RESET_FAILED_COUNTER = Counter(
    "fastblocks_otel_middleware_reset_failed_total",
    "Number of OtelMiddleware trace_context.reset(token) failures, "
    "labelled by exception class name.",
    labelnames=("reason",),
)

_logger = get_logger("fastblocks.observability.otel_middleware")


def _format_trace_context(span: Span) -> TraceContext:
    """Build a ``TraceContext`` from an active OTel ``Span``.

    Reads ``span.get_span_context()`` (returns a ``SpanContext`` whose
    ``trace_id`` and ``span_id`` are 128-bit / 64-bit integers) and
    formats both as zero-padded lowercase hex strings via OTel's
    canonical ``format_trace_id`` / ``format_span_id`` helpers. Returns
    a fresh ``TraceContext`` ready for ``trace_context.set``.

    The OTel SDK populates ``trace_id`` / ``span_id`` as ``0`` when
    the underlying ``SpanContext`` is invalid (no active tracer
    provider). In that case ``format_*_id(0)`` returns ``"000000000000
    0000000000000000"`` / ``"0000000000000000"`` — the spec-compliant
    placeholder; downstream consumers that need a non-zero trace ID
    can detect the all-zeros string and discard.
    """
    from opentelemetry.trace import format_span_id, format_trace_id

    span_context = span.get_span_context()
    return TraceContext(
        trace_id=format_trace_id(span_context.trace_id),
        span_id=format_span_id(span_context.span_id),
    )


class OtelMiddleware(BaseHTTPMiddleware):
    """Outermost HTTP middleware that binds an OTel span to trace_context.

    Per Δ48: registered LAST in ``user_middleware`` so Starlette reverses
    it to be the OUTERMOST. Every request runs through ``dispatch`` and
    inherits a fresh trace context; the ``finally`` block always clears
    the binding so requests do not leak trace state into each other.

    The ``dispatch`` method:

      1. Opens an OTel ``http.request`` span (the OTLP root span when
         no parent is present; otherwise a child of any upstream tracer).
      2. Sets ``trace_context._current_trace`` to the formatted
         ``TraceContext`` (the typed, internal ContextVar), and saves
         the ``Token`` for symmetric ``reset`` later.
      3. Awaits ``call_next(request)``.
      4. On success: sets ``http.status_code`` to the response code.
         On exception: records the exception on the span and sets the
         attribute to ``500`` (Starlette's default 500 rendering code)
         so the span always carries a status_code for the /metrics
         scraper.
      5. The ``finally`` block always invokes
         ``trace_context.reset(token)`` to clear the binding. Per P1-5,
         a failure here increments
         ``fastblocks_otel_middleware_reset_failed_total{reason}`` with
         the exception class name so the failure mode is observable
         without crashing the request.
    """

    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Lazy import the OTel tracer so the lean-install guard in
        # ``tracer.py`` raises ``MissingDependencyError`` only when this
        # middleware actually executes (not at module import time). The
        # guard pattern is the same one ``fastblocks.observability.
        # counters`` uses for prometheus_client.
        from fastblocks.observability.tracer import get_tracer

        tracer = get_tracer("fastblocks.observability")
        token: Token | None = None
        with tracer.start_as_current_span("http.request") as span:
            # Bind trace_context BEFORE call_next so inner handlers
            # (route handlers, downstream middleware) observe the
            # current trace via ``get_trace_context()`` / ``exemplar()``.
            try:
                token = set_trace_context(_format_trace_context(span))
            except Exception:
                # If the binding itself fails, log + proceed without a
                # token; the ``finally`` block handles the no-token
                # case (no-op reset). Failure here does NOT short-
                # circuit the request — observability must not break
                # the request path.
                _logger.exception(
                    "otel_middleware_trace_context_set_failed",
                    path=request.url.path,
                )
                token = None
            try:
                response = await call_next(request)
            except Exception as exc:
                # On exception: record the exception on the span and
                # set http.status_code=500 (Starlette's default). The
                # exception propagates so Starlette's ExceptionMiddleware
                # (also outermost by Δ45 default) can render the 500.
                try:
                    span.record_exception(exc)
                except Exception:
                    # Per the brief: span writes must NEVER break the
                    # request path. Log at debug and continue.
                    _logger.debug(
                        "otel_middleware_record_exception_failed",
                        path=request.url.path,
                        exc_info=True,
                    )
                try:
                    span.set_attribute("http.status_code", 500)
                except Exception:
                    _logger.debug(
                        "otel_middleware_status_code_set_failed",
                        path=request.url.path,
                        exc_info=True,
                    )
                raise
            else:
                try:
                    span.set_attribute(
                        "http.status_code", response.status_code,
                    )
                except Exception:
                    # Per the brief: span attribute writes must NEVER
                    # break the request path. Log at debug and return
                    # the response.
                    _logger.debug(
                        "otel_middleware_status_code_set_failed",
                        path=request.url.path,
                        exc_info=True,
                    )
                return response
            finally:
                # Per P1-5: reset is wrapped in try/except. On failure,
                # the counter is incremented with the exception class
                # name so operators see reset() drift without grepping
                # logs. The reset is best-effort — leaving a stale
                # binding for the next request is observable via the
                # counter but never breaks the request path.
                if token is not None:
                    try:
                        reset_trace_context(token)
                    except Exception as exc:
                        _RESET_FAILED_COUNTER.inc(
                            1.0, reason=type(exc).__name__,
                        )
                        _logger.exception(
                            "otel_middleware_reset_failed",
                            path=request.url.path,
                        )


__all__ = ["OtelMiddleware"]

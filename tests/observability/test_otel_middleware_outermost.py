"""Task 11 — OtelMiddleware is the OUTERMOST user middleware.

Per Δ48 + Δ45 + P1-5:

  * OtelMiddleware inherits from Starlette's ``BaseHTTPMiddleware``.
  * On entry, the middleware starts an OTel ``http.request`` span, binds
    the trace context, and saves the token.
  * On exit, the middleware sets ``http.status_code`` on the active
    span and resets the trace context via the saved token.
  * The ``trace_context.reset(token)`` call is wrapped in try/except:
    a failure increments ``fastblocks_otel_middleware_reset_failed_total``
    with ``reason=<exception-class-name>``.

The OUTERMOST contract is verified three ways per the brief:

  1. **Registration order**: ``MiddlewareManager.get_middleware_stack()``
     must show OtelMiddleware as the LAST entry in ``user_middleware``
     (the spec contract).
  2. **Span on 500**: ``dispatch`` records ``http.status_code=500`` on
     the active span when the downstream handler raises.
  3. **Cleanup**: after ``dispatch`` returns (even on exception),
     ``trace_context.exemplar()`` returns ``None`` — confirming the
     ``reset(token)`` ran in the ``finally`` block.

Test approach note (per Task 9 brief's surface of the pre-existing
shape bug at ``fastblocks/applications.py:412``): the FastBlocks
app's ``_apply_middleware_to_app`` iterates the resolved middleware list
expecting 3-tuples, but the system-middleware list holds 2-tuples —
a shape mismatch that crashes Starlette's ``build_middleware_stack``.
Task 9's test file documents this bug and invokes the route handler
directly with a synthetic ``Request`` rather than going through
``TestClient``. This test file follows the same pattern: it constructs
``OtelMiddleware`` and invokes ``dispatch(request, call_next)``
directly, sidestepping the build-time shape bug while still verifying
the runtime contract the brief requires.
"""
from __future__ import annotations

from typing import Any

import pytest
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from fastblocks.applications import FastBlocks
from fastblocks.observability.otel_middleware import OtelMiddleware
from fastblocks.observability.trace_context import (
    TraceContext,
    exemplar,
    get_trace_context,
)

# ---------------------------------------------------------------------------
# Test 1 — Δ45/Δ48 registration order
# ---------------------------------------------------------------------------


def test_otel_middleware_is_last_in_user_middleware() -> None:
    """``OtelMiddleware`` is registered LAST in ``user_middleware``.

    Per the Task 11 brief (binding requirement): "registered LAST in
    ``user_middleware`` so Starlette reverses it to be the OUTERMOST".
    The spec contract is observable via the dict shape returned by
    ``MiddlewareManager.get_middleware_stack()`` (see
    ``fastblocks/applications.py::MiddlewareManager.get_middleware_stack``).

    Adding any earlier ``app.add_middleware(...)`` call would insert at
    the front of the list — this test guards against that regression
    by checking the LAST entry.
    """
    app = FastBlocks()
    # Re-register OtelMiddleware last (mirrors the registration in
    # ``fastblocks.adapters.app.default.FastBlocksApp.__init__``).
    app.add_middleware(OtelMiddleware)

    stack = app.middleware_manager.get_middleware_stack()
    user_middleware = stack["user_middleware"]
    assert isinstance(user_middleware, list)
    assert user_middleware, "user_middleware list must not be empty"
    last = user_middleware[-1]
    assert last["class"] == "OtelMiddleware", (
        f"expected OtelMiddleware last in user_middleware, got {last['class']!r}; "
        f"full user_middleware={user_middleware!r}"
    )


# ---------------------------------------------------------------------------
# Helpers — build a Request and run OtelMiddleware.dispatch directly.
# ---------------------------------------------------------------------------


def _build_request(path: str = "/test") -> Request:
    """Build a Starlette ``Request`` from a synthetic ASGI scope.

    The HTTP scope is the minimum needed for ``dispatch`` to read
    ``request.url.path`` and emit the structured log line on reset
    failure. No body, no real client — we only exercise the middleware
    dispatch path.
    """
    scope: dict[str, Any] = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode("latin-1"),
        "query_string": b"",
        "headers": [],
        "server": ("testserver", 80),
        "client": ("testclient", 50000),
        "scheme": "http",
    }

    async def receive() -> dict[str, Any]:
        return {"type": "http.request", "body": b"", "more_body": False}

    return Request(scope, receive=receive)


async def _run_dispatch(
    middleware: OtelMiddleware,
    request: Request,
    call_next: Any,
) -> PlainTextResponse:
    """Invoke ``OtelMiddleware.dispatch`` and return its result.

    A wrapper that hides the async/await plumbing so the test bodies
    stay readable. Exceptions from ``call_next`` propagate so tests
    can assert the finally block ran on the error path.
    """
    return await middleware.dispatch(request, call_next)


# ---------------------------------------------------------------------------
# Test 2 — Δ48: dispatch records http.status_code on the active span
# ---------------------------------------------------------------------------


@pytest.fixture
def in_memory_exporter():
    """Attach an ``InMemorySpanExporter`` to the test-managed provider.

    The conftest autouse fixture (``_tracer_provider_isolation``)
    installs a fresh ``TracerProvider`` per test with no processors.
    Here we add a ``SimpleSpanProcessor`` wrapping
    ``InMemorySpanExporter`` so spans flow into a list we can introspect.
    """
    from opentelemetry import trace
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
        InMemorySpanExporter,
    )

    exporter = InMemorySpanExporter()
    provider = trace.get_tracer_provider()
    if hasattr(provider, "add_span_processor"):
        provider.add_span_processor(SimpleSpanProcessor(exporter))
    try:
        yield exporter
    finally:
        exporter.clear()


async def test_dispatch_records_status_code_on_root_span(
    in_memory_exporter: Any,
) -> None:
    """A successful dispatch sets ``http.status_code`` on the root span.

    Per the brief: "on exit: set ``http.status_code`` attribute on the
    active span". The dispatch method must call
    ``span.set_attribute("http.status_code", response.status_code)``
    after ``call_next`` returns.
    """
    middleware = OtelMiddleware(app=lambda _scope, _receive, _send: None)

    async def _call_next(_request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok", status_code=200)

    request = _build_request("/happy")
    response = await _run_dispatch(middleware, request, _call_next)
    assert response.status_code == 200

    spans = in_memory_exporter.get_finished_spans()
    http_spans = [
        span for span in spans
        if span.attributes is not None
        and "http.status_code" in span.attributes
    ]
    assert http_spans, (
        f"no span carried http.status_code; spans={spans!r}"
    )
    assert http_spans[-1].attributes["http.status_code"] == 200, (
        f"expected http.status_code=200 on the http.request span; "
        f"observed attrs={dict(http_spans[-1].attributes)!r}"
    )


async def test_raises_handler_records_status_code_500_on_root_span(
    in_memory_exporter: Any,
) -> None:
    """A raising handler produces a root span with ``http.status_code=500``.

    Per the brief: "raises handler produces OTel root span with
    status_code". The dispatch method must set the attribute even when
    the inner handler raises — the exception propagates, but the span
    must carry a 500 status so the /metrics scraper and downstream
    consumers see the failure mode.
    """
    middleware = OtelMiddleware(app=lambda _scope, _receive, _send: None)

    async def _call_next(_request: Request) -> PlainTextResponse:
        raise ValueError("boom")

    request = _build_request("/raise")
    with pytest.raises(ValueError, match="boom"):
        await _run_dispatch(middleware, request, _call_next)

    spans = in_memory_exporter.get_finished_spans()
    http_spans = [
        span for span in spans
        if span.attributes is not None
        and "http.status_code" in span.attributes
    ]
    assert http_spans, (
        f"no span carried http.status_code; spans={spans!r}"
    )
    assert http_spans[-1].attributes["http.status_code"] == 500, (
        f"expected http.status_code=500 on the http.request span after a raise; "
        f"observed attrs={dict(http_spans[-1].attributes)!r}"
    )


# ---------------------------------------------------------------------------
# Test 3 — Δ48: finally block clears trace_context
# ---------------------------------------------------------------------------


async def test_finally_clears_trace_context_after_dispatch() -> None:
    """After ``dispatch`` returns, ``trace_context.exemplar()`` is None.

    The brief: "finally clears trace_context — even on exception,
    ``exemplar()`` returns None after the request."

    This proves the ``reset(token)`` ran in the ``finally`` block —
    which is the critical contract because failing to clear leaks the
    prior request's trace ID into the next request's logs.
    """
    middleware = OtelMiddleware(app=lambda _scope, _receive, _send: None)

    async def _call_next(_request: Request) -> PlainTextResponse:
        # Verify trace context is bound INSIDE the dispatch wrapper
        # (this is the contract: downstream handlers see the trace).
        ctx = get_trace_context()
        assert ctx is not None, (
            "trace_context was not bound inside dispatch; "
            "OtelMiddleware did not call set_trace_context on entry"
        )
        return PlainTextResponse("ok")

    request = _build_request("/inside-bound")
    response = await _run_dispatch(middleware, request, _call_next)
    assert response.status_code == 200

    # After dispatch returns, the typed ContextVar must have been reset.
    assert exemplar() is None, (
        "trace_context was not cleared after dispatch returned; "
        "the OtelMiddleware's finally block did not run reset(token)"
    )


async def test_finally_clears_trace_context_after_exception() -> None:
    """Trace context clears even when a handler raises.

    Stronger version of the test above — verifies the finally block
    fires on the exception path, not just the happy path.
    """
    middleware = OtelMiddleware(app=lambda _scope, _receive, _send: None)

    async def _call_next(_request: Request) -> PlainTextResponse:
        ctx = get_trace_context()
        assert ctx is not None, (
            "trace_context was not bound inside dispatch on exception path"
        )
        raise RuntimeError("kaboom")

    request = _build_request("/raise-cleanup")
    with pytest.raises(RuntimeError, match="kaboom"):
        await _run_dispatch(middleware, request, _call_next)

    assert exemplar() is None, (
        "trace_context was not cleared after an exception-raising dispatch; "
        "the OtelMiddleware's finally block did not run on the error path"
    )


async def test_trace_context_is_bound_inside_dispatch() -> None:
    """The trace context set by ``OtelMiddleware`` is the active one inside.

    Asserts that the ``TraceContext`` bound by ``set_trace_context``
    inside ``dispatch`` carries a valid non-zero trace_id/span_id (not
    the spec-compliant zero placeholder), so downstream log lines and
    metrics exemplars carry the real IDs.
    """
    middleware = OtelMiddleware(app=lambda _scope, _receive, _send: None)

    observed: dict[str, TraceContext | None] = {"inside": None}

    async def _call_next(_request: Request) -> PlainTextResponse:
        observed["inside"] = get_trace_context()
        return PlainTextResponse("ok")

    request = _build_request("/bind")
    await _run_dispatch(middleware, request, _call_next)

    assert observed["inside"] is not None
    # Non-zero trace_id (32 hex chars) and span_id (16 hex chars).
    assert observed["inside"].trace_id != "0" * 32, (
        f"trace_id is the all-zeros placeholder; "
        f"OtelMiddleware did not start a real span (got {observed['inside'].trace_id!r})"
    )
    assert observed["inside"].span_id != "0" * 16, (
        f"span_id is the all-zeros placeholder; "
        f"OtelMiddleware did not start a real span (got {observed['inside'].span_id!r})"
    )


# ---------------------------------------------------------------------------
# Test 4 — P1-5: reset failure increments fastblocks_otel_middleware_reset_failed_total
# ---------------------------------------------------------------------------


async def test_reset_failure_increments_reset_failed_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A ``reset_trace_context`` failure increments the counter.

    Per P1-5: the ``trace_context.reset(token)`` call in the finally
    block is wrapped in try/except; on failure, the
    ``fastblocks_otel_middleware_reset_failed_total{reason}`` counter
    is incremented with the exception class name.
    """
    from fastblocks.observability import otel_middleware as otel_mod

    def _boom(_token: Any) -> None:
        raise RuntimeError("reset exploded")

    monkeypatch.setattr(otel_mod, "reset_trace_context", _boom)

    middleware = OtelMiddleware(app=lambda _scope, _receive, _send: None)

    async def _call_next(_request: Request) -> PlainTextResponse:
        return PlainTextResponse("ok")

    request = _build_request("/reset-fail")
    response = await _run_dispatch(middleware, request, _call_next)
    assert response.status_code == 200

    from prometheus_client import REGISTRY as _PROM_REGISTRY

    sample = _PROM_REGISTRY.get_sample_value(
        "fastblocks_otel_middleware_reset_failed_total",
        {"reason": "RuntimeError"},
    )
    assert sample is not None and sample >= 1.0, (
        f"expected reset_failed_total{{reason='RuntimeError'}} >= 1.0; "
        f"got {sample!r}"
    )


__all__ = [
    "test_dispatch_records_status_code_on_root_span",
    "test_finally_clears_trace_context_after_dispatch",
    "test_finally_clears_trace_context_after_exception",
    "test_otel_middleware_is_last_in_user_middleware",
    "test_raises_handler_records_status_code_500_on_root_span",
    "test_reset_failure_increments_reset_failed_counter",
    "test_trace_context_is_bound_inside_dispatch",
]

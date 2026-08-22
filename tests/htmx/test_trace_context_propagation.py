"""Regression test for the executor-thread boundary in htmx.py.

Per ADR 0013 Decision 4: a previous implementation used
`executor.submit(asyncio.run, coro).result()` which created a new
thread with empty ContextVar storage. contextvars.copy_context()
now bridges the boundary so trace context set in the caller
survives into the coroutine running on the executor.

Test pattern: ``loop.run_in_executor(None, captured_ctx.run,
_run_async_safely, probe())`` where ``captured_ctx`` is
``contextvars.copy_context()`` captured in the caller thread.
``ctx.run`` installs the captured context in the worker thread,
so the trace ContextVar set by ``set_trace_context`` is visible
inside ``_run_async_safely``. The internal
``contextvars.copy_context()`` inside ``_run_async_safely`` then
re-captures that context for the second executor hop
(``executor.submit(ctx.run, asyncio.run, coro)``) where
``asyncio.run`` would otherwise see an empty ContextVar store.
"""
from __future__ import annotations

import asyncio
import contextvars

from fastblocks.htmx import _run_async_safely
from fastblocks.observability.trace_context import (
    TraceContext,
    get_trace_context,
    reset_trace_context,
    set_trace_context,
)


async def test_trace_context_survives_executor_boundary() -> None:
    """Setting trace context in caller, then running coro on the
    executor via _run_async_safely, must surface the same context
    inside the coroutine.
    """
    observed: dict[str, TraceContext | None] = {"inside": None}

    async def probe() -> None:
        observed["inside"] = get_trace_context()

    ctx = TraceContext(trace_id="abc123", span_id="def456")
    token = set_trace_context(ctx)
    try:
        # _run_async_safely is the synchronous helper used internally
        # by htmx.py. It runs the coroutine on a thread-pool executor
        # and blocks until completion. We invoke it from inside the
        # event loop without deadlocking by wrapping it in
        # ``loop.run_in_executor``.
        #
        # ``loop.run_in_executor`` does NOT propagate ContextVars
        # to the worker thread on its own; the brief's pre-flight
        # therefore instructs us to wrap the callable with
        # ``captured_ctx.run`` so the caller's context (including
        # the trace ContextVar set above) is installed in the
        # worker thread. Once visible inside ``_run_async_safely``,
        # its own ``contextvars.copy_context()`` re-captures the
        # context for the second executor hop where ``asyncio.run``
        # actually runs the probe.
        loop = asyncio.get_event_loop()
        captured_ctx = contextvars.copy_context()
        result = await loop.run_in_executor(
            None, captured_ctx.run, _run_async_safely, probe(),
        )
        # probe() returns None; the test asserts observed["inside"].
        assert result is None
    finally:
        reset_trace_context(token)

    assert observed["inside"] is not None, (
        "trace context did NOT survive the executor boundary; "
        "htmx.py:_run_async_safely still drops ContextVars"
    )
    assert observed["inside"].trace_id == "abc123"
    assert observed["inside"].span_id == "def456"

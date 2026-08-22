"""Verify trace_context.set() makes trace_id appear in subsequent
structlog log lines.

Per ADR 0013 Decision 17 + F-PYT-004: structlog's merge_contextvars
reads from stdlib contextvars storage (ContextVar objects whose names
start with STRUCTLOG_KEY_PREFIX). bind_contextvars writes to those
ContextVars; merge_contextvars then surfaces them. Raw ContextVar.set()
writes to unrelated ContextVars are invisible.

The commit ensures trace_context.set() does BOTH the raw set AND
structlog.contextvars.bind_contextvars(**asdict(ctx)) so log lines
carry trace_id without a custom processor.
"""
from __future__ import annotations

import io
import json
import logging

import structlog

from fastblocks.observability.trace_context import (
    TraceContext,
    get_trace_context,
    reset_trace_context,
    set_trace_context,
)


def test_trace_id_appears_in_log_line_after_set() -> None:
    """A trace_id from set_trace_context surfaces in the next structlog line."""
    buf = io.StringIO()
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=buf),
    )
    structlog.contextvars.clear_contextvars()

    ctx = TraceContext(trace_id="abc123", span_id="def456")
    token = set_trace_context(ctx)
    try:
        # structlog bound loggers take `event` as the positional arg; use
        # a different kwarg name for the marker the test will look for.
        structlog.get_logger("t").info("hello", marker="smoke")
    finally:
        reset_trace_context(token)

    output = buf.getvalue()
    records: list[dict[str, object]] = []
    for line in output.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            pass

    assert any(
        "trace_id" in r and r.get("marker") == "smoke" for r in records
    ), f"trace_id missing from log records; got: {records!r}"

    # And the typed get() returns the same TraceContext that was set.
    assert get_trace_context() is None, (
        "reset_trace_context did not restore the prior (None) value"
    )
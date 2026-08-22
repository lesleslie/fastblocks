"""Autouse fixture for observability tests.

Per ADR 0013 Decision 12: OTel's TracerProvider is process-global.
A SpanProcessor installed in test 1 persists into tests 2..N
unless explicitly torn down. Per Phase 6.5 quick-review 2026-08-22
(spec commit ``0a40879``), the canonical isolation pattern is to
swap the TracerProvider per test via
``trace.set_tracer_provider(TracerProvider())``: the OTel
``ProxyTracerProvider`` does not expose its active span-processor
list, so private-attribute introspection is not portable.

A second layer of nuance: OTel's ``trace.set_tracer_provider`` is
guarded by a process-level ``Once`` flag — the second and later
calls log ``Overriding of current TracerProvider is not allowed``
and silently no-op. So per-test swap requires resetting that flag
between tests. We do so explicitly: this is more robust than
introspecting ``_active_span_processor`` on the proxy (which
itself is a private attribute).

Per Task 2 review (T2R-6): the trace-context test calls
``structlog.contextvars.clear_contextvars()`` before
``set_trace_context()``. Without per-test teardown, that
``clear_contextvars()`` would wipe structlog contextvars bound by
other tests in the same process. We snapshot structlog's
contextvars at fixture entry and rebind the snapshot at exit,
so each test's structlog context is restored after teardown —
not leaked across tests, not destroyed by the next test's
``clear_contextvars()``.
"""
from __future__ import annotations

from contextlib import suppress

import pytest

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.trace import _TRACER_PROVIDER_SET_ONCE

    HAS_OTEL_SDK = True
except ImportError:  # pragma: no cover - exercised only in slim envs
    HAS_OTEL_SDK = False


def _set_provider_silently(provider: object) -> None:
    """Reset the OTel Once-flag and call set_tracer_provider.

    OTel's public ``trace.set_tracer_provider`` is one-shot per
    process; the second and later calls log a warning and no-op.
    Resetting the flag is the only way to perform the swap-then-
    restore pattern documented for opentelemetry-test; the flag is
    itself a private API but only its boolean state is touched.
    """
    _TRACER_PROVIDER_SET_ONCE._done = False
    trace.set_tracer_provider(provider)  # type: ignore[arg-type]


@pytest.fixture(autouse=True)
def _tracer_provider_isolation():
    """Swap a fresh ``TracerProvider`` per test, then restore the prior one.

    Also snapshots ``structlog.contextvars`` at entry and rebinds the
    snapshot at exit, so a test's ``clear_contextvars()`` call does
    not bleed into other tests in the same pytest process.

    Yields ``None``; this fixture has no observable output, only
    side-effects on the OTel and structlog global state.
    """
    import structlog.contextvars as _sctxvars

    # Snapshot structlog contextvars at entry so we can restore them
    # at exit. dict() copies to avoid the snapshot itself being
    # mutated by tests via the returned reference.
    snapshot: dict[str, object] = dict(_sctxvars.get_contextvars())

    # Swap in a fresh TracerProvider for the duration of the test.
    # TracerProvider() is intentionally empty: no span processors,
    # no exporters — tests add their own if needed. On teardown we
    # call fresh.shutdown() to flush any pending spans before
    # restoring the previous provider.
    previous_provider: object | None = None
    fresh_provider: object | None = None
    if HAS_OTEL_SDK:
        previous_provider = trace.get_tracer_provider()
        fresh_provider = TracerProvider()
        with suppress(Exception):  # pragma: no cover - defensive
            _set_provider_silently(fresh_provider)

    try:
        yield
    finally:
        # Restore the previous TracerProvider and shut down the
        # test-managed provider so its background threads stop.
        if HAS_OTEL_SDK and fresh_provider is not None:
            with suppress(Exception):  # pragma: no cover - defensive
                _set_provider_silently(previous_provider)
                fresh_provider.shutdown()  # type: ignore[union-attr]

        # Restore structlog contextvars to the entry-time snapshot.
        # clear_contextvars() drops any keys bound during the test;
        # bind_contextvars(**snapshot) restores the entry state.
        # If the snapshot is empty (typical case), the rebind is
        # a no-op. If the test DID bind something before the
        # autouse fixture ran, the rebind restores that state.
        with suppress(Exception):  # pragma: no cover - defensive
            _sctxvars.clear_contextvars()
            if snapshot:
                _sctxvars.bind_contextvars(**snapshot)

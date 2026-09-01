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
    from opentelemetry.trace import TracerProvider as _TracerProviderBase
    from opentelemetry.trace import _TRACER_PROVIDER_SET_ONCE

    HAS_OTEL_SDK = True
except ImportError:  # pragma: no cover - exercised only in slim envs
    HAS_OTEL_SDK = False


def _set_provider_silently(provider: _TracerProviderBase) -> None:
    """Reset the OTel Once-flag and call set_tracer_provider.

    OTel's public ``trace.set_tracer_provider`` is one-shot per
    process; the second and later calls log a warning and no-op.
    Resetting the flag is the only way to perform the swap-then-
    restore pattern documented for opentelemetry-test; the flag is
    itself a private API but only its boolean state is touched.

    The accepted type is the API-level ``opentelemetry.trace.TracerProvider``
    (aliased here as ``_TracerProviderBase``); both the SDK's
    ``TracerProvider`` (the fresh test-managed provider) and the
    ``ProxyTracerProvider`` returned by ``trace.get_tracer_provider()``
    inherit from it, so this signature accepts the previous provider
    and the fresh provider without a widening-to-``object`` cast.

    Note: ``ProxyTracerProvider`` cannot be safely re-installed as
    the active provider. Its ``get_tracer`` method falls back to
    ``opentelemetry.trace._TRACER_PROVIDER`` (the global module
    variable), and storing the proxy ITSELF in that slot creates an
    infinite recursion — ``proxy.get_tracer()`` -> ``_TRACER_PROVIDER.
    get_tracer()`` -> ``proxy.get_tracer()`` -> ... -> RecursionError.
    Callers should pass the underlying SDK provider or ``None``
    instead. This helper accepts the type for backward compatibility
    but is no longer used to install a captured proxy — see
    ``_tracer_provider_isolation`` for the run-time guard.
    """
    _TRACER_PROVIDER_SET_ONCE._done = False
    # Defensive: do NOT call set_tracer_provider with a
    # ProxyTracerProvider. The fixture captures ``previous_provider``
    # via ``trace.get_tracer_provider()`` which returns a
    # ``ProxyTracerProvider`` when nothing has been set yet, and
    # also returns the previously-stored proxy on subsequent calls.
    # Re-installing it would cause the RecursionError described in
    # the docstring. Treat any ProxyTracerProvider as ``None`` so
    # ``trace.get_tracer_provider()`` returns the static default
    # proxy (``_PROXY_TRACER_PROVIDER``) which is recursion-safe.
    from opentelemetry.trace import ProxyTracerProvider

    if isinstance(provider, ProxyTracerProvider):
        # Clear the global so the next get_tracer_provider() returns
        # the static _PROXY_TRACER_PROVIDER (which has a special
        # "no _TRACER_PROVIDER set" fallback in get_tracer()).
        trace._TRACER_PROVIDER = None  # type: ignore[attr-defined]
    else:
        trace.set_tracer_provider(provider)


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
    # restoring the previous provider. Variable types are the API
    # base ``_TracerProviderBase`` (alias of
    # ``opentelemetry.trace.TracerProvider``); the SDK's TracerProvider
    # and ProxyTracerProvider both inherit from it.
    previous_provider: _TracerProviderBase | None = None
    fresh_provider: _TracerProviderBase | None = None
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
                if previous_provider is not None:
                    _set_provider_silently(previous_provider)
                fresh_provider.shutdown()

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

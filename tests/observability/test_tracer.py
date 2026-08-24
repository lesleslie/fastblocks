"""Tests for fastblocks.observability.tracer.

Per v6 Δ10/Δ18: OTel Tracer + BatchSpanProcessor.shutdown contract.
Per v6 Δ5: shipped regression preservation for ``tests/htmx/test_trace_context_propagation.py``.

The OTel SDK ``TracerProvider`` is process-global (see tests/observability/conftest.py
which swaps a fresh provider per test). All tests in this module therefore
go through ``setup_default_tracer_provider()`` so the default cache is
warmed before any assertion.

Public-API contract under test:

  * ``get_tracer(name) -> opentelemetry.trace.Tracer`` — returns the SDK's
    tracer (NOT a wrapper) so callers can use the full OTel surface area.
  * ``get_default_tracer_provider() -> opentelemetry.trace.TracerProvider``
    — returns the cached provider.
  * ``setup_default_tracer_provider()`` is idempotent — second call is a
    no-op so re-init never replaces the active processor chain mid-process
    (same pattern as ``loggers._CONFIGURED``).
  * FastBlocksApp.lifespan and App.lifespan both call
    ``await get_default_tracer_provider().shutdown()`` after ``yield`` so
    BatchSpanProcessor flushes pending spans on app exit.

Lifespan-shutdown verification uses ``monkeypatch`` to track the call rather
than reading the private ``BatchSpanProcessor._batch_processor._shutdown``
flag (which is two layers deep and more brittle than the brief's
``_active_span_processor._shutdown_called`` literal — that exact attribute
does not exist on the public SDK surface area).
"""
from __future__ import annotations

import pytest

# Use opentelemetry.trace.Tracer (the API-level base class) so the test
# passes against any compliant provider (SDK or shim).
from opentelemetry.trace import Tracer as OTelTracer


def test_module_declares_all() -> None:
    """Per module pattern: every public module declares __all__."""
    import fastblocks.observability.tracer as tracer_mod

    assert hasattr(tracer_mod, "__all__"), "tracer.py must declare __all__"
    expected = {
        "get_tracer",
        "get_default_tracer_provider",
        "setup_default_tracer_provider",
    }
    assert expected.issubset(set(tracer_mod.__all__)), (
        f"tracer.__all__ must include {expected!r}; got {tracer_mod.__all__!r}"
    )


def test_get_tracer_returns_sdk_tracer() -> None:
    """Per brief: ``get_tracer(name) -> opentelemetry.trace.Tracer``.

    Returned object must be an OTel SDK Tracer (NOT a wrapper), so callers
    can use ``start_as_current_span``, ``start_span``, and the rest of the
    public OTel surface area without learning a wrapper API.
    """
    from fastblocks.observability.tracer import (
        get_tracer,
        setup_default_tracer_provider,
    )

    setup_default_tracer_provider()
    tracer = get_tracer("test")
    # OTel's API-level Tracer is the canonical public type; SDK providers
    # return subclasses. isinstace check against the API base class is
    # portable across SDK versions.
    assert isinstance(tracer, OTelTracer), (
        f"get_tracer must return an OTel SDK Tracer; got {type(tracer).__name__}"
    )


def test_span_from_get_tracer_has_nonzero_trace_id() -> None:
    """Per brief: span with ``get_tracer("test")`` has non-zero trace_id.

    Verifies the provider is wired to a real (non-noop) TracerProvider —
    if ``setup_default_tracer_provider`` accidentally returned a
    no-op or a proxy that swallowed the real provider, trace_id would
    remain 0 (the OTel API's "invalid" sentinel).
    """
    from fastblocks.observability.tracer import (
        get_tracer,
        setup_default_tracer_provider,
    )

    setup_default_tracer_provider()
    tracer = get_tracer("test")
    with tracer.start_as_current_span("probe") as span:
        ctx = span.get_span_context()

    assert ctx.trace_id != 0, (
        f"span from get_tracer('test') has invalid trace_id=0; the default "
        f"provider is not wired to a real SDK TracerProvider. trace_id={ctx.trace_id}"
    )


def test_setup_default_tracer_provider_is_idempotent() -> None:
    """Per brief: idempotent re-setup skips re-init.

    A second call must not create a second provider / second
    BatchSpanProcessor / second exporter, otherwise app-restart would
    leak resources and the second call would race the first's background
    threads. The brief's pattern matches ``loggers._CONFIGURED``.
    """
    from fastblocks.observability.tracer import (
        get_default_tracer_provider,
        setup_default_tracer_provider,
    )

    first = setup_default_tracer_provider()
    second = setup_default_tracer_provider()
    cached = get_default_tracer_provider()
    assert first is second, (
        "setup_default_tracer_provider must return the same provider on "
        "every call; first/repeat instances diverged"
    )
    assert second is cached, (
        "get_default_tracer_provider must return the cached instance "
        "that setup_default_tracer_provider populated"
    )


def test_get_default_tracer_provider_returns_real_sdk_provider() -> None:
    """Sanity: the cached provider is an SDK ``TracerProvider``.

    Guards against a regression where the module-level cache accidentally
    stores a ProxyTracerProvider or a None sentinel — both would break
    the lifecycle ``.shutdown()`` call that the lifespan relies on.
    """
    from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider
    from fastblocks.observability.tracer import (
        get_default_tracer_provider,
        setup_default_tracer_provider,
    )

    setup_default_tracer_provider()
    provider = get_default_tracer_provider()
    assert isinstance(provider, SDKTracerProvider), (
        "cached provider must be an SDK TracerProvider so .shutdown() is "
        f"available; got {type(provider).__name__}"
    )


@pytest.mark.asyncio
async def test_fastblocks_app_lifespan_calls_provider_shutdown(monkeypatch) -> None:
    """Per brief: FastBlocksApp.lifespan calls provider.shutdown() after yield.

    The literal brief assertion is
    ``provider._active_span_processor._shutdown_called is True`` —
    that exact attribute does not exist on the public SDK surface area
    (the real flag is on ``BatchSpanProcessor._batch_processor._shutdown``,
    two layers deep). This test uses a ``monkeypatch`` sentinel instead:
    swapping the cached provider's ``shutdown`` method for a tracker is
    a more public-API contract than reading a private attr.
    """
    from fastblocks.adapters.app.default import FastBlocksApp
    from fastblocks.observability.tracer import (
        get_default_tracer_provider,
        setup_default_tracer_provider,
    )

    setup_default_tracer_provider()
    provider = get_default_tracer_provider()

    called = {"flag": False}

    async def tracking_shutdown(*args, **kwargs) -> None:
        called["flag"] = True

    # Replace the instance method with the tracker for the duration of
    # this test. monkeypatch auto-restores on teardown.
    monkeypatch.setattr(provider, "shutdown", tracking_shutdown)

    app = FastBlocksApp()
    async with app.lifespan(app):
        # body — startup runs, then we yield control, then shutdown
        pass

    assert called["flag"], (
        "FastBlocksApp.lifespan must call `await provider.shutdown()` after "
        "`yield` so BatchSpanProcessor flushes pending spans on app exit"
    )


@pytest.mark.asyncio
async def test_app_lifespan_calls_provider_shutdown(monkeypatch) -> None:
    """App.lifespan must also call provider.shutdown() after yield.

    The brief's literal target was FastBlocksApp.lifespan (lines 194-229),
    but App.lifespan (lines 341-360) is the class instantiated at runtime
    (App at line 232 extends AppBase; the FastBlocksApp instance lives
    inside App.fastblocks_app). Both paths need the shutdown contract
    to satisfy Δ10/Δ18.
    """
    from fastblocks.adapters.app.default import App
    from fastblocks.observability.tracer import (
        get_default_tracer_provider,
        setup_default_tracer_provider,
    )

    setup_default_tracer_provider()
    provider = get_default_tracer_provider()

    called = {"flag": False}

    async def tracking_shutdown(*args, **kwargs) -> None:
        called["flag"] = True

    monkeypatch.setattr(provider, "shutdown", tracking_shutdown)
    # ``App.lifespan`` calls ``self._cancel_remaining_tasks()`` at the
    # end of its post-yield teardown; that cancels the current test
    # task and propagates ``CancelledError`` out of the ``async with``.
    # Patch the helper to a no-op so the assertion can fire without
    # the test self-cancelling.
    monkeypatch.setattr(
        App, "_cancel_remaining_tasks", lambda self: None,
    )

    app = App()
    async with app.lifespan(app.fastblocks_app):
        pass

    assert called["flag"], (
        "App.lifespan must call `await provider.shutdown()` after `yield` "
        "so the runtime-instantiated path also flushes spans"
    )


def test_otel_sdk_pinned_in_observability_dep_group() -> None:
    """Pin Δ10/Δ18 contract: lean installs can resolve opentelemetry-sdk.

    Without the [observability] group pin, ``uv sync --no-group dev``
    cannot import ``fastblocks.observability.tracer`` (the
    ``MissingDependencyError`` guard correctly fires) and the wire-up
    is unreachable.
    """
    import tomllib
    from pathlib import Path

    pyproject = tomllib.loads(Path("pyproject.toml").read_text())
    group = pyproject["dependency-groups"]["observability"]
    matches = [
        entry for entry in group
        if entry.split("[")[0].split("~")[0].split("=")[0].strip() == "opentelemetry-sdk"
    ]
    assert matches, (
        "opentelemetry-sdk must be pinned in the [dependency-groups].observability "
        "table so lean installs can wire up fastblocks.observability.tracer; "
        f"observed group: {group!r}"
    )
    assert "~=" in matches[0], (
        f"opentelemetry-sdk pin must use compatible-release clause '~=' per "
        f"Global Constraint line 25; got {matches[0]!r}"
    )

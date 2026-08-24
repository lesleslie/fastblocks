"""Tests for fastblocks.observability.sentry_bridge.

Per v6 Δ11/Δ19/Δ20/Δ34/Δ39-ζ:

  * Δ34: SentryImportError(reason="import_error") on import failure when
    ``disabled_on_import_error=False`` (loud-fail default).
  * Δ39-ζ: SentryImportError(reason="init_runtime_error") on init runtime
    failures (e.g. Sentry SDK ``init()`` raises on an invalid DSN).
  * Δ20: ``profiling_enabled=True`` raises ``RuntimeError`` (alpha lock).
  * Δ19: TracerProvider must be configured before init_sentry(). Documented
    in the docstring; the lifespan does the ordering.
  * Δ11: Counter ``fastblocks_sentry_disabled_total{reason}`` is registered
    in ``ObservabilityRegistry`` so /metrics scrapes it.

ALPHA path notes:
  * The installed ``sentry-sdk==3.0.0a7[opentelemetry]`` does NOT expose a
    top-level ``OpenTelemetryIntegration`` class — the integration is shipped
    as primitives under ``sentry_sdk.opentelemetry`` (``SentrySpanProcessor``,
    ``SentryPropagator``, ``SentrySampler``). The bridge uses
    ``sentry_sdk.init(...)`` with no explicit ``integrations`` arg and lets
    the alpha auto-wire OTel on init (the SDK auto-discovers the active
    OTel TracerProvider). The ``"OpenTelemetryIntegration"`` import path is
    tried first as a defensive no-op; the test for the bridge does not
    assert on the integration class — only on the call into ``sentry_sdk.init``.

Lean-install contract (per Δ34 + the brief's "Lean installs" note): when the
``[observability]`` PEP 735 group is NOT installed, ``init_sentry()`` raises
``SentryImportError(reason="import_error")`` instead of bare ``ImportError``
so callers see a structured diagnostic. ``MissingDependencyError`` is NOT
re-raised because Sentry's group membership is ``[observability]``, same as
prometheus — a lean install without prometheus has nothing to register
counters against either, so the Sentry path is reported as the canonical
error.
"""
from __future__ import annotations

from typing import Any

import pytest

# Sentinel DSN for tests — must be syntactically valid per the sentry-sdk
# DSN parser but does not need to point at a real collector. The exact
# value is irrelevant; ``init_sentry`` only forwards it through.
_FAKE_DSN = "https://public@example.com/1"


def test_module_declares_all() -> None:
    """Per module pattern: every public module declares ``__all__``."""
    import fastblocks.observability.sentry_bridge as mod

    assert hasattr(mod, "__all__"), "sentry_bridge.py must declare __all__"
    assert "init_sentry" in mod.__all__, (
        f"init_sentry must be in sentry_bridge.__all__; got {mod.__all__!r}"
    )


def test_init_sentry_no_dsn_is_noop(monkeypatch: pytest.MonkeyPatch) -> None:
    """Per brief: ``SENTRY_DSN`` unset → init_sentry is a no-op.

    No spans are sent, no exception is raised, no ``sentry_sdk.init``
    call is issued. This is the lean-install default behavior; the
    bridge is opt-in.
    """
    import sentry_sdk
    from fastblocks.observability.sentry_bridge import init_sentry

    init_calls: list[dict[str, Any]] = []

    def _tracking_init(**kwargs: Any) -> None:
        init_calls.append(kwargs)

    monkeypatch.setattr(sentry_sdk, "init", _tracking_init)

    init_sentry()  # No DSN, no exception
    init_sentry(dsn=None)
    assert init_calls == [], (
        f"init_sentry must not call sentry_sdk.init when DSN is unset; "
        f"observed calls: {init_calls!r}"
    )


def test_init_sentry_with_dsn_calls_sentry_sdk_init(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Per brief: ``SENTRY_DSN`` set → single span tree wired through Sentry.

    When a DSN is provided, ``init_sentry()`` calls ``sentry_sdk.init(...)``
    exactly once with the DSN forwarded as a kwarg. We monkeypatch
    ``sentry_sdk.init`` to capture the call shape; the actual span-tree
    contract is exercised end-to-end by the alpha SDK's own integration
    tests (we only verify the bridge wires the call).
    """
    import sentry_sdk
    from fastblocks.observability.sentry_bridge import init_sentry

    init_calls: list[dict[str, Any]] = []

    def _tracking_init(**kwargs: Any) -> None:
        init_calls.append(kwargs)

    monkeypatch.setattr(sentry_sdk, "init", _tracking_init)

    init_sentry(dsn=_FAKE_DSN)

    assert len(init_calls) == 1, (
        f"init_sentry must call sentry_sdk.init exactly once when DSN is set; "
        f"observed calls: {init_calls!r}"
    )
    assert init_calls[0].get("dsn") == _FAKE_DSN, (
        f"DSN must be forwarded to sentry_sdk.init; got {init_calls[0]!r}"
    )


def test_init_sentry_profiling_enabled_raises_runtime_error() -> None:
    """Per Δ20: ``profiling_enabled=True`` is forbidden in the alpha path.

    Loud-fail: caller cannot silently enable profiling. The bridge raises
    ``RuntimeError`` with a message that names the constant (``Δ20``)
    so operators see the spec anchor in the traceback.
    """
    from fastblocks.observability.sentry_bridge import init_sentry

    with pytest.raises(RuntimeError, match=r"Δ20"):
        init_sentry(dsn=_FAKE_DSN, profiling_enabled=True)


def test_init_sentry_loud_fail_on_import_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Per Δ34: import error + ``disabled_on_import_error=False`` → loud fail.

    When the Sentry SDK cannot be imported (lean install without
    ``[observability]`` PEP 735 group), the bridge re-raises
    ``SentryImportError(reason="import_error")`` (NOT a bare ``ImportError``)
    so callers see the structured reason label.

    We monkeypatch the bridge's public ``sentry_sdk`` alias to a stub
    that raises ``ImportError`` on attribute access — the bridge's
    import-error guard sees the failure, classifies it as
    ``"import_error"``, and raises the typed exception.
    """
    import fastblocks.observability.sentry_bridge as sentry_bridge_mod

    class _ImportRaisingStub:
        def __getattr__(self, _name: str) -> Any:
            raise ImportError("simulated sentry_sdk missing")

    # Set both the public alias AND the underscore-prefixed module
    # reference to ``None`` so the bridge's pre-init guard
    # (``if not _SENTRY_SDK_AVAILABLE``) takes the import-error path.
    monkeypatch.setattr(sentry_bridge_mod, "sentry_sdk", _ImportRaisingStub())
    monkeypatch.setattr(sentry_bridge_mod, "_sentry_sdk", None)
    monkeypatch.setattr(sentry_bridge_mod, "_SENTRY_SDK_AVAILABLE", False)

    from fastblocks.observability.sentry_bridge import init_sentry

    with pytest.raises(sentry_bridge_mod.SentryImportError) as exc_info:
        init_sentry(dsn=_FAKE_DSN, disabled_on_import_error=False)

    assert exc_info.value.reason == "import_error", (
        f"SentryImportError.reason must be 'import_error' on import failure; "
        f"got {exc_info.value.reason!r}"
    )


def test_init_sentry_disabled_on_import_error_emits_counter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Per Δ11 + ALPHA: ``disabled_on_import_error=True`` swallows the error.

    When the SDK cannot be imported AND the caller has opted into the
    quiet path, ``init_sentry()`` returns silently and increments the
    ``fastblocks_sentry_disabled_total{reason="import_error"}`` counter.
    The counter is registered in ``ObservabilityRegistry`` so /metrics
    scrapes it alongside the rest of the metrics surface.
    """
    import fastblocks.observability.sentry_bridge as sentry_bridge_mod

    class _ImportRaisingStub:
        def __getattr__(self, _name: str) -> Any:
            raise ImportError("simulated sentry_sdk missing")

    monkeypatch.setattr(sentry_bridge_mod, "sentry_sdk", _ImportRaisingStub())
    monkeypatch.setattr(sentry_bridge_mod, "_sentry_sdk", None)
    monkeypatch.setattr(sentry_bridge_mod, "_SENTRY_SDK_AVAILABLE", False)

    from fastblocks.observability.sentry_bridge import init_sentry

    # Should NOT raise despite the import error (disabled_on_import_error=True).
    init_sentry(dsn=_FAKE_DSN, disabled_on_import_error=True)

    # The disabled counter must be registered in ObservabilityRegistry AND
    # incremented with the ``import_error`` reason label.
    from fastblocks.observability.registry import ObservabilityRegistry

    registry_names = ObservabilityRegistry._names  # type: ignore[attr-defined]
    assert "fastblocks_sentry_disabled_total" in registry_names, (
        f"fastblocks_sentry_disabled_total must be registered in "
        f"ObservabilityRegistry; observed names: {sorted(registry_names)!r}"
    )

    # Inspect the prometheus_client counter value directly — the bridge's
    # counter is lazy-initialized via ``_get_disabled_counter()`` so we
    # read its labeled child for reason='import_error' and verify the
    # increment took effect.
    disabled_counter = sentry_bridge_mod._get_disabled_counter()._inner
    labeled = disabled_counter.labels(reason="import_error")
    assert labeled._value.get() >= 1.0, (
        f"fastblocks_sentry_disabled_total{{reason='import_error'}} must be "
        f"incremented when disabled_on_import_error=True swallows an import "
        f"failure; observed value: {labeled._value.get()}"
    )

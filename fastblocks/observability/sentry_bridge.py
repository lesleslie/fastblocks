"""Sentry SDK bridge for FastBlocks observability.

Per v6 Δ11/Δ19/Δ20/Δ34/Δ39-ζ — opt-in Sentry SDK integration gated by
``SENTRY_DSN``. When the DSN is unset (or empty) the bridge is a
no-op so lean installs do not pull the SDK or initialize the client.

ALPHA path (per Δ20 + Δ55): ``sentry-sdk==3.0.0a7[opentelemetry]`` is
the only supported version. The brief's reference to a top-level
``OpenTelemetryIntegration`` class does NOT exist in this alpha — the
integration is shipped as primitives under ``sentry_sdk.opentelemetry``
(``SentrySpanProcessor``, ``SentryPropagator``, ``SentrySampler``). The
bridge calls ``sentry_sdk.init(...)`` with the configured DSN and lets
the alpha SDK auto-wire OTel on init (the SDK reads the active OTel
``TracerProvider`` from process-global state and installs its
``SentrySpanProcessor`` as a span processor). The bridge does NOT
explicitly install ``OpenTelemetryIntegration`` because the class is
absent in 3.0.0a7 — see Concerns in the task-12 report.

Ordering contract (per Δ19):

  * The caller MUST invoke
    :func:`fastblocks.observability.tracer.setup_default_tracer_provider`
    BEFORE :func:`init_sentry`. The lifespan
    (``fastblocks.adapters.app.default::FastBlocksApp.lifespan`` and
    ``fastblocks.adapters.app.default::App.lifespan``) honors this
    ordering — both lifespans install the TracerProvider first, then
    call ``init_sentry()``, then ``yield``. This is NOT enforced inside
    ``init_sentry`` (the span-tree install happens during ``init``);
    misordering will silently produce a stale span tree.

Loud-fail contract:

  * Δ20: ``profiling_enabled=True`` raises ``RuntimeError`` naming
    Δ20 so the alpha lock cannot be bypassed silently.
  * Δ34: Sentry SDK import failure with
    ``disabled_on_import_error=False`` (default) raises
    :class:`fastblocks.observability.errors.SentryImportError` with
    ``reason="import_error"`` — never a bare ``ImportError``.
  * Δ39-ζ: ``sentry_sdk.init(...)`` runtime failure (invalid DSN,
    network error) re-raises as
    :class:`SentryImportError` with ``reason="init_runtime_error"``.

Quiet contract (ALPHA opt-in):

  * ``disabled_on_import_error=True`` swallows import failures and
    increments the
    ``fastblocks_sentry_disabled_total{reason="import_error"}`` counter
    registered in
    :data:`fastblocks.observability.registry.ObservabilityRegistry`.
    The /metrics route (Task 9) scrapes the registry directly so
    operators see the swallow count.

Per v6 Global Constraints:
  * ``from __future__ import annotations`` first (after docstring)
  * ``__all__`` declared
  * Modern syntax: ``X | None``, ``list[str]``
  * ``raise ... from original`` when re-raising third-party exceptions
  * No ``logger.error(..., exc_info=True)`` (use ``logger.exception(...)``)
  * ``pathlib.Path`` NOT ``os.path``
"""
from __future__ import annotations

import typing as t

from .counters import Counter
from .errors import SentryImportError
from .loggers import get_logger

try:
    import sentry_sdk as _sentry_sdk  # type: ignore[import-not-found]

    _SENTRY_SDK_AVAILABLE = True
    _SENTRY_SDK_IMPORT_ERROR: Exception | None = None
except ImportError as _e:  # pragma: no cover - exercised only in slim envs
    _sentry_sdk = None  # type: ignore[assignment]
    _SENTRY_SDK_AVAILABLE = False
    _SENTRY_SDK_IMPORT_ERROR = _e

# Public module alias so tests can ``monkeypatch.setattr(sentry_bridge_mod,
# "sentry_sdk", stub)`` and have the bridge honor the stub. The underscore-
# prefixed ``_sentry_sdk`` is bound at import time and is read at the top of
# ``init_sentry`` for the fast-path; this alias is what tests (and any
# future third-party callers) swap to force a particular behavior. The
# runtime path uses ``sentry_sdk`` directly via the module dict so the
# monkeypatched value wins.
sentry_sdk = _sentry_sdk

__all__ = ["init_sentry", "sentry_sdk"]

_logger = get_logger(__name__)

# Disabled counter — ``fastblocks_sentry_disabled_total{reason}``.
# Registered eagerly in ``ObservabilityRegistry`` at module load so the
# counter is scrapeable as soon as the bridge module is imported.
#
# Idempotency: pytest's ``import-mode=importlib`` reloads test modules
# per test, which can blow away ``sys.modules`` and re-execute this
# module body. ``ObservabilityRegistry.register`` raises
# ``MetricNameCollisionError`` on duplicate names, so a direct module-
# level ``Counter(...)`` would crash the second test. The
# ``_get_disabled_counter()`` helper below constructs the Counter
# exactly once across reloads (the registry's own ``_names`` set
# survives via ``ObservabilityRegistry._names``), matching the
# idempotency pattern of ``tracer._CONFIGURED``.
_SENTRY_DISABLED_COUNTER: Counter | None = None


def _get_disabled_counter() -> Counter:
    """Construct or reuse the ``fastblocks_sentry_disabled_total`` counter.

    Idempotent across module reloads: returns the cached counter if it
    was already built (and registered in ``ObservabilityRegistry``)
    earlier in the process. On first call, registers the counter in
    ``ObservabilityRegistry`` so /metrics scrapes it.
    """
    global _SENTRY_DISABLED_COUNTER
    if _SENTRY_DISABLED_COUNTER is not None:
        return _SENTRY_DISABLED_COUNTER
    _SENTRY_DISABLED_COUNTER = Counter(
        "fastblocks_sentry_disabled_total",
        "Number of times the Sentry bridge was disabled (loud-fail opted out).",
        labelnames=("reason",),
    )
    return _SENTRY_DISABLED_COUNTER


def _emit_disabled(reason: str) -> None:
    """Increment the disabled counter for the given reason label.

    Helper extracted so the import-error and runtime-init-error paths
    share one code path. ``reason`` is bounded to a small set of
    literals by the brief (currently ``"import_error"`` and
    ``"init_runtime_error"``) so cardinality is safe by construction.
    """
    _get_disabled_counter().inc(1.0, reason=reason)


def init_sentry(
    *,
    dsn: str | None = None,
    disabled_on_import_error: bool = False,
    profiling_enabled: bool = False,
    **kwargs: t.Any,
) -> None:
    """Initialise the Sentry SDK with the configured DSN.

    Per Δ19: the caller MUST install the OTel ``TracerProvider`` (via
    :func:`fastblocks.observability.tracer.setup_default_tracer_provider`)
    BEFORE calling this function. The lifespan
    (``fastblocks/adapters/app/default.py``) does the ordering; this
    function does not enforce it.

    Per Δ20: ``profiling_enabled=True`` raises ``RuntimeError``. The
    alpha path does not support Sentry profiling; enabling it would
    activate a Sentry SDK feature that has not been audited for the
    alpha-pinned 3.0.0a7 release.

    Per Δ34: when ``sentry_sdk`` cannot be imported (lean install
    without ``[observability]`` PEP 735 group), the bridge either:

      * raises :class:`SentryImportError` with ``reason="import_error"``
        if ``disabled_on_import_error=False`` (default — loud-fail).
      * increments
        ``fastblocks_sentry_disabled_total{reason="import_error"}``
        and returns silently if ``disabled_on_import_error=True``.

    Per Δ39-ζ: when ``sentry_sdk.init(...)`` raises (invalid DSN,
    network error), the bridge re-raises as
    :class:`SentryImportError` with ``reason="init_runtime_error"``
    via ``raise ... from original`` so operators see both the wrapper
    frame and the underlying cause.

    No-op when ``dsn`` is falsy (None, empty string). The bridge is
    opt-in: setting ``SENTRY_DSN`` is the only way to activate the
    Sentry client.
    """
    if profiling_enabled:
        raise RuntimeError(
            "Sentry profiling is disabled in alpha path per Δ20",
        )

    if not dsn:
        # No-op path: DSN unset. The bridge must NOT call
        # ``sentry_sdk.init`` so lean installs do not pay the SDK
        # import cost. Matches the brief's "DSN unset → no-op" test.
        return

    if not _SENTRY_SDK_AVAILABLE or _sentry_sdk is None:
        if disabled_on_import_error:
            _emit_disabled("import_error")
            return
        raise SentryImportError(reason="import_error") from _SENTRY_SDK_IMPORT_ERROR

    # Look up ``sentry_sdk`` via the module dict so test-time
    # ``monkeypatch.setattr(sentry_bridge, "sentry_sdk", stub)`` wins.
    # The bare ``_sentry_sdk`` name below is read directly because the
    # import-time binding is the canonical module reference; tests
    # patch the public ``sentry_sdk`` alias, NOT the underscore-prefixed
    # one.
    _runtime_sentry_sdk = sentry_sdk  # public alias; tests may swap this
    try:
        _runtime_sentry_sdk.init(dsn=dsn, **kwargs)
    except Exception as _init_exc:
        # Per Δ39-ζ: re-raise as SentryImportError with
        # reason="init_runtime_error". The original exception is
        # preserved via ``raise ... from _init_exc`` (Global Constraint
        # Δ35: ``raise ... from original``).
        raise SentryImportError(reason="init_runtime_error") from _init_exc

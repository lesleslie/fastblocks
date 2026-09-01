"""OTel Tracer + TracerProvider singleton for FastBlocks.

Per v6 Δ10/Δ18: wires an OTel SDK ``TracerProvider`` with a
``BatchSpanProcessor(OTLPSpanExporter(...))`` so spans flush on app
shutdown. Exposes three public names:

  * ``get_tracer(name) -> opentelemetry.trace.Tracer`` — returns the
    SDK tracer (NOT a wrapper) so callers can use the full OTel surface.
  * ``get_default_tracer_provider() -> opentelemetry.trace.TracerProvider``
    — returns the cached SDK provider. ``lifespan`` shutdown awaits
    ``.shutdown()`` on this instance.
  * ``setup_default_tracer_provider()`` — idempotent installer of the
    SDK provider + BatchSpanProcessor + OTLPSpanExporter chain. The
    module-level ``_CONFIGURED`` flag short-circuits repeat calls so
    re-init never replaces the active processor chain mid-process (same
    pattern as ``loggers._CONFIGURED``).

Lean installs: ``opentelemetry-sdk`` and
``opentelemetry-exporter-otlp-proto-http`` live in the
``[observability]`` PEP 735 group (Task 0a). When the lean env is
active and the OTel packages are absent, ``_require_otel()`` raises
``MissingDependencyError(pip_group="observability", package="opentelemetry-sdk")``
so callers see the install instruction rather than a bare ``ImportError``.

Per v6 Global Constraints:
  * ``from __future__ import annotations`` first (after docstring)
  * ``__all__`` declared
  * Modern syntax: ``X | None``, ``list[str]``
  * ``raise ... from original`` when re-raising third-party exceptions
  * No ``logger.error(..., exc_info=True)`` (use ``logger.exception(...)``)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from .loggers import get_logger

if TYPE_CHECKING:
    from opentelemetry.trace import Tracer, TracerProvider

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider as SDKTracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    _OTEL_SDK_AVAILABLE = True
    _OTEL_SDK_IMPORT_ERROR: Exception | None = None
except ImportError as _e:  # pragma: no cover - exercised only in slim envs
    _OTEL_SDK_AVAILABLE = False
    _OTEL_SDK_IMPORT_ERROR = _e

try:
    # OTLPSpanExporter lives in the HTTP/proto exporter package, NOT
    # in opentelemetry.sdk.trace.export (that path exposes only the
    # base exporter interfaces). Lean installs may have the SDK
    # without the exporter, so the import is gated separately.
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
        OTLPSpanExporter,
    )

    _OTEL_EXPORTER_AVAILABLE = True
    _OTEL_EXPORTER_IMPORT_ERROR: Exception | None = None
except ImportError as _e:  # pragma: no cover - exercised only in slim envs
    _OTEL_EXPORTER_AVAILABLE = False
    _OTEL_EXPORTER_IMPORT_ERROR = _e

__all__ = [
    "get_default_tracer_provider",
    "get_tracer",
    "setup_default_tracer_provider",
]

_logger = get_logger(__name__)

# Idempotency guard: app-startup calls ``setup_default_tracer_provider()``
# once; the module-level flag short-circuits subsequent calls so the
# active TracerProvider + BatchSpanProcessor are never replaced mid-
# process. The cached provider instance lives in ``_provider``; both
# are reset together so a real re-install is impossible without an
# explicit reset hook (none exists by design).
_CONFIGURED: bool = False
_provider: TracerProvider | None = None


def _require_otel_sdk() -> None:
    """Raise ``MissingDependencyError`` if the OTel SDK cannot be imported.

    Lean installs (``uv sync --no-group dev``) ship without the
    ``[observability]`` PEP 735 group. Without this guard, the module
    would raise bare ``ImportError`` on import-time — which callers
    can't distinguish from a real install bug. The wrapped error points
    the operator at the install command.
    """
    if not _OTEL_SDK_AVAILABLE:
        from .errors import MissingDependencyError

        raise MissingDependencyError(
            pip_group="observability",
            package="opentelemetry-sdk",
        ) from _OTEL_SDK_IMPORT_ERROR


def _require_otel_exporter() -> None:
    """Raise ``MissingDependencyError`` if the OTLPSpanExporter is absent.

    Split from ``_require_otel_sdk`` because a lean install might ship
    ``opentelemetry-sdk`` without the HTTP/proto exporter package; the
    missing-export path needs the same diagnostic without conflating
    two install instructions.
    """
    if not _OTEL_EXPORTER_AVAILABLE:
        from .errors import MissingDependencyError

        raise MissingDependencyError(
            pip_group="observability",
            package="opentelemetry-exporter-otlp-proto-http",
        ) from _OTEL_EXPORTER_IMPORT_ERROR


def setup_default_tracer_provider() -> TracerProvider:
    """Install the default OTel SDK ``TracerProvider`` + ``BatchSpanProcessor``.

    Idempotent: a second call within the same process is a no-op so the
    active processor chain is never replaced after the first
    configuration. The exporter is an ``OTLPSpanExporter`` (HTTP/proto,
    per the pin in ``pyproject.toml [dependency-groups].observability``);
    the default endpoint (``http://localhost:4318``) follows OTel
    convention so the standard collector config picks it up unchanged.

    Returns the cached provider so callers can chain ``.shutdown()``
    without a second ``get_default_tracer_provider()`` lookup.
    """
    global _CONFIGURED, _provider
    _require_otel_sdk()
    _require_otel_exporter()
    if _CONFIGURED and _provider is not None:
        return _provider
    try:
        provider = SDKTracerProvider()
        exporter = OTLPSpanExporter()
        provider.add_span_processor(BatchSpanProcessor(exporter))
    except (RuntimeError, ValueError, TypeError, OSError) as _e:
        # Re-raise with the module's context while preserving the
        # original exception via ``raise ... from _e`` so operators see
        # both the wrapper's frame and the underlying cause (per
        # Global Constraint: ``raise ... from original``).
        raise RuntimeError(
            "fastblocks.observability.tracer: OTel provider install failed",
        ) from _e
    _provider = provider
    _CONFIGURED = True
    _logger.info("otel_tracer_provider_configured")
    return _provider


def get_default_tracer_provider() -> TracerProvider:
    """Return the cached default SDK ``TracerProvider``.

    If ``setup_default_tracer_provider()`` has not been called yet
    (typical in tests that wire a fresh provider per case), this
    function installs one lazily. Tests that swap providers per case
    via ``trace.set_tracer_provider(...)`` still get a working
    ``get_tracer()`` because the SDK's ``trace.get_tracer()`` reads the
    *current* process-global provider.
    """
    _require_otel_sdk()
    if _provider is None:
        return setup_default_tracer_provider()
    return _provider


def get_tracer(name: str) -> Tracer:
    """Return an OTel ``Tracer`` for ``name``.

    The returned object is the OTel SDK's ``Tracer`` (NOT a wrapper) so
    callers can use ``start_as_current_span``, ``start_span``, and the
    rest of the public OTel surface without learning a wrapper API.
    """
    _require_otel_sdk()
    # Always read the process-global provider (NOT ``_provider``) so
    # tests that swap providers per case via ``trace.set_tracer_provider``
    # see the test-managed provider — ``_provider`` is the *cached*
    # default for production use, but the SDK's lookup honors any
    # in-process override installed via ``trace.set_tracer_provider``.
    return trace.get_tracer(name)

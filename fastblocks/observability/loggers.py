"""structlog Logger factory for FastBlocks.

Per v6 Δ40 + log_correlation mapping: pre-configures structlog with
``merge_contextvars`` + ``JSONRenderer`` so log events flow through
Oneiric's structured-logging pipeline. ``TraceContext.set()`` (see
``trace_context.py``) calls ``structlog.contextvars.bind_contextvars``
for ``trace_id`` / ``span_id`` / ``parent_span_id``; the
``merge_contextvars`` processor in our chain then surfaces those on
every log line without a custom processor.

``configure_logging()`` is idempotent: app-startup calls it once;
subsequent calls become no-ops so a re-configure never replaces the
active processor chain mid-process. The ``get_logger()`` factory
calls ``configure_logging()`` lazily so callers can use it without
explicit setup, while tests can pre-configure ``structlog.configure``
without our guard undoing their work.

Per v6 Global Constraints:
  * ``from __future__ import annotations`` first (after docstring)
  * ``__all__`` declared
  * Modern syntax: ``X | None``, ``list[str]``
  * ``raise ... from original`` when re-raising third-party exceptions
  * No ``logger.error(..., exc_info=True)`` (use ``logger.exception(...)``)
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from structlog.stdlib import BoundLogger

try:
    import structlog

    _STRUCTLOG_AVAILABLE = True
    _IMPORT_ERROR: Exception | None = None
except ImportError as _e:  # pragma: no cover - exercised only in slim envs
    _STRUCTLOG_AVAILABLE = False
    _IMPORT_ERROR = _e


def _require_structlog() -> None:
    if not _STRUCTLOG_AVAILABLE:
        from fastblocks.observability.errors import MissingDependencyError

        raise MissingDependencyError(
            pip_group="observability",
            package="structlog",
        ) from _IMPORT_ERROR


__all__ = [
    "configure_logging",
    "get_logger",
]

# Idempotency guard: app-startup calls ``configure_logging()`` once; the
# module-level flag short-circuits subsequent calls so the active
# processor chain is never replaced mid-process. Tests that need a
# different configuration call ``structlog.configure(...)`` directly,
# which is independent of this flag.
_CONFIGURED: bool = False


def configure_logging() -> None:
    """Configure structlog once at app startup.

    Idempotent: a second call within the same process is a no-op so
    the processor chain is never replaced after the first configuration.
    The processor chain is:

      1. ``structlog.contextvars.merge_contextvars`` — surfaces the
         ``trace_id`` / ``span_id`` / ``parent_span_id`` bound by
         ``TraceContext.set()`` on every log line.
      2. ``structlog.processors.JSONRenderer`` — emits structured JSON
         to stdout for the Oneiric log aggregator.

    Re-raises any structlog configuration error (``RuntimeError`` from
    ``structlog.configure``) via ``raise ... from original`` so the
    operator sees both the wrapper's context and the underlying cause.
    """
    global _CONFIGURED
    _require_structlog()
    if _CONFIGURED:
        return
    try:
        structlog.configure(
            processors=[
                structlog.contextvars.merge_contextvars,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.BoundLogger,
            context_class=dict,
            logger_factory=structlog.PrintLoggerFactory(),
        )
    except (RuntimeError, ValueError, TypeError) as _e:
        raise RuntimeError(
            "structlog.configure() failed inside fastblocks.observability.loggers",
        ) from _e
    _CONFIGURED = True


def get_logger(name: str) -> BoundLogger:
    """Return a structlog ``BoundLogger`` for ``name``.

    Lazy-configures on first call: if app-startup hasn't called
    ``configure_logging()`` yet, the factory configures once here so
    loggers work without explicit setup. The underlying
    ``structlog.get_logger()`` honors the active processor chain
    configured by ``configure_logging()`` (or by an explicit
    ``structlog.configure(...)`` call before this factory runs).
    """
    _require_structlog()
    configure_logging()
    return structlog.get_logger(name)

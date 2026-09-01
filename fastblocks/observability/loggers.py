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

from typing import Any

try:
    import structlog
    from structlog.stdlib import BoundLogger

    _STRUCTLOG_AVAILABLE = True
    _IMPORT_ERROR: Exception | None = None
except ImportError as _e:  # pragma: no cover - exercised only in slim envs
    _STRUCTLOG_AVAILABLE = False
    _IMPORT_ERROR = _e
    BoundLogger = Any  # type: ignore[assignment,misc]  # ty: ignore[invalid-assignment]


def _require_structlog() -> None:
    if not _STRUCTLOG_AVAILABLE:
        from fastblocks.observability.errors import MissingDependencyError

        raise MissingDependencyError(
            pip_group="observability",
            package="structlog",
        ) from _IMPORT_ERROR


def _interpolate_positional_args(
    logger: Any, method_name: str, event_dict: Any
) -> dict[str, Any]:
    """Interpolate ``%s`` / ``%d`` placeholders in ``event`` from positional args.

    The stdlib ``BoundLogger`` accepts ``(event, *args, **kw)`` but does
    **not** apply ``%`` formatting — it forwards the raw args to stdlib
    ``logging``. With our ``PrintLoggerFactory`` + ``JSONRenderer`` chain
    (no stdlib formatter), that would emit ``event="got %s"`` with a
    detached ``positional_args=["value"]`` field instead of the
    formatted string. To preserve the printf-style idiom used widely
    across fastblocks (``_log.warning("msg %s", value)``) without
    forcing 50+ call sites to switch to f-strings, we interpolate here
    in a single processor — matching structlog's own native logger's
    ``_maybe_interpolate`` behavior.

    Args:
        logger: Unused (structlog processor protocol).
        method_name: Unused (structlog processor protocol).
        event_dict: The event dict being built; mutated in place.

    Returns:
        The same ``event_dict`` with ``event`` interpolated and the
        temporary ``positional_args`` key removed.
    """
    positional = event_dict.pop("positional_args", None)
    if positional and isinstance(event_dict.get("event"), str):
        try:
            event_dict["event"] = event_dict["event"] % positional
        except (TypeError, ValueError):
            # Placeholder mismatch (e.g. event has no %s but args provided).
            # Leave the event untouched so callers still see the raw string.
            event_dict["positional_args"] = positional
    return event_dict


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
                _interpolate_positional_args,
                structlog.processors.JSONRenderer(),
            ],
            # stdlib BoundLogger supports positional ``*args`` (matches
            # the type hint in this module). The generic
            # ``structlog.BoundLogger`` is keyword-only and rejects
            # ``_log.warning("msg %s", value)`` with a TypeError.
            wrapper_class=structlog.stdlib.BoundLogger,
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

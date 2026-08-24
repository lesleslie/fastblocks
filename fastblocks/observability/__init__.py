"""Public API for fastblocks.observability.

Per Δ46: __all__ defines the explicit public surface.
"""
from __future__ import annotations

from .trace_context import (
    TraceContext,
    exemplar,
    get_trace_context,
    reset_trace_context,
    set_trace_context,
)
from .errors import (
    ObservabilityError,
    MissingDependencyError,
    MetricNameCollisionError,
    SentryImportError,
)
from .counters import Counter, Histogram
from .registry import (
    ObservabilityRegistry,  # noqa: F401 — singleton instance (Δ52)
    get_default_registry,
)

__all__ = [
    "TraceContext",
    "exemplar",
    "get_trace_context",
    "reset_trace_context",
    "set_trace_context",
    "ObservabilityError",
    "MissingDependencyError",
    "MetricNameCollisionError",
    "SentryImportError",
    "Counter",
    "Histogram",
    "ObservabilityRegistry",
    "get_default_registry",
]

"""Public API for fastblocks.observability.

Per Δ46: __all__ defines the explicit public surface.
"""

from __future__ import annotations

from .counters import Counter, Histogram
from .errors import (
    MetricNameCollisionError,
    MissingDependencyError,
    ObservabilityError,
    SentryImportError,
)
from .registry import (
    ObservabilityRegistry,
    get_default_registry,
)
from .trace_context import (
    TraceContext,
    exemplar,
    get_trace_context,
    reset_trace_context,
    set_trace_context,
)

__all__ = [
    "Counter",
    "Histogram",
    "MetricNameCollisionError",
    "MissingDependencyError",
    "ObservabilityError",
    "ObservabilityRegistry",
    "SentryImportError",
    "TraceContext",
    "exemplar",
    "get_default_registry",
    "get_trace_context",
    "reset_trace_context",
    "set_trace_context",
]

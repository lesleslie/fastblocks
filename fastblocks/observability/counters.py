"""Counter and Histogram wrappers around prometheus_client.

Per Δ31: Counter constructor requires documentation arg (positional only).
Per P1-2: Histogram.observe exemplar is keyword-only.
Per Δ34: lazy import guard raises MissingDependencyError (not RuntimeError).
"""
from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from prometheus_client import Counter as _PromCounter
    from prometheus_client import Histogram as _PromHistogram

try:
    from prometheus_client import Counter as _PromCounter
    from prometheus_client import Histogram as _PromHistogram
    _PROMETHEUS_AVAILABLE = True
    _IMPORT_ERROR: Exception | None = None
except ImportError as _e:
    _PROMETHEUS_AVAILABLE = False
    _IMPORT_ERROR = _e

def _require_prometheus() -> None:
    if not _PROMETHEUS_AVAILABLE:
        from fastblocks.observability.errors import MissingDependencyError
        raise MissingDependencyError(
            pip_group="observability",
            package="prometheus-client",
        ) from _IMPORT_ERROR

__all__ = [
    "Counter",
    "Histogram",
]


class Counter:
    def __init__(self, name: str, /, documentation: str, labelnames: tuple[str, ...] = ()) -> None:
        _require_prometheus()
        from fastblocks.observability.registry import ObservabilityRegistry
        # Δ74: register FIRST so duplicate names surface as MetricNameCollisionError
        # (not raw prometheus_client.ValueError). _Registry.register() catches
        # prometheus_client.ValueError and re-raises as the typed exception
        # via raise from (Δ35).
        ObservabilityRegistry.register(name)
        self._inner = _PromCounter(name, documentation, labelnames=labelnames)

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        self._inner.inc(amount, **labels)

class Histogram:
    def __init__(
        self,
        name: str, /,
        documentation: str,
        labelnames: tuple[str, ...],
        buckets: tuple[float, ...],
    ) -> None:
        _require_prometheus()
        self._inner = _PromHistogram(name, documentation, labelnames=list(labelnames), buckets=list(buckets))

    def observe(self, value: float, *, exemplar: dict[str, str] | None = None) -> None:
        self._inner.observe(value, exemplar=exemplar)

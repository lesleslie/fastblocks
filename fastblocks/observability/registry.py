"""Singleton registry wrapping prometheus_client.CollectorRegistry.

Per Δ15: explicitly owned by Commit 1.
Per Δ18 #9: raises MetricNameCollisionError on name collision.
Per Δ35: raise from prometheus_client.ValueError to preserve chain.
Per P1-8: threading.Lock protects registration only; increments lock-free.
"""
from __future__ import annotations
import threading

__all__ = [
    "ObservabilityRegistry",
    "get_default_registry",
]


_registry: "_Registry | None" = None

class _Registry:
    def __init__(self) -> None:
        from prometheus_client import CollectorRegistry
        from fastblocks.observability.counters import _PROMETHEUS_AVAILABLE, _IMPORT_ERROR
        if not _PROMETHEUS_AVAILABLE:
            from fastblocks.observability.errors import MissingDependencyError
            raise MissingDependencyError(
                pip_group="observability", package="prometheus-client",
            ) from _IMPORT_ERROR
        self._collector = CollectorRegistry()
        self._names: set[str] = set()
        self._lock = threading.Lock()

    def register(self, name: str) -> None:
        with self._lock:
            if name in self._names:
                from fastblocks.observability.errors import MetricNameCollisionError
                try:
                    raise ValueError(f"Duplicated timeseries: {name}")
                except ValueError as e:
                    raise MetricNameCollisionError(metric_name=name) from e
            self._names.add(name)

def get_default_registry() -> _Registry:
    global _registry
    if _registry is None:
        _registry = _Registry()
    return _registry

# Δ52 + Δ76: singleton INSTANCE (not module-level property). Module-level
# property(...) would return a descriptor object that lacks .register(...),
# .inc(...), etc. — `from fastblocks.observability import ObservabilityRegistry`
# would yield the descriptor, not the registry. Re-export the instance.
_registry = _Registry()
ObservabilityRegistry = _registry

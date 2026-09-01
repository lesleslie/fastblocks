"""Observability exception hierarchy per MahavishnuError precedent.

Per v6 Δ34 + Δ46: ObservabilityError(Exception) base (NOT FastBlocksError,
which doesn't exist), plain attributes (NOT kw_only constructor params).
"""

from __future__ import annotations

__all__ = [
    "MetricNameCollisionError",
    "MissingDependencyError",
    "ObservabilityError",
    "SentryImportError",
]


class ObservabilityError(Exception):
    """Base class for all observability-related errors.

    Mirrors MahavishnuError(Exception) at mahavishnu/core/errors.py:150.
    """


class MissingDependencyError(ObservabilityError):
    def __init__(self, *, pip_group: str, package: str | None = None, **kwargs) -> None:
        super().__init__(
            f"observability dep '{package or pip_group}' missing; uv sync --group {pip_group}",
            **kwargs,
        )
        self.pip_group = pip_group
        self.package = package


class MetricNameCollisionError(ObservabilityError):
    def __init__(self, *, metric_name: str, **kwargs) -> None:
        super().__init__(f"metric '{metric_name}' already registered", **kwargs)
        self.metric_name = metric_name


class SentryImportError(ObservabilityError):
    def __init__(self, *, reason: str, **kwargs) -> None:
        super().__init__(f"sentry bridge failed: {reason}", **kwargs)
        self.reason = reason

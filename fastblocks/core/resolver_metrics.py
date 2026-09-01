"""Phase 1.5 observability counters for the Oneiric resolver.

Three surfaces per the master plan
(``docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md``
line 288):

1. ``fastblocks_resolver_registry_size_total{phase}`` counter.
   After Phase 1.5 the value is 1 — the consolidation invariant.
   Future Oneiric upstream changes that introduce additional
   registries would bump this counter, surfacing the drift.

2. ``fastblocks_resolver_shadow_count_total`` counter.
   Sum of ``list_shadowed()`` across all domains. Per the plan:
   "post-Phase-1.5 should be 1 registry, N candidates, M shadowed."
   Shadowed candidates are an early-warning indicator for
   duplicate registrations that hide each other.

3. Startup log line: ``Oneiric resolver: 1 registry, N candidates,
   M shadowed``. Emitted from ``fastblocks/main.get_app()`` AFTER
   the application init path so the line reflects post-init
   registry state.

Phase 6 (master plan) will replace these with Prometheus exporters
over Oneiric's built-in resolution events. Until then, the counters
are exposed as plain integers with a ``compute_*`` snapshot
helper; no third-party observability dependency is introduced.

Phase 1.5 deliberately does NOT add ``prometheus_client`` or
``opentelemetry`` deps — those are Phase 6's scope. This module
uses only the stdlib + Oneiric (already a dep).
"""

from __future__ import annotations

import threading
from collections.abc import Iterable
from typing import Any

from oneiric.core.logging import get_logger
from fastblocks.core.resolver import FastblocksRegistry

_log = get_logger("fastblocks.resolver_metrics")

# Process-wide counter module — single instance across all
# FastblocksRegistry facades. Thread-safe via a lock; the hot path
# (register_candidate) takes the lock once per registration.
_lock = threading.Lock()

_registry_size_total: int = 0
_registration_count_total: int = 0
_shadow_count_total: int = 0

# Phase label is fixed at "post-phase-1.5" today. Future phases
# that bump this counter (e.g. Phase 6 adding a parallel metrics
# resolver) override the constant via ``set_phase_label``. The
# label is what the master plan's PromQL/Cardinality guards key on.
_phase_label: str = "post-phase-1.5"


def get_phase_label() -> str:
    """Return the current phase label for the registry_size counter."""
    return _phase_label


def set_phase_label(label: str) -> None:
    """Override the phase label. Test-only or operator-only."""
    global _phase_label
    _phase_label = label


def increment_registry_size() -> None:
    """Increment the registry-size counter.

    Called from :func:`FastblocksRegistry.__init__` — every new
    facade instance that wraps the singleton bumps the counter by
    one. Post-Phase-1.5 the expected value is 1 because the
    consolidation invariant enforces a single facade instance per
    process (see ADR 0008).
    """
    global _registry_size_total
    with _lock:
        _registry_size_total += 1


def increment_registration_count() -> None:
    """Bump the per-registration counter on every successful register_candidate."""
    global _registration_count_total
    with _lock:
        _registration_count_total += 1


def reset_for_tests() -> None:
    """Reset all counters. Test-only — production code never calls this."""
    global _registry_size_total, _registration_count_total, _shadow_count_total
    with _lock:
        _registry_size_total = 0
        _registration_count_total = 0
        _shadow_count_total = 0


def compute_registry_size_total() -> int:
    """Return the registry-size counter for the current phase label.

    Shape matches the master plan's
    ``fastblocks_resolver_registry_size_total{phase}`` metric —
    Phase 6 will wire this to a Prometheus gauge with the same
    label.
    """
    return _registry_size_total


def compute_shadow_count_total(
    facade: FastblocksRegistry,
    domains: Iterable[str] | None = None,
) -> int:
    """Return the total shadowed candidates across the given domains.

    The ``facade`` parameter is REQUIRED (no default) — Phase 1.5x
    Card 3 (F-L1-01 fix): the previous default ``facade=None``
    auto-constructed ``FastblocksRegistry(get_resolver())`` here,
    which bumped ``_registry_size_total`` via ``__init__``. Every
    call to ``emit_startup_log`` therefore inflated the registry-size
    counter, defeating the Phase 1.5 consolidation invariant the
    metric was supposed to enforce. Callers now pass the facade they
    already hold (typically ``FastblocksRegistry(get_resolver())``
    constructed once at module load).

    If ``domains`` is None, returns 0 — Oneiric exposes no
    domain-list helper, so we can't enumerate all domains without
    Phase 6's planned cached domain-list. The canary path passes
    ``domains`` explicitly.

    Phase 6 should cache the snapshot and replace this function with
    a Prometheus exporter over the same counter.
    """
    global _shadow_count_total
    if domains is None:
        domains = []
    total = 0
    for domain in domains:
        total += len(facade.list_shadowed(domain))
    with _lock:
        _shadow_count_total = total
    return total


def compute_registration_count_total() -> int:
    """Return the total successful register_candidate calls."""
    return _registration_count_total


def compute_metrics_snapshot(
    facade: FastblocksRegistry,
    domains: Iterable[str] | None = None,
) -> dict[str, Any]:
    """Return a dict snapshot of all resolver metrics.

    Shape::

        {
            "phase": "post-phase-1.5",
            "registry_size_total": <int>,
            "registration_count_total": <int>,
            "shadow_count_total": <int>,
            "domains_observed": <list[str]> | None,
        }

    The ``facade`` parameter is REQUIRED (no default) — Card 3 fix:
    prevents the auto-construction side effect that previously
    inflated ``registry_size_total`` on every call.

    Phase 6 (master plan) wires this dict to its Prometheus
    exporter. Today, the test suite asserts on it directly.
    """
    return {
        "phase": _phase_label,
        "registry_size_total": compute_registry_size_total(),
        "registration_count_total": compute_registration_count_total(),
        "shadow_count_total": compute_shadow_count_total(facade, domains=domains),
        "domains_observed": list(domains) if domains is not None else None,
    }


def emit_startup_log(
    facade: FastblocksRegistry,
    *,
    domains: Iterable[str] | None = None,
) -> None:
    """Emit the Phase 1.5 startup log line.

    Format (per master plan line 288)::

        Oneiric resolver: <N> registry, <C> candidates, <S> shadowed

    The ``facade`` parameter is REQUIRED (no default) — Card 3 fix:
    prevents the auto-construction side effect that previously
    inflated ``registry_size_total`` on every emit.

    Emitted via Oneiric's structured logger (``fastblocks.resolver_metrics``)
    at INFO level. Phase 6 will replace this with a metrics push; until
    then, the log line is the operator's primary signal that the
    consolidation invariant holds.
    """
    snapshot = compute_metrics_snapshot(facade, domains=domains)
    _log.info(
        "Oneiric resolver: %d registry, %d candidates, %d shadowed",
        snapshot["registry_size_total"],
        snapshot["registration_count_total"],
        snapshot["shadow_count_total"],
        extra={
            "phase": snapshot["phase"],
            "registry_size_total": snapshot["registry_size_total"],
            "registration_count_total": snapshot["registration_count_total"],
            "shadow_count_total": snapshot["shadow_count_total"],
        },
    )

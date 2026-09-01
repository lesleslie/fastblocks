import threading

import pytest
from fastblocks.observability import Counter, Histogram
from fastblocks.observability.errors import MetricNameCollisionError
from fastblocks.observability.registry import (
    ObservabilityRegistry,
    get_default_registry,
)


def test_counter_reuse_returns_existing_collector():
    """Module-reload safety: a second ``Counter(name, ...)`` call returns the
    existing collector instead of crashing with ``MetricNameCollisionError``.

    Pre-change behavior was to raise ``MetricNameCollisionError`` on every
    second registration of the same name. That collided with pytest's
    ``importlib.reload`` pattern (used in
    ``tests/unit/test_websocket_auth.py`` and elsewhere) where a module's
    module-level ``Counter(...)`` constructs re-execute against the same
    process-global prometheus_client REGISTRY. Without the reuse branch,
    the second pass crashed with
    ``ValueError: Duplicated timeseries: ...`` and the entire test
    session aborted. Silent reuse is the right tradeoff here: the
    collector is already wired, the increments are indistinguishable,
    and any caller that genuinely wants strict-name collision detection
    can inspect ``ObservabilityRegistry._names`` directly.
    """
    first = Counter("collide_test", "first", labelnames=("a",))
    second = Counter("collide_test", "second", labelnames=("a",))
    # Reuse: same backing collector. ``_inner`` identity is what matters
    # for increment forwarding — a label change in the second call would
    # be ignored, but the metric name collision is silent.
    assert first._inner is second._inner

def test_concurrent_register_thread_safe():
    """Per P1-8: registration-only lock; concurrent Counter calls race-safely."""
    results = []
    def reg(name):
        try:
            Counter(f"concurrent_test_{name}", "test", labelnames=("r",))
            results.append("ok")
        except MetricNameCollisionError:
            results.append("collide")
    threads = [threading.Thread(target=reg, args=(i,)) for i in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert sum(1 for r in results if r == "ok") == 10

# ---------------------------------------------------------------------------
# Wave 6 / Task 3 — drop the dead-code ``_collector`` field
# ---------------------------------------------------------------------------
#
# Per Task 3 brief: ``ObservabilityRegistry._collector = CollectorRegistry()``
# was never populated — the canonical global registry is
# ``prometheus_client.REGISTRY`` (verified correct from Task 9 in
# ``fastblocks/adapters/app/default.py``). Without removal, future maintainers
# would add ``_collector`` calls that silently produce zero metrics — the
# surface looks right but emits nothing. These tests pin the contract: NO
# ``_collector`` attribute on the registry after this commit.


def test_observability_registry_has_no_collector_attribute() -> None:
    """Per Wave 6 Task 3: ``ObservabilityRegistry`` MUST NOT expose ``_collector``.

    The field was previously initialized to ``CollectorRegistry()`` but never
    populated — every Counter is constructed via bare ``prometheus_client.
    Counter(...)`` which auto-registers on the global ``prometheus_client.
    REGISTRY`` (not on any local wrapper). Removing the dead field prevents
    future code from accidentally calling ``_collector`` and getting an empty
    registry back (silent failure mode flagged by the Task 5 review).
    """
    instance = get_default_registry()
    assert not hasattr(instance, "_collector"), (
        "ObservabilityRegistry still exposes the dead-code '_collector' field; "
        "the canonical global registry is prometheus_client.REGISTRY "
        "(see fastblocks/adapters/app/default.py:_PROM_REGISTRY)."
    )


def test_observability_registry_module_level_alias_has_no_collector() -> None:
    """Per Wave 6 Task 3: the re-exported module-level alias MUST also lack it.

    ``fastblocks.observability.registry.ObservabilityRegistry`` is a singleton
    instance (per Δ52/Δ76), not the ``_Registry`` class. Both surfaces must
    drop ``_collector`` to prevent callers from picking up the dead attribute
    via either name. Covers the public re-export path used by
    ``fastblocks.observability.__init__`` and ``fastblocks/mcp/observability.py``.
    """
    from fastblocks.observability import registry as registry_mod

    assert not hasattr(registry_mod.ObservabilityRegistry, "_collector"), (
        "fastblocks.observability.registry.ObservabilityRegistry (singleton) "
        "still exposes the dead-code '_collector' field."
    )
    # ``ObservabilityRegistry`` and ``get_default_registry()`` return the
    # same instance — both paths must agree.
    assert (
        registry_mod.ObservabilityRegistry
        is get_default_registry()
    )


# ---------------------------------------------------------------------------
# Wave 6 / Task 5 — Histogram self-registers parallel to Counter
# ---------------------------------------------------------------------------
#
# Per Task 5: ``Histogram.__init__`` MUST call
# ``ObservabilityRegistry.register(name)`` on construction, parallel to
# ``Counter.__init__:313``. Today the manual registration in
# ``fastblocks/mcp/observability.py:84`` exists ONLY because Histogram
# skipped self-registration — after Task 5 the Histogram path goes
# through the same singleton registry as Counter, so the manual call
# in ``mcp/observability.py`` is redundant and must be removed.
#
# Test name uses a unique metric name to avoid colliding with other
# tests on the process-global ``_names`` set.


def test_histogram_path_registers_via_counter_style() -> None:
    """Per Wave 6 Task 5: ``Histogram.__init__`` self-registers in
    ``ObservabilityRegistry`` parallel to ``Counter.__init__``.

    Today the only Histogram-registration test surface is the manual
    ``ObservabilityRegistry.register(name)`` call in
    ``fastblocks/mcp/observability.py:84``. After this commit that
    manual call is redundant: ``Histogram.__init__`` registers the
    name itself, so the same singleton that catches Counter name
    collisions also catches Histogram name collisions.
    """  # noqa: D205
    name = "task5_histogram_path_registers_unique"
    assert name not in ObservabilityRegistry._names  # type: ignore[attr-defined]

    Histogram(
        name, "task5 histogram-path register test",
        labelnames=(), buckets=(0.01, 1.0),
    )

    assert name in ObservabilityRegistry._names  # type: ignore[attr-defined]

import threading

import pytest
from fastblocks.observability import Counter
from fastblocks.observability.errors import MetricNameCollisionError
from fastblocks.observability.registry import (
    get_default_registry,
)


def test_counter_collision_raises_via_prometheus_chain():
    """Per Δ35: raise from prometheus_client.ValueError to preserve chain."""
    Counter("collide_test", "first", labelnames=("a",))
    with pytest.raises(MetricNameCollisionError) as exc_info:
        Counter("collide_test", "second", labelnames=("a",))
    assert exc_info.value.metric_name == "collide_test"
    assert isinstance(exc_info.value.__cause__, ValueError)

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

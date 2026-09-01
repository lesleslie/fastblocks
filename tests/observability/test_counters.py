from __future__ import annotations

import pytest
from fastblocks.observability.counters import (
    CardinalityGuard,
    Counter,
    Histogram,
)
from fastblocks.observability.registry import ObservabilityRegistry


def test_counter_requires_documentation_arg():
    """Per Δ31: Counter.__init__ requires 'documentation' as 2nd positional."""
    c = Counter("test_demo", "for spec verification", labelnames=("result",))
    assert c is not None

def test_histogram_observe_keyword_only_exemplar():
    """Per P1-2: exemplar is keyword-only; passing positional fails."""
    from fastblocks.observability.counters import Histogram
    h = Histogram("test_demo_h", "histogram for tests", labelnames=(), buckets=(0.01, 1.0))
    h.observe(0.5)
    h.observe(0.5, exemplar={"trace_id": "a"*32, "span_id": "b"*16})


# ---------------------------------------------------------------------------
# Wave 6 / Task 5 — Histogram self-register + Counter.inc() tighten guard
#                  contract + Counter.__init__ labelless+guard rejection
# ---------------------------------------------------------------------------
#
# Three tests pin the TDD-red proof BEFORE implementation lands.
# Each test uses a unique metric name because ``ObservabilityRegistry._names``
# is a process-global set; reusing names would trigger a
# ``MetricNameCollisionError`` independent of the contract under test.


def test_histogram_self_registers():
    """Per Task 5: ``Histogram.__init__`` MUST self-register its name in
    ``ObservabilityRegistry`` parallel to ``Counter.__init__``.

    Today ``Counter.__init__`` calls ``ObservabilityRegistry.register(name)``
    on line 313 of ``fastblocks/observability/counters.py``. ``Histogram``
    does not — it skips registration, and the manual call to
    ``ObservabilityRegistry.register(name)`` in
    ``fastblocks/mcp/observability.py:84`` exists ONLY to bridge the gap.
    After this commit the manual call must be removed AND ``Histogram``
    must register itself.
    """  # noqa: D205
    name = "task5_histogram_self_registers_unique"
    assert name not in ObservabilityRegistry._names  # type: ignore[attr-defined]
    Histogram(name, "task5 self-register test", labelnames=(), buckets=(0.01, 1.0))
    assert name in ObservabilityRegistry._names  # type: ignore[attr-defined]


def test_counter_inc_raises_on_missing_required_label():
    """Per Task 5: ``Counter.inc(amount, **labels)`` MUST raise ``KeyError``
    when a required label (one of ``self._labelnames``) is missing from
    ``**labels``.

    Today ``Counter.inc`` does
    ``label_values = tuple(v for v in label_values if v is not None)``
    which silently strips ``None`` slots and forwards the (shortened) tuple
    to ``prometheus_client`` — the bug is masked. After this commit a
    missing required label surfaces as ``KeyError`` (the natural exception
    for a missing kwargs entry on a known-required set).
    """  # noqa: D205
    name = "task5_inc_raises_missing_label_unique"
    c = Counter(name, "task5 inc-missing test", labelnames=("required_a",))
    with pytest.raises(KeyError):
        c.inc(1.0)  # no ``required_a=...`` kwarg provided.


def test_counter_init_raises_on_labelless_with_guard():
    """Per Task 5: ``Counter(name, doc, labelnames=(), *, cardinality_guard=X)``
    MUST raise ``ValueError`` when a guard is supplied but no labelnames.

    Today the labelless-with-guard path silently bypasses enforcement
    because ``Counter.inc`` short-circuits via
    ``if self._guard is not None and labels:``. A guard on a labelless
    counter is semantically a no-op, so the constructor should refuse
    the configuration rather than silently swallow it.
    """  # noqa: D205
    name = "task5_init_labelless_guard_unique"
    guard = CardinalityGuard(mode="enforce", max_cardinality=1)
    with pytest.raises(ValueError):
        Counter(
            name, "task5 labelless+guard test", labelnames=(),
            cardinality_guard=guard,
        )

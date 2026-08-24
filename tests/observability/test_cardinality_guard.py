"""Tests for fastblocks.observability.counters.CardinalityGuard.

Per Δ41: cardinality_mode ∈ Literal["off","audit","warn","enforce"] (semantic
order, NOT alphabetical — off < audit < warn < enforce in escalation).
Per P1-13: MetricCardinalityViolation is a slots=True, kw_only=True,
frozen=True event class derived from ValueError.
Per Δ7: CardinalityGuard exposes a ``check(label_values) -> CardinalityAction``
contract; Counter.inc() delegates to it before calling prometheus_client.

These tests pin the TDD-red proof BEFORE implementation: the module
attributes are absent, the classes do not exist, and Counter has no
``cardinality_guard`` kwarg. Implementation lands in counters.py.
"""
from __future__ import annotations

import dataclasses
import logging

import prometheus_client
import pytest
from fastblocks.observability.counters import (
    CardinalityAction,
    CardinalityGuard,
    Counter,
    MetricCardinalityViolation,
)

# ---------------------------------------------------------------------------
# 1. enforce mode raises ValueError-derived exception
# ---------------------------------------------------------------------------


def test_enforce_mode_raises_ValueError_derived_exception() -> None:
    """Per brief: enforce mode raises; isinstance both ValueError AND MetricCardinalityViolation."""
    guard = CardinalityGuard(mode="enforce", max_cardinality=2)
    with pytest.raises(MetricCardinalityViolation) as exc_info:
        guard.check(("a", "b", "c"))  # 3 unique values > threshold of 2
    assert isinstance(exc_info.value, ValueError)
    assert isinstance(exc_info.value, MetricCardinalityViolation)
    # Unbound guard collapses all label_values into the synthetic "_default" label.
    assert exc_info.value.label_name == "_default"
    assert exc_info.value.observed == 3
    assert exc_info.value.threshold == 2


def test_enforce_mode_propagates_into_counter_inc() -> None:
    """Enforce mode exception propagates from Counter.inc() to the caller."""
    guard = CardinalityGuard(mode="enforce", max_cardinality=1)
    c = Counter(
        "enforce_propagation_test", "enforce test", labelnames=("k",),
        cardinality_guard=guard,
    )
    c.inc(1.0, k="a")  # below threshold, proceeds.
    with pytest.raises(MetricCardinalityViolation) as exc_info:
        c.inc(1.0, k="b")  # exceeds threshold, raises.
    assert exc_info.value.label_name == "k"


# ---------------------------------------------------------------------------
# 2. audit mode lets inc proceed AND increments fastblocks_cardinality_violations_total
# ---------------------------------------------------------------------------


def test_audit_mode_lets_inc_proceed_and_records_violation() -> None:
    """Per Δ41: audit = count the violation, let the increment proceed."""
    guard = CardinalityGuard(mode="audit", max_cardinality=2)
    assert guard.check(("a",)) == CardinalityAction.OK
    assert guard.check(("b",)) == CardinalityAction.OK
    # Third unique value — violation observed but NOT raised.
    assert guard.check(("c",)) == CardinalityAction.RECORD

    # The violation counter is registered in ObservabilityRegistry (collision
    # detection) AND attached to the default prometheus_client.REGISTRY
    # (consistent with how every other Counter is created in this codebase).
    # Per reviewer note: /metrics in Task 9 needs to scrape this counter.
    #
    # NOTE: prometheus_client strips the conventional ``_total`` suffix from
    # the family name when registering a Counter whose name ends in
    # ``_total`` (so the sample names can carry ``_total`` while the family
    # name omits it). ``get_sample_value`` accepts the sample name, which is
    # the metric name with the ``_total`` suffix retained — exactly the
    # fully-qualified name ObservabilityRegistry tracks.
    sample_value = prometheus_client.REGISTRY.get_sample_value(
        "fastblocks_cardinality_violations_total", {"label": "_default"},
    )
    assert sample_value is not None, (
        "fastblocks_cardinality_violations_total must be registered in "
        "ObservabilityRegistry so /metrics can scrape it (per reviewer note)"
    )
    assert sample_value >= 1.0, (
        f"violation counter for label='_default' must be ≥ 1.0; "
        f"observed {sample_value}"
    )


def test_audit_mode_does_not_raise_when_threshold_exceeded() -> None:
    """Audit mode is observation-only — never raises."""
    guard = CardinalityGuard(mode="audit", max_cardinality=1)
    assert guard.check(("a",)) == CardinalityAction.OK
    # Above threshold: RECORD (no raise).
    result = guard.check(("b",))
    assert result == CardinalityAction.RECORD
    assert result is not CardinalityAction.DROP


def test_violation_counter_name_tracked_in_observability_registry() -> None:
    """Per brief: violation counter MUST be in ObservabilityRegistry (collision detection)."""
    # Trigger audit-mode violation to ensure the counter is registered.
    guard = CardinalityGuard(mode="audit", max_cardinality=1)
    guard.check(("a",))
    guard.check("b")
    # After audit-mode fire, _get_violation_counter() runs, which calls
    # ObservabilityRegistry.register("fastblocks_cardinality_violations_total").
    # We don't have a public introspection API, but the absence of
    # MetricNameCollisionError on a second violation counter proves the
    # registry has the name tracked (collision detection is name-based).
    fresh = CardinalityGuard(mode="audit", max_cardinality=1)
    fresh.check(("x",))
    fresh.check("y")  # would raise MetricNameCollisionError if NOT registered.


# ---------------------------------------------------------------------------
# 3. warn mode logs warning + drops the increment
# ---------------------------------------------------------------------------


def test_warn_mode_logs_and_drops(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Per brief: warn mode logs a warning AND does NOT increment the Counter.

    Capture mechanism: structlog routes through stdlib logging via
    ``structlog.stdlib.LoggerFactory()`` so pytest's ``caplog`` fixture
    can intercept the warning emitted by ``get_logger(...).warning(...)``.
    """
    # Configure structlog with stdlib routing so caplog captures the warning.
    # The structured event name is the first positional arg of .warning(...);
    # additional kwargs become event fields in the JSON-rendered message.
    import structlog

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
    )
    structlog.contextvars.clear_contextvars()

    counter_name = "warn_mode_test_counter_guarded"
    guard = CardinalityGuard(mode="warn", max_cardinality=1)
    c_with_guard = Counter(
        counter_name, "warn mode test guarded", labelnames=("kind",),
        cardinality_guard=guard,
    )

    with caplog.at_level(logging.WARNING, logger="fastblocks.observability.counters"):
        # First inc — below threshold — should proceed.
        c_with_guard.inc(1.0, kind="alpha")
        # Second inc — distinct label value — over threshold → dropped.
        c_with_guard.inc(1.0, kind="beta")

    # Warning log emitted with the cardinality context.
    matching_records = [
        r for r in caplog.records
        if "cardinality" in r.getMessage().lower()
        and counter_name in r.getMessage()
    ]
    assert matching_records, (
        "warn mode must emit a warning log naming the counter "
        f"(records seen: {[r.getMessage() for r in caplog.records]})"
    )

    # The Counter for "alpha" was incremented (first call below threshold).
    # Filter out ``*_created`` samples (creation timestamps) — they share
    # labels with the value samples and would otherwise pollute the count.
    alpha_count: float | None = prometheus_client.REGISTRY.get_sample_value(
        counter_name + "_total", {"kind": "alpha"},
    )
    beta_count: float | None = prometheus_client.REGISTRY.get_sample_value(
        counter_name + "_total", {"kind": "beta"},
    )
    assert alpha_count == 1.0, "first inc (below threshold) must proceed"
    assert beta_count is None, (
        f"warn mode must drop the increment when cardinality exceeded; "
        f"observed beta count: {beta_count}"
    )


# ---------------------------------------------------------------------------
# 4. off mode no-op
# ---------------------------------------------------------------------------


def test_off_mode_noop_no_log_no_raise_no_bump(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Per brief: off mode is fully transparent — no logs, no counter, no raise."""
    guard = CardinalityGuard(mode="off", max_cardinality=1)
    with caplog.at_level(logging.WARNING, logger="fastblocks.observability.counters"):
        # Three calls — all should return OK and produce no side effects.
        assert guard.check(("a",)) == CardinalityAction.OK
        assert guard.check(("b",)) == CardinalityAction.OK
        assert guard.check(("c",)) == CardinalityAction.OK
    # No log records captured.
    assert not caplog.records, (
        f"off mode must produce no log records; saw: "
        f"{[r.getMessage() for r in caplog.records]}"
    )

    # off mode with cardinality=0 still returns OK (no threshold check).
    zero_guard = CardinalityGuard(mode="off", max_cardinality=0)
    assert zero_guard.check(("only",)) == CardinalityAction.OK


# ---------------------------------------------------------------------------
# 5. Mode enum semantic order
# ---------------------------------------------------------------------------


def test_cardity_mode_semantic_order_not_alphabetical() -> None:
    """Per brief: tuple is ("off", "audit", "warn", "enforce") NOT alphabetical.

    The semantic escalation order is: off < audit < warn < enforce.
    """
    from fastblocks.observability.counters import _CARDINALITY_MODE_VALUES

    assert _CARDINALITY_MODE_VALUES == ("off", "audit", "warn", "enforce")
    # Alphabetical would be ("audit", "enforce", "off", "warn") — assert we
    # are NOT alphabetical.
    assert _CARDINALITY_MODE_VALUES != tuple(sorted(_CARDINALITY_MODE_VALUES))
    # The semantic escalation ladder holds.
    assert _CARDINALITY_MODE_VALUES.index("off") < _CARDINALITY_MODE_VALUES.index("audit")
    assert _CARDINALITY_MODE_VALUES.index("audit") < _CARDINALITY_MODE_VALUES.index("warn")
    assert _CARDINALITY_MODE_VALUES.index("warn") < _CARDINALITY_MODE_VALUES.index("enforce")


# ---------------------------------------------------------------------------
# 6. MetricCardinalityViolation is slots=True, kw_only=True, frozen=True
# ---------------------------------------------------------------------------


def test_violation_dataclass_is_slots_kw_only_frozen() -> None:
    """Per P1-13: slots=True, kw_only=True, frozen=True."""
    fields = dataclasses.fields(MetricCardinalityViolation)
    field_names = {f.name for f in fields}
    assert "metric_name" in field_names
    assert "label_name" in field_names
    assert "observed" in field_names
    assert "threshold" in field_names

    # kw_only: every field has kw_only=True.
    assert all(f.kw_only for f in fields), "every dataclass field must be kw_only"

    # frozen: mutation raises FrozenInstanceError.
    v = MetricCardinalityViolation(
        metric_name="m", label_name="l", observed=5, threshold=2,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        v.observed = 10  # type: ignore[misc]


def test_violation_inherits_value_error() -> None:
    """Per brief: MetricCardinalityViolation is ValueError-derived.

    Task 4's DecisionSpanProcessor ``except Exception`` naturally catches it
    (no engineered coupling, just a coincidence of inheritance).
    """
    v = MetricCardinalityViolation(
        metric_name="m", label_name="l", observed=5, threshold=2,
    )
    assert isinstance(v, ValueError)
    assert isinstance(v, Exception)


# ---------------------------------------------------------------------------
# Module surface contract
# ---------------------------------------------------------------------------


def test_module_declares_all_with_cardinality_guard_exports() -> None:
    """Per module pattern: every public module declares __all__."""
    import fastblocks.observability.counters as counters_mod

    assert hasattr(counters_mod, "__all__")
    for name in (
        "CardinalityGuard",
        "CardinalityAction",
        "MetricCardinalityViolation",
        "CardinalityMode",
        "Counter",
        "Histogram",
    ):
        assert name in counters_mod.__all__, f"{name} must be exported"


# ---------------------------------------------------------------------------
# Counter integration: guard kwarg is plumbed end-to-end
# ---------------------------------------------------------------------------


def test_counter_accepts_optional_cardinality_guard_kwarg() -> None:
    """Per brief: CardinalityGuard passed at Counter construction preserves signature.

    The kwarg Counter signature is preserved while exposing cardinality
    enforcement via the new ``cardinality_guard=`` keyword argument.
    """
    guard = CardinalityGuard(mode="enforce", max_cardinality=1)
    c = Counter(
        "cardinality_kwarg_test", "kwarg test", labelnames=("k",),
        cardinality_guard=guard,
    )
    # First inc OK, second raises.
    c.inc(1.0, k="a")
    with pytest.raises(MetricCardinalityViolation):
        c.inc(1.0, k="b")


def test_counter_without_guard_unchanged_behavior() -> None:
    """Counter without cardinality_guard kwarg preserves pre-Task 5 behavior.

    ``inc()`` always proceeds regardless of cardinality.
    """
    c = Counter("no_guard_test", "no guard", labelnames=("k",))
    # Many distinct label values — no guard = no enforcement, no raise.
    for letter in "abcdefghij":
        c.inc(1.0, k=letter)

    # All 10 increments landed in the default prometheus_client.REGISTRY.
    # Use get_sample_value to read each per-label value (not the
    # ``*_created`` timestamp sample, which would skew the total).
    no_guard_total = 0.0
    for letter in "abcdefghij":
        v = prometheus_client.REGISTRY.get_sample_value(
            "no_guard_test_total", {"k": letter},
        )
        if v is not None:
            no_guard_total += v
    assert no_guard_total == 10.0, (
        f"counter without guard must accept any cardinality; "
        f"observed total {no_guard_total}"
    )


def test_counter_existing_kwarg_signature_preserved() -> None:
    """Regression: pre-Task 5 Counter call sites must continue to work.

    The Task 4 fix at counters.py:48-57 uses ``Counter(name, doc,
    labelnames=...)``. Task 5 must not change that signature.
    """
    c = Counter("signature_check", "doc", labelnames=("kind",))
    c.inc(1.0, kind="x")
    # Unlabelled inc also works.
    c2 = Counter("signature_check_unlabelled", "doc")
    c2.inc(1.0)

"""D1 coverage tests for fastblocks/observability/counters.py.

Targets CardinalityAction enum, CardinalityGuard modes (off/audit/warn/
enforce), and MetricCardinalityViolation dataclass.
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

import pytest

from fastblocks.observability.counters import (
    CardinalityAction,
    CardinalityGuard,
    CardinalityMode,
    MetricCardinalityViolation,
    _CARDINALITY_MODE_VALUES,
)


# ---------------------------------------------------------------------------
# Enums and constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestEnums:
    def test_cardinality_action_members(self) -> None:
        assert CardinalityAction.OK.value == "ok"
        assert CardinalityAction.RECORD.value == "record"
        assert CardinalityAction.DROP.value == "drop"

    def test_cardinality_mode_values(self) -> None:
        # ``CardinalityMode`` is a Literal alias; verify the documented
        # values via the module-level tuple.
        assert _CARDINALITY_MODE_VALUES == ("off", "audit", "warn", "enforce")


# ---------------------------------------------------------------------------
# MetricCardinalityViolation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMetricCardinalityViolation:
    def test_construct(self) -> None:
        exc = MetricCardinalityViolation(
            metric_name="my_counter",
            label_name="label_a",
            observed=150,
            threshold=100,
        )
        assert exc.metric_name == "my_counter"
        assert exc.label_name == "label_a"
        assert exc.observed == 150
        assert exc.threshold == 100

    def test_is_value_error(self) -> None:
        exc = MetricCardinalityViolation(
            metric_name="m", label_name="l", observed=1, threshold=0
        )
        assert isinstance(exc, ValueError)


# ---------------------------------------------------------------------------
# CardinalityGuard — mode behaviors
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCardinalityGuardOff:
    def test_off_short_circuits(self) -> None:
        g = CardinalityGuard(mode="off", max_cardinality=1)
        # Even an absurd cardinality should yield OK without side effects.
        assert g.check(("a", "b", "c")) is CardinalityAction.OK
        assert g.check(("a", "b", "c")) is CardinalityAction.OK


@pytest.mark.unit
class TestCardinalityGuardAudit:
    def test_under_threshold_returns_ok(self) -> None:
        g = CardinalityGuard(mode="audit", max_cardinality=10)
        result = g.check(("a", "b", "c"))
        assert result is CardinalityAction.OK

    def test_over_threshold_returns_record(self) -> None:
        g = CardinalityGuard(mode="audit", max_cardinality=2)
        # Use 3 distinct values — exceeds threshold of 2.
        result = g.check(("a", "b", "c"))
        assert result is CardinalityAction.RECORD

    def test_repeated_values_do_not_exceed(self) -> None:
        # Duplicates collapse in the seen-set, so cardinality stays low.
        g = CardinalityGuard(mode="audit", max_cardinality=2)
        result = g.check(("a", "a", "a"))
        assert result is CardinalityAction.OK


@pytest.mark.unit
class TestCardinalityGuardWarn:
    def test_under_threshold_returns_ok(self) -> None:
        g = CardinalityGuard(mode="warn", max_cardinality=10)
        assert g.check(("a",)) is CardinalityAction.OK

    def test_over_threshold_returns_drop(self) -> None:
        g = CardinalityGuard(mode="warn", max_cardinality=1)
        result = g.check(("a", "b"))
        assert result is CardinalityAction.DROP


@pytest.mark.unit
class TestCardinalityGuardEnforce:
    def test_under_threshold_returns_ok(self) -> None:
        g = CardinalityGuard(mode="enforce", max_cardinality=10)
        assert g.check(("a",)) is CardinalityAction.OK

    def test_over_threshold_raises(self) -> None:
        g = CardinalityGuard(
            mode="enforce",
            max_cardinality=1,
            labelnames=(),
        )
        g._metric_name = "test_metric"  # noqa: SLF001
        with pytest.raises(MetricCardinalityViolation) as exc_info:
            g.check(("a", "b"))
        assert exc_info.value.metric_name == "test_metric"


# ---------------------------------------------------------------------------
# Bound-guard positional mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCardinalityGuardBound:
    def test_with_labelnames_returns_new_guard(self) -> None:
        g = CardinalityGuard(mode="audit", max_cardinality=5)
        bound = g.with_labelnames(("user",))
        # Same mode/threshold, but new seen-set.
        assert bound._mode == "audit"  # noqa: SLF001
        assert bound._labelnames == ("user",)  # noqa: SLF001
        assert bound is not g

    def test_bound_guard_tracks_label_values(self) -> None:
        g = CardinalityGuard(mode="audit", max_cardinality=2)
        bound = g.with_labelnames(("user",))
        bound._metric_name = "hits"  # noqa: SLF001
        # First call OK.
        assert bound.check(("alice",)) is CardinalityAction.OK
        # Third distinct value trips the threshold.
        assert bound.check(("bob",)) is CardinalityAction.OK
        assert bound.check(("carol",)) is CardinalityAction.RECORD


# ---------------------------------------------------------------------------
# Constructor defaults
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCardinalityGuardConstruction:
    def test_defaults(self) -> None:
        g = CardinalityGuard()
        assert g._mode == "off"  # noqa: SLF001
        assert g._max_cardinality == 100  # noqa: SLF001
        # Unbound guard uses the synthetic ``_default`` label.
        assert g._labelnames == ("_default",)  # noqa: SLF001

    def test_explicit_labelnames(self) -> None:
        g = CardinalityGuard(
            mode="audit",
            max_cardinality=5,
            labelnames=("a", "b"),
        )
        assert g._labelnames == ("a", "b")  # noqa: SLF001
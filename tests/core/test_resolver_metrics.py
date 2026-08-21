"""Phase 1.5 observability counters — metrics integration test.

Proves the three Phase 1.5 observability surfaces wired in
``fastblocks/core/resolver_metrics.py`` actually behave as
specified in the master plan:

1. ``fastblocks_resolver_registry_size_total{phase}`` — should
   be 1 post-Phase-1.5 (consolidation invariant; ADR 0008).
2. ``fastblocks_resolver_shadow_count_total`` — sum of
   ``list_shadowed()`` across observed domains.
3. The startup log line shape — emitted from
   ``fastblocks/main.get_app()``.

The ``clean_resolver`` autouse fixture in ``tests/conftest.py``
preserves the singleton instance identity (uses
``get_resolver().__init__()``). It does NOT reset the metrics
counters, so this test calls ``resolver_metrics.reset_for_tests()``
explicitly to get a known starting state — matching the test-only
nature of that helper.
"""

from __future__ import annotations

import pytest
from fastblocks.core import resolver_metrics
from fastblocks.core.resolver import FastblocksRegistry, get_resolver


@pytest.mark.unit
def test_registry_size_counter_increments_per_facade_construction() -> None:
    """Every new FastblocksRegistry facade bumps the counter.

    Post-Phase-1.5 the expected value is exactly 1 (the
    consolidation invariant from the master plan line 288: "post-
    Phase-1.5 should be 1"). This test resets to zero, then
    asserts a SINGLE facade construction bumps the counter to 1.
    """
    resolver_metrics.reset_for_tests()
    assert resolver_metrics.compute_registry_size_total() == 0
    FastblocksRegistry(get_resolver())
    assert resolver_metrics.compute_registry_size_total() == 1, (
        "After constructing a single FastblocksRegistry facade "
        "against the singleton, registry_size_total should be 1. "
        "If this fails, FastblocksRegistry.__init__ is not calling "
        "resolver_metrics.increment_registry_size()."
    )


@pytest.mark.unit
def test_registration_count_counter_increments_per_register_candidate() -> None:
    """Each successful register_candidate bumps the registration counter."""
    resolver_metrics.reset_for_tests()
    registry = FastblocksRegistry(get_resolver())
    assert resolver_metrics.compute_registration_count_total() == 0
    assert registry.register_candidate(
        "phase1_5_metrics_test",
        "first",
        factory=lambda: "instance-1",
    )
    assert resolver_metrics.compute_registration_count_total() == 1
    assert registry.register_candidate(
        "phase1_5_metrics_test",
        "second",
        factory=lambda: "instance-2",
    )
    assert resolver_metrics.compute_registration_count_total() == 2


@pytest.mark.unit
def test_phase_label_default_is_post_phase_1_5() -> None:
    """The phase label defaults to ``post-phase-1.5``.

    Per the master plan the counter shape is
    ``fastblocks_resolver_registry_size_total{phase}`` — the
    label is what the cardinality guards key on. Phase 6 may
    override via ``set_phase_label`` when it adds a parallel
    metrics resolver.
    """
    assert resolver_metrics.get_phase_label() == "post-phase-1.5"


@pytest.mark.unit
def test_shadow_count_via_explicit_domain() -> None:
    """compute_shadow_count_total sums ``list_shadowed()`` for the given domains."""
    resolver_metrics.reset_for_tests()
    registry = FastblocksRegistry(get_resolver())
    # Register two candidates under the same key; the first is
    # shadowed by the second (later registration wins under
    # default Oneiric selection).
    assert registry.register_candidate(
        "shadow_test_domain",
        "shadowed_key",
        factory=lambda: "first",
    )
    assert registry.register_candidate(
        "shadow_test_domain",
        "shadowed_key",
        factory=lambda: "second",
    )
    # No list_shadowed emissions on the first registration (it was
    # the only one). After the second registration, the first is
    # shadowed.
    total = resolver_metrics.compute_shadow_count_total(
        facade=registry, domains=["shadow_test_domain"]
    )
    assert total == 1, (
        f"Expected 1 shadowed candidate in 'shadow_test_domain', "
        f"got {total}. The second register_candidate should have "
        "shadowed the first (default Oneiric selection ordering)."
    )


@pytest.mark.unit
def test_compute_metrics_snapshot_shape() -> None:
    """The snapshot dict has all required keys for Phase 6's exporter."""
    resolver_metrics.reset_for_tests()
    FastblocksRegistry(get_resolver())
    snapshot = resolver_metrics.compute_metrics_snapshot()
    assert snapshot == {
        "phase": "post-phase-1.5",
        "registry_size_total": 1,
        "registration_count_total": 0,
        "shadow_count_total": 0,
        "domains_observed": None,
    }


@pytest.mark.unit
def test_emit_startup_log_calls_log_info_with_planned_format(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """emit_startup_log dispatches the planned log line shape.

    Format per master plan line 288:
        ``Oneiric resolver: %d registry, %d candidates, %d shadowed``

    Asserted by spying on the module-level ``_log.info`` (Oneiric's
    structured logger; not the stdlib ``logging`` propagation
    chain that ``caplog`` hooks into). We swap ``_log.info`` for a
    Mock that captures the format string + args, then assert the
    format string matches the master plan exactly.
    """
    from unittest.mock import MagicMock

    resolver_metrics.reset_for_tests()
    FastblocksRegistry(get_resolver())
    spy = MagicMock()
    monkeypatch.setattr(resolver_metrics._log, "info", spy)
    resolver_metrics.emit_startup_log()
    spy.assert_called_once()
    args = spy.call_args.args
    # Positional args: format-string, then %d values for registry,
    # candidates, shadowed. The ``extra=`` kwarg carries the
    # structured payload for Phase 6's exporter.
    assert args[0] == "Oneiric resolver: %d registry, %d candidates, %d shadowed"
    assert args[1] == 1  # registry_size_total
    assert args[2] == 0  # registration_count_total
    assert args[3] == 0  # shadow_count_total
    extra = spy.call_args.kwargs["extra"]
    assert extra["phase"] == "post-phase-1.5"
    assert extra["registry_size_total"] == 1

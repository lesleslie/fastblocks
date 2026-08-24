"""Tests for fastblocks.adapters.oneiric.observability.DecisionSpanProcessor.

Per v6 Δ8/Δ29/Δ38/Δ39-γ:
  * Δ8: filter span name == "resolver.decision" (other spans silently skipped).
  * Δ29: decision ∈ Literal["resolved","error"] enforced at type level.
  * Δ38: inherit from OTel's concrete SpanProcessor (NOT a Protocol).
  * Δ39-γ: own try/except around Counter.inc; on failure increment
    ``fastblocks_oneiric_decision_emit_failed_total{reason}``.

The bare-attrs contract is also tested here (rather than in
``test_oneiric_adapter.py``) so this file is sufficient on its own to
cover the brief's required test cases 1-5. The companion test file
focuses on the oneiric-side attribute emission contract.
"""
from __future__ import annotations

import pytest


def test_module_declares_all() -> None:
    """Per module pattern: every public module declares __all__."""
    import fastblocks.adapters.oneiric.observability as obs_mod

    assert hasattr(obs_mod, "__all__"), (
        "fastblocks.adapters.oneiric.observability must declare __all__"
    )
    assert "DecisionSpanProcessor" in obs_mod.__all__, (
        "DecisionSpanProcessor must be exported from __all__"
    )


def test_decision_span_processor_inherits_concrete_span_processor() -> None:
    """Per Δ38: inherit from OTel's concrete SpanProcessor (NOT a Protocol).

    ``opentelemetry.sdk.trace.SpanProcessor`` is the concrete base class
    TracerProvider.add_span_processor() accepts. A Protocol subclass
    would be structurally correct but OTel's isinstance-check on
    add_span_processor would fail. We assert the concrete inheritance
    both via ``issubclass`` and via ``isinstance(instance, ...)`` to
    catch either regression.
    """
    from opentelemetry.sdk.trace import SpanProcessor
    from fastblocks.adapters.oneiric.observability import DecisionSpanProcessor

    assert issubclass(DecisionSpanProcessor, SpanProcessor), (
        "DecisionSpanProcessor must inherit from the concrete "
        "opentelemetry.sdk.trace.SpanProcessor (NOT a Protocol) per Δ38"
    )

    # Concrete-instantiable: must not require arguments.
    proc = DecisionSpanProcessor()
    assert isinstance(proc, SpanProcessor), (
        "DecisionSpanProcessor() instance must satisfy "
        "isinstance(..., opentelemetry.sdk.trace.SpanProcessor)"
    )


def _make_span(name: str, attrs: dict[str, object]):
    """Build a minimal ReadableSpan-like mock with ``name`` and ``attributes``.

    Uses the SDK's ReadableSpan constructor so the .attributes property
    returns a real MappingProxyType (matching what on_end receives in
    production). Imports are lazy so missing-sdk slim envs still
    collect this test (the RED proof is a ModuleNotFoundError on
    ``fastblocks.adapters.oneiric.observability``).
    """
    from opentelemetry.sdk.trace import ReadableSpan
    from opentelemetry.trace import SpanContext, TraceFlags

    ctx = SpanContext(
        trace_id=0x1234,
        span_id=0xABCD,
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )
    return ReadableSpan(
        name=name,
        context=ctx,
        attributes=attrs,
    )


def test_on_end_resolver_decision_span_increments_counter() -> None:
    """Per brief #1+#2: domain/key/provider/decision attrs read; decision inc'd.

    Emit one resolver.decision span with decision="resolved" and assert
    the fastblocks_oneiric_decision_total{decision="resolved"} counter
    reaches 1. Uses a unique metric name to avoid registry collisions
    with other tests in the same process (ObservabilityRegistry is
    process-global).
    """
    from fastblocks.adapters.oneiric import observability as obs_mod

    # Use unique names so this test is independent of any other
    # DecisionSpanProcessor tests in the same process (Counter names
    # are process-global via ObservabilityRegistry).
    proc = obs_mod.DecisionSpanProcessor(
        decision_metric_name="test_dsp_decision_total_v1",
        emit_failed_metric_name="test_dsp_emit_failed_total_v1",
    )
    span = _make_span(
        "resolver.decision",
        {
            "domain": "fastblocks",
            "key": "templates",
            "provider": "jinja",
            "decision": "resolved",
        },
    )
    proc.on_end(span)

    # The Prometheus client value is read from the underlying inner counter.
    # prometheus_client auto-appends "_total" to Counter names; the
    # ``_name`` attribute on the wrapped Prometheus counter is the
    # public name with the suffix, while the inner ``_name`` carries
    # the unsuffixed form.
    samples = next(iter(proc._decision_counter._inner.collect())).samples
    matched = [
        s
        for s in samples
        if s.name == "test_dsp_decision_total_v1_total"
        and s.labels.get("decision") == "resolved"
    ]
    assert matched, (
        f"expected a sample with decision=resolved; got: {samples!r}"
    )
    assert matched[0].value == 1.0, (
        f"expected counter==1 after one resolver.decision emit; got {matched[0].value}"
    )


def test_on_end_resolver_decision_error_label_increments_separately() -> None:
    """Per brief #2: decision counter increments per Literal['resolved','error'].

    Emit one span with decision='resolved' then one with
    decision='error'; assert the two labels hold independent counts.
    """
    from fastblocks.adapters.oneiric import observability as obs_mod

    proc = obs_mod.DecisionSpanProcessor(
        decision_metric_name="test_dsp_decision_total_v2",
        emit_failed_metric_name="test_dsp_emit_failed_total_v2",
    )

    for decision in ("resolved", "error"):
        span = _make_span(
            "resolver.decision",
            {
                "domain": "fastblocks",
                "key": "templates",
                "provider": "jinja",
                "decision": decision,
            },
        )
        proc.on_end(span)

    samples = next(iter(proc._decision_counter._inner.collect())).samples
    by_label = {
        s.labels.get("decision"): s.value
        for s in samples
        if s.name == "test_dsp_decision_total_v2_total"
    }
    assert by_label.get("resolved") == 1.0, (
        f"expected resolved==1; got samples: {samples!r}"
    )
    assert by_label.get("error") == 1.0, (
        f"expected error==1; got samples: {samples!r}"
    )


def test_on_start_filters_non_resolver_decision_spans() -> None:
    """Per Δ8: spans whose name != 'resolver.decision' are silently skipped.

    on_start receives the same ReadableSpan shape; the processor must
    not touch the decision counter (or any other state) for unrelated
    spans. We assert by collecting the counter's value before and
    after a non-matching span; the value must remain zero.
    """
    from fastblocks.adapters.oneiric import observability as obs_mod

    proc = obs_mod.DecisionSpanProcessor(
        decision_metric_name="test_dsp_decision_total_v3",
        emit_failed_metric_name="test_dsp_emit_failed_total_v3",
    )
    span = _make_span(
        "http.server.request",
        {
            "domain": "fastblocks",
            "key": "templates",
            "provider": "jinja",
            "decision": "resolved",
        },
    )
    proc.on_start(span)

    samples = next(iter(proc._decision_counter._inner.collect())).samples
    # No labels should exist — the counter was never touched.
    assert all(s.value == 0.0 for s in samples if s.name.endswith("_total")), (
        f"non-resolver.decision span must not touch the counter; got: {samples!r}"
    )


def test_emit_failed_counter_increments_on_counter_inc_failure(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Per Δ39-γ: own try/except wrapping Counter.inc; on failure bump emit-failed.

    Inject a raising stub Counter into the DecisionSpanProcessor so
    the ``inc(amount, **labels)`` call raises. The processor's own
    try/except must catch the failure and increment
    ``fastblocks_oneiric_decision_emit_failed_total{reason}`` instead.
    """
    from fastblocks.adapters.oneiric import observability as obs_mod

    proc = obs_mod.DecisionSpanProcessor(
        decision_metric_name="test_dsp_decision_total_v4",
        emit_failed_metric_name="test_dsp_emit_failed_total_v4",
    )

    class _RaisingCounter:
        def __init__(self, fail_message: str) -> None:
            self._msg = fail_message

        def inc(self, amount: float = 1.0, **labels: str) -> None:
            raise RuntimeError(self._msg)

    raising = _RaisingCounter("cardinality_guard_reject")
    monkeypatch.setattr(proc, "_decision_counter", raising)

    span = _make_span(
        "resolver.decision",
        {
            "domain": "fastblocks",
            "key": "templates",
            "provider": "jinja",
            "decision": "resolved",
        },
    )
    # Must not raise — the try/except absorbs the failure.
    proc.on_end(span)

    samples = next(iter(proc._emit_failed_counter._inner.collect())).samples
    matched = [
        s
        for s in samples
        if s.name == "test_dsp_emit_failed_total_v4_total"
        and s.labels.get("reason") == "RuntimeError"
    ]
    assert matched, (
        f"expected emit-failed counter to increment with reason label; got: {samples!r}"
    )
    assert matched[0].value == 1.0, (
        f"expected emit-failed==1 after one failing inc; got {matched[0].value}"
    )


def test_emit_failed_counter_does_not_increment_on_success() -> None:
    """Sanity: when the decision counter inc succeeds, emit-failed stays at 0."""
    from fastblocks.adapters.oneiric import observability as obs_mod

    proc = obs_mod.DecisionSpanProcessor(
        decision_metric_name="test_dsp_decision_total_v5",
        emit_failed_metric_name="test_dsp_emit_failed_total_v5",
    )
    span = _make_span(
        "resolver.decision",
        {
            "domain": "fastblocks",
            "key": "templates",
            "provider": "jinja",
            "decision": "resolved",
        },
    )
    proc.on_end(span)

    failed_samples = next(iter(proc._emit_failed_counter._inner.collect())).samples
    assert all(s.value == 0.0 for s in failed_samples if s.name.endswith("_total")), (
        f"successful inc must not bump the emit-failed counter; got: {failed_samples!r}"
    )


def test_decision_label_restricted_to_literal_values() -> None:
    """Per Δ29: decision is Literal['resolved','error']; counter labels follow.

    Static-analysis style check: the processor's documented decision
    label set is exactly {'resolved','error'}. We don't try to enforce
    this via mypy at test time (the type annotation does that); we
    assert the labelnames tuple passed to Counter is exactly
    ('decision',) so Prometheus labels stay minimal/cardinality-safe.
    """
    from fastblocks.adapters.oneiric import observability as obs_mod

    proc = obs_mod.DecisionSpanProcessor(
        decision_metric_name="test_dsp_decision_total_v6",
        emit_failed_metric_name="test_dsp_emit_failed_total_v6",
    )
    assert proc._decision_counter._inner._labelnames == ("decision",), (
        "decision counter must label by 'decision' only (cardinality-safe); "
        f"got {proc._decision_counter._inner._labelnames!r}"
    )
    assert proc._emit_failed_counter._inner._labelnames == ("reason",), (
        "emit-failed counter must label by 'reason' only; "
        f"got {proc._emit_failed_counter._inner._labelnames!r}"
    )

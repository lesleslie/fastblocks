"""FastBlocks SpanProcessor for Oneiric resolver-decision spans.

Per v6 Δ8/Δ29/Δ38/Δ39-γ:

  * **Δ8** — filter span name to ``"resolver.decision"`` in
    :meth:`DecisionSpanProcessor.on_start`. Spans whose name does
    not match are silently skipped (no metric, no log) so the
    processor imposes zero overhead on the OTel hot path for
    unrelated spans.
  * **Δ29** — the ``decision`` attribute is a
    ``Literal["resolved","error"]`` and the Prometheus counter is
    labelled by ``decision`` only, keeping cardinality bounded.
  * **Δ38** — :class:`DecisionSpanProcessor` inherits from OTel's
    **concrete** :class:`opentelemetry.sdk.trace.SpanProcessor`
    (NOT a Protocol). OTel's ``TracerProvider.add_span_processor``
    type-checks against the concrete class; a Protocol subclass
    would be rejected on registration.
  * **Δ39-γ** — :meth:`on_end` wraps the
    :meth:`fastblocks.observability.counters.Counter.inc` call in
    its own try/except. On any exception (CardinalityGuard reject,
    registry collision at runtime, etc.) the processor increments
    ``fastblocks_oneiric_decision_emit_failed_total{reason}``
    instead of propagating the failure to the OTel SDK.

Both counters are registered through
:class:`fastblocks.observability.registry.ObservabilityRegistry` so
the existing Task 9 ``/metrics`` endpoint (committed in a later
phase) can scrape them. They are NOT mounted on the endpoint here;
that wiring is Task 9's job.

Per v6 Global Constraints:
  * ``from __future__ import annotations`` first (after docstring)
  * ``__all__`` declared
  * Modern syntax: ``X | None``, ``list[str]``
  * ``raise ... from original`` when re-raising third-party exceptions
  * No ``logger.error(..., exc_info=True)`` (use ``logger.exception(...)``)
  * Concrete ``SpanProcessor`` (not Protocol) per Δ38
  * ``__init__`` carries the standard kwarg surface so the
    ObservabilityRegistry singleton (process-global) is not required
    to know our metric names at construction time
"""
from __future__ import annotations

from typing import Any, Literal

from opentelemetry.sdk.trace import ReadableSpan, SpanProcessor
from opentelemetry.trace import Span
from fastblocks.observability.counters import Counter
from fastblocks.observability.loggers import get_logger

__all__ = [
    "DecisionSpanProcessor",
]


_logger = get_logger("fastblocks.adapters.oneiric.observability")

# Default counter names per the Phase 6 plan. Tests can construct the
# processor with override names (see the test fixtures) so multiple
# DecisionSpanProcessor instances can coexist in a single test
# process without registry-name collisions.
DEFAULT_DECISION_METRIC: str = "fastblocks_oneiric_decision_total"
DEFAULT_EMIT_FAILED_METRIC: str = "fastblocks_oneiric_decision_emit_failed_total"

# Δ29: decision is a Literal at the type level. The runtime check
# below is defense-in-depth: a future refactor that drops the type
# annotation cannot accidentally widen the label set.
_DECISION_VALUES: tuple[Literal["resolved", "error"], ...] = ("resolved", "error")


def _coerce_decision(value: object) -> Literal["resolved", "error"] | None:
    """Coerce a span attribute to the ``Literal["resolved","error"]`` set.

    Returns ``None`` for any value not in the documented set so the
    caller can decide whether to drop the span (unknown decision) or
    fall back to a default. Used to keep the Prometheus label set
    cardinality-safe (any unknown value would otherwise be a label
    series that breaks PromQL aggregations).
    """
    if value == "resolved":
        return "resolved"
    if value == "error":
        return "error"
    return None


class DecisionSpanProcessor(SpanProcessor):
    """OTel ``SpanProcessor`` that emits decision-spans metrics.

    On :meth:`on_start`, the processor filters by span name and
    returns immediately for non-matching spans (no side effects).
    On :meth:`on_end`, the processor reads the ``domain`` / ``key``
    / ``provider`` / ``decision`` attributes and increments
    ``fastblocks_oneiric_decision_total{decision=<value>}``. Any
    failure during the increment is caught and routed to
    ``fastblocks_oneiric_decision_emit_failed_total{reason=<...>}``
    so the OTel SDK never sees an exception from this processor.

    Construction parameters
    -----------------------

    ``decision_metric_name``
        Override the decision-counter name. Default:
        ``"fastblocks_oneiric_decision_total"``.
    ``emit_failed_metric_name``
        Override the emit-failed counter name. Default:
        ``"fastblocks_oneiric_decision_emit_failed_total"``.

    The two override knobs exist for one reason: the
    :class:`ObservabilityRegistry` is process-global, so two
    processors in the same test process must use distinct metric
    names to avoid a :class:`MetricNameCollisionError` at the
    second ``Counter()`` call.
    """

    def __init__(
        self,
        *,
        decision_metric_name: str = DEFAULT_DECISION_METRIC,
        emit_failed_metric_name: str = DEFAULT_EMIT_FAILED_METRIC,
    ) -> None:
        # Note: SpanProcessor has no __init__; we don't call
        # super().__init__() because the base class is the concrete
        # SDK SpanProcessor, not a Protocol. Per Δ38 the inheritance
        # alone is what makes the OTel SDK accept this class on
        # TracerProvider.add_span_processor(...).
        self._decision_counter: Counter = Counter(
            decision_metric_name,
            "Oneiric resolver-decision span outcomes.",
            labelnames=("decision",),
        )
        self._emit_failed_counter: Counter = Counter(
            emit_failed_metric_name,
            "Failures encountered while emitting the resolver-decision counter.",
            labelnames=("reason",),
        )

    def on_start(
        self,
        span: Span,
        parent_context: Any = None,
    ) -> None:
        """Filter: only ``resolver.decision`` spans are observed.

        Δ8: spans whose ``name`` is not exactly ``"resolver.decision"``
        are silently skipped. The processor does not log, does not
        emit, does not record any state for non-matching spans so
        the per-span overhead is one attribute access plus a
        string equality check.

        ``parent_context`` is accepted for signature parity with
        :class:`opentelemetry.sdk.trace.SpanProcessor.on_start` and
        is intentionally ignored.
        """
        del parent_context  # signature parity; not used
        # Span here is the API-level ``Span`` (not a ReadableSpan);
        # the SDK's Span wrapper exposes ``.name`` directly. Use a
        # try/except because some test mocks may not have a name.
        try:
            name = span.name  # type: ignore[attr-defined]
        except AttributeError:
            return
        if name != "resolver.decision":
            return
        # No state to record on start — the work happens on_end when
        # the span carries its terminal attributes.

    def on_end(self, span: ReadableSpan) -> None:
        """Read resolver-decision attrs and emit the decision counter.

        Δ29: only ``decision ∈ {"resolved","error"}`` produces a
        labelled increment. Unknown values are logged at debug
        and dropped (no counter touched, no emit-failed bump — the
        span simply is not in the contract we promised to count).

        Δ39-γ: the increment is wrapped in its own try/except. Any
        exception (e.g. a CardinalityGuard rejection) is routed to
        ``fastblocks_oneiric_decision_emit_failed_total{reason=<class name>}``
        so the OTel SDK never sees an exception from this processor.
        """
        if span.name != "resolver.decision":
            return
        attrs = span.attributes or {}
        decision = _coerce_decision(attrs.get("decision"))
        if decision is None:
            _logger.debug(
                "resolver_decision_unrecognised",
                domain=attrs.get("domain"),
                key=attrs.get("key"),
                decision=attrs.get("decision"),
            )
            return
        try:
            self._decision_counter.inc(1.0, decision=decision)
        except Exception as exc:  # Δ39-γ: own try/except absorbs failures
            reason = type(exc).__name__
            try:
                self._emit_failed_counter.inc(1.0, reason=reason)
            except Exception:  # pragma: no cover - last-ditch guard
                # If even the failure counter cannot increment (e.g.
                # observability registry torn down during shutdown),
                # surface the failure via the structured logger so
                # operators see something rather than a silent drop.
                _logger.exception(
                    "resolver_decision_emit_failed_counter_unavailable",
                    reason=reason,
                )
                return
            _logger.exception(
                "resolver_decision_emit_failed",
                domain=attrs.get("domain"),
                key=attrs.get("key"),
                provider=attrs.get("provider"),
                decision=decision,
                reason=reason,
            )
            return
        _logger.info(
            "resolver_decision",
            domain=attrs.get("domain"),
            key=attrs.get("key"),
            provider=attrs.get("provider"),
            decision=decision,
        )

"""Counter and Histogram wrappers around prometheus_client.

Per Δ31: Counter constructor requires documentation arg (positional only).
Per P1-2: Histogram.observe exemplar is keyword-only.
Per Δ34: lazy import guard raises MissingDependencyError (not RuntimeError).
Per Δ41: CardinalityMode ∈ Literal["off","audit","warn","enforce"] (semantic
        order, NOT alphabetical — escalation: off < audit < warn < enforce).
Per P1-13: MetricCardinalityViolation is a slots=True, kw_only=True,
        frozen=True, ValueError-derived event class.
Per Δ7: CardinalityGuard.check(label_values) -> CardinalityAction; Counter.inc
        delegates to it before calling prometheus_client.inc.
Per Δ39-γ compatibility: the exception class is ValueError-derived so
        DecisionSpanProcessor's existing ``except Exception`` naturally
        catches it (no engineered coupling — pure coincidence of inheritance).
"""
from __future__ import annotations

import dataclasses
import enum
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from prometheus_client import Counter as _PromCounter
    from prometheus_client import Histogram as _PromHistogram

try:
    from prometheus_client import Counter as _PromCounter
    from prometheus_client import Histogram as _PromHistogram
    _PROMETHEUS_AVAILABLE = True
    _IMPORT_ERROR: Exception | None = None
except ImportError as _e:
    _PROMETHEUS_AVAILABLE = False
    _IMPORT_ERROR = _e


def _require_prometheus() -> None:
    if not _PROMETHEUS_AVAILABLE:
        from fastblocks.observability.errors import MissingDependencyError
        raise MissingDependencyError(
            pip_group="observability",
            package="prometheus-client",
        ) from _IMPORT_ERROR


__all__ = [
    "CardinalityAction",
    "CardinalityGuard",
    "CardinalityMode",
    "Counter",
    "Histogram",
    "MetricCardinalityViolation",
]


# Per Δ41: cardinality_mode ∈ Literal["off","audit","warn","enforce"]. The
# order is SEMANTIC escalation (off → audit → warn → enforce), NOT
# alphabetical. off = bypass; audit = count + proceed; warn = log + drop;
# enforce = raise. The escalation ladder reflects how intrusive each
# mode is — off does nothing, audit is purely observational, warn
# discards offending increments, and enforce halts the offending inc.
CardinalityMode = Literal["off", "audit", "warn", "enforce"]
_CARDINALITY_MODE_VALUES: tuple[str, ...] = ("off", "audit", "warn", "enforce")


class CardinalityAction(enum.Enum):
    """Result of ``CardinalityGuard.check()`` — pre-raise return value.

    ``RAISE`` is handled by the guard raising ``MetricCardinalityViolation``
    directly from inside ``check()`` (enforce mode) and is therefore NOT
    a member of this enum. Counter.inc() interprets the return value to
    decide whether to drop the increment (DROP) or proceed (OK / RECORD).
    """
    OK = "ok"             # no violation; proceed with increment.
    RECORD = "record"     # audit mode: violation observed + counted; proceed.
    DROP = "drop"         # warn mode: violation observed; drop the increment.


@dataclasses.dataclass(slots=True, kw_only=True, frozen=True)
class MetricCardinalityViolation(ValueError):
    """Raised when a metric label's cardinality exceeds the configured threshold.

    Per P1-13: ``slots=True``, ``kw_only=True``, ``frozen=True`` event class.
    Per brief: ValueError-derived so Task 4's ``DecisionSpanProcessor``
    ``except Exception`` would naturally catch it (coincidence, not
    engineered coupling — Task 4's except clause remains unchanged).

    Attributes:
    ----------
    metric_name : str
        Name of the counter whose ``inc()`` triggered the violation.
    label_name : str
        Name of the label whose unique-value set exceeded the threshold
        (NOT the offending value; per Δ41 cardinality-violated metrics
        carry the label NAME in their dimension, never the value).
    observed : int
        Number of unique label values actually observed when the
        threshold was crossed.
    threshold : int
        Configured ``max_cardinality`` for the offending guard.
    """
    metric_name: str
    label_name: str
    observed: int
    threshold: int


class CardinalityGuard:
    """Cardinality budget enforcement for metric labels.

    Per Δ7: exposes ``check(label_values) -> CardinalityAction`` (or raises
    in enforce mode). ``Counter.inc()`` delegates to it BEFORE calling
    ``prometheus_client._inner.inc(amount)`` so that:

    * **off**      — guard returns OK without inspection (no log, no counter
                     bump, no raise). Existing Counters created without a
                     guard behave identically to off mode.
    * **audit**    — guard returns RECORD after incrementing the global
                     ``fastblocks_cardinality_violations_total{label}``
                     counter (the ``{label}`` dimension carries the
                     violated label NAME, not value, per Δ41). The inc
                     proceeds as if nothing happened.
    * **warn**     — guard returns DROP after emitting a structlog
                     warning via ``fastblocks.observability.loggers``.
                     Counter.inc() sees DROP and skips the underlying
                     ``_inner.inc(amount)`` call entirely.
    * **enforce**  — guard raises ``MetricCardinalityViolation`` from
                     inside ``check()``; Counter.inc() propagates the
                     exception to its caller.

    Counter rebinds the guard at construction via ``with_labelnames(...)``
    so a user-supplied guard can be reused across Counters with different
    labelnames. The rebound guard's seen-sets start empty (mode + threshold
    preserved).
    """

    # Class-level cache for the singleton audit-mode violation counter.
    # Lazy-initialized on first audit-mode violation; avoids paying the
    # cost of a prometheus counter creation on every CardinalityGuard
    # instance and keeps lean installs (no prometheus_client) safe.
    _VIOLATION_COUNTER: _PromCounter | None = None

    def __init__(
        self,
        *,
        mode: CardinalityMode = "off",
        max_cardinality: int = 100,
        labelnames: tuple[str, ...] = (),
    ) -> None:
        self._mode: CardinalityMode = mode
        self._max_cardinality = max_cardinality
        # Resolve effective labelnames: when the caller passes ``()`` the
        # guard operates in "unbound" mode with a single synthetic
        # "_default" label so direct ``guard.check(("a",))`` style use
        # still tracks cardinality. When bound via with_labelnames(...),
        # ``labelnames`` carries the Counter's labelnames tuple.
        self._labelnames: tuple[str, ...] = (
            labelnames if labelnames else ("_default",)
        )
        # Metric name is set when the guard is wired to a Counter.
        self._metric_name: str = ""
        # Per-label seen-set.
        self._seen: dict[str, set[str]] = {ln: set() for ln in self._labelnames}

    def with_labelnames(
        self,
        labelnames: tuple[str, ...],
        *,
        metric_name: str = "",
    ) -> CardinalityGuard:
        """Return a copy of this guard keyed to the given labelnames.

        The mode and threshold are preserved; the seen-sets reset to empty
        for the new labelnames. Used by ``Counter.__init__`` at construction
        time so a user-supplied guard can be wired to a specific Counter's
        labelnames without losing the configured mode/threshold.

        ``metric_name`` is recorded so enforce-mode exceptions identify the
        counter that triggered the violation.
        """
        new = CardinalityGuard(
            mode=self._mode,
            max_cardinality=self._max_cardinality,
            labelnames=labelnames,
        )
        new._metric_name = metric_name
        return new

    @classmethod
    def _get_violation_counter(cls) -> _PromCounter:
        """Lazy-init the singleton audit-mode violation counter.

        Registered in ``ObservabilityRegistry`` so name collisions surface
        as ``MetricNameCollisionError`` (per Δ18 #9) rather than raw
        prometheus_client ``ValueError``. Attached to the default
        ``prometheus_client.REGISTRY`` to match where every other Counter
        in this codebase lives — ``/metrics`` (Task 9) scrapes that
        registry directly.
        """
        if cls._VIOLATION_COUNTER is None:
            _require_prometheus()
            from fastblocks.observability.registry import ObservabilityRegistry
            ObservabilityRegistry.register("fastblocks_cardinality_violations_total")
            cls._VIOLATION_COUNTER = _PromCounter(
                "fastblocks_cardinality_violations_total",
                "Number of cardinality violations observed (audit mode).",
                labelnames=("label",),
            )
        return cls._VIOLATION_COUNTER

    def check(self, label_values: tuple[str, ...]) -> CardinalityAction:
        """Inspect ``label_values`` for a cardinality violation.

        ``label_values`` is a tuple of label values; when the guard is
        unbound (``labelnames=()``) the whole tuple is treated as values
        for a single synthetic ``"_default"`` label. When bound to a
        Counter's labelnames, values are mapped positionally to the
        configured labelnames (extra values fall back to ``f"label_{i}"``).

        Returns ``OK`` if no label's unique-value count exceeds
        ``max_cardinality``; ``RECORD`` (audit) or ``DROP`` (warn) on the
        first label that breaches the threshold. ``enforce`` raises
        ``MetricCardinalityViolation`` from inside this method.
        """
        if self._mode == "off":
            # Off mode short-circuits: no seen-set mutation, no logging,
            # no exception, no side effects. Returning OK lets Counter.inc
            # proceed normally.
            return CardinalityAction.OK

        if self._labelnames == ("_default",):
            # Unbound guard: collapse every value into the synthetic
            # "_default" label. This is the path used by tests that call
            # ``guard.check((...))`` directly without wiring to a Counter.
            seen_set = self._seen["_default"]
            for val in label_values:
                seen_set.add(val)
            observed = len(seen_set)
            if observed > self._max_cardinality:
                return self._handle_violation("_default", observed)
            return CardinalityAction.OK

        # Bound guard: positionally map values to labelnames.
        for i, val in enumerate(label_values):
            if i < len(self._labelnames):
                label_name = self._labelnames[i]
            else:
                # Values beyond the configured labelnames still get tracked
                # under synthetic names so off-by-one inc calls surface.
                label_name = f"label_{i}"
            self._seen.setdefault(label_name, set()).add(val)

        # Check all labels for threshold breaches.
        for label_name, seen_set in self._seen.items():
            observed = len(seen_set)
            if observed > self._max_cardinality:
                return self._handle_violation(label_name, observed)

        return CardinalityAction.OK

    def _handle_violation(
        self,
        label_name: str,
        observed: int,
    ) -> CardinalityAction:
        """Dispatch a threshold breach according to the configured mode.

        Called only when ``self._mode != "off"`` and the threshold is
        exceeded. Enforce raises; audit counts + returns RECORD; warn
        logs + returns DROP. Return value tells ``Counter.inc()``
        whether to proceed (OK / RECORD) or drop (DROP).
        """
        if self._mode == "enforce":
            raise MetricCardinalityViolation(
                metric_name=self._metric_name,
                label_name=label_name,
                observed=observed,
                threshold=self._max_cardinality,
            )
        if self._mode == "audit":
            counter = self._get_violation_counter()
            counter.labels(label=label_name).inc(1.0)
            return CardinalityAction.RECORD
        if self._mode == "warn":
            from fastblocks.observability.loggers import get_logger
            get_logger("fastblocks.observability.counters").warning(
                "cardinality_violation",
                counter=self._metric_name or "<unknown>",
                label=label_name,
                observed=observed,
                threshold=self._max_cardinality,
            )
            return CardinalityAction.DROP
        # Unreachable: off was already short-circuited, enforce raised.
        return CardinalityAction.OK


class Counter:
    def __init__(
        self,
        name: str,
        /,
        documentation: str,
        labelnames: tuple[str, ...] = (),
        *,
        cardinality_guard: CardinalityGuard | None = None,
    ) -> None:
        _require_prometheus()
        # Wave 6 Task 5: reject the labelless-with-guard configuration
        # up front. A cardinality guard on a labelless counter is a
        # semantic no-op (the only thing it can track is the synthetic
        # ``"_default"`` slot, which carries no per-call information).
        # Silently bypassing enforcement — the current behavior via
        # ``if self._guard is not None and labels:`` — would mask
        # the bug at runtime. Raise ValueError at construction so the
        # misconfiguration surfaces at import/test time, not in
        # production under load.
        if cardinality_guard is not None and not labelnames:
            raise ValueError(
                f"cardinality_guard requires labelnames (got labelnames=() "
                f"for counter {name!r}); a guard on a labelless counter "
                f"cannot enforce any cardinality budget."
            )
        from fastblocks.observability.registry import ObservabilityRegistry
        # Δ74: register FIRST so duplicate names surface as MetricNameCollisionError
        # (not raw prometheus_client.ValueError). _Registry.register() catches
        # prometheus_client.ValueError and re-raises as the typed exception
        # via raise from (Δ35).
        ObservabilityRegistry.register(name)
        self._inner = _PromCounter(name, documentation, labelnames=labelnames)
        # Cache the labelnames tuple for ``inc()`` so it can validate the
        # ``**labels`` kwargs without round-tripping through prometheus_client
        # internals. The guard (when wired) carries a parallel tuple; we
        # mirror it here on the Counter for the labelless-with-guard
        # rejection path and the missing-required-label check.
        self._labelnames: tuple[str, ...] = labelnames
        # Wire the cardinality guard (if provided) to this counter's
        # labelnames + metric name. Guard mode + threshold are preserved;
        # the seen-sets start empty so each Counter tracks its own
        # cardinality budget independently. cardinality_guard=None
        # preserves the pre-Task 5 behavior (no enforcement).
        if cardinality_guard is None:
            self._guard: CardinalityGuard | None = None
        else:
            self._guard = cardinality_guard.with_labelnames(
                labelnames, metric_name=name,
            )

    def inc(self, amount: float = 1.0, **labels: str) -> None:
        # prometheus_client's Counter.inc() does NOT accept label kwargs;
        # the proper call shape is ``_inner.labels(**labels).inc(amount)``.
        # The wrapper transparently forwards both forms: unlabelled counters
        # accept the bare inc(amount) path, labelled counters take labels
        # via the **labels kwargs and forward through the .labels() chain.
        #
        # Wave 6 Task 5: when the counter is labelled, every required
        # label MUST appear in ``**labels``. The previous code did
        #     label_values = tuple(labels.get(ln) for ln in ...)
        #     label_values = tuple(v for v in label_values if v is not None)
        # which silently stripped the missing slot and forwarded a
        # shortened tuple to prometheus_client — masking the bug. The
        # tightened contract surfaces the missing required label as a
        # KeyError on the label NAME (least-surprising diagnostic; the
        # natural exception for a missing kwargs entry on a known-required
        # set). Applies regardless of whether a cardinality guard is
        # wired: a missing required label is a programmer error, not a
        # cardinality policy decision.
        if self._labelnames:
            for ln in self._labelnames:
                if ln not in labels:
                    raise KeyError(
                        f"counter {self._inner._name!r} requires label "
                        f"{ln!r} but it was not provided to inc()"
                    )
        #
        # Cardinality enforcement (Task 5): when a guard is wired, check
        # the incoming label values BEFORE delegating to prometheus_client.
        # - off mode returns OK → inc proceeds unchanged.
        # - audit mode returns RECORD → inc proceeds (violation counted).
        # - warn mode returns DROP → inc is skipped (no _inner.inc call).
        # - enforce mode raises MetricCardinalityViolation from inside
        #   check(); the exception propagates naturally to the caller.
        if self._guard is not None and labels:
            label_values = tuple(labels[ln] for ln in self._guard._labelnames)
            action = self._guard.check(label_values)
            if action is CardinalityAction.DROP:
                return  # warn mode drops the increment entirely.
        if labels:
            self._inner.labels(**labels).inc(amount)
        else:
            self._inner.inc(amount)


class Histogram:
    def __init__(
        self,
        name: str, /,
        documentation: str,
        labelnames: tuple[str, ...],
        buckets: tuple[float, ...],
    ) -> None:
        _require_prometheus()
        # Wave 6 Task 5: self-register in ``ObservabilityRegistry`` parallel
        # to ``Counter.__init__`` (line 313 above). The manual call at
        # ``fastblocks/mcp/observability.py:84`` is now redundant — Histogram
        # registers its own name via the same singleton that catches Counter
        # name collisions, so the manual call must be removed in the same
        # commit. Mirrors Δ74 / Δ35: register FIRST so duplicate names
        # surface as ``MetricNameCollisionError`` (not raw
        # prometheus_client.ValueError).
        from fastblocks.observability.registry import ObservabilityRegistry

        ObservabilityRegistry.register(name)
        self._inner = _PromHistogram(name, documentation, labelnames=list(labelnames), buckets=list(buckets))

    def observe(
        self,
        value: float,
        *,
        exemplar: dict[str, str] | None = None,
        **labels: str,
    ) -> None:
        # Mirror Counter.inc (lines 393-397): if labels are passed via kwargs,
        # delegate via _inner.labels(**labels); otherwise emit on the bare
        # metric. This was missing in Wave 6 Task 5 — only Counter got label
        # forwarding, leaving every labelled Histogram.observe("kwargs") call
        # to raise TypeError, silently swallowed by mcp/observability.py:132.
        if labels:
            self._inner.labels(**labels).observe(value, exemplar=exemplar)
        else:
            self._inner.observe(value, exemplar=exemplar)

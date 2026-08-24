"""Shared helpers for the FastBlocks Grafana dashboard schema test.

This is a **support module** (not a test) imported by
``tests/dashboards/test_fastblocks_dashboard_schema.py``. It exists
under ``tests/`` (rather than ``fastblocks/``) because it is test-only
plumbing: it depends on ``jsonschema`` + ``prometheus_client`` which
are dev-only dependencies.

Exposes four public helpers:

* :func:`extract_metrics_from_promql` — PromQL-aware metric-name
  extraction (NOT a substring match). Recognises PromQL function
  wrappers (``rate()``, ``histogram_quantile()``, ``sum()``,
  ``irate()``, ``increase()``, ``avg()``, ``max()``, ``min()``,
  ``count()``, etc.) and label-set / offset decorators.
* :func:`load_dashboard` — load a dashboard JSON file as ``dict``.
* :func:`load_schema` — load a vendored schema JSON file as ``dict``.
* :func:`validate_dashboard_against_schema` — return a list of
  validation error strings (empty list means valid).

Also exposes :data:`PER_METRIC_INSTRUMENTATION_MATRIX` — the canonical
frozen set of metric names referenced in the dashboard. Each entry is
the **base** metric name (no ``_bucket`` / ``_count`` / ``_sum``
suffixes) per the v6 spec §Decision 36 per-metric instrumentation
matrix.
"""
from __future__ import annotations

import json
import pathlib
import re

import jsonschema

__all__ = [
    "PER_METRIC_INSTRUMENTATION_MATRIX",
    "extract_metrics_from_promql",
    "load_dashboard",
    "load_schema",
    "validate_dashboard_against_schema",
]

# Canonical per-metric instrumentation matrix per v6 spec §Decision 36
# (runbook table at fastblocks-overview Runbook section). Each entry is
# the base metric name — the Prometheus exporter appends ``_bucket`` /
# ``_count`` / ``_sum`` automatically for histograms.
PER_METRIC_INSTRUMENTATION_MATRIX: frozenset[str] = frozenset(
    {
        # Task 8 — MCP tool invocation counter
        "fastblocks_mcp_tool_invocations_total",
        # Task 8 — MCP tool duration histogram
        "fastblocks_mcp_tool_duration_seconds",
        # Task 4 — Oneiric resolver decision counter (DEFAULT_DECISION_METRIC)
        "fastblocks_oneiric_decision_total",
        # Task 4 — DecisionSpanProcessor emit-failure counter
        "fastblocks_oneiric_decision_emit_failed_total",
        # Task 5 — CardinalityGuard violation counter (audit mode)
        "fastblocks_cardinality_violations_total",
        # Task 9 — /metrics endpoint dispatch counter
        "fastblocks_metrics_endpoint_dispatch_total",
        # Task 9 — /metrics endpoint error counter
        "fastblocks_metrics_endpoint_errors_total",
        # Task 11 — OtelMiddleware trace_context.reset failure counter
        "fastblocks_otel_middleware_reset_failed_total",
        # Task 12 — Sentry bridge disabled counter
        # (brief mentioned Δ57 rename to ``sentry_init_failures_total``;
        # current Task 12 code uses ``sentry_disabled_total`` — see
        # ``fastblocks/observability/sentry_bridge.py:_SENTRY_DISABLED_COUNTER``)
        "fastblocks_sentry_disabled_total",
        # Task 13 — a11y bridge dropped counter
        "fastblocks_a11y_bridge_dropped_total",
    }
)

# PromQL function names that wrap one or more metric expressions.
# Each must be followed by an argument list (possibly nested, possibly
# with label-matching braces). The extractor strips these wrappers
# before scanning for metric names.
_PROMQL_FUNCTIONS: frozenset[str] = frozenset(
    {
        "abs",
        "absent",
        "absent_over_time",
        "avg",
        "avg_over_time",
        "bottomk",
        "ceil",
        "changes",
        "clamp",
        "clamp_max",
        "clamp_min",
        "count",
        "count_over_time",
        "count_values",
        "day_of_month",
        "day_of_week",
        "days_in_month",
        "delta",
        "deriv",
        "exp",
        "floor",
        "group",
        "histogram_quantile",
        "hour",
        "idelta",
        "increase",
        "irate",
        "label_join",
        "label_replace",
        "ln",
        "log10",
        "log2",
        "max",
        "max_over_time",
        "min",
        "min_over_time",
        "minute",
        "month",
        "predict_linear",
        "quantile",
        "quantile_over_time",
        "rate",
        "resets",
        "round",
        "scalar",
        "sgn",
        "sort",
        "sort_desc",
        "sqrt",
        "stddev",
        "stddev_over_time",
        "stdvar",
        "stdvar_over_time",
        "sum",
        "sum_over_time",
        "time",
        "timestamp",
        "topk",
        "vector",
        "year",
    }
)

# PromQL binary operators + reserved words that are valid identifier-shaped
# tokens but never metric names. Filtering these keeps the extractor from
# returning false positives like ``le`` from ``le="0.5"`` (already stripped)
# or ``on`` from ``sum by (tool_name) on (...)``.
_PROMQL_RESERVED: frozenset[str] = frozenset(
    {
        "and",
        "bool",
        "by",
        "eq",
        "ge",
        "group_left",
        "group_right",
        "gt",
        "ignoring",
        "le",
        "lt",
        "ne",
        "offset",
        "on",
        "or",
        "unless",
        "without",
    }
)

# Suffixes auto-appended by the Prometheus exposition format for
# histograms. When the extractor encounters a ``_bucket`` / ``_count``
# / ``_sum`` suffix it normalises the metric back to its base name
# (the form registered with ``Counter(name, ...)`` / ``Histogram(name, ...)``).
_HISTOGRAM_SUFFIXES: tuple[str, ...] = ("_bucket", "_count", "_sum")


def _strip_promql_functions(expr: str) -> str:
    """Recursively strip ``func_name(...)`` wrappers from ``expr``.

    Each iteration finds the leftmost identifier that is followed by an
    opening parenthesis, and removes the call if the identifier is a
    known PromQL function name. ``sum by (foo, bar) (...)`` therefore
    becomes ``...`` after stripping ``sum(...)``; the ``by`` clause is
    then removed separately (it is not a metric name).

    Raises ``ValueError`` if a paren is left unbalanced (indicating a
    malformed expression).
    """
    result = expr
    while True:
        match = re.search(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", result)
        if match is None:
            break
        func_name = match.group(1).lower()
        if func_name not in _PROMQL_FUNCTIONS:
            break
        # Find the matching closing paren, scanning forward from the open paren.
        open_idx = match.end() - 1
        depth = 0
        close_idx = -1
        for idx in range(open_idx, len(result)):
            char = result[idx]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    close_idx = idx
                    break
        if close_idx == -1:
            msg = (
                f"unbalanced parens in PromQL expression while stripping "
                f"{func_name!r}: {expr!r}"
            )
            raise ValueError(msg)
        # Drop ``func_name`` and the surrounding parens, keep the args.
        result = (
            result[: match.start()] + result[match.end() : close_idx] + result[close_idx + 1 :]
        )
    # Strip ``by (...)`` and ``without (...)`` label-modifier clauses that
    # may remain after the wrapper functions are removed. Their contents
    # are label names, not metric names.
    result = re.sub(r"\bby\s*\([^()]*\)", " ", result, flags=re.IGNORECASE)
    result = re.sub(
        r"\bwithout\s*\([^()]*\)", " ", result, flags=re.IGNORECASE
    )
    return result


def _strip_label_braces_and_offset(expr: str) -> str:
    """Remove ``{label_filter}`` decorations and ``offset <duration>`` modifiers."""
    expr = re.sub(r"\{[^{}]*\}", " ", expr)
    expr = re.sub(r"\boffset\s+\S+", " ", expr)
    return expr


def _normalize_metric_name(name: str) -> str:
    """Strip ``_bucket`` / ``_count`` / ``_sum`` to recover base metric name."""
    for suffix in _HISTOGRAM_SUFFIXES:
        if name.endswith(suffix) and len(name) > len(suffix):
            return name[: -len(suffix)]
    return name


def extract_metrics_from_promql(expr: str) -> list[str]:
    """Extract the unique metric names referenced by a PromQL expression.

    PromQL-aware: strips wrapper functions (``rate()``,
    ``histogram_quantile()``, ``sum()``, ``irate()``, etc.) and
    decorations (label-match ``{...}`` and ``offset 5m``) before
    scanning for metric identifiers. Normalises ``_bucket`` /
    ``_count`` / ``_sum`` suffixes back to the base metric name.

    NOT a substring match: ``rate`` does not match a metric named
    ``rate_count`` because the function is stripped first and the
    remaining ``rate_count`` IS a valid metric name (not normalised
    here — only Prometheus histogram suffixes are normalised).

    Returns a list of unique metric names in the order they first
    appear in the expression. An empty list is returned for
    expressions that reference no metrics (e.g. ``vector(1)``).
    """
    if not expr:
        return []
    stripped = _strip_label_braces_and_offset(expr)
    stripped = _strip_promql_functions(stripped)
    candidates = re.findall(r"\b([a-zA-Z_][a-zA-Z0-9_]*)\b", stripped)
    metrics: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        lowered = candidate.lower()
        if lowered in _PROMQL_FUNCTIONS or lowered in _PROMQL_RESERVED:
            continue
        if not candidate:
            continue
        # Strip leading underscore — private/internal identifiers.
        if candidate.startswith("_"):
            continue
        normalised = _normalize_metric_name(candidate)
        if normalised in seen:
            continue
        seen.add(normalised)
        metrics.append(normalised)
    return metrics


def load_dashboard(path: pathlib.Path) -> dict[str, object]:
    """Load a dashboard JSON file and return the parsed ``dict``.

    Raises ``FileNotFoundError`` if ``path`` is missing,
    ``json.JSONDecodeError`` if the file is malformed JSON.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def load_schema(path: pathlib.Path) -> dict[str, object]:
    """Load a vendored schema JSON file and return the parsed ``dict``.

    Raises ``FileNotFoundError`` if ``path`` is missing,
    ``json.JSONDecodeError`` if the file is malformed JSON.
    """
    return json.loads(path.read_text(encoding="utf-8"))


def validate_dashboard_against_schema(
    dashboard: dict[str, object], schema: dict[str, object]
) -> list[str]:
    """Return a list of validation errors for ``dashboard`` against ``schema``.

    Empty list means the dashboard validates cleanly. Errors are
    human-readable strings (not ``jsonschema.exceptions.ValidationError``
    instances) so the test can assert on them without coupling to
    library internals.
    """
    validator = jsonschema.Draft7Validator(schema)
    return [
        f"{'.'.join(str(p) for p in error.absolute_path)}: {error.message}"
        for error in sorted(validator.iter_errors(dashboard), key=lambda e: list(e.absolute_path))
    ]

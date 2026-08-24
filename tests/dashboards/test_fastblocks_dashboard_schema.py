"""Tests for the vendored Grafana dashboard ``fastblocks-overview.json``.

Per v6 spec §Decision 36 (per-metric instrumentation matrix) and P1-8
(PromQL-aware extraction, not substring match), the dashboard must:

1. Parse cleanly against the vendored Grafana 10.x schema.
2. Have every panel's metric present in the canonical matrix.
3. Contain no TBD / TODO / FIXME markers anywhere in titles, targets,
   or expression bodies.
4. Reference at least 8 distinct metrics across all panel targets.

The PromQL extraction logic lives in
:mod:`tests.dashboards.grafana-test-helpers` (a support module, not a
test).
"""
from __future__ import annotations

__all__ = [
    "test_vendored_schema_parses_as_json",
    "test_dashboard_has_required_top_level_keys",
    "test_dashboard_validates_against_vendored_schema",
    "test_each_panel_metric_in_per_metric_matrix",
    "test_dashboard_references_at_least_eight_distinct_metrics",
    "test_dashboard_has_eight_panels",
    "test_no_placeholder_markers_in_dashboard",
    "test_extractor_is_promql_aware_strips_rate_wrapper",
    "test_extractor_handles_histogram_quantile_with_bucket_suffix",
    "test_extractor_skips_reserved_words_like_by_and_le",
    "test_extractor_handles_nested_wrappers",
    "test_matrix_contains_known_metrics",
    "test_dashboard_is_valid_json",
]

import importlib
import json
import pathlib
import re

import pytest

# The helper module filename uses hyphens (per the brief:
# ``tests/dashboards/grafana-test-helpers.py``). Python's
# ``from ... import`` syntax rejects hyphens, so load via
# ``importlib.import_module``.
_helpers = importlib.import_module("tests.dashboards.grafana-test-helpers")

PER_METRIC_INSTRUMENTATION_MATRIX = _helpers.PER_METRIC_INSTRUMENTATION_MATRIX
extract_metrics_from_promql = _helpers.extract_metrics_from_promql
load_dashboard = _helpers.load_dashboard
load_schema = _helpers.load_schema
validate_dashboard_against_schema = _helpers.validate_dashboard_against_schema

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
DASHBOARD_PATH = REPO_ROOT / "dashboards" / "fastblocks-overview.json"
SCHEMA_PATH = REPO_ROOT / "dashboards" / "grafana-10.x-schema.json"

# Forbidden placeholder substrings — the brief requires zero TBD markers.
_PLACEHOLDER_RE = re.compile(r"\b(TBD|TODO|FIXME)\b", flags=re.IGNORECASE)


@pytest.fixture(scope="module")
def dashboard() -> dict[str, object]:
    """Load and return the FastBlocks overview dashboard JSON."""
    return load_dashboard(DASHBOARD_PATH)


@pytest.fixture(scope="module")
def schema() -> dict[str, object]:
    """Load and return the vendored Grafana 10.x schema JSON."""
    return load_schema(SCHEMA_PATH)


# ---------------------------------------------------------------------------
# 1. Vendored schema + dashboard load cleanly as JSON
# ---------------------------------------------------------------------------


def test_vendored_schema_parses_as_json() -> None:
    """The vendored Grafana 10.x schema must itself be valid JSON."""
    # ``load_schema`` raises JSONDecodeError on malformed input; reaching
    # the assertion means parsing succeeded.
    parsed = load_schema(SCHEMA_PATH)
    assert parsed["$schema"].startswith("http://json-schema.org/")


def test_dashboard_has_required_top_level_keys(dashboard: dict[str, object]) -> None:
    """Dashboard JSON must carry the canonical top-level Grafana keys."""
    assert "title" in dashboard, "dashboard.title missing"
    assert "uid" in dashboard, "dashboard.uid missing"
    assert "panels" in dashboard, "dashboard.panels missing"
    assert isinstance(dashboard["panels"], list), "dashboard.panels must be a list"


# ---------------------------------------------------------------------------
# 2. Dashboard validates against vendored schema (no schema errors)
# ---------------------------------------------------------------------------


def test_dashboard_validates_against_vendored_schema(
    dashboard: dict[str, object], schema: dict[str, object]
) -> None:
    """Validate every required field declared in the vendored schema."""
    errors = validate_dashboard_against_schema(dashboard, schema)
    assert not errors, "schema validation failed: " + "; ".join(errors)


# ---------------------------------------------------------------------------
# 3. Every panel references at least one metric, every metric in matrix
# ---------------------------------------------------------------------------


def _iter_panel_metrics(dashboard: dict[str, object]) -> list[tuple[str, str, list[str]]]:
    """Yield ``(panel_title, expr, extracted_metrics)`` for every panel target."""
    results: list[tuple[str, str, list[str]]] = []
    panels = dashboard.get("panels", [])
    assert isinstance(panels, list)
    for panel in panels:
        assert isinstance(panel, dict)
        title = str(panel.get("title", ""))
        targets = panel.get("targets", [])
        if not isinstance(targets, list):
            continue
        for target in targets:
            assert isinstance(target, dict)
            expr = target.get("expr", "")
            if not expr:
                continue
            results.append((title, str(expr), extract_metrics_from_promql(str(expr))))
    return results


def test_each_panel_metric_in_per_metric_matrix(
    dashboard: dict[str, object],
) -> None:
    """Every metric extracted from a panel expr must be in the canonical matrix."""
    matrix = PER_METRIC_INSTRUMENTATION_MATRIX
    missing: list[str] = []
    for title, expr, metrics in _iter_panel_metrics(dashboard):
        for metric in metrics:
            if metric not in matrix:
                missing.append(f"{title!r}: {expr!r} -> {metric!r}")
    assert not missing, "metrics outside the per-metric matrix: " + ", ".join(missing)


def test_dashboard_references_at_least_eight_distinct_metrics(
    dashboard: dict[str, object],
) -> None:
    """The dashboard must reference ≥ 8 distinct metrics from the matrix."""
    distinct: set[str] = set()
    for _title, _expr, metrics in _iter_panel_metrics(dashboard):
        distinct.update(metrics)
    assert len(distinct) >= 8, (
        f"dashboard references only {len(distinct)} distinct metrics; need ≥ 8: "
        f"{sorted(distinct)}"
    )


def test_dashboard_has_eight_panels(dashboard: dict[str, object]) -> None:
    """The dashboard must contain exactly 8 panels per the brief."""
    panels = dashboard.get("panels", [])
    assert isinstance(panels, list)
    assert len(panels) == 8, f"expected 8 panels, got {len(panels)}"


# ---------------------------------------------------------------------------
# 4. No TBD / TODO / FIXME markers anywhere in titles, targets, or exprs
# ---------------------------------------------------------------------------


def test_no_placeholder_markers_in_dashboard(dashboard: dict[str, object]) -> None:
    """No panel title, target expr, or description may contain TBD/TODO/FIXME."""
    findings: list[str] = []
    panels = dashboard.get("panels", [])
    assert isinstance(panels, list)
    for panel in panels:
        assert isinstance(panel, dict)
        title = str(panel.get("title", ""))
        if _PLACEHOLDER_RE.search(title):
            findings.append(f"panel.title: {title!r}")
        description = panel.get("description")
        if isinstance(description, str) and _PLACEHOLDER_RE.search(description):
            findings.append(f"panel.description: {description!r}")
        for target in panel.get("targets", []):
            if not isinstance(target, dict):
                continue
            expr = target.get("expr", "")
            if _PLACEHOLDER_RE.search(str(expr)):
                findings.append(f"target.expr: {expr!r}")
            ref_id = target.get("refId")
            if isinstance(ref_id, str) and _PLACEHOLDER_RE.search(ref_id):
                findings.append(f"target.refId: {ref_id!r}")
    if dashboard.get("title") and _PLACEHOLDER_RE.search(str(dashboard["title"])):
        findings.append(f"dashboard.title: {dashboard['title']!r}")
    assert not findings, "placeholder markers found: " + "; ".join(findings)


# ---------------------------------------------------------------------------
# 5. Extractor sanity checks (PromQL-aware, not substring)
# ---------------------------------------------------------------------------


def test_extractor_is_promql_aware_strips_rate_wrapper() -> None:
    """The extractor must strip ``rate(...)`` before matching the metric name.

    A naive substring matcher would report ``rate`` as the metric; the
    PromQL-aware extractor must return ``fastblocks_mcp_tool_invocations_total``.
    """
    metrics = extract_metrics_from_promql(
        'sum by (tool_name) (rate(fastblocks_mcp_tool_invocations_total[5m]))'
    )
    assert metrics == ["fastblocks_mcp_tool_invocations_total"]


def test_extractor_handles_histogram_quantile_with_bucket_suffix() -> None:
    """Histogram queries reference ``_bucket``; extractor must normalise to base."""
    metrics = extract_metrics_from_promql(
        "histogram_quantile(0.95, "
        "sum by (tool_name, le) (rate(fastblocks_mcp_tool_duration_seconds_bucket[5m])))"
    )
    assert metrics == ["fastblocks_mcp_tool_duration_seconds"]


def test_extractor_skips_reserved_words_like_by_and_le() -> None:
    """Reserved PromQL words (``by``, ``le``, ``on``) must not appear as metrics."""
    metrics = extract_metrics_from_promql(
        "sum by (tool_name) (rate(fastblocks_mcp_tool_invocations_total{tool_name=~\".+\"}[5m]))"
    )
    assert "by" not in metrics
    assert "le" not in metrics
    assert "on" not in metrics
    assert metrics == ["fastblocks_mcp_tool_invocations_total"]


def test_extractor_handles_nested_wrappers() -> None:
    """Nested PromQL wrappers (rate inside sum) must be unwrapped correctly."""
    metrics = extract_metrics_from_promql(
        "sum(rate(fastblocks_metrics_endpoint_errors_total{reason=\"encoder\"}[5m]))"
    )
    assert metrics == ["fastblocks_metrics_endpoint_errors_total"]


# ---------------------------------------------------------------------------
# 6. Per-metric instrumentation matrix sanity
# ---------------------------------------------------------------------------


def test_matrix_contains_known_metrics() -> None:
    """The matrix must include the core metrics referenced by the dashboard."""
    matrix = PER_METRIC_INSTRUMENTATION_MATRIX
    expected = {
        "fastblocks_mcp_tool_invocations_total",
        "fastblocks_mcp_tool_duration_seconds",
        "fastblocks_oneiric_decision_total",
        "fastblocks_cardinality_violations_total",
        "fastblocks_metrics_endpoint_dispatch_total",
    }
    assert expected.issubset(matrix), (
        f"expected metrics missing from matrix: {expected - matrix}"
    )


# ---------------------------------------------------------------------------
# 7. Dashboard JSON is itself parseable as JSON (smoke test)
# ---------------------------------------------------------------------------


def test_dashboard_is_valid_json() -> None:
    """The dashboard file must round-trip through :func:`json.loads`."""
    # ``load_dashboard`` already parses; assert no exception + key shape.
    parsed = json.loads(DASHBOARD_PATH.read_text(encoding="utf-8"))
    assert "panels" in parsed
    assert isinstance(parsed["panels"], list)
    assert len(parsed["panels"]) == 8

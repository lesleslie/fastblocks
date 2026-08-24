"""Cardinality-safe metric label Literal registry for FastBlocks observability.

Per v6 Δ29/Δ30/Δ41: the cardinality of every Prometheus metric label must
be bounded at the type level. This module is the **single source of
truth** for the Literal sets that label values may take. Downstream code
(Task 5 ``CardinalityGuard``, Task 7 cardinality check, future
``/metrics`` tooling) consults :data:`_KNOWN_LABELS` to validate that a
given label only carries values drawn from its declared Literal type.

Convention
----------

The underscore prefix in the filename signals that this module is
**internal/underscore-imported only**. External code should import the
Literal types directly (e.g. ``from fastblocks.observability._label_allowlist
import ToolStatus``) rather than the :data:`_KNOWN_LABELS` dict, so the
dict itself can be reorganised without breaking the public surface.

Label mapping
-------------

The keys of :data:`_KNOWN_LABELS` are the canonical label names that
appear in the FastBlocks observability contract. The values are the
Literal types that bound each label's value set:

- ``StyleResult`` mirrors ``ToolStatus`` because the style adapter
  renders templates and components that share the same outcome
  taxonomy (success, runtime error, validation failure).
- ``ToolName`` enumerates all 7 P1-5 MCP tools in declaration order so
  tool-to-task dispatchers can iterate them predictably.
- ``ToolStatus`` is the reduced 3-element set per Δ30: the wider set
  (``ok``, ``validation_error``, ``error``, ``timeout``, ``cancelled``,
  ``skipped``, ``unknown``) was rejected at the planning stage because
  timeout/cancelled/skipped are dead labels that no current fastblocks
  tool emits.
- ``OneiricDomain`` matches the canonical Oneiric ``SUPPORTED_DOMAINS``
  set (``adapter``, ``service``, ``task``, ``event``, ``workflow``,
  ``action``). The ``DecisionSpanProcessor`` (Task 4) reads ``domain``
  off every ``resolver.decision`` span; bounding the label to this set
  prevents accidental domain-name drift from breaking PromQL
  aggregations across ecosystem repos.
- ``OneiricDecision`` is the reduced 2-element set per Δ29 and MUST
  match Task 4's ``_DECISION_VALUES`` tuple at
  ``fastblocks/adapters/oneiric/observability.py`` exactly.
- ``RenderEscaped`` records whether a renderer escaped its output
  (``safe`` = autoescape applied OR output was pre-marked-safe,
  ``raw`` = caller-supplied HTML passed through unescaped).
"""
from __future__ import annotations

from typing import Any, Literal

# ---------------------------------------------------------------------------
# Literal types — see module docstring for the rationale of each set.
# ---------------------------------------------------------------------------

# Per Δ30: the reduced 3-element set. Matches the outcome taxonomy the
# tool layer actually emits; wider sets are rejected at the cardinality
# check (Task 7) to prevent label cardinality drift.
ToolStatus = Literal["ok", "error", "validation_error"]

# All 7 P1-5 MCP tools in declaration order. Tool-call telemetry tags
# every tool invocation with the tool's exact name; bounding this to
# a fixed enumeration lets the metrics layer label aggregations without
# worrying about a misspelled tool name creating a new label series.
ToolName = Literal[
    "validate_template",
    "list_templates",
    "render_template",
    "list_components",
    "validate_component",
    "list_adapters",
    "check_adapter_health",
]

# DecisionSpanProcessor (Task 4) emits one of these two labels per
# resolver.decision span. MUST match the runtime set in
# ``fastblocks/adapters/oneiric/observability.py::_DECISION_VALUES``.
OneiricDecision = Literal["resolved", "error"]

# Oneiric's ``SUPPORTED_DOMAINS`` is the canonical set of resolver
# domains. Bounding this label to that set keeps cross-ecosystem PromQL
# aggregations (e.g. ``sum by (domain) (rate(...))``) stable even if a
# future Oneiric version adds a new domain.
OneiricDomain = Literal[
    "adapter",
    "service",
    "task",
    "event",
    "workflow",
    "action",
]

# Style adapter outcome taxonomy — mirrors ``ToolStatus``. Style
# rendering has the same shape of operation as a tool call
# (synchronous, may raise, may emit validation errors) so the label set
# is identical.
StyleResult = Literal["ok", "error", "validation_error"]

# Whether a renderer escaped its output. ``safe`` = autoescape applied
# or caller supplied a ``SafeHTML``-marked value; ``raw`` = caller-
# supplied HTML passed through unescaped. Bounded to two values so the
# renderer can report a single, bounded label without risking
# stringly-typed cardinality drift (e.g. ``"marked_safe"`` vs
# ``"safe_marked"``).
RenderEscaped = Literal["safe", "raw"]

# ---------------------------------------------------------------------------
# The registry itself — key=label name, value=Literal type.
#
# Convention: keys are the canonical label names that appear in
# observability metric definitions. Values are the Literal aliases
# declared above. The dict is consulted by downstream tooling (Task 7
# cardinality check, /metrics scraper validation, etc.) but the Literal
# types themselves are the canonical contract.
# ---------------------------------------------------------------------------

_KNOWN_LABELS: dict[str, type[Any]] = {
    "tool_status": ToolStatus,
    "tool_name": ToolName,
    "decision": OneiricDecision,
    "domain": OneiricDomain,
    "style_result": StyleResult,
    "render_escaped": RenderEscaped,
}

__all__ = [
    "_KNOWN_LABELS",
    "OneiricDecision",
    "OneiricDomain",
    "RenderEscaped",
    "StyleResult",
    "ToolName",
    "ToolStatus",
]

"""Tests for ``fastblocks.observability._label_allowlist``.

Per v6 Δ29/Δ30/Δ41: the cardinality of every Prometheus metric label
must be bounded at the type level. This module pins the **literal**
contract:

1. All known label names are present in :data:`_KNOWN_LABELS`.
2. ``ToolStatus`` is the reduced 3-element Literal per Δ30 — wider
   sets (``timeout``, ``cancelled``, ``skipped``, ``unknown``) are
   explicitly NOT allowed.
3. ``ToolName`` is the 7-element P1-5 enumeration, in declaration
   order.
4. ``OneiricDecision`` is exactly the 2-element set per Δ29 and
   matches Task 4's ``_DECISION_VALUES`` tuple.
5. Every entry in :data:`_KNOWN_LABELS` is a class/type (the values
   are the Literal aliases).
6. ``__all__`` exports the Literal types and the registry dict.
"""
from __future__ import annotations

import typing

import pytest
from fastblocks.observability._label_allowlist import (
    OneiricDecision,
    OneiricDomain,
    RenderEscaped,
    StyleResult,
    ToolName,
    ToolStatus,
    _KNOWN_LABELS,
)


# ---------------------------------------------------------------------------
# 1. All known labels present
# ---------------------------------------------------------------------------

EXPECTED_LABEL_NAMES: tuple[str, ...] = (
    "tool_status",
    "tool_name",
    "decision",
    "domain",
    "style_result",
    "render_escaped",
)


@pytest.mark.parametrize("label_name", EXPECTED_LABEL_NAMES)
def test_known_label_present(label_name: str) -> None:
    """Each declared label name is a key in :data:`_KNOWN_LABELS`."""
    assert label_name in _KNOWN_LABELS, (
        f"label {label_name!r} must be a key in _KNOWN_LABELS"
    )


def test_known_labels_no_extras() -> None:
    """No surprise labels in :data:`_KNOWN_LABELS` (catches typos)."""
    assert set(_KNOWN_LABELS) == set(EXPECTED_LABEL_NAMES)


# ---------------------------------------------------------------------------
# 2. ToolStatus has the reduced 3-element set per Δ30
# ---------------------------------------------------------------------------


def test_tool_status_literal_reduced_set() -> None:
    """Per Δ30: ToolStatus is the reduced 3-element Literal, NOT a wider enum."""
    args = typing.get_args(ToolStatus)
    assert set(args) == {"ok", "error", "validation_error"}


def test_tool_status_literal_wider_set_rejected() -> None:
    """The wider set that Δ30 explicitly rejected must NOT appear."""
    args = set(typing.get_args(ToolStatus))
    rejected: set[str] = {"timeout", "cancelled", "skipped", "unknown"}
    assert args.isdisjoint(rejected), (
        f"ToolStatus contains rejected values from the wider set: {args & rejected}"
    )


# ---------------------------------------------------------------------------
# 3. ToolName has 7 enumerated values in declaration order
# ---------------------------------------------------------------------------


EXPECTED_TOOL_NAMES: tuple[str, ...] = (
    "validate_template",
    "list_templates",
    "render_template",
    "list_components",
    "validate_component",
    "list_adapters",
    "check_adapter_health",
)


def test_tool_name_literal_has_seven_values() -> None:
    """Per P1-5: ToolName has all 7 enumerated values."""
    args = typing.get_args(ToolName)
    assert len(args) == 7, f"expected 7 tool names, got {len(args)}: {args}"


def test_tool_name_literal_declaration_order() -> None:
    """Per brief: ToolName values appear in the exact P1-5 declaration order."""
    args = typing.get_args(ToolName)
    assert args == EXPECTED_TOOL_NAMES, (
        f"ToolName values out of order: got {args}, "
        f"expected {EXPECTED_TOOL_NAMES}"
    )


# ---------------------------------------------------------------------------
# 4. OneiricDecision has exactly the 2-element set per Δ29 and matches Task 4
# ---------------------------------------------------------------------------


def test_oneiric_decision_literal_exact_set() -> None:
    """Per Δ29: OneiricDecision is the reduced 2-element Literal."""
    args = typing.get_args(OneiricDecision)
    assert set(args) == {"resolved", "error"}


def test_oneiric_decision_matches_task_4_tuple() -> None:
    """OneiricDecision MUST match Task 4's ``_DECISION_VALUES`` tuple."""
    from fastblocks.adapters.oneiric.observability import _DECISION_VALUES

    decision_values = set(typing.get_args(OneiricDecision))
    task4_values = set(_DECISION_VALUES)
    assert decision_values == task4_values, (
        f"OneiricDecision={decision_values} disagrees with Task 4 "
        f"_DECISION_VALUES={task4_values}. Update one or the other."
    )


# ---------------------------------------------------------------------------
# 5. Lookup returns correct type (each value is a class/type)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("label_name", EXPECTED_LABEL_NAMES)
def test_known_label_value_is_a_literal_type(label_name: str) -> None:
    """Each value in :data:`_KNOWN_LABELS` is a Literal type alias.

    A ``typing.Literal[...]`` is a ``_SpecialForm`` at runtime — not a
    ``type`` instance — so the more accurate check is that the value
    exposes ``__args__`` (i.e. ``typing.get_args`` returns a non-empty
    tuple of string members). This pins the runtime contract that
    downstream cardinality tooling (Task 7) relies on.
    """
    value = _KNOWN_LABELS[label_name]
    args = typing.get_args(value)
    assert args, (
        f"label {label_name!r} value {value!r} has no get_args — not a Literal?"
    )
    assert all(isinstance(member, str) for member in args), (
        f"label {label_name!r} Literal members must be strings, got {args!r}"
    )


def test_lookup_specific_labels() -> None:
    """Spot-check that specific label names return the expected Literal types."""
    assert _KNOWN_LABELS["tool_status"] is ToolStatus
    assert _KNOWN_LABELS["tool_name"] is ToolName
    assert _KNOWN_LABELS["decision"] is OneiricDecision
    assert _KNOWN_LABELS["domain"] is OneiricDomain
    assert _KNOWN_LABELS["style_result"] is StyleResult
    assert _KNOWN_LABELS["render_escaped"] is RenderEscaped


# ---------------------------------------------------------------------------
# 6. __all__ declared
# ---------------------------------------------------------------------------


def test_module_declares_all() -> None:
    """Per module pattern: every public module declares ``__all__``."""
    import fastblocks.observability._label_allowlist as allowlist_mod

    assert hasattr(allowlist_mod, "__all__"), (
        "fastblocks.observability._label_allowlist must declare __all__"
    )


def test_all_exports_present() -> None:
    """``__all__`` exports the Literal types and the registry dict."""
    import fastblocks.observability._label_allowlist as allowlist_mod

    expected: set[str] = {
        "ToolStatus",
        "ToolName",
        "OneiricDecision",
        "OneiricDomain",
        "StyleResult",
        "RenderEscaped",
        "_KNOWN_LABELS",
    }
    assert expected.issubset(set(allowlist_mod.__all__)), (
        f"__all__ missing exports: {expected - set(allowlist_mod.__all__)}"
    )

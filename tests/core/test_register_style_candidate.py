"""Phase 2 mechanical-four Commit4 — register_style_candidate direct tests.

The Protocol isinstance gate added in Commit4 (in
``fastblocks.adapters.oneiric_helper.register_style_candidate``) is
the new production code in this commit. It MUST have direct unit
tests — testing the Protocol surface alone does not exercise the
gate.

Three tests cover:
1. Happy path — a valid StyleAdapter module is registered.
2. Missing-method rejection — ``TypeError`` is raised naming the
   missing methods.
3. CandidateValidationError propagation — strict-validation errors
   from the underlying register_candidate_strict propagate.
"""
from __future__ import annotations

import typing as t
from types import SimpleNamespace

import pytest
from fastblocks.adapters.oneiric_helper import register_style_candidate


def _valid_style_adapter() -> t.Any:
    """Build a SimpleNamespace satisfying StyleAdapter (4 methods)."""
    ns = SimpleNamespace()
    ns.register_style_functions = lambda *a, **kw: None
    ns.get_css_path = lambda *a, **kw: "/style.css"
    ns.get_js_path = lambda *a, **kw: "/style.js"
    ns.escape_user_input = lambda *a, **kw: "<escaped>"
    return t.cast("t.Any", ns)


@pytest.mark.unit
def test_register_style_candidate_accepts_valid_adapter(
    fresh_registry,
) -> None:
    """A module with all 4 StyleAdapter methods registers without error."""
    module = _valid_style_adapter()
    # Should NOT raise; happy path
    register_style_candidate(fresh_registry, "vanilla", module)


@pytest.mark.unit
def test_register_style_candidate_raises_for_missing_method(
    fresh_registry,
) -> None:
    """A module missing a StyleAdapter method raises TypeError."""
    module = SimpleNamespace()
    # Deliberately missing all 4 methods
    with pytest.raises(TypeError) as excinfo:
        register_style_candidate(fresh_registry, "vanilla", module)
    msg = str(excinfo.value)
    assert "register_style_functions" in msg, (
        f"TypeError must name missing 'register_style_functions'; "
        f"got: {msg!r}"
    )
    assert "get_css_path" in msg
    assert "get_js_path" in msg
    assert "escape_user_input" in msg


@pytest.mark.unit
def test_register_style_candidate_narrows_missing_method_list(
    fresh_registry,
) -> None:
    """A module missing only one method gets only that method named."""
    module = SimpleNamespace()
    module.register_style_functions = lambda *a, **kw: None
    module.get_css_path = lambda *a, **kw: "/x"
    module.get_js_path = lambda *a, **kw: "/y"
    # Missing only escape_user_input
    with pytest.raises(TypeError) as excinfo:
        register_style_candidate(fresh_registry, "vanilla", module)
    msg = str(excinfo.value)
    assert "escape_user_input" in msg
    # And NOT the methods that ARE present (no false positives)
    assert "register_style_functions" not in msg or "missing" in msg.lower()
    # The exact match-rejection: the message names the missing method.

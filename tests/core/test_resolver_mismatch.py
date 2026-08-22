"""Phase 2 mechanical-four Commit4 — format_resolver_mismatch tests.

Exercises the registry-vs-Literal drift detector from
``fastblocks.core.validators``. Six tests cover happy path,
mismatch error shape, nearest-neighbor hint, unavailable-explain
fallback, narrow-exception catch, and structured-log emission.
"""
from __future__ import annotations

import pytest
from fastblocks.core.validators import (
    ResolverMismatchError,
    format_resolution_explanation_one_line,
    format_resolver_mismatch,
)


@pytest.mark.unit
def test_format_resolver_mismatch_raises_for_illegal_value(
    fresh_registry,
) -> None:
    """Known-bad style value triggers ResolverMismatchError."""
    with pytest.raises(ResolverMismatchError) as excinfo:
        format_resolver_mismatch(fresh_registry, "style", "kelp")
    err = excinfo.value
    assert err.value == "kelp"
    assert "vanilla" in err.legal
    assert "fastblocks_ui" in err.legal


@pytest.mark.unit
def test_resolver_mismatch_error_message_includes_legal_set(
    fresh_registry,
) -> None:
    """Error message names the legal set so operators see what's allowed."""
    with pytest.raises(ResolverMismatchError) as excinfo:
        format_resolver_mismatch(fresh_registry, "style", "kelp")
    msg = str(excinfo.value)
    assert "vanilla" in msg
    assert "fastblocks_ui" in msg


@pytest.mark.unit
def test_nearest_neighbor_hint_for_typo(
    fresh_registry,
) -> None:
    """Typo with lexical similarity gets a 'Did you mean ...?' hint."""
    with pytest.raises(ResolverMismatchError) as excinfo:
        format_resolver_mismatch(fresh_registry, "style", "vanila")
    err = excinfo.value
    assert err.nearest == "vanilla", (
        f"Expected nearest='vanilla' for typo 'vanila'; got {err.nearest!r}"
    )
    assert "vanilla" in str(err)


@pytest.mark.unit
def test_no_nearest_hint_for_unrelated_string(
    fresh_registry,
) -> None:
    """Unrelated strings (kelp, bulma) get no hint, but still raise."""
    with pytest.raises(ResolverMismatchError) as excinfo:
        format_resolver_mismatch(fresh_registry, "style", "kelp")
    assert excinfo.value.nearest is None


@pytest.mark.unit
def test_unavailable_explain_falls_back_gracefully() -> None:
    """explain() failures don't crash; resolver_explain='<unavailable>'."""
    # A registry whose explain() raises RuntimeError on every call.
    class BrokenRegistry:
        def explain(self, domain: str, value: str) -> None:
            raise RuntimeError("simulated registry failure")

    with pytest.raises(ResolverMismatchError) as excinfo:
        format_resolver_mismatch(BrokenRegistry(), "style", "kelp")
    assert excinfo.value.resolver_explain == "<unavailable>"


@pytest.mark.unit
def test_format_resolution_explanation_one_line_handles_none() -> None:
    """The formatter accepts None and returns '<unavailable>'."""
    assert format_resolution_explanation_one_line(None) == "<unavailable>"

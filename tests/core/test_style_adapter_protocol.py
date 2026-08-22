"""Phase 2 mechanical-four Commit4 — StyleAdapter Protocol gate tests.

The registration gate ``isinstance(module, StyleAdapter)`` requires
both ``@runtime_checkable`` (Python 3.13) and the four expected
methods. These tests exercise the gate via direct isinstance calls
and via the ``_protocol_missing_methods`` helper.
"""
from __future__ import annotations

import typing as t
from types import SimpleNamespace

import pytest
from fastblocks.core.validators import (
    StyleAdapter,
    _protocol_missing_methods,
)


def _make_module_with(methods: set[str]) -> t.Any:
    """Build a SimpleNamespace with the given methods populated as no-ops."""
    ns = SimpleNamespace()
    for method in ("register_style_functions", "get_css_path",
                    "get_js_path", "escape_user_input"):
        if method in methods:
            setattr(ns, method, lambda *a, **kw: None)
        else:
            # Don't set the attribute at all — module genuinely lacks it
            pass
    return t.cast("StyleAdapter", ns)


@pytest.mark.unit
@pytest.mark.parametrize(
    "missing_method",
    ["register_style_functions", "get_css_path", "get_js_path",
     "escape_user_input"],
)
def test_protocol_missing_methods_reports_missing_method(
    missing_method: str,
) -> None:
    """Each missing method is named in the helper's return value."""
    module = _make_module_with(
        {"register_style_functions", "get_css_path", "get_js_path",
         "escape_user_input"} - {missing_method}
    )
    missing = _protocol_missing_methods(module, StyleAdapter)
    assert missing_method in missing, (
        f"_protocol_missing_methods must report '{missing_method}' as "
        f"missing; got {missing}"
    )


@pytest.mark.unit
def test_full_style_adapter_satisfies_protocol() -> None:
    """A module with all four methods is a StyleAdapter."""
    module = _make_module_with(
        {"register_style_functions", "get_css_path", "get_js_path",
         "escape_user_input"}
    )
    assert isinstance(module, StyleAdapter), (
        "Module with all 4 StyleAdapter methods must satisfy the Protocol"
    )


@pytest.mark.unit
def test_protocol_is_runtime_checkable() -> None:
    """StyleAdapter carries @runtime_checkable."""
    assert hasattr(StyleAdapter, "_is_runtime_protocol"), (
        "StyleAdapter is not @runtime_checkable; isinstance() will "
        "raise TypeError at registration time"
    )

"""Phase 2 mechanical-four Commit1 — core/validators module smoke test."""
from __future__ import annotations

import pytest


@pytest.mark.unit
def test_validators_module_exports_required_names() -> None:
    from fastblocks.core import validators

    required = (
        "StyleName",
        "DEFAULT_STYLE",
        "StyleAdapter",
        "TemplateAdapter",
        "ResolverMismatchError",
        "format_resolver_mismatch",
        "format_resolution_explanation_one_line",
    )
    for name in required:
        assert hasattr(validators, name), (
            f"fastblocks.core.validators is missing required export: {name}"
        )


@pytest.mark.unit
def test_style_name_literal_has_two_members() -> None:
    import typing
    from fastblocks.core.validators import StyleName

    args = typing.get_args(StyleName)
    assert args == ("vanilla", "fastblocks_ui"), (
        f"StyleName members {args!r} do not match expected "
        "('vanilla', 'fastblocks_ui')"
    )


@pytest.mark.unit
def test_default_style_is_a_style_name_member() -> None:
    from fastblocks.core.validators import DEFAULT_STYLE, StyleName

    # runtime check (Literal isn't enforceable at runtime, but at minimum
    # DEFAULT_STYLE must be one of the members)
    assert DEFAULT_STYLE in ("vanilla", "fastblocks_ui"), (
        f"DEFAULT_STYLE {DEFAULT_STYLE!r} is not a valid StyleName member"
    )
    # static check (ty catches if DEFAULT_STYLE's annotation drifts)
    _: StyleName = DEFAULT_STYLE


@pytest.mark.unit
def test_style_adapter_protocol_has_four_methods() -> None:
    from fastblocks.core.validators import StyleAdapter

    methods = {"register_style_functions", "get_css_path", "get_js_path", "escape_user_input"}
    assert methods.issubset(set(dir(StyleAdapter))), (
        f"StyleAdapter missing methods: "
        f"{methods - set(dir(StyleAdapter))}"
    )


@pytest.mark.unit
def test_template_adapter_protocol_has_two_methods() -> None:
    from fastblocks.core.validators import TemplateAdapter

    methods = {"render", "init_envs"}
    assert methods.issubset(set(dir(TemplateAdapter))), (
        f"TemplateAdapter missing methods: {methods - set(dir(TemplateAdapter))}"
    )


@pytest.mark.unit
def test_protocols_are_runtime_checkable() -> None:
    from fastblocks.core.validators import StyleAdapter, TemplateAdapter

    # runtime_checkable is required for isinstance() on method-only
    # Protocols on Python 3.13
    assert hasattr(StyleAdapter, "_is_runtime_protocol"), (
        "StyleAdapter is not @runtime_checkable; isinstance() will raise TypeError"
    )
    assert hasattr(TemplateAdapter, "_is_runtime_protocol"), (
        "TemplateAdapter is not @runtime_checkable; isinstance() will raise TypeError"
    )

"""Phase 4 v2.1 Commit 1 — capabilities.py smoke test.

Verifies the public API contract: capability tuples, registration map,
and tool-capability tag map.
"""
from __future__ import annotations

import typing as t

import pytest


@pytest.mark.unit
def test_all_capabilities_contains_exactly_seven_tools() -> None:
    from fastblocks.mcp.capabilities import ALL_CAPABILITIES

    assert len(ALL_CAPABILITIES) == 7, (
        f"Expected 7 tools in ALL_CAPABILITIES; got {len(ALL_CAPABILITIES)}: "
        f"{ALL_CAPABILITIES!r}"
    )


@pytest.mark.unit
def test_capability_tuples_are_mutually_exclusive() -> None:
    from fastblocks.mcp.capabilities import (
        TEMPLATE_CAPABILITY,
        COMPONENT_CAPABILITY,
        ADAPTER_CAPABILITY,
    )

    all_tools = (
        set(TEMPLATE_CAPABILITY)
        | set(COMPONENT_CAPABILITY)
        | set(ADAPTER_CAPABILITY)
    )
    assert len(all_tools) == 7, (
        f"Tool names overlap across capability tuples; "
        f"TEMPLATE={TEMPLATE_CAPABILITY}, "
        f"COMPONENT={COMPONENT_CAPABILITY}, "
        f"ADAPTER={ADAPTER_CAPABILITY}"
    )


@pytest.mark.unit
def test_registration_map_covers_all_seven_tools() -> None:
    from fastblocks.mcp.capabilities import (
        ALL_CAPABILITIES,
        get_registration_map,
    )

    registration_map = get_registration_map()
    assert set(registration_map.keys()) == set(ALL_CAPABILITIES), (
        f"Registration map missing tools: "
        f"{set(ALL_CAPABILITIES) - set(registration_map.keys())}; "
        f"extra tools: {set(registration_map.keys()) - set(ALL_CAPABILITIES)}"
    )
    for tool_name, fn in registration_map.items():
        assert callable(fn), f"{tool_name!r} maps to non-callable: {fn!r}"


@pytest.mark.unit
def test_get_tool_capability_returns_expected_tags() -> None:
    from fastblocks.mcp.capabilities import get_tool_capability

    expected: dict[str, str] = {
        "validate_template": "template",
        "list_templates": "template",
        "render_template": "template",
        "list_components": "component",
        "validate_component": "component",
        "list_adapters": "adapter",
        "check_adapter_health": "adapter",
    }
    for tool_name, expected_tag in expected.items():
        got = get_tool_capability(tool_name)
        assert got == expected_tag, (
            f"get_tool_capability({tool_name!r}) returned {got!r}; "
            f"expected {expected_tag!r}"
        )
    # Unknown tool returns None
    assert get_tool_capability("nonexistent_tool") is None

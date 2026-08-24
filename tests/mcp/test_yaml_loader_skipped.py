"""Phase 4 v2.1 Commit 2 — yaml-loader deferred-state documentation tests.

Documents that v2.1 does NOT export a yaml-loader helper from
``fastblocks.mcp.capabilities``. Consumers who want yaml-driven profile
must pass their own ``yaml_loader`` to ``apply_tool_profile``, or rely
on env-var only.
"""
from __future__ import annotations

import pytest


@pytest.mark.unit
def test_capabilities_does_not_export_yaml_loader() -> None:
    """v2.1 does NOT export a yaml-loader helper from capabilities."""
    import fastblocks.mcp.capabilities as cap_mod

    # No yaml_loader function exists in capabilities
    yaml_loader_attrs = [
        attr for attr in dir(cap_mod)
        if "yaml" in attr.lower() and "loader" in attr.lower()
    ]
    assert yaml_loader_attrs == [], (
        f"capabilities.py must NOT export a yaml-loader helper in v2.1 "
        f"(deferred to Phase 6+ config extension); found: {yaml_loader_attrs}"
    )


@pytest.mark.unit
def test_capabilities_does_not_export_oneiric_yaml_loader() -> None:
    """v2.1 removed the v2 _oneiric_yaml_loader function entirely."""
    import fastblocks.mcp.capabilities as cap_mod

    assert not hasattr(cap_mod, "_oneiric_yaml_loader"), (
        "_oneiric_yaml_loader must NOT exist in v2.1 (v2 referenced nonexistent "
        "fastblocks.core.config.get_settings; v2.1 dropped it entirely)"
    )


@pytest.mark.unit
def test_discover_tools_skipped_tool_not_listed() -> None:
    """When a gate returns False, the corresponding tools are NOT in
    discover_tools (they never register). Documents the R3 design
    decision: there is no ``is_available`` field because unavailable
    tools aren't in the list to begin with."""
    from unittest.mock import AsyncMock, MagicMock, patch

    from fastblocks.mcp.capabilities import (
        register_adapter_capability,
        register_component_capability,
        register_template_capability,
    )

    mock_server = MagicMock()
    # Empty server.list_tools() — adapter gate skipped it
    mock_server.list_tools = AsyncMock(return_value=[])

    with patch(
        "fastblocks.mcp.capabilities._is_template_available", return_value=False
    ), patch(
        "fastblocks.mcp.capabilities._is_component_available", return_value=False
    ), patch(
        "fastblocks.mcp.capabilities._is_adapter_available", return_value=False
    ):
        register_template_capability(mock_server)
        register_component_capability(mock_server)
        register_adapter_capability(mock_server)

    # No tools registered (all gates False)
    assert not mock_server.tool.called, (
        "All capability functions must skip silently when all gates return False"
    )

"""Phase 4 v2.1 Commit 1 — fastblocks_discovery custom discovery_fn tests.

Verifies the optional consumer-side discovery override emits the
{name, capability, description, inputSchema} schema with no
``is_available`` field (per R3 — ``is_available`` is structurally
impossible because unavailable tools aren't in ``server.list_tools()``).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest


@pytest.mark.unit
async def test_fastblocks_discovery_emits_full_schema() -> None:
    """fastblocks_discovery returns the documented schema for registered tools."""
    from fastblocks.mcp.discovery import fastblocks_discovery

    # Mock server with 3 registered tools
    mock_tool_template = MagicMock()
    mock_tool_template.name = "validate_template"
    mock_tool_template.description = "Validate a template."
    mock_tool_template.inputSchema = {"type": "object", "properties": {}}

    mock_tool_component = MagicMock()
    mock_tool_component.name = "list_components"
    mock_tool_component.description = "List components."
    mock_tool_component.inputSchema = {"type": "object", "properties": {}}

    mock_tool_adapter = MagicMock()
    mock_tool_adapter.name = "check_adapter_health"
    mock_tool_adapter.description = "Check adapter health."
    mock_tool_adapter.inputSchema = {"type": "object", "properties": {}}
    mock_server = MagicMock()
    mock_server.list_tools = AsyncMock(
        return_value=[mock_tool_template, mock_tool_component, mock_tool_adapter]
    )

    result = await fastblocks_discovery(mock_server, filter_query=None)

    assert len(result) == 3
    # Each entry has the documented schema
    for entry in result:
        assert set(entry.keys()) == {"name", "capability", "description", "inputSchema"}, (
            f"Entry has unexpected keys: {set(entry.keys())}; expected "
            f"{{name, capability, description, inputSchema}}"
        )
        assert entry["capability"] in {"template", "component", "adapter"}, (
            f"Capability tag must be one of template/component/adapter; got {entry['capability']!r}"
        )
    # Verify capability tags per tool name
    by_name = {entry["name"]: entry for entry in result}
    assert by_name["validate_template"]["capability"] == "template"
    assert by_name["list_components"]["capability"] == "component"
    assert by_name["check_adapter_health"]["capability"] == "adapter"


@pytest.mark.unit
async def test_fastblocks_discovery_query_filter() -> None:
    """``query='template'`` filters to TEMPLATE_CAPABILITY tools."""
    from fastblocks.mcp.discovery import fastblocks_discovery

    mock_tools = []
    for name, desc in [
        ("validate_template", "Validate a template."),
        ("list_components", "List components."),
    ]:
        m = MagicMock()
        m.name = name
        m.description = desc
        m.inputSchema = {"type": "object"}
        mock_tools.append(m)
    mock_server = MagicMock()
    mock_server.list_tools = AsyncMock(return_value=mock_tools)

    result = await fastblocks_discovery(mock_server, filter_query="template")

    assert len(result) == 1, (
        f"Expected query='template' to filter to 1 template tool; got {len(result)}"
    )
    assert result[0]["name"] == "validate_template"


@pytest.mark.unit
async def test_fastblocks_discovery_skipped_tool_not_in_result() -> None:
    """Tools that failed a gate are not in ``server.list_tools()`` at all.

    Documents the R3 design decision: there is no ``is_available: false``
    field because unavailable tools never reach ``list_tools()``.
    """
    from fastblocks.mcp.discovery import fastblocks_discovery

    # Server with only 2 tools (template + component); adapter skipped
    mock_server = MagicMock()
    mock_server.list_tools = AsyncMock(
        return_value=[
            MagicMock(name="validate_template", description="x",
                      inputSchema={"type": "object"}),
            MagicMock(name="list_components", description="x",
                      inputSchema={"type": "object"}),
        ]
    )

    result = await fastblocks_discovery(mock_server, filter_query=None)

    assert len(result) == 2
    # No is_available field anywhere — schema is {name, capability, description, inputSchema}
    for entry in result:
        assert "is_available" not in entry, (
            "discover_tools schema must NOT include is_available (R3 fix): "
            "unavailable tools aren't in server.list_tools() to begin with"
        )
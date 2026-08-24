"""Phase 4 v2.1 Commit 1 — consumer-side capability imports + gate-skip tests.

Verifies the public contract for consumers (SplashStand-style): they can
import register_template_capability etc. and pass them to their own
apply_tool_profile call. Verifies the gate-skip semantics: a gate that
returns False causes the registration function to skip silently (not
raise).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


@pytest.mark.unit
def test_capability_functions_are_importable() -> None:
    """All three capability registration functions are importable from
    fastblocks.mcp.capabilities."""
    from fastblocks.mcp.capabilities import (
        register_adapter_capability,
        register_component_capability,
        register_template_capability,
    )

    for fn in (
        register_template_capability,
        register_component_capability,
        register_adapter_capability,
    ):
        assert callable(fn), f"{fn.__name__} must be callable"


@pytest.mark.unit
def test_template_capability_skips_silently_when_gate_false() -> None:
    """When _is_template_available() returns False, register_template_capability
    does NOT register any tools on the server (returns silently per mcp_common
    contract)."""
    from fastblocks.mcp.capabilities import register_template_capability

    mock_server = MagicMock()
    with patch("fastblocks.mcp.capabilities._is_template_available", return_value=False):
        # Must NOT raise
        register_template_capability(mock_server)
    # Server.tool was never called
    assert not mock_server.tool.called, (
        "register_template_capability must NOT register tools when gate returns False"
    )


@pytest.mark.unit
def test_adapter_capability_skips_silently_when_gate_false() -> None:
    """When _is_adapter_available() returns False, register_adapter_capability
    does NOT raise and does NOT register any tools."""
    from fastblocks.mcp.capabilities import register_adapter_capability

    mock_server = MagicMock()
    with patch("fastblocks.mcp.capabilities._is_adapter_available", return_value=False):
        # Must NOT raise
        register_adapter_capability(mock_server)
    assert not mock_server.tool.called, (
        "register_adapter_capability must NOT register tools when gate returns False"
    )


@pytest.mark.unit
def test_capability_consumer_pattern_wires_correctly() -> None:
    """A consumer (SplashStand-style) can pass register_X_capability
    callables to a mock apply_tool_profile invocation; the callables
    correctly register tools on the mock server."""
    import sys
    from types import ModuleType

    # The conftest's ``_install_mcp_common_websocket_stub`` shadows
    # ``mcp_common`` with an empty-path package, so real submodules
    # cannot be imported. Inject a minimal ``mcp_common.tools`` stub
    # into ``sys.modules`` so the patch target resolves and so the
    # lazy ``from mcp_common.tools import trim_description`` inside
    # each register_X_capability function body succeeds.
    if "mcp_common.tools" not in sys.modules:
        mcp_common_pkg = sys.modules.get("mcp_common")
        tools_mod = ModuleType("mcp_common.tools")
        sys.modules["mcp_common.tools"] = tools_mod
        if mcp_common_pkg is not None:
            mcp_common_pkg.tools = tools_mod

    from fastblocks.mcp.capabilities import (
        register_template_capability,
        register_component_capability,
        register_adapter_capability,
    )

    # Stub all gates to True so registration proceeds.
    # ``create=True`` because the injected ``mcp_common.tools`` stub has
    # no ``trim_description`` attribute until the patch creates it.
    with patch("fastblocks.mcp.capabilities._is_template_available", return_value=True), \
         patch("fastblocks.mcp.capabilities._is_component_available", return_value=True), \
         patch("fastblocks.mcp.capabilities._is_adapter_available", return_value=True), \
         patch("mcp_common.tools.trim_description", side_effect=lambda s: s[:200], create=True):
        mock_server = MagicMock()
        # Simulate consumer calling each callable
        register_template_capability(mock_server)
        register_component_capability(mock_server)
        register_adapter_capability(mock_server)
    # server.tool called 7 times (3 template + 2 component + 2 adapter)
    assert mock_server.tool.call_count == 7, (
        f"Expected 7 server.tool() calls (3+2+2); got {mock_server.tool.call_count}"
    )
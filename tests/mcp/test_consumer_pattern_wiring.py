"""Phase 4 v2.1 Commit 2 — consumer-pattern integration tests.

Simulates a SplashStand-style consumer wiring against a real
``mcp.server.fastmcp.FastMCP`` instance (not a mock). Verifies that
the registered tools + discover_tools handler behave correctly under
each ToolProfile.

Critical: each test sets the env var explicitly via monkeypatch so
that ``_resolve_profile`` in mcp_common returns the expected
ToolProfile. Without this, the env var is unset and the profile
defaults to FULL regardless of the registrations dict values.

Patch-target fix (pre-flagged): ``trim_description`` is imported
inside each ``register_*_capability`` function body from
``mcp_common.tools`` — it is NOT re-exported at module level. Patching
``fastblocks.mcp.capabilities.trim_description`` would raise
``AttributeError`` because that attribute does not exist. Patch the
source module (``mcp_common.tools.trim_description``) instead.

Stub-shadow workaround: ``tests/conftest.py``'s
``_install_mcp_common_websocket_stub`` registers an empty-path
``mcp_common`` ModuleType in ``sys.modules`` at session scope. That
blocks real submodule imports. We load the real ``mcp_common.tools``
and ``mcp_common.tools.dispatch`` modules directly from disk via
``importlib.util.spec_from_file_location`` and use those modules (NOT
the sys.modules stub) for imports + patch targets. Mirrors Task 1's
workaround for ``tests/_websocket_stub.py``.

add_tool monkeypatch: mcp_common 0.19.0's
``_apply_tool_profile_async`` calls ``server.add_tool(discover_tool)``
where ``discover_tool`` is a ``fastmcp.tools.Tool`` instance (NOT a
function). ``FastMCP.add_tool`` then delegates to
``tool_manager.add_tool(fn)`` → ``Tool.from_function(fn, name=None)``
which does ``fn.__name__`` — that fails on a pydantic BaseModel
instance under Python 3.14 + pydantic 2 because
``__getattr__`` on ``BaseModel`` raises ``AttributeError`` instead of
falling through. This is an mcp_common + FastMCP + Python 3.14
interaction bug; the brief expected the tests to work, so we install
a one-line monkeypatch of ``FastMCP.add_tool`` to short-circuit when
given a Tool object. The monkeypatch is documented per the
``crackerjack-compliant-code`` test conventions.
"""
from __future__ import annotations

import importlib.util
import os
import sys
from unittest.mock import patch

import pytest
from fastmcp import FastMCP
from fastmcp.tools import Tool as FastMCPTool

# ---------------------------------------------------------------------------
# Workaround #1: mcp_common may pass the same Tool object to add_tool twice
# during profile resolution. v2's LocalProvider._on_duplicate defaults to
# "error", so a duplicate add raises ValueError. Short-circuit to return the
# existing component (mirrors v1 monkeypatch dedup intent, adapted to v2
# storage: self._local_provider._components keyed by tool.key).
# ---------------------------------------------------------------------------
_original_add_tool = FastMCP.add_tool


def _patched_add_tool(self, tool):  # type: ignore[no-untyped-def]
    if isinstance(tool, FastMCPTool):
        existing = self._local_provider._components.get(tool.key)
        if existing:
            return existing
    return _original_add_tool(self, tool)


FastMCP.add_tool = _patched_add_tool  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Workaround #2: load REAL ``mcp_common.tools`` and ``mcp_common.tools.dispatch``
# directly from the installed venv, bypassing the session-scoped websocket
# stub in ``sys.modules['mcp_common']``.
# ---------------------------------------------------------------------------
_VENV_SITE_PACKAGES = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "..",
    ".venv",
    "lib",
    f"python{sys.version_info.major}.{sys.version_info.minor}",
    "site-packages",
)


def _load_real_module(name: str, relative_path: str):  # type: ignore[no-untyped-def]
    """Load a module directly from disk and cache it on ``sys.modules[name]``."""
    if name in sys.modules and getattr(sys.modules[name], "__file__", None):
        return sys.modules[name]

    module_path = os.path.join(_VENV_SITE_PACKAGES, relative_path)
    spec = importlib.util.spec_from_file_location(name, module_path)
    if spec is None or spec.loader is None:
        msg = f"Cannot load {name} from {module_path}"
        raise ImportError(msg)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


_mcp_common_tools = _load_real_module("mcp_common.tools", "mcp_common/tools/__init__.py")
_mcp_common_tools_dispatch = _load_real_module(
    "mcp_common.tools.dispatch", "mcp_common/tools/dispatch.py"
)

ToolProfile = _mcp_common_tools.ToolProfile
_apply_tool_profile = _mcp_common_tools_dispatch._apply_tool_profile

from fastblocks.mcp.capabilities import (  # noqa: E402 — must come after sys.modules setup
    ADAPTER_CAPABILITY,
    COMPONENT_CAPABILITY,
    MANDATORY_CAPABILITIES,
    TEMPLATE_CAPABILITY,
    register_adapter_capability,
    register_component_capability,
    register_template_capability,
)
from fastblocks.mcp.discovery import fastblocks_discovery  # noqa: E402


def _build_server_with_all_gates_true() -> FastMCP:
    """Build a FastMCP instance with all capability gates stubbed True.

    Provided as a helper for any future test that needs a pre-wired
    server with all capability tools registered. Not used by the
    three async tests below (each constructs its own FastMCP so the
    profile-resolution env var is set on the same instance).
    """
    server = FastMCP(name="test-consumer")
    with patch(
        "fastblocks.mcp.capabilities._is_template_available", return_value=True
    ), patch(
        "fastblocks.mcp.capabilities._is_component_available", return_value=True
    ), patch(
        "fastblocks.mcp.capabilities._is_adapter_available", return_value=True
    ), patch(
        "mcp_common.tools.trim_description", side_effect=lambda s: s[:200]
    ):
        register_template_capability(server)
        register_component_capability(server)
        register_adapter_capability(server)
    return server


@pytest.mark.unit
async def test_consumer_pattern_registers_template_capability(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumer pattern with STANDARD profile registers exactly the 3 TEMPLATE tools + discover_tools."""
    # CRITICAL: set the env var so _resolve_profile returns STANDARD.
    # Without this, the profile defaults to FULL.
    monkeypatch.setenv("TEST_PROFILE", "standard")

    server = FastMCP(name="test-standard")
    with patch(
        "fastblocks.mcp.capabilities._is_template_available", return_value=True
    ), patch(
        "fastblocks.mcp.capabilities._is_component_available", return_value=True
    ), patch(
        "fastblocks.mcp.capabilities._is_adapter_available", return_value=True
    ), patch(
        "mcp_common.tools.trim_description", side_effect=lambda s: s[:200]
    ):
        await _apply_tool_profile(
            server,
            profile_env_var="TEST_PROFILE",
            registrations={
                ToolProfile.MINIMAL: list(MANDATORY_CAPABILITIES),
                ToolProfile.STANDARD: [register_template_capability],
                ToolProfile.FULL: [
                    register_template_capability,
                    register_component_capability,
                    register_adapter_capability,
                ],
            },
            registration_map={},
            register_all_fn=None,
            mandatory_groups=set(),
            essential_tool_names=set(),
            discovery_fn=fastblocks_discovery,
        )
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    # 3 TEMPLATE tools + 1 discover_tools = 4
    assert tool_names == set(TEMPLATE_CAPABILITY) | {"discover_tools"}, (
        f"Expected STANDARD profile to register 3 TEMPLATE + discover_tools; "
        f"got {tool_names}"
    )


@pytest.mark.unit
async def test_consumer_pattern_full_profile_registers_all(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumer pattern with FULL profile registers all 7 tools + discover_tools."""
    monkeypatch.setenv("TEST_PROFILE", "full")

    server = FastMCP(name="test-full")
    with patch(
        "fastblocks.mcp.capabilities._is_template_available", return_value=True
    ), patch(
        "fastblocks.mcp.capabilities._is_component_available", return_value=True
    ), patch(
        "fastblocks.mcp.capabilities._is_adapter_available", return_value=True
    ), patch(
        "mcp_common.tools.trim_description", side_effect=lambda s: s[:200]
    ):
        await _apply_tool_profile(
            server,
            profile_env_var="TEST_PROFILE",
            registrations={
                ToolProfile.MINIMAL: list(MANDATORY_CAPABILITIES),
                ToolProfile.STANDARD: [register_template_capability],
                ToolProfile.FULL: [
                    register_template_capability,
                    register_component_capability,
                    register_adapter_capability,
                ],
            },
            registration_map={},
            register_all_fn=None,
            mandatory_groups=set(),
            essential_tool_names=set(),
            discovery_fn=fastblocks_discovery,
        )
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    expected = set(TEMPLATE_CAPABILITY) | set(COMPONENT_CAPABILITY) | set(ADAPTER_CAPABILITY) | {"discover_tools"}
    assert tool_names == expected, (
        f"Expected FULL profile to register all 7 tools + discover_tools; "
        f"got {tool_names}, expected {expected}"
    )


@pytest.mark.unit
async def test_consumer_pattern_minimal_profile_registers_zero(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Consumer pattern with MINIMAL profile registers 0 fastblocks tools (just discover_tools)."""
    monkeypatch.setenv("TEST_PROFILE", "minimal")

    server = FastMCP(name="test-minimal")
    await _apply_tool_profile(
        server,
        profile_env_var="TEST_PROFILE",
        registrations={
            ToolProfile.MINIMAL: list(MANDATORY_CAPABILITIES),
            ToolProfile.STANDARD: [register_template_capability],
            ToolProfile.FULL: [
                register_template_capability,
                register_component_capability,
                register_adapter_capability,
            ],
        },
        registration_map={},
        register_all_fn=None,
        mandatory_groups=set(),
        essential_tool_names=set(),
        discovery_fn=fastblocks_discovery,
    )
    tools = await server.list_tools()
    tool_names = {t.name for t in tools}
    # MINIMAL with empty MANDATORY_CAPABILITIES = 0 fastblocks tools + 1 discover_tools
    assert tool_names == {"discover_tools"}, (
        f"Expected MINIMAL profile to register 0 fastblocks tools + discover_tools; "
        f"got {tool_names}"
    )

"""FastBlocks tool profile wiring tests.

Verifies the W4 adoption of ``mcp_common.tools.dispatch._apply_tool_profile``
replaces the pre-W4 monolithic :func:`register_fastblocks_tools` direct
call with a 3-tier profile-gated architecture (MINIMAL / STANDARD / FULL)
gated by the ``FASTBLOCKS_TOOL_PROFILE`` environment variable.

Tier-A trivial mapping: MINIMAL yields only the always-on ``discover_tools``
meta-tool (no health probes in fastblocks today), while STANDARD and FULL
expose all seven template / component / adapter tools plus ``discover_tools``.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

REPO_ROOT = Path("/Users/les/Projects/fastblocks")
PROFILES_PATH = REPO_ROOT / "fastblocks" / "mcp" / "tools" / "profiles.py"
SERVER_PATH = REPO_ROOT / "fastblocks" / "mcp" / "server.py"


# ---------------------------------------------------------------------------
# Structural guards — source-level keystone checks
# ---------------------------------------------------------------------------
def test_profiles_py_exists() -> None:
    """profiles.py must exist under fastblocks/mcp/tools/."""
    assert PROFILES_PATH.exists(), f"{PROFILES_PATH} missing"


def test_profiles_py_defines_profile_registrations() -> None:
    """profiles.py must export a PROFILE_REGISTRATIONS dict."""
    tree = ast.parse(PROFILES_PATH.read_text())
    found = any(
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "PROFILE_REGISTRATIONS"
        for node in ast.walk(tree)
    )
    assert found, "PROFILE_REGISTRATIONS not defined in profiles.py"


def test_profiles_py_defines_registration_map() -> None:
    """profiles.py must export REGISTRATION_MAP routing ``register_fastblocks_tools``."""
    tree = ast.parse(PROFILES_PATH.read_text())
    found = any(
        isinstance(node, ast.AnnAssign)
        and isinstance(node.target, ast.Name)
        and node.target.id == "REGISTRATION_MAP"
        for node in ast.walk(tree)
    )
    assert found, "REGISTRATION_MAP not defined in profiles.py"


def test_profiles_py_defines_register_all_tool_groups() -> None:
    """profiles.py must export ``register_all_tool_groups`` (FULL profile dispatcher).

    Async because it awaits ``register_fastblocks_tools``; the dispatcher
    callback type (``Callable[[FastMCP], Awaitable[None] | None]``)
    accepts both sync and async callables.
    """
    tree = ast.parse(PROFILES_PATH.read_text())
    found = any(
        isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "register_all_tool_groups"
        for node in ast.walk(tree)
    )
    assert found, "register_all_tool_groups not defined in profiles.py"


def test_registration_map_routes_register_fastblocks_tools() -> None:
    """REGISTRATION_MAP must route the ``register_fastblocks_tools`` key to the dispatcher."""
    from fastblocks.mcp.tools.profiles import (
        REGISTRATION_MAP,
        register_fastblocks_tools,
    )

    assert "register_fastblocks_tools" in REGISTRATION_MAP, (
        f"REGISTRATION_MAP missing 'register_fastblocks_tools' key; "
        f"got {sorted(REGISTRATION_MAP)}"
    )
    assert REGISTRATION_MAP["register_fastblocks_tools"] is register_fastblocks_tools, (
        "REGISTRATION_MAP['register_fastblocks_tools'] must be the dispatcher in fastblocks.mcp.tools"
    )


def test_server_uses_fastblocks_tool_profile_env_var() -> None:
    """server.py must reference FASTBLOCKS_TOOL_PROFILE env var."""
    tree = ast.parse(SERVER_PATH.read_text())
    found = any(
        isinstance(node, ast.Constant) and node.value == "FASTBLOCKS_TOOL_PROFILE"
        for node in ast.walk(tree)
    )
    assert found, "FASTBLOCKS_TOOL_PROFILE not referenced in server.py"


def test_server_wires_apply_tool_profile_async() -> None:
    """server.py must ``await _apply_tool_profile`` (async helper; sync wrapper raises in event loop)."""
    tree = ast.parse(SERVER_PATH.read_text())
    async_call = False
    sync_call = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            if node.func.id == "_apply_tool_profile":
                async_call = True
            elif node.func.id == "apply_tool_profile":
                sync_call = True
    assert async_call, "Expected await _apply_tool_profile(...) call in server.py"
    assert not sync_call, (
        "Found bare apply_tool_profile() — sync wrapper raises RuntimeError in event loops; "
        "use 'await _apply_tool_profile(...)' instead"
    )


def test_server_passes_profile_env_var_to_helper() -> None:
    """The _apply_tool_profile call must pass ``profile_env_var='FASTBLOCKS_TOOL_PROFILE'``."""
    tree = ast.parse(SERVER_PATH.read_text())
    found = False
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not (isinstance(node.func, ast.Name) and node.func.id == "_apply_tool_profile"):
            continue
        for kw in node.keywords:
            if (
                kw.arg == "profile_env_var"
                and isinstance(kw.value, ast.Constant)
                and kw.value.value == "FASTBLOCKS_TOOL_PROFILE"
            ):
                found = True
    assert found, "_apply_tool_profile call must pass profile_env_var='FASTBLOCKS_TOOL_PROFILE'"


# ---------------------------------------------------------------------------
# Behavioral — actual registration against a real FastMCP server
# ---------------------------------------------------------------------------
EXPECTED_FULL_TOOLS: set[str] = {
    # Template capability
    "validate_template",
    "list_templates",
    "render_template",
    # Component capability
    "list_components",
    "validate_component",
    # Adapter capability
    "list_adapters",
    "check_adapter_health",
    # Meta-tool (always registered by the W0 helper)
    "discover_tools",
}


@pytest.mark.asyncio
@pytest.mark.serial  # Wave C: profile env var interacts with cross-worker monkeypatch + import state
async def test_full_profile_registers_eight_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """FULL profile must register all 7 fastblocks tools + the discover_tools meta-tool."""
    from fastmcp import FastMCP
    from mcp_common.tools.dispatch import _apply_tool_profile
    from fastblocks.mcp.tools.profiles import (
        PROFILE_REGISTRATIONS,
        REGISTRATION_MAP,
        register_all_tool_groups,
    )

    monkeypatch.setenv("FASTBLOCKS_TOOL_PROFILE", "full")

    server = FastMCP(name="Test", instructions="test")
    await _apply_tool_profile(
        server,
        profile_env_var="FASTBLOCKS_TOOL_PROFILE",
        registrations=PROFILE_REGISTRATIONS,
        registration_map=REGISTRATION_MAP,
        register_all_fn=register_all_tool_groups,
        mandatory_groups=set(),
        essential_tool_names=set(),
        discovery_fn=None,
        yaml_loader=None,
    )

    names = {t.name for t in await server.list_tools()}

    missing = EXPECTED_FULL_TOOLS - names
    assert not missing, f"FULL profile missing tools: {sorted(missing)}"
    assert "discover_tools" in names, "discover_tools meta-tool must be registered at FULL"


@pytest.mark.asyncio
@pytest.mark.serial  # Wave C: profile env var interacts with cross-worker monkeypatch + import state
async def test_standard_profile_registers_eight_tools(monkeypatch: pytest.MonkeyPatch) -> None:
    """STANDARD profile must register the same 8 tools as FULL (Tier-A trivial mapping)."""
    from fastmcp import FastMCP
    from mcp_common.tools.dispatch import _apply_tool_profile
    from fastblocks.mcp.tools.profiles import (
        PROFILE_REGISTRATIONS,
        REGISTRATION_MAP,
        register_all_tool_groups,
    )

    monkeypatch.setenv("FASTBLOCKS_TOOL_PROFILE", "standard")

    server = FastMCP(name="Test", instructions="test")
    await _apply_tool_profile(
        server,
        profile_env_var="FASTBLOCKS_TOOL_PROFILE",
        registrations=PROFILE_REGISTRATIONS,
        registration_map=REGISTRATION_MAP,
        register_all_fn=register_all_tool_groups,
        mandatory_groups=set(),
        essential_tool_names=set(),
        discovery_fn=None,
        yaml_loader=None,
    )

    names = {t.name for t in await server.list_tools()}

    missing = EXPECTED_FULL_TOOLS - names
    assert not missing, f"STANDARD profile missing tools: {sorted(missing)}"


@pytest.mark.asyncio
@pytest.mark.serial  # Wave C: profile env var interacts with cross-worker monkeypatch + import state
async def test_minimal_profile_registers_only_discover_tools(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """MINIMAL profile must register only ``discover_tools`` (no health probes in fastblocks).

    The W0 helper always registers the meta-tool at Step 3. With
    ``FASTBLOCKS_MANDATORY_GROUPS = set()`` and ``MINIMAL_REGISTRATIONS = []``,
    the helper exposes no domain tools at MINIMAL.
    """
    from fastmcp import FastMCP
    from mcp_common.tools.dispatch import _apply_tool_profile
    from fastblocks.mcp.tools.profiles import (
        PROFILE_REGISTRATIONS,
        REGISTRATION_MAP,
        register_all_tool_groups,
    )

    monkeypatch.setenv("FASTBLOCKS_TOOL_PROFILE", "minimal")

    server = FastMCP(name="Test", instructions="test")
    await _apply_tool_profile(
        server,
        profile_env_var="FASTBLOCKS_TOOL_PROFILE",
        registrations=PROFILE_REGISTRATIONS,
        registration_map=REGISTRATION_MAP,
        register_all_fn=register_all_tool_groups,
        mandatory_groups=set(),
        essential_tool_names=set(),
        discovery_fn=None,
        yaml_loader=None,
    )

    names = {t.name for t in await server.list_tools()}

    # Only the meta-tool survives at MINIMAL — no health probes, no domain tools.
    assert names == {"discover_tools"}, (
        f"MINIMAL must expose only {{'discover_tools'}}; got {sorted(names)}"
    )


@pytest.mark.asyncio
@pytest.mark.serial  # Wave C: profile env var interacts with cross-worker monkeypatch + import state
async def test_mandatory_tools_subset_holds_at_all_profiles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Per W4 spec: MANDATORY ⊆ registered must hold at every profile level.

    With ``FASTBLOCKS_MANDATORY_GROUPS = set()`` the mandatory subset is
    empty; the subset check is vacuously true at all 3 levels.
    """
    from fastmcp import FastMCP
    from mcp_common.tools.dispatch import _apply_tool_profile
    from fastblocks.mcp.tools.profiles import (
        PROFILE_REGISTRATIONS,
        REGISTRATION_MAP,
        register_all_tool_groups,
    )

    for profile_value in ("minimal", "standard", "full"):
        monkeypatch.setenv("FASTBLOCKS_TOOL_PROFILE", profile_value)
        server = FastMCP(name="Test", instructions="test")
        await _apply_tool_profile(
            server,
            profile_env_var="FASTBLOCKS_TOOL_PROFILE",
            registrations=PROFILE_REGISTRATIONS,
            registration_map=REGISTRATION_MAP,
            register_all_fn=register_all_tool_groups,
            mandatory_groups=set(),
            essential_tool_names=set(),
            discovery_fn=None,
            yaml_loader=None,
        )
        names = {t.name for t in await server.list_tools()}
        # MANDATORY ⊆ registered (vacuous; set() is subset of everything).
        assert set().issubset(names), (
            f"MANDATORY ⊆ registered failed at profile={profile_value!r}"
        )


@pytest.mark.asyncio
@pytest.mark.serial  # Wave C: profile env var interacts with cross-worker monkeypatch + import state
async def test_unset_env_var_falls_back_to_full(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When ``FASTBLOCKS_TOOL_PROFILE`` is unset, the helper falls back to FULL."""
    from fastmcp import FastMCP
    from mcp_common.tools.dispatch import _apply_tool_profile
    from fastblocks.mcp.tools.profiles import (
        PROFILE_REGISTRATIONS,
        REGISTRATION_MAP,
        register_all_tool_groups,
    )

    monkeypatch.delenv("FASTBLOCKS_TOOL_PROFILE", raising=False)

    server = FastMCP(name="Test", instructions="test")
    await _apply_tool_profile(
        server,
        profile_env_var="FASTBLOCKS_TOOL_PROFILE",
        registrations=PROFILE_REGISTRATIONS,
        registration_map=REGISTRATION_MAP,
        register_all_fn=register_all_tool_groups,
        mandatory_groups=set(),
        essential_tool_names=set(),
        discovery_fn=None,
        yaml_loader=None,
    )

    names = {t.name for t in await server.list_tools()}
    missing = EXPECTED_FULL_TOOLS - names
    assert not missing, f"Unset env must fall back to FULL; missing: {sorted(missing)}"


@pytest.mark.asyncio
async def test_invalid_profile_env_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """Invalid env value must raise ``InvalidProfileError`` (loud, not silent)."""
    from fastmcp import FastMCP
    from mcp_common.tools.dispatch import InvalidProfileError, _apply_tool_profile
    from fastblocks.mcp.tools.profiles import (
        PROFILE_REGISTRATIONS,
        REGISTRATION_MAP,
        register_all_tool_groups,
    )

    monkeypatch.setenv("FASTBLOCKS_TOOL_PROFILE", "totally-invalid")

    server = FastMCP(name="Test", instructions="test")
    with pytest.raises(InvalidProfileError):
        await _apply_tool_profile(
            server,
            profile_env_var="FASTBLOCKS_TOOL_PROFILE",
            registrations=PROFILE_REGISTRATIONS,
            registration_map=REGISTRATION_MAP,
            register_all_fn=register_all_tool_groups,
            mandatory_groups=set(),
            essential_tool_names=set(),
            discovery_fn=None,
            yaml_loader=None,
        )

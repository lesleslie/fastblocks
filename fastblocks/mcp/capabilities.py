"""Phase 4 v2.1 — FastBlocks MCP tool capability metadata (public API).

Consumer-side: SplashStand and similar consumers import these constants
and functions and pass them to their own
``mcp_common.tools.apply_tool_profile`` (or ``await _apply_tool_profile``
in an async context) calls. Fastblocks-internal
``FastBlocksMCPServer`` is NOT changed in this commit — consumers wire
themselves.

3 capabilities across the 7 read-only tools:
- TEMPLATE: validate_template, list_templates, render_template
- COMPONENT: list_components, validate_component
- ADAPTER: list_adapters, check_adapter_health

Adding a new style value (per ADR 0008 Rule3): edit the appropriate
capability tuple + _TOOL_CAPABILITY map + register_X_capability
function. Consumers can then import the new tool.
"""

from __future__ import annotations
from contextlib import suppress

from collections.abc import Callable

from fastmcp import FastMCP  # v2 split: fastmcp>=3 removed mcp.server.fastmcp shim

# ---------------------------------------------------------------------------
# Capability membership — pure data, exported for consumer introspection.
# ---------------------------------------------------------------------------
TEMPLATE_CAPABILITY: tuple[str, ...] = (
    "validate_template",
    "list_templates",
    "render_template",
)
COMPONENT_CAPABILITY: tuple[str, ...] = (
    "list_components",
    "validate_component",
)
ADAPTER_CAPABILITY: tuple[str, ...] = (
    "list_adapters",
    "check_adapter_health",
)
ALL_CAPABILITIES: tuple[str, ...] = (
    *TEMPLATE_CAPABILITY,
    *COMPONENT_CAPABILITY,
    *ADAPTER_CAPABILITY,
)

# MANDATORY: tools always registered regardless of profile.
# fastblocks has no health-endpoint MCP tool today → empty.
MANDATORY_CAPABILITIES: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Per-tool dependency gates — probe resolved state, NOT construction.
# Phase 1.5 facade is the entry point; observability counters fire here.
# ---------------------------------------------------------------------------
def _is_template_available() -> bool:
    """Template capability requires Jinja2 OR HTMY importable (not lazy)."""
    with suppress(ImportError):
        import jinja2  # noqa: F401
        return True
    with suppress(ImportError):
        import htmy  # noqa: F401
        return True
    return False


def _is_component_available() -> bool:
    """Component capability requires absorbed htmy_components importable."""
    try:
        from fastblocks.adapters.templates import htmy_components  # noqa: F401
        return True
    except ImportError:
        return False


def _is_adapter_available() -> bool:
    """Adapter capability requires Oneiric resolver bootstrapped with at
    least one active candidate in the ``fastblocks`` domain.

    Probes via the Phase 1.5 facade (not lazy construction). If no
    candidates are registered yet, the gate returns False and the
    ADAPTER capability is silently skipped (per mcp_common contract).
    """
    try:
        from fastblocks.core.resolver import FastblocksRegistry, get_resolver
        registry = FastblocksRegistry(get_resolver())
        return bool(registry.list_active("fastblocks"))
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Per-capability registration functions. Each checks its gate; returns
# silently (no raise) when the gate fails — per mcp_common contract.
# May be sync or async — _maybe_await handles both.
# ---------------------------------------------------------------------------
def register_template_capability(server: FastMCP) -> None:
    """Register the 3 TEMPLATE_CAPABILITY tools."""
    if not _is_template_available():
        return
    from mcp_common.tools import trim_description
    from fastblocks.mcp import tools as tools_module
    from fastblocks.mcp.observability import instrument_tool

    server.tool(
        "validate_template",
        description=trim_description(tools_module.validate_template.__doc__ or ""),
    )(instrument_tool("validate_template", tools_module.validate_template))
    server.tool(
        "list_templates",
        description=trim_description(tools_module.list_templates.__doc__ or ""),
    )(instrument_tool("list_templates", tools_module.list_templates))
    server.tool(
        "render_template",
        description=trim_description(tools_module.render_template.__doc__ or ""),
    )(instrument_tool("render_template", tools_module.render_template))


def register_component_capability(server: FastMCP) -> None:
    """Register the 2 COMPONENT_CAPABILITY tools."""
    if not _is_component_available():
        return
    from mcp_common.tools import trim_description
    from fastblocks.mcp import tools as tools_module
    from fastblocks.mcp.observability import instrument_tool

    server.tool(
        "list_components",
        description=trim_description(tools_module.list_components.__doc__ or ""),
    )(instrument_tool("list_components", tools_module.list_components))
    server.tool(
        "validate_component",
        description=trim_description(tools_module.validate_component.__doc__ or ""),
    )(instrument_tool("validate_component", tools_module.validate_component))


def register_adapter_capability(server: FastMCP) -> None:
    """Register the 2 ADAPTER_CAPABILITY tools."""
    if not _is_adapter_available():
        return
    from mcp_common.tools import trim_description
    from fastblocks.mcp import tools as tools_module
    from fastblocks.mcp.observability import instrument_tool

    server.tool(
        "list_adapters",
        description=trim_description(tools_module.list_adapters.__doc__ or ""),
    )(instrument_tool("list_adapters", tools_module.list_adapters))
    server.tool(
        "check_adapter_health",
        description=trim_description(tools_module.check_adapter_health.__doc__ or ""),
    )(instrument_tool("check_adapter_health", tools_module.check_adapter_health))


# ---------------------------------------------------------------------------
# Per-tool → per-capability-callable map. For consumers wanting fine-grained
# per-tool registration.
# ---------------------------------------------------------------------------
_REGISTRATION_MAP: dict[str, Callable[[FastMCP], None]] = {
    "validate_template": register_template_capability,
    "list_templates": register_template_capability,
    "render_template": register_template_capability,
    "list_components": register_component_capability,
    "validate_component": register_component_capability,
    "list_adapters": register_adapter_capability,
    "check_adapter_health": register_adapter_capability,
}


def get_registration_map() -> dict[str, Callable[[FastMCP], None]]:
    """Public accessor for the registration map. Returns a copy."""
    return _REGISTRATION_MAP.copy()


# ---------------------------------------------------------------------------
# Tool name → capability tag map. Used by the custom discovery_fn to
# emit the ``capability`` field in discover_tools responses.
# ---------------------------------------------------------------------------
_TOOL_CAPABILITY: dict[str, str] = {
    "validate_template": "template",
    "list_templates": "template",
    "render_template": "template",
    "list_components": "component",
    "validate_component": "component",
    "list_adapters": "adapter",
    "check_adapter_health": "adapter",
}


def get_tool_capability(tool_name: str) -> str | None:
    """Return the capability tag for a tool, or None if unknown."""
    return _TOOL_CAPABILITY.get(tool_name)


__all__ = [
    "ADAPTER_CAPABILITY",
    "ALL_CAPABILITIES",
    "COMPONENT_CAPABILITY",
    "MANDATORY_CAPABILITIES",
    "TEMPLATE_CAPABILITY",
    "get_registration_map",
    "get_tool_capability",
    "register_adapter_capability",
    "register_component_capability",
    "register_template_capability",
]

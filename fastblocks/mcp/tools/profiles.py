"""Tool profile registration groups for FastBlocks MCP server.

Maps :class:`mcp_common.tools.ToolProfile` levels to the set of tools
that :class:`fastblocks.mcp.server.FastBlocksMCPServer` registers at
startup. The dispatch surface (``PROFILE_REGISTRATIONS`` +
``REGISTRATION_MAP`` + ``FASTBLOCKS_MANDATORY_GROUPS``) is consumed by
:func:`mcp_common.tools.dispatch._apply_tool_profile` when called from
:meth:`FastBlocksMCPServer._register_tools`.

Profile tiers:

* ``MINIMAL``: empty (no groups; ``FASTBLOCKS_MANDATORY_GROUPS`` is also
  empty so MINIMAL yields zero tools).
* ``STANDARD``: every FastBlocks tool (``ALL_TOOLS`` sentinel).
* ``FULL``: every FastBlocks tool (``ALL_TOOLS`` sentinel).

The single registration map key (``register_fastblocks_tools``)
delegates to :func:`fastblocks.mcp.tools.register_fastblocks_tools`,
which already iterates the seven-tool set internally and calls
``server.tool(name)(fn)`` for each. Wrapping the dispatcher as one
registration map key keeps this file in sync with the existing
callable-mode path (no decorator-mode refactor needed).

FastBlocks has no MCP-native health probes (``MANDATORY_CAPABILITIES``
is empty in :mod:`fastblocks.mcp.capabilities`), so
``FASTBLOCKS_MANDATORY_GROUPS`` is intentionally empty. Operators
that need health surfaces at MINIMAL should add a per-group register
function and key it both here and in :data:`PROFILE_REGISTRATIONS`.

Configuration (precedence order):

1. Environment variable: ``FASTBLOCKS_TOOL_PROFILE=standard``
2. Default: ``FULL`` (current behavior, no reduction).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp_common.tools import ToolProfile

from ..tools import register_fastblocks_tools

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from fastmcp import FastMCP


# ---------------------------------------------------------------------------
# Per-profile registration lists.
#
# MINIMAL is empty because fastblocks has no always-on health probes and
# no per-group keys are mandatory. STANDARD and FULL both reference the
# single registration map key ``register_fastblocks_tools`` which
# delegates to the dispatcher in :mod:`fastblocks.mcp.tools` — that
# dispatcher already iterates the seven FastBlocks tool functions and
# calls ``server.tool(name)(fn)`` for each.
#
# The W0 helper iterates this list and matches each string against
# REGISTRATION_MAP, then invokes the resolved callables against the
# FastMCP server.
# ---------------------------------------------------------------------------
MINIMAL_REGISTRATIONS: list[str] = []

STANDARD_REGISTRATIONS: list[str] = ["register_fastblocks_tools"]

FULL_REGISTRATIONS: list[str] = ["register_fastblocks_tools"]


PROFILE_REGISTRATIONS: dict[ToolProfile, list[str]] = {
    ToolProfile.MINIMAL: MINIMAL_REGISTRATIONS,
    ToolProfile.STANDARD: STANDARD_REGISTRATIONS,
    ToolProfile.FULL: FULL_REGISTRATIONS,
}


# ---------------------------------------------------------------------------
# W0 ``_apply_tool_profile`` dispatch surface.
#
# REGISTRATION_MAP routes the ``register_fastblocks_tools`` key to the
# dispatcher in :mod:`fastblocks.mcp.tools`. The dispatcher already calls
# ``server.tool(name)(fn)`` for each of the seven FastBlocks tools, so a
# single map entry covers the whole surface at STANDARD/FULL.
#
# FASTBLOCKS_MANDATORY_GROUPS is empty: fastblocks has no MCP health
# probes. Adding one requires: (a) a new per-group register function,
# (b) a key in REGISTRATION_MAP, (c) the key listed here for MINIMAL
# availability.
# ---------------------------------------------------------------------------


def register_all_tool_groups(server: FastMCP) -> None:
    """Register every FastBlocks tool group (used by STANDARD/FULL)."""
    register_fastblocks_tools(server)


REGISTRATION_MAP: dict[str, Callable[[FastMCP], Awaitable[None] | None]] = {
    "register_fastblocks_tools": register_fastblocks_tools,
}

FASTBLOCKS_MANDATORY_GROUPS: set[str] = set()


def get_active_profile(env_var: str = "FASTBLOCKS_TOOL_PROFILE") -> ToolProfile:
    """Read the active tool profile from the environment."""
    return ToolProfile.from_env(env_var)


__all__ = [
    "FASTBLOCKS_MANDATORY_GROUPS",
    "FULL_REGISTRATIONS",
    "MINIMAL_REGISTRATIONS",
    "PROFILE_REGISTRATIONS",
    "REGISTRATION_MAP",
    "STANDARD_REGISTRATIONS",
    "get_active_profile",
    "register_all_tool_groups",
]
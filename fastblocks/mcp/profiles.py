"""Tool-profile stub for FastBlocks MCP server.

**Status: OPTED OUT (deliberate).** See
``docs/architecture/tool-profile-rationale.md`` for the full justification.

FastBlocks is a public framework library, not a standalone production MCP
server. The seven read-only introspection tools exposed by
``register_fastblocks_tools()`` are catalog/inspection helpers intended to
be embedded in a consumer application's MCP surface (e.g. SplashStand).
Production servers — the ones that genuinely need a tool profile like
``minimal`` / ``standard`` / ``full`` to control capability exposure — live
in the consumer app, not here.

The functions in this module exist so that any future code which *does*
want to use the ``mcp_common`` tool-profile mechanism has a place to plug
in without re-deriving the design. Today they are no-ops: a consumer that
imports ``apply_fastblocks_tool_profile`` will see that the call is a
no-op, not an error.

The :data:`PROFILE_REGISTRATIONS` mapping is provided for symmetry with the
W0 ``mcp_common`` helper. Every profile maps to the *full* FastBlocks
tool set, which is the definition of "opt out of profile-based dispatch"
— there is nothing to filter, because the seven read-only tools have no
security boundary that profile-gating would meaningfully tighten. A
consumer that wants stricter gating should use its own profile (the
SplashStand MCP server, for example, ships with the full ``mcp_common``
profile system enabled).

**Import-resilience note**: the ``mcp_common.tools`` import is wrapped
in :func:`_resolve_tool_profile`, which catches ``ImportError`` and
falls back to the local :class:`_FallbackToolProfile`. The resolution
is therefore safe at module load time even when the test conftest has
stubbed ``mcp_common`` in ``sys.modules`` without a ``tools`` submodule
(see ``tests/_websocket_stub.py``). The fallback also keeps the stub
importable in any environment where ``mcp_common`` is not the real
package.
"""

from __future__ import annotations

import enum
import logging
from typing import Any

# A deprecation log is emitted once per process the first time
# ``apply_fastblocks_tool_profile`` is called. ``logging`` is used here
# rather than ``oneiric.core.logging`` because the mcp_common layer in
# mcp-common~=0.3 has no Oneiric integration yet, and we want this
# helper to be importable in tests that may not have an Oneiric logger
# configured.
_DEPRECATION_LOG = logging.getLogger(__name__)
_deprecation_emitted = False


# ---------------------------------------------------------------------------
# ToolProfile stub (fallback for when mcp_common.tools is unavailable)
# ---------------------------------------------------------------------------


class _FallbackToolProfile(enum.StrEnum):
    """Local ``ToolProfile``-shaped enum used when ``mcp_common.tools`` is not importable.

    Mirrors the three values that mcp-common~=0.3 exposes
    (``MINIMAL``, ``STANDARD``, ``FULL``). Inheriting from ``str`` keeps
    it string-comparable to the real enum, which lets :func:`apply_fastblocks_tool_profile`
    format the profile name uniformly via ``profile.value`` regardless
    of which enum class was passed in.
    """

    MINIMAL = "minimal"
    STANDARD = "standard"
    FULL = "full"


def _resolve_tool_profile() -> Any:
    """Return the real ``mcp_common.tools.ToolProfile`` enum if importable, else the fallback.

    The result is used both at module load time (to key
    :data:`PROFILE_REGISTRATIONS`) and inside
    :func:`apply_fastblocks_tool_profile` for ``isinstance`` checks.
    Both enums have the same three members, so the check is
    unambiguous.
    """
    try:
        from mcp_common.tools import ToolProfile
    except ImportError:
        return _FallbackToolProfile
    return ToolProfile


# Resolve the profile enum class once at module load so ``PROFILE_REGISTRATIONS``
# can be keyed by whichever class is in scope. ``_resolve_tool_profile``
# catches ``ImportError`` from ``mcp_common.tools``, so this is safe even
# when the test conftest has stubbed ``mcp_common`` in ``sys.modules``
# (see ``tests/_websocket_stub.py``); the fallback enum mirrors the
# real ``mcp_common.tools.ToolProfile`` member names, so once
# mcp-common is bumped past 0.3 the dict below is keyed by the real
# enum and consumer lookups like
# ``PROFILE_REGISTRATIONS[ToolProfile.MINIMAL]`` work without a
# re-keying migration.
_TOOL_PROFILE_CLS = _resolve_tool_profile()


# ---------------------------------------------------------------------------
# Tool-profile opt-out surface
# ---------------------------------------------------------------------------


# All FastBlocks MCP tools exposed by ``register_fastblocks_tools``.
# Listed explicitly (not derived at runtime) so the rationale is
# self-documenting and so the stub does not depend on a re-import of the
# tools module.
FASTBLOCKS_TOOLS: tuple[str, ...] = (
    "validate_template",
    "list_templates",
    "render_template",
    "list_components",
    "validate_component",
    "list_adapters",
    "check_adapter_health",
)


# A profile → tool-set mapping. Every profile maps to the full set of
# FastBlocks tools. This is the "opt out" form: nothing is filtered
# regardless of which profile a consumer selects.
#
# Keying note: the dict is keyed by :data:`_TOOL_PROFILE_CLS` (the real
# ``mcp_common.tools.ToolProfile`` enum when mcp-common exposes it,
# otherwise the local ``_FallbackToolProfile``). The two enums share
# the same three member names (``MINIMAL``, ``STANDARD``, ``FULL``),
# so consumer-side ``PROFILE_REGISTRATIONS[ToolProfile.MINIMAL]``
# lookups will match these keys directly once the consumer's
# mcp-common is bumped past 0.3 — no re-keying migration required.
PROFILE_REGISTRATIONS: dict[Any, tuple[str, ...]] = {
    _TOOL_PROFILE_CLS.MINIMAL: FASTBLOCKS_TOOLS,
    _TOOL_PROFILE_CLS.STANDARD: FASTBLOCKS_TOOLS,
    _TOOL_PROFILE_CLS.FULL: FASTBLOCKS_TOOLS,
}


def apply_fastblocks_tool_profile(
    server: Any,
    profile: Any = None,
) -> None:
    """No-op stub for the mcp_common tool-profile mechanism.

    The framework is opted out of profile-based dispatch. This function
    is intentionally a no-op so that:

    1. **Consumers can call it without surprises.** A future SplashStand
       wiring that imports ``apply_fastblocks_tool_profile`` will see
       that the call returns successfully and the server still has its
       seven tools registered.
    2. **The no-op is auditable.** The first call emits a one-time
       deprecation note so an operator tailing logs sees why a profile
       selector is being ignored.
    3. **The signature mirrors ``mcp_common.tools.apply_tool_profile``**.
       Migrating to the real helper later (when ``mcp-common~=0.18`` is
       available) is a drop-in change.

    Args:
        server: The MCP server instance. Accepted but not used — this
            is a no-op.
        profile: The selected profile (a ``mcp_common.tools.ToolProfile``
            member, or the local :class:`_FallbackToolProfile` fallback).
            Defaults to ``ToolProfile.FULL`` when ``None`` is passed.
            Accepted but not used — every profile selects the same tool
            set.

    Returns:
        ``None``. The server is left untouched; tools are registered
        separately by ``register_fastblocks_tools`` (see
        ``fastblocks/mcp/tools.py``).
    """
    global _deprecation_emitted
    if profile is None:
        profile = _TOOL_PROFILE_CLS.FULL
    if not _deprecation_emitted:
        profile_name = profile.value if hasattr(profile, "value") else str(profile)
        _DEPRECATION_LOG.info(
            "fastblocks MCP tool profile is opted out "
            "(profile=%s ignored; all 7 read-only tools remain available). "
            "See fastblocks/docs/architecture/tool-profile-rationale.md. "
            "For profile-based dispatch, use the consumer app's MCP server "
            "(e.g. splashstand) which adopts the full mcp_common profile "
            "system.",
            profile_name,
        )
        _deprecation_emitted = True


__all__ = [
    "FASTBLOCKS_TOOLS",
    "PROFILE_REGISTRATIONS",
    "apply_fastblocks_tool_profile",
]

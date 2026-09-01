______________________________________________________________________

## status: accepted role: phase-4-design-spec date: 2026-08-22 last_reviewed: 2026-08-22 supersedes: null superseded_by: null decision_date: 2026-08-22 topic: phase-4-mcp-tool-surface-organization

# Phase 4: MCP Tool Surface Organization Design

## Status

**Accepted** (Phase 4 spec — companion to master plan
`docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
§Pillar 4 line 89, §Phase 4 line 339).

## Scope decision

Phase 4 delivers the master plan's Pillar 4 (line 89) and Phase 4 row
(line 339): "Tag the 7 tools by capability; add `discover_tools`
Python helper; behavioral resolution gates." Fastblocks historically
opted out of `mcp_common.tools.apply_tool_profile()` (per CLAUDE.md:155-190);
Phase 4 opts back in for cross-component consistency.

**In scope:**

1. Replace the manual `register_fastblocks_tools` body with
   `mcp_common.tools.apply_tool_profile(...)` — the canonical Bodai
   MCP registration orchestrator.
1. Tag the 7 existing tools by capability (3 groups: template,
   component, adapter).
1. Per-tool behavioral gates (`_is_X_available() -> bool`) that
   gate registration when a dependency (library import, Oneiric
   resolver state) is unavailable.
1. The `discover_tools` MCP tool is auto-registered by
   `mcp_common.tools.apply_tool_profile` (no manual implementation).
1. Tests for capabilities, profile integration, discover_tools,
   and per-tool gates.

**Out of scope:**

- Adding new MCP tools (Phase 7 or later — the 7 are sufficient for
  the current surface).
- Replacing the FastMCP server with Mahavishnu's MCP infrastructure
  (separate effort; see CLAUDE.md:155-190).
- CLI subcommand `fastblocks mcp discover` (Python helper is
  sufficient; CLI is a future ergonomic).
- Per-tool runtime cost optimization (deferred — Phase 6 observability).

## Why Phase 4 uses mcp_common

`mcp_common` (the shared Bodai MCP infrastructure at
`/Users/les/Projects/mcp-common/mcp_common/tools/`) provides:

- `ToolProfile = StrEnum(MINIMAL | STANDARD | FULL)` — the canonical
  profile enum, with comparison operators for tier gating.
- `apply_tool_profile(server, *, profile_env_var, registrations, registration_map, register_all_fn, mandatory_groups)` — the
  orchestrator that wires capability → tool list → registration
  function → server.tool(...) calls.
- `discover_tools` — auto-registered as an MCP tool named
  `discover_tools`, returning `list[dict]` of registered tool
  metadata. Optional `query: str | None` filter.
- `trim_description(docstring, max_length=200)` — reduces MCP
  context consumption per tool.
- `MANDATORY_TOOLS` — always-registered regardless of profile
  (infrastructure-critical: health probes, load balancer
  endpoints). For fastblocks this set is empty (no health-endpoint
  MCP tool today).
- `ALL_TOOLS`, `InvalidProfileError` — public catalog + exception
  types.

Using `mcp_common` aligns fastblocks with Mahavishnu, css-mcp,
graphics-mcp, mailgun-mcp, langsmith-mcp, and the other -mcp
servers — the same `discover_tools` handler signature, the same
profile semantics, the same `trim_description` defaults.

## Architecture

Three layers, all delegated to `mcp_common` where possible.

### Layer 1 — Canonical types (mcp_common)

`mcp_common.tools.ToolProfile` (StrEnum), `mcp_common.tools.discover_tools`
(auto-registered MCP tool), `mcp_common.tools.trim_description` (200-char
default cap). fastblocks imports these; doesn't redefine them.

### Layer 2 — Capability definitions (NEW: `fastblocks/mcp/capabilities.py`)

Single source of truth for the 3 capability groups:

```python
"""FastBlocks MCP tool capabilities.

Source of truth for which tools belong to which capability, the
registration functions for each capability, and the per-capability
dependency gates.

Phase 4 ships 3 capabilities: TEMPLATE, COMPONENT, ADAPTER — matching
the 7 read-only tools in fastblocks/mcp/tools.py.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from fastblocks.mcp.tools import (
        validate_template,
        list_templates,
        render_template,
        list_components,
        validate_component,
        list_adapters,
        check_adapter_health,
    )

# Capability membership — pure data, used by both registration_map and tests.
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

# fastblocks has no MANDATORY tools (no health-endpoint MCP tool today).
MANDATORY_CAPABILITIES: tuple[str, ...] = ()


# Per-tool behavioral gates — pure functions, no side effects.
def _is_template_available() -> bool:
    """Template capability requires Jinja2 or HTMY importable."""
    try:
        import jinja2  # noqa: F401
        return True
    except ImportError:
        pass
    try:
        import htmy  # noqa: F401
        return True
    except ImportError:
        pass
    return False


def _is_component_available() -> bool:
    """Component capability requires absorbed htmy_components importable."""
    try:
        from fastblocks.adapters.templates import htmy_components  # noqa: F401
        return True
    except ImportError:
        return False


def _is_adapter_available() -> bool:
    """Adapter capability requires Oneiric resolver initialized."""
    try:
        from fastblocks.core.resolver import get_resolver
        get_resolver()
        return True
    except Exception:
        return False


def register_template_capability(server: FastMCP) -> None:
    """Register the 3 TEMPLATE_CAPABILITY tools. Skips silently if gate fails."""
    if not _is_template_available():
        return
    from fastblocks.mcp import tools as tools_module
    from mcp_common.tools import trim_description

    server.tool(
        "validate_template",
        description=trim_description(tools_module.validate_template.__doc__ or ""),
    )(tools_module.validate_template)
    server.tool(
        "list_templates",
        description=trim_description(tools_module.list_templates.__doc__ or ""),
    )(tools_module.list_templates)
    server.tool(
        "render_template",
        description=trim_description(tools_module.render_template.__doc__ or ""),
    )(tools_module.render_template)


def register_component_capability(server: FastMCP) -> None:
    """Register the 2 COMPONENT_CAPABILITY tools."""
    if not _is_component_available():
        return
    from fastblocks.mcp import tools as tools_module
    from mcp_common.tools import trim_description

    server.tool(
        "list_components",
        description=trim_description(tools_module.list_components.__doc__ or ""),
    )(tools_module.list_components)
    server.tool(
        "validate_component",
        description=trim_description(tools_module.validate_component.__doc__ or ""),
    )(tools_module.validate_component)


def register_adapter_capability(server: FastMCP) -> None:
    """Register the 2 ADAPTER_CAPABILITY tools."""
    if not _is_adapter_available():
        return
    from fastblocks.mcp import tools as tools_module
    from mcp_common.tools import trim_description

    server.tool(
        "list_adapters",
        description=trim_description(tools_module.list_adapters.__doc__ or ""),
    )(tools_module.list_adapters)
    server.tool(
        "check_adapter_health",
        description=trim_description(tools_module.check_adapter_health.__doc__ or ""),
    )(tools_module.check_adapter_health)


# Registration map: tool name → registration function. Used by
# apply_tool_profile's registration_map parameter.
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
    """Public accessor for the registration map.

    Returns a copy so callers cannot mutate the module-level state.
    """
    return dict(_REGISTRATION_MAP)
```

### Layer 3 — Server wiring (`fastblocks/mcp/server.py`)

Replace the existing `await register_fastblocks_tools(self._server)` call
in `FastBlocksMCPServer.initialize()` with:

```python
from mcp_common.tools import ToolProfile, apply_tool_profile
from .capabilities import (
    MANDATORY_CAPABILITIES,
    TEMPLATE_CAPABILITY,
    ALL_CAPABILITIES,
    get_registration_map,
)

await apply_tool_profile(
    self._server,
    profile_env_var="FASTBLOCKS_TOOL_PROFILE",
    registrations={
        ToolProfile.MINIMAL:  MANDATORY_CAPABILITIES,
        ToolProfile.STANDARD: MANDATORY_CAPABILITIES + TEMPLATE_CAPABILITY,
        ToolProfile.FULL:     ALL_CAPABILITIES,
    },
    registration_map=get_registration_map(),
)
```

`apply_tool_profile` handles:

- Reading `FASTBLOCKS_TOOL_PROFILE` env var (defaults to `full` if unset).
- Calling each registration function from `registration_map`.
- Auto-registering `discover_tools` as the 8th MCP tool (always).
- Trimming each tool's description via `trim_description`.
- Validating MANDATORY tools are registered (loud `ValueError` otherwise).

## Data flow

### Scenario A — Default startup (`FASTBLOCKS_TOOL_PROFILE` unset → FULL)

```
mahavishnu_mcp_server starts
    │
    ▼
FastBlocksMCPServer.initialize()
    │
    ▼
apply_tool_profile(server, profile_env_var="FASTBLOCKS_TOOL_PROFILE", ...)
    │
    ▼
mcp_common reads env: var not set → defaults to ToolProfile.FULL
    │
    ▼
For each capability in ALL_CAPABILITIES (3 groups):
    For each tool in capability (7 total):
        get_registration_map()[tool_name](server)
            │
            ▼
        _is_X_available()? → True (Jinja2 + Oneiric present)
            │
            ▼
        server.tool(name, description=trim_description(...))(fn)
    │
    ▼
discover_tools auto-registered by mcp_common
    │
    ▼
7 + 1 = 8 MCP tools exposed
```

### Scenario B — Operator sets `FASTBLOCKS_TOOL_PROFILE=standard`

```
env: FASTBLOCKS_TOOL_PROFILE=standard
    │
    ▼
apply_tool_profile reads STANDARD
    │
    ▼
Registers MANDATORY + TEMPLATE_CAPABILITY = 3 tools
    (validate_template, list_templates, render_template)
    │
    ▼
COMPONENT_CAPABILITY + ADAPTER_CAPABILITY NOT registered
    │
    ▼
discover_tools still registered (always, by mcp_common contract)
    │
    ▼
4 MCP tools exposed (3 + discover_tools)
    discover_tools handler returns list of 4 entries with capability metadata
```

### Scenario C — Claude calls discover_tools()

```
Claude calls discover_tools(query="template")
    │
    ▼
discover_tools_handler(query="template") returns
    [
      {"name": "validate_template",  "capability": "template", "description": "...", "is_available": true},
      {"name": "list_templates",     "capability": "template", "description": "...", "is_available": true},
      {"name": "render_template",    "capability": "template", "description": "...", "is_available": true},
    ]
    │
    ▼
Claude picks the right tool from the filtered list
```

### Scenario D — Per-tool gate returns False (degraded dependency)

```
register_adapter_capability(server) called
    │
    ▼
_is_adapter_available() returns False (e.g., Oneiric resolver not initialized)
    │
    ▼
Registration skipped silently (NOT a raise) — mcp_common contract
    │
    ▼
list_adapters, check_adapter_health NOT in server's tool list
    │
    ▼
discover_tools handler (mcp_common's auto-registered handler) returns the
    REGISTERED tool list only — unavailable tools are not in the list at all
```

**Why discover_tools doesn't show unavailable tools**: mcp_common's
`discover_tools_handler` reads from `server.list_tools()` (the FastMCP
3.4+ public API), which returns only successfully-registered tools.
A tool that was skipped because its gate returned False is not in
`server.list_tools()` and therefore not visible via `discover_tools`.

**If observability of unavailable tools is needed later** (Phase 6+
work), the right move is to extend mcp_common's `discover_tools_handler`
to take an `include_unavailable: bool = False` parameter that reads
from a separate "capability manifest" registered alongside the tools.
That's a mcp_common change, not a fastblocks one.

## Failure modes

| Failure | Behavior |
|---|---|
| `apply_tool_profile` raises `ValueError` (MANDATORY tool missing) | Loud startup error with missing tool name |
| Profile env var set to invalid value (`FASTBLOCKS_TOOL_PROFILE=foo`) | `mcp_common.tools.InvalidProfileError` raised at startup; loud failure |
| Gate returns False | Registration skipped silently for that capability; discover_tools reports `is_available: false` |
| `trim_description` returns empty (docstring missing) | Tool registered with empty description; no crash |
| Duplicate tool name across capabilities | `capabilities.py` import-time `assert len(set(ALL_CAPABILITIES)) == 7` catches at module load |
| `_is_adapter_available()` raises unexpectedly | Caught by broad `except Exception: return False` — degraded mode, not a crash |

## Test surface

| File | New tests | Markers | Purpose |
|---|---|---|---|
| `tests/mcp/test_capabilities.py` | 4 | `@pytest.mark.unit` | Each capability list non-empty; registration_map covers all 7 tools; MANDATORY ⊂ STANDARD ⊂ FULL ordering; uniqueness assertion passes |
| `tests/mcp/test_apply_tool_profile_integration.py` | 5 | `@pytest.mark.unit` | profile=MINIMAL registers MANDATORY only (0 fastblocks tools + discover_tools); profile=STANDARD registers MANDATORY + TEMPLATE (3 + discover_tools); profile=FULL registers ALL (7 + discover_tools); discover_tools registered in all 3 profiles; `trim_description` applied (each description ≤ 200 chars) |
| `tests/mcp/test_discover_tools_handler.py` | 3 | `@pytest.mark.unit` | `discover_tools_handler(query=None)` returns full list; `query="template"` filters to TEMPLATE_CAPABILITY; unavailable tool has `is_available: false` |
| `tests/mcp/test_per_tool_dependency_gates.py` | 4 | `@pytest.mark.unit` | Each `_is_X_available()` returns bool; mock jinja2 missing → `_is_template_available()=False`; mock Oneiric broken → `_is_adapter_available()=False`; gates don't raise on any input |

**Total: 16 new tests.** Combined with Phase 2's 50 + Phase 2.5's 18 = 84 distinct Phase 2/2.5/4 tests, plus the existing ~1800 baseline.

### Canary validation

| Canary | Action | Expected failure |
|---|---|---|
| Profile gating | Revert STANDARD profile to MANDATORY only | `test_apply_tool_profile_integration.py::test_standard_registers_template_capability` fails — TEMPLATE tools not registered |
| Capability gate | Revert `_is_template_available()` to `return False` | `test_apply_tool_profile_integration.py::test_full_registers_all` fails — TEMPLATE tools not registered |
| Discover tools | (mcp_common-managed; no canary) | n/a |
| Trim description | Stub `trim_description` to return raw docstring | `test_apply_tool_profile_integration.py::test_trim_description_applied` fails |
| Uniqueness | Remove a tool name from TEMPLATE_CAPABILITY (duplicate across capabilities) | `capabilities.py` import-time assertion fails → all tests using capabilities fail at module load |

## Verification gate

- All 16 new tests pass
- All 50 Phase 2 tests pass (no regression)
- All 18 Phase 2.5 tests pass (no regression)
- `tests/core/` full sweep: 119 + 16 = 135 PASS expected (with the 10 Phase 2.5 tests + 16 Phase 4 tests added; pre-existing 20 baseline failures unchanged)
- ty ratchet prod 0/50 PASS (no new suppressions)
- suppress(Exception) ratchet at 122 (no new sites; Phase 4 doesn't touch style_registry.py)
- Manual smoke: `FASTBLOCKS_TOOL_PROFILE=standard fastblocks mcp serve` → 4 tools exposed
- Manual smoke: `fastblocks mcp tools discover` (if CLI present) returns 7 tool metadata entries

## Per-task Integration Contracts

Three commits, all additive or backwards-compatible (the 7 tools are unchanged; only their registration mechanism is restructured).

### Commit 1 — `feat(mcp): capabilities.py — capability definitions + per-tool gates`

- *Triggered from:* Pillar 4 (master plan line 89); Phase 4 row (line 339)
- *Returns to / updates:* NEW `fastblocks/mcp/capabilities.py`; 4 new tests in `tests/mcp/test_capabilities.py`; 4 new tests in `tests/mcp/test_per_tool_dependency_gates.py`
- *Demonstrable by:* `python -c "from fastblocks.mcp.capabilities import ALL_CAPABILITIES; assert len(ALL_CAPABILITIES) == 7"` succeeds; tests pass
- *Rollback signal:* `git revert`; pure addition, no behavior change
- *Observability added:* None — pure data + pure-function gates

### Commit 2 — `refactor(mcp): register_fastblocks_tools delegates to apply_tool_profile`

- *Triggered from:* Commit 1 supplies the capability definitions; mcp_common supplies the orchestrator
- *Returns to / updates:* `fastblocks/mcp/server.py` — replace manual registration body with `apply_tool_profile(...)` call. **Decision: `fastblocks/mcp/tools.py` is NOT modified.** The 7 tool functions stay where they are. `register_fastblocks_tools` (the existing function in tools.py) is kept as a thin pass-through wrapper for any callers that still reference it; its body delegates to capabilities.py's `register_template_capability` / `register_component_capability` / `register_adapter_capability` functions. This minimizes the diff and keeps the existing tools.py module intact for future Phase 6 observability work.
- *Demonstrable by:* `tests/mcp/test_apply_tool_profile_integration.py` 5/5 pass; the 7 tools are registered under the right profile; `register_fastblocks_tools` (the legacy entry point) still works as a thin wrapper
- *Rollback signal:* `git revert`; manual registration restored (the existing `register_fastblocks_tools` body still works as a fallback)
- *Observability added:* `discover_tools` MCP tool auto-registered; structured logs via mcp_common (profile + count of tools registered)

### Commit 3 — `test(mcp): discover_tools handler tests + manual smoke verification`

- *Triggered from:* Commit 2 ships the discover_tools wiring
- *Returns to / updates:* `tests/mcp/test_discover_tools_handler.py` (NEW, 3 tests)
- *Demonstrable by:* Tests pass; manual smoke confirms `discover_tools()` returns the 7 tool metadata entries with correct capability tags
- *Rollback signal:* `git revert`; tests only
- *Observability added:* None (test-only)

## Cross-references

- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md` §Pillar 4 (line 89), §Phase 4 (line 339)
- Phase 1.5 spec: `docs/superpowers/specs/2025-09-fastblocks-oneiric-registry-design.md` (registry consolidation that Phase 4 builds on)
- Phase 2 spec: `docs/superpowers/specs/2026-08-21-fastblocks-phase-2-design.md` (Literal types + Protocol gates)
- Phase 2.5 spec: `docs/superpowers/specs/2026-08-22-fastblocks-phase-2-5-design.md` (app.yml wiring)
- mcp-common public API: `/Users/les/Projects/mcp-common/mcp_common/tools/__init__.py`
- mcp-common dispatch: `/Users/les/Projects/mcp-common/mcp_common/tools/dispatch.py:233` (discover_tools_handler), `:253` (apply_tool_profile)
- mcp-common profiles: `/Users/les/Projects/mcp-common/mcp_common/tools/profiles.py` (ToolProfile StrEnum)
- fastblocks current state: `fastblocks/mcp/tools.py:562-610` (existing register_fastblocks_tools body); `fastblocks/mcp/server.py:74-82` (current registration call)
- CLAUDE.md:155-190 (historical opt-out note — Phase 4 opts back in)

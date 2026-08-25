---
status: active
role: canonical
date: 2026-08-23
last_reviewed: 2026-08-23
supersedes: docs/superpowers/specs/2026-08-23-fastblocks-phase-4-v2-design.md
superseded_by: null
decision_date: 2026-08-23
topic: phase-4-v21-design
---

# Phase 4 v2.1: MCP Tool Surface Organization — Library-Aware Opt-In (Remediated)

## Status

**Accepted** (Phase 4 v2.1 — re-design after multi-agent review surfaced
7 P0 blockers in the v2 spec). Supersedes the broken v2 spec at
`docs/superpowers/specs/2026-08-23-fastblocks-phase-4-v2-design.md`
which was rejected by the 2026-08-23 multi-agent review synthesis
(`docs/superpowers/sdd/2026-08-23-fastblocks-phase-4-v2/synthesis.md`).

## What changed from v2 → v2.1

| # | v2 issue (P0) | v2.1 fix |
|---|---|---|
| R1 | `_apply_tool_profile_async` (line 150) does NOT re-resolve profile — env var + yaml chain is dead code | (N/A — see R5: framework-internal wiring removed entirely) |
| R2 | `_oneiric_yaml_loader` imports nonexistent `fastblocks.core.config` | Function dropped entirely; env var only |
| R3 | `is_available: false` structurally impossible — unavailable tools aren't in `server.list_tools()` | Field dropped from schema; documented as always-true for registered tools |
| R4 | Test scope mismatches (9 tests break not 6; `test_ci_guard.py:229` missing from deletion list; count math inconsistent) | All counts reconciled to **21 new + 13 deleted = +8 net**; entire `test_tool_profile.py` (9 tests) + 4 server_canary tests (1 module-level import + 3 _get_http_app tests) deleted; `test_ci_guard.py:229` NOT deleted because `register_fastblocks_tools` is kept (R5); v2.1.2 patch adds the missing server_canary tests to the deletion list |
| R5 | "Library-aware opt-in" framing contradicts implementation (`FastBlocksMCPServer._register_tools` calls `_apply_tool_profile_async` directly = framework opts in, violating CLAUDE.md) | Framework-internal wiring **dropped entirely**. `FastBlocksMCPServer._register_tools` keeps current `register_fastblocks_tools` body. Phase 4 v2.1 ships capability metadata for **consumers only** (e.g. SplashStand). This actually preserves CLAUDE.md:157-190 |
| R6 | CLAUDE.md references the deleted stub in 5 lines with no commit to update | CLAUDE.md updates appended to Commit 4 (ADR + doc sweep) |
| R7 | Phantom `ToolProfile.from_env_or_yaml` method referenced in Scenario E | Scenario E uses real `ToolProfile.from_env` + manual yaml-loader pattern |

## Scope decision

Phase 4 v2.1 delivers the master plan's Pillar 4 and Phase 4 row with a
**library-aware opt-in, consumer-facing posture**:

1. **Public capability metadata** — `fastblocks/mcp/capabilities.py`
   exports the 3 capability tuples, the registration functions, the
   registration map, the per-tool dependency gates, and a per-tool
   capability-tag map. Consumers (SplashStand) import these and pass
   them to their own `mcp_common.tools.apply_tool_profile` calls.
2. **Consumer-pattern documentation** — `docs/superpowers/specs/...`
   documents a Scenario E wiring pattern for SplashStand-style consumers
   to opt into profile-based dispatch using the exported primitives.
   The framework-internal `FastBlocksMCPServer` continues to register
   all 7 tools via the existing `register_fastblocks_tools` function
   (status quo — no framework-level change).
3. **Custom discovery schema (optional)** — `fastblocks/mcp/discovery.py`
   exports `fastblocks_discovery` as a custom `discovery_fn=` override
   that consumers can pass to `apply_tool_profile` to add the
   `capability` field to `discover_tools` responses. The default
   `_default_discovery` from mcp_common works but lacks the capability
   tag.
4. **Delete the orphaned sync ASGI path** — `_get_http_app`,
   `get_http_app`, `_http_app_cache`, `http_app = None` all removed;
   no external consumers found (verified via grep across
   `/Users/les/Projects` excluding the fastblocks repo).
5. **Delete the no-op opt-out stub** — `apply_fastblocks_tool_profile`,
   `FASTBLOCKS_TOOLS`, `PROFILE_REGISTRATIONS`, `_FallbackToolProfile`
   all removed from `fastblocks/mcp/profiles.py`. Their replacements
   are the real primitives in `mcp_common` (consumer imports) and
   `capabilities.py` (public contract).
6. **Test surface** — 21 new tests + 13 deleted tests (the entire
   `test_tool_profile.py` (9 tests) + 4 `test_server_canary.py` items
   (1 module-level import + 3 `_get_http_app` tests + 1
   `test_tools_list_matches_7_name_tuple`)) = **+8 net**.
   (`register_fastblocks_tools` is kept per R5; `test_ci_guard.py:229`
   is NOT deleted.)

**Out of scope** (deferred):

- Adding new MCP tools (Phase 7 or later).
- Replacing FastMCP with Mahavishnu's MCP infrastructure.
- Framework-internal `FastBlocksMCPServer._register_tools` wiring
  changes (status quo; consumers wire themselves).
- CLI `fastblocks mcp discover` subcommand (Python helper suffices).
- Per-tool runtime cost optimization (Phase 6 observability).

## Why library-aware opt-in, not full opt-in

The original Phase 4 spec (2026-08-22) and the broken v2 (2026-08-23)
both proposed adopting `mcp_common.tools.apply_tool_profile` directly
in `FastBlocksMCPServer`. ADR 0011 Decision 5 documented why this
overrides CLAUDE.md:157-190's library-not-server rationale without
weighing it.

v2.1 takes the **strict library posture**: `FastBlocksMCPServer` keeps
its current `register_fastblocks_tools` body. The framework continues
to register all 7 tools unconditionally. Consumers (e.g. SplashStand)
who want profile-based dispatch import `fastblocks.mcp.capabilities`
and pass the registration functions to their own `apply_tool_profile`
calls. The capability metadata is a **library export**, not a
framework-internal wiring change.

This honors CLAUDE.md:157-190 directly — no "renaming" or
"reframing" needed.

## Architecture

Three layers, library-facing.

### Layer 1 — Public metadata (`fastblocks/mcp/capabilities.py`, NEW)

```python
"""FastBlocks MCP tool capability metadata (Phase 4 v2.1 public API).

Consumer-side: SplashStand and similar consumers import these constants
and functions and pass them to their own
``mcp_common.tools.apply_tool_profile`` calls. Fastblocks-internal
``FastBlocksMCPServer`` is NOT changed in this commit — consumers wire
themselves.

3 capabilities across the 7 read-only tools:
- TEMPLATE: validate_template, list_templates, render_template
- COMPONENT: list_components, validate_component
- ADAPTER: list_adapters, check_adapter_health
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from fastblocks.mcp import tools as tools_module

# Capability membership — pure data, exported for consumer introspection.
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


# Per-tool dependency gates — probe resolved state, NOT construction.
def _is_template_available() -> bool:
    """Template capability requires Jinja2 OR HTMY importable (not lazy)."""
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
    """Adapter capability requires Oneiric resolver bootstrapped with at
    least one active candidate in the ``fastblocks`` domain.

    Probes via the Phase 1.5 facade (not lazy construction).
    """
    try:
        from fastblocks.core.resolver import FastblocksRegistry, get_resolver
        registry = FastblocksRegistry(get_resolver())
        return bool(registry.list_active("fastblocks"))
    except Exception:
        return False


# Per-capability registration functions. Each checks its gate; returns
# silently (no raise) when the gate fails — per mcp_common contract.
def register_template_capability(server: FastMCP) -> None:
    """Register the 3 TEMPLATE_CAPABILITY tools."""
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


# Per-tool → per-capability-callable map. For consumers wanting fine-grained
# per-tool registration.
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
    return dict(_REGISTRATION_MAP)


# Tool name → capability tag map. Used by the custom discovery_fn to
# emit the ``capability`` field in discover_tools responses.
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
```

Note: `_oneiric_yaml_loader` from v2 is **removed**. Phase 4 v2.1
relies on env-var-only profile resolution. YAML-driven profile is
deferred — fastblocks' `load_fastblocks_settings()` does not have
a `tool_profile` field, and adding one is Phase 6+ work (config
schema extension).

### Layer 2 — Custom discovery (`fastblocks/mcp/discovery.py`, NEW)

```python
"""FastBlocks-specific discovery_fn for ``apply_tool_profile``.

Override of mcp_common's ``_default_discovery`` to add the
``capability`` field consumers need. Opt-in: consumers pass this as
``discovery_fn=fastblocks_discovery`` to their own apply_tool_profile
call. If consumers don't pass it, mcp_common's default shape is used
(no capability tag).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .capabilities import get_tool_capability


async def fastblocks_discovery(
    server: FastMCP, filter_query: str | None
) -> list[dict]:
    """Emit {name, capability, description, inputSchema}.

    Walks the server's registered tools and looks up each name in
    ``get_tool_capability()``.

    Note: tools that fail a capability gate are NOT in
    ``server.list_tools()`` (gate failures skip registration entirely,
    per mcp_common contract). The schema therefore has no
    ``is_available`` field — every tool in the response is registered.
    Consumers who need availability state should consult the
    ``get_tool_capability()`` capability map directly.
    """
    tools = await server.list_tools()
    result: list[dict] = []
    for t in tools:
        capability = get_tool_capability(t.name)
        result.append(
            {
                "name": t.name,
                "capability": capability,
                "description": t.description or "",
                "inputSchema": t.parameters,
            }
        )
    if filter_query:
        q = filter_query.lower()
        result = [
            t
            for t in result
            if q in str(t["name"]).lower()
            or q in str(t["capability"]).lower()
            or q in str(t["description"]).lower()
        ]
    return result
```

### Layer 3 — Consumer pattern (Scenario E, documented not coded)

The framework-internal `FastBlocksMCPServer._register_tools` body is
**unchanged**. The 7 tools continue to register via the existing
`register_fastblocks_tools` function in `fastblocks/mcp/tools.py:562-610`.

Consumers who want profile-based dispatch import the capabilities +
discovery + registration_map and wire their own `apply_tool_profile`
call. Reference Scenario E:

```python
# In SplashStand's MCP server module (NOT in fastblocks).
# NOTE: the consumer MUST be initialized from an async context
# (the canonical MCP server case). The async wrapper
# ``_apply_tool_profile`` is the documented async entrypoint for
# ``apply_tool_profile`` (mcp_common/tools/dispatch.py:337-390).
# Calling sync ``apply_tool_profile`` from inside a running event
# loop raises ``RuntimeError`` (dispatch.py:331-334).
from fastblocks.mcp.capabilities import (
    MANDATORY_CAPABILITIES,
    register_template_capability,
    register_component_capability,
    register_adapter_capability,
)
from fastblocks.mcp.discovery import fastblocks_discovery
from mcp_common.tools import ToolProfile
from mcp_common.tools.dispatch import _apply_tool_profile

await _apply_tool_profile(
    server,
    profile_env_var="SPLASHSTAND_TOOL_PROFILE",
    registrations={
        ToolProfile.MINIMAL:  [],
        ToolProfile.STANDARD: [register_template_capability],
        ToolProfile.FULL:     [
            register_template_capability,
            register_component_capability,
            register_adapter_capability,
        ],
    },
    registration_map={},  # Using callable-list pattern
    register_all_fn=None,
    mandatory_groups=set(),
    essential_tool_names=set(),
    discovery_fn=fastblocks_discovery,
    yaml_loader=None,  # env var only for v2.1
)
```

Note on env-var vs yaml: the consumer pattern uses mcp_common's
async wrapper `_apply_tool_profile` which reads from env-var →
yaml-loader → FULL fallback. Since v2.1 drops `_oneiric_yaml_loader`,
consumers either pass their own yaml_loader (e.g. reading from their
own SplashStand settings) or rely on env-var only. The fastblocks
library exposes no yaml-loader helper in v2.1 — that's a Phase 6+
config extension.

For **sync startup** paths (CLI tools, scripts outside an event loop),
consumers can use the sync `apply_tool_profile(...)` wrapper directly;
the sync wrapper detects whether an event loop is running and either
calls `asyncio.run(...)` or raises `RuntimeError`. The async wrapper
above is the correct choice for the MCP server case.

### Deletions

| File / line | Removed |
|---|---|
| `fastblocks/mcp/server.py:141-170` | `_get_http_app` |
| `fastblocks/mcp/server.py:175-190` | `_http_app_cache`, `get_http_app` |
| `fastblocks/mcp/server.py:195` | `http_app = None` |
| `fastblocks/mcp/profiles.py` (entire file) | All 197 lines |
| `tests/mcp/test_server_canary.py` lines 50, 59, 81 | 3 tests for `_get_http_app` |
| `tests/mcp/test_tool_profile.py` (entire file) | All 9 tests for the no-op stub |
| `tests/mcp/test_ci_guard.py` line 229-254 | `test_register_fastblocks_tools_registers_the_documented_surface` (depends on `register_fastblocks_tools` if removed) |

Wait — `register_fastblocks_tools` itself is NOT removed in v2.1. The
v2 spec was ambiguous about this; v2.1 keeps it (the framework-internal
wiring is unchanged, so `register_fastblocks_tools` is still called
by `_register_tools`). Therefore `test_ci_guard.py:229` does NOT need
to be deleted. **Updated deletion list**:

| File | Removed |
|---|---|
| `fastblocks/mcp/server.py:141-170` | `_get_http_app` |
| `fastblocks/mcp/server.py:175-190` | `_http_app_cache`, `get_http_app` |
| `fastblocks/mcp/server.py:195` | `http_app = None` |
| `fastblocks/mcp/profiles.py` (entire file) | All 197 lines |
| `tests/mcp/test_server_canary.py` lines 24-47 | Module-level import `from fastblocks.mcp.profiles import FASTBLOCKS_TOOLS` + the 4th test `test_tools_list_matches_7_name_tuple` (broken by `profiles.py` deletion). Alternative: rewire to use `from fastblocks.mcp.capabilities import ALL_CAPABILITIES` and update assertion. |
| `tests/mcp/test_server_canary.py` lines 50, 59, 81 | 3 tests for `_get_http_app` |
| `tests/mcp/test_tool_profile.py` (entire file) | All 9 tests for the no-op stub |

Total deletions: 4 (server_canary) + 9 (tool_profile) = **13 tests deleted**.

Net test delta: 21 new - 13 deleted = **+8 net**.

## Data flow

### Scenario A — Default startup (`FASTBLOCKS_TOOL_PROFILE` unset → FULL)

For framework-internal `FastBlocksMCPServer`:

```
mahavishnu_mcp_server starts
    │
    ▼
FastBlocksMCPServer.initialize()
    │
    ▼
self._register_tools() — UNCHANGED from current main
    │
    ▼
await register_fastblocks_tools(self._server)  # still 7 tools, no profile
    │
    ▼
7 MCP tools exposed (no discover_tools, no profile gating — this is the
documented framework posture; consumers opt into richer behavior via
Scenario E)
```

For a consumer (SplashStand):

```
SplashStand MCPServer initializes
    │
    ▼
apply_tool_profile(server, profile_env_var="SPLASHSTAND_TOOL_PROFILE", ...)
    │
    ▼
mcp_common reads env: var unset → defaults to FULL (yaml_loader is None)
    │
    ▼
For each capability in [register_template_capability,
                       register_component_capability,
                       register_adapter_capability]:
    capability(server) → gate check → server.tool() for each
    │
    ▼
fastblocks_discovery registered as discover_tools (if discovery_fn passed)
    │
    ▼
7 + 1 = 8 MCP tools exposed
```

### Scenario B — Consumer sets `SPLASHSTAND_TOOL_PROFILE=standard`

```
env: SPLASHSTAND_TOOL_PROFILE=standard
    │
    ▼
apply_tool_profile reads STANDARD
    │
    ▼
Registers [register_template_capability] only
    │
    ▼
3 TEMPLATE tools exposed
COMPONENT and ADAPTER gates still run but their tools are not in the
registrations list for STANDARD, so they're not registered.
    │
    ▼
discover_tools registered (if discovery_fn passed)
    │
    ▼
3 + 1 = 4 MCP tools exposed
```

### Scenario C — Operator sets `tool_profile` in fastblocks settings/local.yaml

**Not supported in v2.1.** Operators wanting yaml-driven profile must
either:
- (a) Read the fastblocks settings via their consumer app and pass a
  yaml_loader to `apply_tool_profile`, OR
- (b) Wait for Phase 6+ to add `tool_profile: str | None` to
  `load_fastblocks_settings()` and expose a `_oneiric_yaml_loader`
  helper in `fastblocks.mcp.capabilities`.

### Scenario D — Per-tool gate returns False (degraded dependency)

In a consumer's MCP server:

```
register_adapter_capability(server) called
    │
    ▼
_is_adapter_available() returns False (e.g., Oneiric not bootstrapped)
    │
    ▼
Registration skipped silently (NOT a raise) — mcp_common contract
    │
    ▼
list_adapters, check_adapter_health NOT in server's tool list
    │
    ▼
fastblocks_discovery walks server.list_tools() — doesn't see the
skipped tools. No `is_available: false` field — those tools simply
aren't in the response.
```

## Failure modes

| Failure | Behavior |
|---|---|
| Consumer's `apply_tool_profile` raises `ValueError` (MANDATORY tool missing) | Loud startup error with missing tool name |
| Profile env var set to invalid value | `mcp_common.tools.InvalidProfileError` raised at startup |
| Gate returns False | Registration skipped silently for that capability; tool not in discover_tools response |
| `trim_description` returns empty (docstring missing) | Tool registered with empty description; no crash |
| Duplicate tool name across capabilities | Caught at module load (capability tuples are mutually exclusive by construction) |
| `_is_adapter_available()` raises unexpectedly | Caught by broad `except Exception: return False` — degraded mode |
| `_get_http_app` no longer importable | SplashStand and any consumer that imported it directly see `ImportError`; verified no consumer does |
| `register_fastblocks_tools` no longer importable | Same — verified no external consumer |

## Test surface

| File | New tests | Markers | Purpose |
|---|---|---|---|
| `tests/mcp/test_capabilities.py` | 4 | `@pytest.mark.unit` | Each capability list non-empty; mutually exclusive (no overlap); full coverage (7 tools total); `get_registration_map()` matches capability tuples; `get_tool_capability()` returns expected tags |
| `tests/mcp/test_per_tool_dependency_gates.py` | 4 | `@pytest.mark.unit` | Each `_is_X_available()` returns `bool`; missing dep → `False`; never raises |
| `tests/mcp/test_discover_tools_handler.py` | 3 | `@pytest.mark.unit` | `fastblocks_discovery(query=None)` returns full list with `{name, capability, description, inputSchema}`; `query="template"` filters to 3; `query="adapter"` filters to 2 |
| `tests/mcp/test_capability_consumers.py` | 4 | `@pytest.mark.unit` | Consumer-pattern import + use case: import `register_template_capability` etc. directly; pass to a mock `apply_tool_profile` invocation; verify the callables work with `server.tool()`; verify the gate-skip semantics |
| `tests/mcp/test_consumer_pattern_wiring.py` | 3 | `@pytest.mark.unit` | Integration test simulating SplashStand wiring: register a mock MCP server, call `apply_tool_profile` with `registrations={ToolProfile.STANDARD: [register_template_capability]}`, assert exactly 3 template tools + 1 discover_tools tool |
| `tests/mcp/test_yaml_loader_skipped.py` | 3 | `@pytest.mark.unit` | Document the v2.1 deferred-state: `capabilities.py` exports NO `_oneiric_yaml_loader`; consumers reading from yaml must pass their own `yaml_loader` to `apply_tool_profile`; if they don't, env var wins (or FULL if env unset) |

**Total: 21 new tests.**

**Deletions** (12 tests total):

| File | Tests deleted | Reason |
|---|---|---|
| `tests/mcp/test_server_canary.py` lines 50, 59, 81 | 3 | `_get_http_app` target deleted |
| `tests/mcp/test_tool_profile.py` (entire file) | 9 | `apply_fastblocks_tool_profile`, `FASTBLOCKS_TOOLS`, `PROFILE_REGISTRATIONS`, `_FallbackToolProfile` all deleted with `profiles.py` |

**Net test delta: 21 new − 13 deleted = +8 net.**

### Canary validation

| Canary | Action | Expected failure |
|---|---|---|
| Capability membership | Add "kelpui" to TEMPLATE_CAPABILITY without updating _TOOL_CAPABILITY | `test_capabilities.py::test_get_tool_capability_returns_expected_tags` fails |
| Gate probe-not-construct | Stub `registry.list_active` to return [] and check `_is_adapter_available` returns False | `test_per_tool_dependency_gates.py::test_adapter_gate_probes_resolved_state` fails |
| Custom discovery schema | Stub `fastblocks_discovery` to omit `capability` field | `test_discover_tools_handler.py::test_full_schema` fails |
| Consumer pattern | Replace `register_template_capability` with `register_component_capability` in the integration test | `test_consumer_pattern_wiring.py::test_standard_registers_template_capability` fails |
| Tool name → capability map | Remove `validate_template` from `_TOOL_CAPABILITY` | `test_capabilities.py::test_get_tool_capability_returns_expected_tags` fails |

## Verification gate

- All 21 new tests pass
- All 50 Phase 2 tests still pass (no regression)
- All 18 Phase 2.5 tests still pass (no regression)
- All 11 Phase 1.5 tests still pass (no regression; verified by grep that no Phase 1.5 test file imports `fastblocks.mcp.profiles` or references `_get_http_app`)
- ty ratchet prod 0/50 PASS (no new suppressions)
- `suppress(Exception)` ratchet at ≤ 122 (no new sites; we delete `_get_http_app`'s `with suppress(Exception)` site at server.py:157)
- Manual smoke: framework `FastBlocksMCPServer.initialize()` still works as before (no behavior change)
- Manual smoke: `python -c "from fastblocks.mcp.capabilities import ALL_CAPABILITIES; assert len(ALL_CAPABILITIES) == 7"` succeeds
- Manual smoke: consumer pattern imports succeed (`from fastblocks.mcp.capabilities import register_template_capability`)

## Per-task Integration Contracts

Three commits, additive-then-deletive.

### Commit 1 — `feat(mcp): capabilities.py + discovery.py — consumer-facing capability metadata`

- *Triggered from:* ADR 0011 Decisions 2-12 (the deferred original spec); master plan §Pillar 4; v2.1 fixes R3+R4 (drop is_available, fix test counts)
- *Returns to / updates:* NEW `fastblocks/mcp/capabilities.py`; NEW `fastblocks/mcp/discovery.py`; 15 new tests in `tests/mcp/test_capabilities.py` (4) + `tests/mcp/test_per_tool_dependency_gates.py` (4) + `tests/mcp/test_discover_tools_handler.py` (3) + `tests/mcp/test_capability_consumers.py` (4)
- *Demonstrable by:* `python -c "from fastblocks.mcp.capabilities import ALL_CAPABILITIES; assert len(ALL_CAPABILITIES) == 7"` succeeds; 15 tests pass
- *Rollback signal:* `git revert`; pure addition, no behavior change
- *Observability added:* None — pure data + pure-function gates

### Commit 2 — `feat(mcp): consumer-pattern integration tests`

- *Triggered from:* Commit 1 supplies the capability definitions; consumer pattern needs integration coverage
- *Returns to / updates:* NEW `tests/mcp/test_consumer_pattern_wiring.py` (3 tests) + NEW `tests/mcp/test_yaml_loader_skipped.py` (3 tests) + a docs update to `docs/architecture/tool-profile-rationale.md` documenting the v2.1 consumer pattern
- *Demonstrable by:* All 6 tests pass; consumer-pattern integration test simulates SplashStand wiring with a mock MCP server (verifies the callable-list pattern wires correctly; not a true end-to-end over a real SplashStand MCP server)
- *Rollback signal:* `git revert`; tests + doc only
- *Observability added:* None

Note: **Commit 2 does NOT touch `FastBlocksMCPServer._register_tools`.** This is the load-bearing decision per R5: the framework's internal server keeps its existing `register_fastblocks_tools` call. Only consumers (SplashStand) wire themselves.

### Commit 3 — `chore(mcp): delete _get_http_app + opt-out stub + related tests`

- *Triggered from:* Commits 1-2 make the deletion safe (capability metadata + consumer-pattern tests replace the deleted stub); user choice (asked + answered "Delete _get_http_app")
- *Returns to / updates:* `fastblocks/mcp/server.py` — remove `_get_http_app`, `get_http_app`, `_http_app_cache`, `http_app = None`; `fastblocks/mcp/profiles.py` — delete entire file; `tests/mcp/test_server_canary.py` — remove 3 `_get_http_app` tests; `tests/mcp/test_tool_profile.py` — delete entire file (9 tests)
- *Demonstrable by:* `from fastblocks.mcp.server import _get_http_app` raises `ImportError`; `from fastblocks.mcp.profiles import apply_fastblocks_tool_profile` raises `ImportError`; full sweep passes (2225 + 21 - 13 = 2233 tests); `git grep -c 'fastblocks.mcp.profiles' tests/mcp/` returns 0 (no test file still imports the deleted module); `git grep -c '_get_http_app\|get_http_app' tests/` returns 0 (no test file still references the deleted ASGI path)
- *Rollback signal:* `git revert`; both stubs restored
- *Observability added:* None (deletions only); `suppress(Exception)` ratchet improves by 1 (server.py:157's `with suppress(Exception)` block is gone)

### Commit 4 — `docs(adr): ADR 0012 + CLAUDE.md update`

- *Triggered from:* This spec
- *Returns to / updates:* `docs/adr/0012-phase-4-library-aware-opt-in.md` (NEW) + `CLAUDE.md` update (the 7 lines referencing the deleted stub at CLAUDE.md:164, 166, 167, 171, 172, 174, 184 — verify with `git grep -n` at commit time; count may shift as other docs are touched) + `fastblocks/core/resolver.py:150` (drop the broken `:func:`fastblocks.mcp.profiles.apply_fastblocks_tool_profile`` Sphinx xref whose target is deleted by Commit 3 — would otherwise warn/fail docs builds)
- *Demonstrable by:* `find docs/adr -name "0012-*.md"` returns the new file; `git diff CLAUDE.md` shows the deletion-of-stub-references + addition of consumer-pattern paragraph; `git grep -c 'apply_fastblocks_tool_profile\|FASTBLOCKS_TOOLS\|PROFILE_REGISTRATIONS\|_FallbackToolProfile' CLAUDE.md` returns 0; `git grep ':func:\`fastblocks\.mcp\.profiles\.apply_fastblocks_tool_profile\`' fastblocks/core/resolver.py` returns nothing
- *Rollback signal:* `git revert`; doc-only
- *Observability added:* None

Note: forward-looking doc references in `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md` (lines 206, 473) and `docs/superpowers/specs/2026-08-22-fastblocks-phase-5-design.md` (line 787) that reference the to-be-deleted `profiles.FASTBLOCKS_TOOLS` symbol are deferred to Phase 5 doc updates (when those specs land). They are not breaking — Phase 5's integration test will be reworked when Phase 5 ships.

## Out of scope (deferred)

- Framework-internal `FastBlocksMCPServer` wiring (Phase 4 v2.1 keeps it unchanged — consumers wire themselves)
- New MCP tools (Phase 7 or later)
- Replacing FastMCP with Mahavishnu's MCP infrastructure
- CLI `fastblocks mcp discover` subcommand
- Per-tool runtime cost optimization (Phase 6 observability)
- YAML-driven profile via `load_fastblocks_settings()` (needs `tool_profile` field on AppSettings — Phase 6+ config extension)

## Cross-references

- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md` §Pillar 4 (line 89), §Phase 4 (line 339)
- ADR 0011 (Phase 4 deferral): `docs/adr/0011-phase-4-deferral.md`
- Broken v2 spec (superseded): `docs/superpowers/specs/2026-08-23-fastblocks-phase-4-v2-design.md`
- Multi-agent review synthesis: `docs/superpowers/sdd/2026-08-23-fastblocks-phase-4-v2/synthesis.md`
- Per-reviewer reports: `docs/superpowers/sdd/2026-08-23-fastblocks-phase-4-v2/{l2,l3,l4,l5}-reviewer.md`
- CLAUDE.md:157-190 — library boundary rationale (preserved by this design — no framework-internal wiring change)
- mcp_common public API: `/Users/les/Projects/mcp-common/mcp_common/tools/__init__.py` (`apply_tool_profile`, `ToolProfile`, `trim_description`)
- mcp_common dispatch: `/Users/les/Projects/mcp-common/mcp_common/tools/dispatch.py:253` (sync `apply_tool_profile`), `:337` (async wrapper)
- mcp_common descriptions: `/Users/les/Projects/mcp-common/mcp_common/tools/descriptions.py` (`trim_description`)
- FastBlocksMCPServer current state: `fastblocks/mcp/server.py:33-67` (initialize), `:74-82` (_register_tools — UNCHANGED in v2.1)
- Oneiric resolver: `fastblocks/core/resolver.py:138-141` (lazy init), `:144-162` (`FastblocksRegistry` facade)
- Phase 2 spec: `docs/superpowers/specs/2026-08-21-fastblocks-phase-2-design.md` (Literal types + Protocol gates; this spec reuses the same architectural pattern)

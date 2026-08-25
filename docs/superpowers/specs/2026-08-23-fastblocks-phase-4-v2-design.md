---
status: complete
role: historical
date: 2026-08-23
last_reviewed: 2026-08-23
supersedes: docs/superpowers/specs/2026-08-22-fastblocks-phase-4-design.md
superseded_by: docs/superpowers/specs/2026-08-23-fastblocks-phase-4-v2.1-design.md
decision_date: 2026-08-23
topic: phase-4-v2-design
---

# Phase 4 v2: MCP Tool Surface Organization — Library-Aware Opt-In Design

## Status

**Accepted** (Phase 4 v2 — re-design after ADR 0011 deferred the original
spec with 5 P0 blockers + 7 P1 issues). Supersedes the original Phase 4
spec at `docs/superpowers/specs/2026-08-22-fastblocks-phase-4-design.md`
which was committed in `85f22e6` and deferred in `22478ce` (ADR 0011).

## Context

The master plan (§Pillar 4 line 89, §Phase 4 line 339) calls for tagging
the 7 FastBlocks MCP tools by capability, adding `discover_tools`, and
introducing behavioral dependency gates. The original Phase 4 spec
(2026-08-22) proposed a full opt-in to `mcp_common.tools.apply_tool_profile`
but was deferred in ADR 0011 after multi-agent review surfaced 5 P0
blockers:

1. `apply_tool_profile` is sync; spec wrote `await apply_tool_profile(...)` —
   server fails to initialize.
2. `registrations` dict passed tool-name strings, causing duplicate
   `server.tool()` calls per element.
3. `discover_tools` response schema invented `{name, capability,
   is_available}` but `mcp_common._default_discovery` returns
   `{name, description, inputSchema, group: None}`.
4. Spec's "opt back in wholesale" overrode CLAUDE.md:155-190's
   load-bearing library-not-server rationale without weighing it.
5. `_get_http_app` (sync uvicorn path) was orphaned; spec only updated
   async `initialize()`.

Plus 6 P1 issues: gates self-fulfilling (lazy `get_resolver()` constructs
empty Resolver), gates bypassed Phase 1.5 facade, no `yaml_loader`
plumbing, signature mismatch with mcp_common, `register_fastblocks_tools`
becomes a built-but-not-wired anti-pattern, opt-out stub invalidated.

This v2 spec addresses all 5 P0s and all 6 P1s **without** touching
mcp_common, by using existing mcp_common APIs correctly and exposing
capability metadata as a public contract that consumers (e.g. SplashStand)
import into their own `apply_tool_profile` calls.

## Scope decision

Phase 4 v2 delivers the master plan's Pillar 4 and Phase 4 row with a
**library-aware opt-in** posture:

1. **Public capability metadata** — `fastblocks/mcp/capabilities.py`
   exports the 3 capability tuples, the registration functions, the
   registration map, and the per-tool dependency gates. Consumers
   (SplashStand) import these and pass them to their own
   `apply_tool_profile` calls.
2. **fastblocks-internal server wiring** — `FastBlocksMCPServer._register_tools`
   wires the same primitives via `_apply_tool_profile_async` (the async
   sibling at `mcp_common/tools/dispatch.py:150` — fixes P0 #1).
3. **Custom discovery schema** — a fastblocks-specific `discovery_fn`
   that emits `{name, capability, is_available, description, inputSchema}`
   (fixes P0 #3) and is passed as the `discovery_fn=` kwarg.
4. **Delete the orphaned sync ASGI path** — `_get_http_app`,
   `get_http_app`, `_http_app_cache`, `http_app` all removed; no
   external consumers found (verified via grep across
   `/Users/les/Projects`).
5. **Delete the no-op opt-out stub** — `apply_fastblocks_tool_profile`,
   `FASTBLOCKS_TOOLS`, `PROFILE_REGISTRATIONS`, `_FallbackToolProfile`
   all removed from `fastblocks/mcp/profiles.py`. Their replacements
   are the real primitives in `mcp_common` and `capabilities.py`.
6. **Test surface** — 16 new tests + 9 deleted tests (the no-op stub
   tests and the ASGI canary tests) = +7 net.

**Out of scope** (deferred):

- Adding new MCP tools (Phase 7 or later — the 7 are sufficient).
- Replacing the FastMCP server with Mahavishnu's MCP infrastructure.
- CLI subcommand `fastblocks mcp discover` (Python helper suffices).
- Per-tool runtime cost optimization (deferred to Phase 6).

## Why library-aware opt-in, not full opt-in

The original spec's one-line reversal ("Phase 4 opts back in for
cross-component consistency") overrode CLAUDE.md:155-190 without weighing
the rationale. CLAUDE.md documents:

> FastBlocks is a **library**, not a standalone production MCP server.
> The 7 tools are embedded in a consumer app's MCP (SplashStand).
> Production servers that need profile-based dispatch live in the
> consumer.

Library-aware opt-in preserves this by exposing the capability
**metadata** as a public contract consumers wire themselves. Consumers
retain profile choice; fastblocks provides the registration functions.
The fastblocks-internal `FastBlocksMCPServer` (used when consumers
don't bring their own MCP) wires the same primitives — so the
internal server does the right thing without overriding the library
posture.

## Architecture

Three layers, library-aware.

### Layer 1 — `fastblocks/mcp/capabilities.py` (NEW, source of truth)

```python
"""FastBlocks MCP tool capability metadata (Phase 4 v2 source of truth).

Public API: consumers (e.g. SplashStand) import these constants and
functions and pass them to their own ``mcp_common.tools.apply_tool_profile``
calls. fastblocks-internal ``FastBlocksMCPServer`` consumes the same
primitives via ``_apply_tool_profile_async``.

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
# Phase 1.5 facade is the entry point; observability counters fire here.
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

    Probes via the Phase 1.5 facade (not lazy construction) — P1 #7 fix.
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


# Per-tool → per-capability-callable map. Used by mcp_common's
# ``registration_map`` parameter when consumer wants fine-grained
# tool-by-tool registration (alternative to the callable-list pattern).
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


def _oneiric_yaml_loader() -> dict | None:
    """Read ``tool_profile`` from Oneiric's layered config (P1 #9 fix).

    Returns ``None`` if Oneiric settings are unavailable or
    ``tool_profile`` is unset. Used as ``yaml_loader=`` kwarg on
    ``_apply_tool_profile_async`` so operators can set profile in
    ``settings/local.yaml`` instead of an env var.
    """
    try:
        from fastblocks.core.config import get_settings
        settings = get_settings()
        profile = getattr(settings, "tool_profile", None)
        if profile is None:
            return None
        return {"tool_profile": profile}
    except Exception:
        return None
```

Layer 1 imports `fastblocks.mcp.tools` only inside function bodies
(under `TYPE_CHECKING` for type hints) — keeps import-time surface
clean and lets tests stub individual modules.

### Layer 2 — `fastblocks/mcp/discovery.py` (NEW, custom discovery_fn)

```python
"""FastBlocks-specific discovery_fn for ``apply_tool_profile``.

Override of mcp_common's ``_default_discovery`` to add the
``capability`` and ``is_available`` fields consumers need (P0 #3 fix).
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .capabilities import get_registration_map, get_tool_capability


async def fastblocks_discovery(
    server: FastMCP, filter_query: str | None
) -> list[dict]:
    """Emit {name, capability, is_available, description, inputSchema}.

    Walks the server's registered tools and looks up each name in
    ``get_tool_capability()``. Tools whose registration function's gate
    returned False are NOT in ``server.list_tools()`` — they get
    ``is_available: False`` only when explicitly registered but later
    hidden via a future mechanism (Phase 6+ work).
    """
    tools = await server.list_tools()
    registration_map = get_registration_map()
    result: list[dict] = []
    for t in tools:
        capability = get_tool_capability(t.name)
        # ``is_available`` is True iff the tool is currently registered.
        # (Gate failures skip registration entirely, so absence = False.)
        result.append(
            {
                "name": t.name,
                "capability": capability,
                "is_available": capability is not None,
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
    # Reference registration_map to satisfy the unused-import lint
    # (kept for consumers who want fine-grained registration).
    _ = registration_map
    return result
```

### Layer 3 — `fastblocks/mcp/server.py` (MODIFIED)

Replace `FastBlocksMCPServer._register_tools` body. The async path
(P0 #1 fix: use `_apply_tool_profile_async`, NOT `await
apply_tool_profile`). Removal of `_get_http_app`/`get_http_app`/
`_http_app_cache`/`http_app = None`.

```python
async def _register_tools(self) -> None:
    """Register FastBlocks MCP tools via apply_tool_profile (Phase 4 v2)."""
    from mcp_common.tools import ToolProfile
    from mcp_common.tools.dispatch import _apply_tool_profile_async
    from .capabilities import (
        ALL_CAPABILITIES,
        MANDATORY_CAPABILITIES,
        TEMPLATE_CAPABILITY,
        _oneiric_yaml_loader,
        register_adapter_capability,
        register_component_capability,
        register_template_capability,
    )
    from .discovery import fastblocks_discovery

    await _apply_tool_profile_async(
        self._server,
        profile=ToolProfile.FULL,  # resolved from env → yaml → FULL by mcp_common
        registrations={
            ToolProfile.MINIMAL:  [],
            ToolProfile.STANDARD: [register_template_capability],
            ToolProfile.FULL:     [
                register_template_capability,
                register_component_capability,
                register_adapter_capability,
            ],
        },
        registration_map={},  # Using callable-list pattern (P0 #2 fix); no string names
        register_all_fn=None,
        mandatory_groups=set(MANDATORY_CAPABILITIES),
        essential_tool_names=set(),
        discovery_fn=fastblocks_discovery,
        profile_env_var="FASTBLOCKS_TOOL_PROFILE",
    )
```

`_apply_tool_profile_async` is called via its direct signature — but
note that the env-var → yaml → FULL resolution happens inside
`_resolve_profile()` which is called inside `_apply_tool_profile_async`.
We pass `profile=ToolProfile.FULL` as a placeholder; the helper
re-resolves via `_resolve_profile(profile_env_var, yaml_loader)` once it
has the env var name. **Final design decision**: pass `yaml_loader=_oneiric_yaml_loader`
so the layered config works.

The `ToolProfile` parameter to `_apply_tool_profile_async` is then
overridden by the internal `_resolve_profile` call. The kwarg exists
for unit tests that bypass env-var resolution.

### Deletions

| File / line | Removed |
|---|---|
| `fastblocks/mcp/server.py:141-170` | `_get_http_app` |
| `fastblocks/mcp/server.py:175-190` | `_http_app_cache`, `get_http_app` |
| `fastblocks/mcp/server.py:195` | `http_app = None` |
| `fastblocks/mcp/profiles.py` (entire file) | All 197 lines |
| `tests/mcp/test_server_canary.py` lines 50, 59, 81 | 3 tests for `_get_http_app` |
| `tests/mcp/test_tool_profile.py` lines 41, 159, 174, 178, 200, 228-230 | 6 tests for the no-op stub |

No external consumers of `_get_http_app` / `apply_fastblocks_tool_profile`
exist (verified via `grep -rn` across `/Users/les/Projects` excluding
the fastblocks repo).

## Data flow

### Scenario A — Default startup (`FASTBLOCKS_TOOL_PROFILE` unset → FULL)

```
mahavishnu_mcp_server starts
    │
    ▼
FastBlocksMCPServer.initialize()
    │
    ▼
self._register_tools()
    │
    ▼
_apply_tool_profile_async(server, profile_env_var="FASTBLOCKS_TOOL_PROFILE", ...)
    │
    ▼
mcp_common reads env: var not set → yaml_loader() → None → defaults to FULL
    │
    ▼
For each capability in [register_template_capability,
                       register_component_capability,
                       register_adapter_capability]:
    await _maybe_await(capability_fn(server))
        │
        ▼
    _is_X_available()? → True (Jinja2 + Oneiric present, htmy_components importable)
        │
        ▼
    server.tool(name, description=trim_description(...))(fn)
    │
    ▼
fastblocks_discovery() registered as discover_tools
    │
    ▼
7 + 1 = 8 MCP tools exposed
```

### Scenario B — Operator sets `FASTBLOCKS_TOOL_PROFILE=standard`

```
env: FASTBLOCKS_TOOL_PROFILE=standard
    │
    ▼
_apply_tool_profile_async resolves profile=STANDARD
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
discover_tools registered (always, by mcp_common contract)
    │
    ▼
4 MCP tools exposed (3 + discover_tools)
discover_tools handler returns 4 entries with capability metadata
```

### Scenario C — Operator uses YAML (`settings/local.yaml`)

```yaml
tool_profile: standard
```

```
yaml_loader() returns {"tool_profile": "standard"}
    │
    ▼
profile resolved to STANDARD (env unset, yaml wins)
    │
    ▼
Same as Scenario B from here
```

### Scenario D — Per-tool gate returns False (degraded dependency)

```
register_adapter_capability(server) called
    │
    ▼
_is_adapter_available() returns False (e.g., Oneiric bootstrap not run
— list_active("fastblocks") returns [])
    │
    ▼
Registration skipped silently (NOT a raise) — mcp_common contract
    │
    ▼
list_adapters, check_adapter_health NOT in server's tool list
    │
    ▼
discover_tools handler (our fastblocks_discovery override) returns the
REGISTERED tool list only
```

### Scenario E — Consumer (SplashStand) wires its own profile

```python
# In SplashStand's MCP server module
from fastblocks.mcp.capabilities import (
    TEMPLATE_CAPABILITY,
    register_template_capability,
    register_component_capability,
    register_adapter_capability,
)
from mcp_common.tools import ToolProfile, apply_tool_profile

await apply_tool_profile(
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
    registration_map={},
    register_all_fn=None,
    mandatory_groups=set(),
    essential_tool_names=set(),
    discovery_fn=None,  # use mcp_common default or SplashStand's own
    yaml_loader=None,
)
```

SplashStand uses fastblocks' capability functions as a library; the
profile choice remains SplashStand's.

## Failure modes

| Failure | Behavior |
|---|---|
| `apply_tool_profile` raises `ValueError` (MANDATORY tool missing) | Loud startup error with missing tool name |
| Profile env var set to invalid value | `mcp_common.tools.InvalidProfileError` raised at startup |
| Gate returns False | Registration skipped silently for that capability; `discover_tools` reports `is_available: false` (or omits the tool entirely) |
| `trim_description` returns empty (docstring missing) | Tool registered with empty description; no crash |
| Duplicate tool name across capabilities | Caught at module load (capability tuples are mutually exclusive by construction) |
| `_is_adapter_available()` raises unexpectedly | Caught by broad `except Exception: return False` — degraded mode, not a crash |
| `_get_http_app` no longer importable | SplashStand and any consumer that imported it directly will see `ImportError`; verified no consumer does |

## Test surface

| File | New tests | Markers | Purpose |
|---|---|---|---|
| `tests/mcp/test_capabilities.py` | 4 | `@pytest.mark.unit` | Each capability list non-empty; mutually exclusive (no overlap); full coverage (7 tools total); `get_registration_map()` matches capability tuples; `get_tool_capability()` returns expected tags |
| `tests/mcp/test_per_tool_dependency_gates.py` | 4 | `@pytest.mark.unit` | Each `_is_X_available()` returns `bool`; mock Jinja2 missing → template gate False; mock Oneiric broken (no active candidates) → adapter gate False; gates don't raise on any input |
| `tests/mcp/test_apply_tool_profile_integration.py` | 5 | `@pytest.mark.unit` | MINIMAL=0 fastblocks tools (just discover_tools); STANDARD=3 template; FULL=7; capability-callable dispatch (not string names); `discover_tools` registered in all profiles |
| `tests/mcp/test_discover_tools_handler.py` | 3 | `@pytest.mark.unit` | `fastblocks_discovery(query=None)` returns full list with `{name, capability, is_available, description, inputSchema}`; `query="template"` filters to 3 TEMPLATE tools; query="adapter" returns 2 ADAPTER tools |
| `tests/mcp/test_yaml_loader_profile_resolution.py` | 2 | `@pytest.mark.unit` | env wins over yaml; yaml wins over default; both unset → FULL; `_oneiric_yaml_loader()` returns `None` when Oneiric settings unavailable |
| `tests/mcp/test_server_wiring.py` | 3 | `@pytest.mark.unit` | `FastBlocksMCPServer._register_tools` invokes `_apply_tool_profile_async`; profile from env var; MANDATORY_CAPABILITIES empty passes essential_tool_names check |

**Total: 21 new tests.** Plus 9 deleted tests (-3 server_canary, -6 tool_profile) = +12 net. The 16-test estimate in the original spec grew to 21 because the custom discovery_fn override needs its own dedicated test file, and yaml_loader profile resolution needs explicit coverage.

### Canary validation

| Canary | Action | Expected failure |
|---|---|---|
| Profile gating | Revert STANDARD profile to MINIMAL-only | `test_apply_tool_profile_integration.py::test_standard_registers_template_capability` fails — TEMPLATE tools not registered |
| Capability gate | Revert `_is_template_available()` to `return False` | `test_apply_tool_profile_integration.py::test_full_registers_all` fails — TEMPLATE tools not registered |
| Custom discovery | Stub `fastblocks_discovery` to omit `capability` field | `test_discover_tools_handler.py::test_full_schema` fails |
| YAML loader | Stub `_oneiric_yaml_loader` to return invalid value | `test_yaml_loader_profile_resolution.py` fails |
| Wires async correctly | Change `_apply_tool_profile_async` to sync `apply_tool_profile` | `test_server_wiring.py::test_uses_async_sibling` fails |

## Verification gate

- All 21 new tests pass
- All 50 Phase 2 tests still pass (no regression)
- All 18 Phase 2.5 tests still pass (no regression)
- ty ratchet prod 0/50 PASS (no new suppressions)
- `suppress(Exception)` ratchet at ≤ 122 (no new sites; we delete `_get_http_app`'s `with suppress(Exception)` site at server.py:157)
- Manual smoke: `FASTBLOCKS_TOOL_PROFILE=standard python -m fastblocks.mcp` → 4 tools exposed
- Manual smoke: `python -c "from fastblocks.mcp.capabilities import ALL_CAPABILITIES; assert len(ALL_CAPABILITIES) == 7"` succeeds
- Manual smoke: consumer pattern (SplashStand-style) imports succeed

## Per-task Integration Contracts

Four commits, additive-then-deletive.

### Commit 1 — `feat(mcp): capabilities.py + custom discovery_fn override`

- *Triggered from:* ADR 0011 Decisions 2-12 (the deferred original spec); master plan §Pillar 4
- *Returns to / updates:* NEW `fastblocks/mcp/capabilities.py`; NEW `fastblocks/mcp/discovery.py`; 11 new tests in `tests/mcp/test_capabilities.py` (4) + `tests/mcp/test_per_tool_dependency_gates.py` (4) + `tests/mcp/test_discover_tools_handler.py` (3)
- *Demonstrable by:* `python -c "from fastblocks.mcp.capabilities import ALL_CAPABILITIES; assert len(ALL_CAPABILITIES) == 7"` succeeds; 11 tests pass
- *Rollback signal:* `git revert`; pure addition, no behavior change
- *Observability added:* None — pure data + pure-function gates

### Commit 2 — `refactor(mcp): server._register_tools wires _apply_tool_profile_async`

- *Triggered from:* Commit 1 supplies the capability definitions; mcp_common supplies the orchestrator
- *Returns to / updates:* `fastblocks/mcp/server.py` — replace `_register_tools` body to call `_apply_tool_profile_async` with the new capability callables and `discovery_fn=fastblocks_discovery`. 5 new wiring tests in `tests/mcp/test_apply_tool_profile_integration.py` (3) + `tests/mcp/test_yaml_loader_profile_resolution.py` (2) + `tests/mcp/test_server_wiring.py` (3)
- *Demonstrable by:* `tests/mcp/test_apply_tool_profile_integration.py` 3/3 pass; `tests/mcp/test_yaml_loader_profile_resolution.py` 2/2 pass; `tests/mcp/test_server_wiring.py` 3/3 pass; the 7 tools are registered under the right profile; `discover_tools` handler returns capability-tagged responses
- *Rollback signal:* `git revert`; manual `register_fastblocks_tools` body restored as a fallback
- *Observability added:* mcp_common's structured logs (profile + count of tools registered); `fastblocks_discovery` emits `capability` and `is_available` fields in `discover_tools` responses

### Commit 3 — `chore(mcp): delete _get_http_app + opt-out stub + related tests`

- *Triggered from:* Commits 1-2 make the deletion safe (capability metadata + wiring replace both stubs); user choice (asked + answered "Delete _get_http_app")
- *Returns to / updates:* `fastblocks/mcp/server.py` — remove `_get_http_app`, `get_http_app`, `_http_app_cache`, `http_app = None`; `fastblocks/mcp/profiles.py` — delete entire file; `tests/mcp/test_server_canary.py` — remove 3 `_get_http_app` tests; `tests/mcp/test_tool_profile.py` — remove all 6 tests
- *Demonstrable by:* `from fastblocks.mcp.server import _get_http_app` raises `ImportError`; `from fastblocks.mcp.profiles import apply_fastblocks_tool_profile` raises `ImportError`; full sweep passes (2225 + 21 - 9 = 2237 tests)
- *Rollback signal:* `git revert`; both stubs restored
- *Observability added:* None (deletions only); `suppress(Exception)` ratchet improves by 1 (server.py:157's `with suppress(Exception)` block is gone)

### Commit 4 — `docs(adr): ADR 0012 Phase 4 v2 library-aware opt-in closeout`

- *Triggered from:* This spec
- *Returns to / updates:* `docs/adr/0012-phase-4-library-aware-opt-in.md` (NEW)
- *Demonstrable by:* `find docs/adr -name "0012-*.md"` returns the new file
- *Rollback signal:* `git revert`; doc-only
- *Observability added:* None

## Out of scope (deferred)

- New MCP tools (Phase 7 or later)
- Replacing FastMCP with Mahavishnu's MCP infrastructure
- CLI `fastblocks mcp discover` subcommand
- Per-tool runtime cost optimization (Phase 6 observability)
- Oneiric config integration for `_oneiric_yaml_loader` beyond the basic `getattr(settings, "tool_profile", None)` probe — Phase 6+ work

## Cross-references

- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md` §Pillar 4 (line 89), §Phase 4 (line 339)
- ADR 0011 (Phase 4 deferral): `docs/adr/0011-phase-4-deferral.md` — the 5 P0 blockers + 7 P1 issues this spec addresses
- Original spec (superseded): `docs/superpowers/specs/2026-08-22-fastblocks-phase-4-design.md` (commit `85f22e6`)
- CLAUDE.md:155-190 — library boundary rationale (preserved by this design)
- mcp_common dispatch: `/Users/les/Projects/mcp-common/mcp_common/tools/dispatch.py:150` (async sibling), `:253` (sync wrapper), `:52-84` (env → yaml → FULL resolver)
- mcp_common profiles: `/Users/les/Projects/mcp-common/mcp_common/tools/profiles.py` (ToolProfile StrEnum)
- mcp_common descriptions: `/Users/les/Projects/mcp-common/mcp_common/tools/descriptions.py` (`trim_description`)
- FastBlocksMCPServer current state: `fastblocks/mcp/server.py:33-67` (initialize), `:74-82` (current _register_tools), `:141-170` (orphaned _get_http_app, to be deleted)
- Oneiric resolver: `fastblocks/core/resolver.py:138-141` (lazy init), `:144-162` (`FastblocksRegistry` facade)
- Phase 1.5x Card 1: `register_candidate_strict` foundation
- Phase 2 spec: `docs/superpowers/specs/2026-08-21-fastblocks-phase-2-design.md` (Literal types + Protocol gates; this spec reuses the same architectural pattern of "single source of truth + thin consumers")

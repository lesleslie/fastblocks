______________________________________________________________________

## status: accepted role: phase-4-deferral date: 2026-08-22 last_reviewed: 2026-08-22 supersedes: null superseded_by: null blocks_on: [] decision_date: 2026-08-22 topic: phase-4-mcp-tool-surface-organization-deferral

# ADR 0011: Phase 4 MCP Tool Surface Organization Deferral

## Status

Accepted (Phase 4 deferral — companion to master plan §Phase 4 row line 339).

## Context

Phase 4 ("Tag the 7 tools by capability; add `discover_tools` Python
helper; behavioral resolution gates") was the next phase per the master
plan. The spec was designed
(`docs/superpowers/specs/2026-08-22-fastblocks-phase-4-design.md`,
commit `85f22e6`) and then reviewed by 5 subagents in parallel
(mcp-integration-expert, python-pro, oneiric-specialist,
fastblocks-specialist, critical-audit-specialist). The review surfaced
5 P0 blockers that would prevent implementation from succeeding and a
set of P1/P2 issues that would compound across the commit series. This
ADR records the deferral decisions and the rationale.

## Decisions

### Decision 1: Phase 4 deferred

Phase 4 scope resolves to **nothing shipped** based on the 5 P0 blockers
listed below. The spec remains in git history as the rationale for the
deferral — the work that would need to happen before any implementation
can succeed is recorded in Decisions 2-6.

### Decision 2 — P0: Use `_apply_tool_profile_async` (not `apply_tool_profile`)

`mcp_common.tools.apply_tool_profile` (dispatch.py:253) is a **sync**
function. Its tail checks for a running event loop and raises
`RuntimeError` if one exists. Calling it via `await apply_tool_profile(...)`
from the async `FastBlocksMCPServer.initialize()` would either return
`None` (making `await` raise `TypeError: object NoneType can't be used in 'await' expression`) or raise `RuntimeError`. Either way, the MCP
server fails to initialize.

The fix: use the async sibling `_apply_tool_profile_async` (dispatch.py:337).
The original spec wrote `await apply_tool_profile(...)` — wrong.

### Decision 3 — P0: `registrations` dict must hold CALLABLES, not tool-name strings

`apply_tool_profile` iterates the `registrations` list **once per element**
and resolves strings through `registration_map`. With:

```python
registrations={
    ToolProfile.STANDARD: MANDATORY_CAPABILITIES + TEMPLATE_CAPABILITY,
    ToolProfile.FULL:     ALL_CAPABILITIES,
}
_REGISTRATION_MAP = {"validate_template": register_template_capability, ...}
```

Under STANDARD profile, the loop calls `register_template_capability(server)`
**3 times** (once per tool name in `TEMPLATE_CAPABILITY`). Each call invokes
`server.tool(...)` for all 3 tools in the capability → **9 `server.tool()`
calls with overlapping names**. FastMCP's response to duplicate names is
undefined (likely `ValueError` or shadowed registrations).

The fix: `registrations` must hold **capability-level callables**, not
per-tool strings:

```python
registrations={
    ToolProfile.MINIMAL:  [],
    ToolProfile.STANDARD: [register_template_capability],
    ToolProfile.FULL:     [
        register_template_capability,
        register_component_capability,
        register_adapter_capability,
    ],
}
```

Keep the `TEMPLATE_CAPABILITY` tuple as metadata for the discovery/manifest
side, but stop passing it as the dispatch list.

### Decision 4 — P0: `discover_tools` response schema is fixed by mcp_common

The spec invented a response shape:
`{name, capability, is_available, description}`. The actual
`_default_discovery` (dispatch.py:93-116) returns:
`{name, description, inputSchema, group: None}`. The fields `capability`
and `is_available` are NOT in the schema. Tools that were skipped by a
gate are not in `server.list_tools()` at all — `discover_tools` cannot
report `is_available: false` for them.

The spec's `test_discover_tools_handler.py::test 3` ("unavailable tool has
`is_available: false`") is impossible without an mcp_common change.
Future Phase 4 work must either: (a) live within the mcp_common schema,
(b) provide a custom `discovery_fn` parameter to `apply_tool_profile`
that emits the fastblocks-specific schema, or (c) wait for an
mcp_common enhancement that supports capability + is_available fields.

### Decision 5 — P0: Library/consumer boundary (CLAUDE.md:155-190)

CLAUDE.md lines 155-190 explicitly say "FastBlocks is a **library**, not
a standalone production MCP server" with a load-bearing three-part
justification:

1. The 7 tools are embedded in a consumer app's MCP (SplashStand).
1. Production servers that need profile-based dispatch live in the
   consumer.
1. `apply_fastblocks_tool_profile` is a deliberate no-op stub with a
   regression test (`tests/mcp/test_tool_profile.py`) pinning the opt-out.

The spec's one-line reversal ("Phase 4 opts back in for cross-component
consistency") does not weigh this rationale. The spec also does not name
SplashStand as the affected consumer or describe what its MCP server
must do if fastblocks opts in.

Future Phase 4 work must address the library boundary explicitly: either
(a) document why the boundary no longer applies (e.g., fastblocks is
now embedded directly in a Starlette app rather than as a library),
(b) preserve the boundary by having fastblocks EXPOSE the capability
metadata for consumer apps to wire into their own `apply_tool_profile`
call, or (c) update CLAUDE.md:155-190 if the library-not-server posture
has actually changed.

### Decision 6 — P0: `_get_http_app` sync uvicorn path orphaned

`server.py:141-170` (`_get_http_app`) is the path uvicorn calls at startup.
It creates a `FastMCP` instance and runs `loop.run_until_complete(register_fastblocks_tools(mcp_instance))`
on it (line 163). The spec only updates the async `initialize()` path.
After Phase 4, ASGI deployments silently register 7 tools via legacy
path (no `discover_tools`, no `trim_description`, no profile gating)
while inline `initialize()` deployments register 8 tools with all the
new wiring. The two paths diverge silently.

The fix: either migrate `_get_http_app` to use the new wiring (with the
same `_apply_tool_profile_async` call from Decision 2) or explicitly
exclude ASGI from Phase 4 scope with a tracking issue.

### Decision 7 — P1: `_is_adapter_available()` is self-fulfilling

The spec writes:

```python
def _is_adapter_available() -> bool:
    try:
        from fastblocks.core.resolver import get_resolver
        get_resolver()
        return True
    except Exception:
        return False
```

`get_resolver()` is lazy — its only real effect is `if _resolver is None: _resolver = Resolver()`.
If any code path reaches this gate before Oneiric's bootstrap runs, the
gate doesn't fail; it LAZILY CONSTRUCTS an empty `Resolver`, returns True,
and registers `list_adapters` / `check_adapter_health`. After that, the
MCP server exposes adapter tools that will resolve to `None` at call time.

The fix: probe resolved state instead of construction. Probe a known
core domain (`resolver.list_active("fastblocks")` returns non-empty) or
add an explicit `_oneiric_bootstrapped` flag flipped in app startup
that all 7 tools consume. Per oneiric-specialist finding F1.

### Decision 8 — P1: Gate must route through Phase 1.5 facade

The spec's gate calls raw `get_resolver()`, bypassing the Phase 1.5
`FastblocksRegistry` facade. Phase 1.5 deliberately moved consumers
off `get_resolver()` and onto `FastblocksRegistry(get_resolver())` —
the facade is where observability counters (`registry_size`) fire.

The fix: route the gate through the facade:

```python
def _is_adapter_available() -> bool:
    try:
        from fastblocks.core.resolver import get_resolver, FastblocksRegistry
        return FastblocksRegistry(get_resolver()) is not None
    except Exception:
        return False
```

### Decision 9 — P1: `yaml_loader=` not wired (Oneiric layered config)

The spec hard-codes env-var-only profile resolution. mcp_common's
`_resolve_profile` supports a fallback chain: env var → `yaml_loader()`
→ FULL default. FastBlocks already uses Oneiric layered config
(per Phase 1.5), so operators reading `settings/local.yaml` for
`tool_profile: standard` would get no effect — only the env var works.

The fix: pass a `yaml_loader` callable that reads `tool_profile` from
Oneiric's settings chain.

### Decision 10 — P1: `apply_tool_profile` signature mismatch

The spec lists required kwargs (`profile_env_var, registrations, registration_map, register_all_fn, mandatory_groups`) but the call
site omits `register_all_fn` and `mandatory_groups`. Either those are
required (the call site must provide them) or optional (the API
description is wrong).

The fix: read `mcp_common/tools/dispatch.py:253` and pin the actual
signature; reconcile the call site.

### Decision 11 — P1: Spec coverage of `register_fastblocks_tools`

The spec keeps `register_fastblocks_tools` (tools.py:562-610) as a thin
pass-through wrapper after Phase 4. The only callers are the (replaced)
async `initialize()` and the (orphaned) `_get_http_app`. After Phase 4,
the wrapper has no first-party callers — it's the "built but not wired"
anti-pattern.

Future Phase 4 work must either (a) move `register_fastblocks_tools` to
`server.py` and update both call sites, (b) delete it after migrating
the two callers and add a deprecation alias in `__init__.py` for any
out-of-tree consumer, or (c) explicitly document the second caller
(`_get_http_app`) as in-scope for Phase 4 and migrate it.

### Decision 12 — P1: `profiles.py` no-op stub silently invalidated

`fastblocks/mcp/profiles.py` exposes `apply_fastblocks_tool_profile`
(line 142), `FASTBLOCKS_TOOLS` (line 113), `PROFILE_REGISTRATIONS`
(line 135). CLAUDE.md:181 says `tests/mcp/test_tool_profile.py` "pins
all three invariants" of the opt-out. Phase 4 opts back in, which makes
all three invariants false. The spec does not include a Commit for
deleting/rewriting the stub or updating the pinning test.

Future Phase 4 work must either (a) delete `profiles.py` outright, (b)
keep `apply_fastblocks_tool_profile` as a thin wrapper around
`apply_tool_profile`, or (c) document the stub's new role (e.g.,
"DEPRECATED: prefer `apply_tool_profile` from mcp_common directly").

### Decision 13 — Phase 4 scope = nothing shipped (this ADR)

The original directive ("ship Phase 4") resolves to **no code shipped**
based on Decisions 2-6 (the 5 P0 blockers). Phase 4 work that remains
is documentation-only — this ADR records the blockers for future
maintainers. The spec at `docs/superpowers/specs/2026-08-22-fastblocks-phase-4-design.md`
remains in git history as the pre-deferral design attempt; future
maintainers can use it as a starting point after addressing the P0s.

## Known Issues (parked, deferred to future Phase 4 attempt)

The following P2/P3 issues from the review are recorded but not blocking:

- Dead `TYPE_CHECKING` block in capabilities.py example (python-pro F1)
- `except Exception` asymmetry in `_is_adapter_available` (python-pro F1)
- Function-body imports unsorted (python-pro F2)
- `MANDATORY_CAPABILITIES` naming as capabilities vs tool names (python-pro F2)
- Empty `MANDATORY_CAPABILITIES` should log warning (oneiric F4)
- `trim_description` calls per startup (mcp-integration P2)
- Test file naming (`test_apply_tool_profile_integration.py` vs `test_apply_tool_profile.py`)
- Uniqueness assertion not in capabilities.py code block (fastblocks-specialist Minor)
- `trim_description` asserts length but not summary line (fastblocks-specialist Minor)
- `register_fastblocks_tools` body delegating to capabilities.py is anti-pattern (per-feature-delivery-lifecycle workflow)

These are recorded for the next attempt's pre-flight review.

## Cross-references

- Spec: `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-08-22-fastblocks-phase-4-design.md`
- Master plan: `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md` §Phase 4 (line 339)
- Phase 4 deferred-items plan: `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-22-fastblocks-phase-2-5.md` (Phase 2.5 plan, which still ships)
- ADR 0010 Phase 2 finish deferrals: `/Users/les/Projects/fastblocks/docs/adr/0010-phase-2-mechanical-four.md` (precedent — same pattern)
- CLAUDE.md:155-190 — library-not-server posture (load-bearing rationale)
- mcp_common dispatch: `/Users/les/Projects/mcp-common/mcp_common/tools/dispatch.py:253` (sync `apply_tool_profile`), `:337` (async sibling), `:93-116` (`_default_discovery`)
- FastBlocksMCPServer: `/Users/les/Projects/fastblocks/fastblocks/mcp/server.py:74-82` (async path), `:141-170` (`_get_http_app` sync path)
- Oneiric resolver: `/Users/les/Projects/fastblocks/fastblocks/core/resolver.py:138-141` (lazy init)
- Phase 1.5 facade: `/Users/les/Projects/fastblocks/fastblocks/core/resolver.py:144-162` (`FastblocksRegistry` constructor)

# FastBlocks MCP Tool-Profile Rationale

**Status:** OPTED OUT (deliberate) — see the decision matrix below.
**Date:** 2026-08-19 (W4.9)
**Owner:** FastBlocks framework maintainers

## TL;DR

FastBlocks is a **public framework library**, not a standalone production MCP
server. The seven read-only introspection tools it exposes (`list_adapters`,
`list_templates`, `validate_template`, `render_template`, `list_components`,
`validate_component`, `check_adapter_health`) are catalog/inspection helpers
designed to be embedded in a **consumer application's** MCP surface
(e.g. SplashStand). Production servers — the ones that genuinely need the
`mcp_common` `MINIMAL` / `STANDARD` / `FULL` tool-profile system to control
capability exposure — live in the consumer app, not here.

For that reason, the framework ships a **no-op stub** at
`fastblocks/mcp/profiles.py` and deliberately does **not** wire its seven
tools through `mcp_common.tools.apply_tool_profile()`. Consumers that want
profile-based dispatch use their own MCP server (e.g. the SplashStand MCP
server, which adopts the full `mcp_common` profile system in W4.10).

## Why this is the right call

### 1. FastBlocks is a library, not a service

`CLAUDE.md` (root) is explicit:

> FastBlocks is an asynchronous web framework built on Starlette, designed
> for server-side-rendered HTMX/Jinja template blocks. It is **public,
> framework-level software** — it is not an end-user product. Production
> deployments are expected to live in consumer applications (e.g.
> SplashStand) that import FastBlocks as a library.

A library's MCP surface is a *capability it makes available*, not a
*production server* that needs runtime capability gating. The seven tools
do not grant anyone the ability to do anything they could not do by
calling the underlying Python API directly. There is no security boundary
that profile-gating would meaningfully tighten.

### 2. The MCP surface is read-only introspection

Per the same `CLAUDE.md`:

> MCP is **read-only for framework introspection** (7 tools: `list_adapters`,
> `list_templates`, `validate_template`, `render_template`,
> `list_components`, `validate_component`, `check_adapter_health`).
> Product operations (WebSocket lifecycle, adapter configuration, site
> buildout) belong in consumer projects such as SplashStand.

The dangerous tools (`fastblocks_create_template`, `fastblocks_create_component`,
`fastblocks_configure_adapter`, `fastblocks_start_websocket`, etc.) were
**already removed** in the 0.8.0 MCP-surface cutover (Phase 0b). The
`tests/mcp/test_ci_guard.py` test fails the build if any of the deleted
symbol names resurface. What remains is harmless introspection.

A `MINIMAL` profile that hides `list_templates` from a model doesn't
provide security: the model can still `from fastblocks.mcp.tools import
list_templates` and call it as a Python function. Profile-gating only
matters when you can credibly claim that a profile is a security
boundary, and for a library exposing read-only helpers over stdio, it
is not.

### 3. The consumer app is the right place for profile dispatch

SplashStand (a fastblocks consumer) ships its own MCP server. That
server is the production control plane for splashstand customers. It
needs the full `mcp_common` profile system: `MINIMAL` for read-only
operator probes, `STANDARD` for everyday customer ops, `FULL` for
admins. SplashStand's W4.10 adoption is where profile-based dispatch
belongs.

Inheriting FastBlocks' opt-out into SplashStand would be wrong:
SplashStand has mutating tools, customer data, and an attack surface
worth gating. Inheriting FastBlocks' opt-out would skip profile
gating that SplashStand's server *does* need.

### 4. The cost of adopting the full pattern is high

| Migration step | Cost | Benefit |
|----------------|------|---------|
| `mcp-common~=0.3` → `mcp-common~=0.18` | High — 15 minor versions of API churn, several breaking renames (`apply_tool_profile` shape, `ToolProfile` enum values, `PROFILE_REGISTRATIONS` contract, etc.) | None — the seven tools are unchanged |
| `mcp` SDK 1.x → 2.x (or 3.x) | High — `from mcp.server.fastmcp import FastMCP` is the 1.x direct import; 2.x renames the class to `MCPServer` and changes the registration API | None — the seven tools are still decorated with the same `register(name)(fn)` pattern |
| Wire `_apply_tool_profile` into `FastBlocksMCPServer.initialize` | Medium — would need a profile selector, a `MAHAVISHNU_TOOL_PROFILE` env var, and dispatch logic | None — every profile would resolve to the same seven tools anyway |

The benefit column is "None" because, for a read-only library, every
profile is identical. The only outcome of doing the work is a
moderately-stricter API contract that adds no security and no
functionality.

### 5. The mcp-common 0.3 surface is incomplete anyway

`mcp-common~=0.3` exposes `ToolProfile` (with `MINIMAL`, `STANDARD`,
`FULL` enum values) and `MANDATORY_TOOLS` (a set of tool names that
must be present in every profile). It does **not** expose:

- `ALL_TOOLS` (a 0.18+ convenience constant for "all tools I have")
- `apply_tool_profile()` (the 0.18+ dispatch helper)

Adopting the full pattern today would require a custom dispatch
function on top of the 0.3 surface anyway. The work would have to be
re-done when 0.18+ becomes the baseline. Better to wait.

## What this means in practice

### The stub

`fastblocks/mcp/profiles.py` exposes three names:

- `FASTBLOCKS_TOOLS`: a tuple of the seven tool names, in registration
  order. Self-documenting and importable by tests.
- `PROFILE_REGISTRATIONS`: a `{ToolProfile.MINIMAL: ALL, STANDARD: ALL,
  FULL: ALL}` mapping. Every profile maps to the full set. This is the
  "opt out of profile-based dispatch" form: nothing is filtered
  regardless of profile.
- `apply_fastblocks_tool_profile(server, profile=ToolProfile.FULL)`:
  a no-op function that accepts a server and a profile, emits a
  one-time deprecation log, and returns `None`. The signature mirrors
  `mcp_common.tools.apply_tool_profile()` so the migration path is a
  drop-in change once `mcp-common~=0.18` is adopted.

### The regression test

`tests/mcp/test_tool_profile.py` verifies:

1. The stub module imports cleanly.
2. `apply_fastblocks_tool_profile(server)` is a no-op: the server is
   not mutated, no methods are called, no exception is raised.
3. The `PROFILE_REGISTRATIONS` mapping covers all three `ToolProfile`
   values and that every value is the full tool set (the "opt out"
   invariant).
4. The deprecation log fires exactly once per process, even on
   repeated calls.

### The CLAUDE.md note

`CLAUDE.md` (root) gains a "Tool Profile System" subsection marked as
opted out, with a pointer to this document.

## Decision matrix

If any of the following changes, re-evaluate this decision:

| Trigger | Re-evaluation |
|---------|---------------|
| FastBlocks starts shipping **mutating** MCP tools (e.g. config CLI via MCP) | **Adopt the full pattern.** The MCP surface is no longer read-only. |
| FastBlocks starts shipping its own **production** MCP server (not a library helper) | **Adopt the full pattern.** A production server needs profile gating. |
| `mcp-common` ≥ 0.18 becomes available AND the upgrade is on the roadmap anyway | **Adopt opportunistically.** Migrate as part of the broader upgrade. |
| A consumer app needs the framework's tools to be **gated by profile** within the consumer's MCP server | **Re-evaluate.** The consumer can import `apply_fastblocks_tool_profile` today (it's a no-op) and replace it with the real call once 0.18+ is available. The stub is the bridge. |

## What this does NOT do

- It does **not** wire `mcp_common.tools.apply_tool_profile` into
  `FastBlocksMCPServer.initialize()`.
- It does **not** introduce a `MAHAVISHNU_TOOL_PROFILE` env var.
- It does **not** add profile-based dispatch to `register_fastblocks_tools()`.
- It does **not** bump `mcp-common` from `~=0.3` to `~=0.18`.
- It does **not** change the `mcp` SDK version (still 1.x, using
  `from mcp.server.fastmcp import FastMCP` directly).

## Note for the W4.10 splashstand wave

SplashStand is a FastBlocks **consumer**, not FastBlocks' MCP server.
SplashStand's MCP server is its own production control plane with
mutating tools (customer site management, etc.) — it **does** need the
full `mcp_common` profile system. The W4.10 brief should:

1. **Adopt the full pattern** in `splashstand/mcp/`. This is the
   "production" half of the equation.
2. **Import fastblocks' tools via the `register_fastblocks_tools` free
   function** so splashstand's MCP server includes the framework's
   read-only introspection helpers as part of its own profile.
3. **Not** import `apply_fastblocks_tool_profile` (the no-op stub) —
   the no-op is for the *framework's* server only. Splashstand's
   server should call `mcp_common.tools.apply_tool_profile` directly,
   not the framework's stub.

If a future contributor reads this and assumes FastBlocks' opt-out
"infects" SplashStand, they will skip the profile-based dispatch that
SplashStand's mutating tools actually need. **Do not let that happen.**

## References

- `fastblocks/CLAUDE.md` — "What this project is" (public, framework-level
  software) and "MCP surface is read-only for framework introspection".
- `fastblocks/mcp/server.py` — `FastBlocksMCPServer` class, line 60
  `await self._register_tools()` call site.
- `fastblocks/mcp/tools.py` — `register_fastblocks_tools` free function
  (line 561) and the seven tool definitions.
- `fastblocks/tests/mcp/test_ci_guard.py` — CI guard against the
  0.8.0-deleted symbol names.
- `fastblocks/mcp/profiles.py` — the no-op stub.
- `fastblocks/tests/mcp/test_tool_profile.py` — the regression test.
- W4.9 task brief: `/Users/les/Projects/mahavishnu/.superpowers/sdd/2026-08-18-mcp-tool-profile-adoption/task-22-brief.md`

______________________________________________________________________

## status: accepted role: phase-4-closeout date: 2026-08-23 last_reviewed: 2026-08-23 supersedes: null superseded_by: null decision_date: 2026-08-23 topic: phase-4-mcp-tool-surface-organization-library-aware-opt-in-closeout

# ADR 0015: Phase 4 Library-Aware Opt-In Closeout

## Status

Accepted (Phase 4 v2.1 — re-design after multi-agent review deferred
the original spec via ADR 0011).

## Context

The master plan (§Pillar 4 line 89, §Phase 4 line 339) calls for
tagging the 7 FastBlocks MCP tools by capability, adding
`discover_tools`, and introducing behavioral dependency gates.
Phase 4 was deferred in commit `22478ce` (ADR 0011) with 5 P0 + 6 P1
blockers against the original spec. The v2 spec (`2026-08-23`)
attempted to fix those but introduced 7 P0s in the multi-agent review.
v2.1 (this ADR) drops the framework-internal wiring entirely and ships
the capability metadata as a public library export.

## Decisions

### Decision 1: Library-aware opt-in posture (strict)

`FastBlocksMCPServer._register_tools` is **unchanged** in v2.1. It
continues to register all 7 read-only tools via the existing
`register_fastblocks_tools` function. The framework-internal server
is NOT profile-gated; it always exposes the full 7-tool surface.

Consumers (e.g. SplashStand) who want profile-based dispatch import
`fastblocks.mcp.capabilities` and pass the registration functions to
their own `apply_tool_profile` calls. The capability metadata is a
**library export**, not a framework-internal wiring change.

This honors CLAUDE.md:157-190's library-not-server rationale directly
— no "reframing" or "renaming" required.

### Decision 2: `@runtime_checkable`-equivalent on Protocols

`capabilities.py` does NOT define new `t.Protocol` classes. The
capability functions are plain callables; consumers can pass them
directly to `apply_tool_profile`'s `registrations` parameter (which
accepts callables per dispatch.py:177-191). The consumer-pattern
integration tests verify the callable-list dispatch.

### Decision 3: Custom `discovery_fn` override

`fastblocks/mcp/discovery.py` ships `fastblocks_discovery` as an
optional override. Consumers pass it as `discovery_fn=...` to their
own `apply_tool_profile` call. Schema: `{name, capability, description, inputSchema}`. No `is_available` field — tools that fail
a capability gate are NOT in `server.list_tools()` (gate failures
skip registration entirely, per mcp_common contract).

### Decision 4: Probe-not-construct gates

`_is_adapter_available()` probes via `FastblocksRegistry( get_resolver()).list_active('fastblocks')` — checks **resolved
state**, not lazy construction. If no candidates are registered yet,
the gate returns False and the ADAPTER capability is silently
skipped. Same posture for `_is_template_available()` (checks
Jinja2/HTMY importability) and `_is_component_available()` (checks
htmy_components importability).

### Decision 5: Consumer uses async wrapper

Consumers in an async context (the canonical MCP server case) must
use `await _apply_tool_profile(...)` (dispatch.py:337), NOT the sync
`apply_tool_profile(...)` wrapper which raises `RuntimeError` from
inside a running event loop (dispatch.py:331-334). The sync wrapper
is only valid in CLI startup paths and scripts outside event loops.

### Decision 6: `suppress(Exception)` ratchet at master plan baseline

The deletion removes server.py:157's `with suppress(Exception)` block
(inside the deleted `_get_http_app` function). Ratchet improves by 1.
Master plan line 313 baseline holds at 122 (or 121 after this commit).
The ratchet test (`tests/core/test_suppress_exception_ratchet.py`)
continues to assert ≤ baseline.

### Decision 7: Deleted symbols are documented, not deprecated

The following symbols are **deleted**, not deprecated:

- `apply_fastblocks_tool_profile`
- `FASTBLOCKS_TOOLS`
- `PROFILE_REGISTRATIONS`
- `_FallbackToolProfile`
- `_get_http_app`, `get_http_app`, `_http_app_cache`, `http_app`

Deprecation aliases (e.g., \`apply_fastblocks_tool_profile = ...

# DEPRECATED\`) are NOT added. The deletion is clean; consumers that

imported the symbols must update to the new capability primitives.

### Decision 8: YAML-driven profile deferred

`_oneiric_yaml_loader` (v2's R1/R9 attempt) is **removed entirely**.
v2.1 is env-var-only. Adding `tool_profile: str | None` to
`load_fastblocks_settings()` is Phase 6+ config extension work —
out of scope for the mechanical library export.

## Deferred Items

| Item | Lands in |
|---|---|
| YAML-driven profile via `load_fastblocks_settings()` | Phase 6+ config extension |
| Custom `Protocol` types for `register_X_capability` (currently plain callables) | Phase 7 or later — not needed until stricter typing is required |
| Renderer match-statement dispatch (master plan line 311) | Phase 4 / 6 follow-up |
| `register_template_candidate` decorator | When first renderer adopts the contract |

## Cross-references

- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md` §Pillar 4 (line 89), §Phase 4 (line 339)
- ADR 0011 (Phase 4 deferral): `docs/adr/0011-phase-4-deferral.md`
- v2 spec (superseded): `docs/superpowers/specs/2026-08-23-fastblocks-phase-4-v2-design.md`
- v2.1 spec (this ADR's companion): `docs/superpowers/specs/2026-08-23-fastblocks-phase-4-v2.1-design.md`
- Multi-agent review synthesis: `docs/superpowers/sdd/2026-08-23-fastblocks-phase-4-v2/synthesis.md`
- CLAUDE.md:157-190 — library boundary rationale (preserved by this design)
- mcp_common public API: `mcp_common/tools/__init__.py` (`apply_tool_profile`, `ToolProfile`, `trim_description`)
- mcp_common dispatch: `mcp_common/tools/dispatch.py:253` (sync `apply_tool_profile`), `:337` (async wrapper)

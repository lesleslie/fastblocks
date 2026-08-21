# FastBlocks Master Plan: Becoming a Modern Web Framework

**Date:** 2026-08-21
**Status:** Draft (4-reviewer audit complete; comprehensive rewrite incorporating all critical/high findings)
**Branch:** in-place on fastblocks main
**Repository:** `/Users/les/Projects/fastblocks`
**Maintainer:** `les` (single maintainer, confirmed via `git log` on the fastblocks-htmy standalone). Single-developer decisions are explicit throughout this plan.
**Scope:** Multi-quarter architectural rewrite. No backwards compatibility required (zero external users, zero websites in production).
**Companion documents:** Style/renderer spec + plan at `docs/superpowers/{specs,plans}/2026-08-21-style-renderer-architecture.md` (Phase 1 detail).

---

## TL;DR

Goal: turn fastblocks from a 7-tool, ACB-described, RCE-vulnerable library into a typed, observable, dead-code-free internal framework. Phases 1A/1B ship in 2026 (style/renderer consolidation + fastblocks-htmy absorption); Phases 1.5/2-8 are planned. **Phase 1.5 is the addition from this audit cycle** — it consolidates 77 separate `Resolver()` instances onto a single shared resolver before Phases 2/4/5/6 build on top of a fractured registry layer.

Read §Subsystem status (line 174) and §Verification standards (line 380) before starting any task. The fresh-session prompt at the bottom is self-contained; treat its live state (HEAD, pytest baseline) as authoritative.

## Table of Contents

1. [Ecosystem context](#ecosystem-context)
2. [Context](#context)
3. [Framing choice: internal infrastructure](#framing-choice-internal-infrastructure)
4. [Vision](#vision)
5. [Architectural pillars](#architectural-pillars)
6. [Subsystem status](#subsystem-status)
7. [Phase 1: Style/renderer consolidation (already specced)](#phase-1-stylerenderer-consolidation-already-specced)
8. [Phase 1.5: Oneiric Adapter Registry Consolidation](#phase-15-oneiric-adapter-registry-consolidation)
9. [Phase 2: Type-safe configuration](#phase-2-type-safe-configuration)
10. [Phase 3-8: Subsequent work](#phase-3-8-subsequent-work)
11. [Master roadmap](#master-roadmap)
12. [Migration strategy: no backwards compatibility](#migration-strategy-no-backwards-compatibility)
13. [Verification standards](#verification-standards)
14. [Risks](#risks)
15. [Out of scope](#out-of-scope)
16. [Reference artifacts](#reference-artifacts)
17. [Process](#process)
18. [Fresh-session prompt](#fresh-session-prompt)

---

## Ecosystem context (for new readers)

Bodai is a multi-component ecosystem:

- **mahavishnu** — orchestration (multi-pool, MCP tools, routing)
- **akosha** — intelligence and search (semantic memory, embeddings)
- **dhara** — state persistence (Oneiric adapter distribution)
- **session-buddy** — memory and conversation context
- **crackerjack** — quality gates (the gate tool for CI)

**fastblocks** is a sibling: a Starlette-based Python web framework for SSR/HTMX apps. It is NOT the orchestration layer (that's Mahavishnu), NOT the state layer (that's Dhara). It is internal infrastructure for Bodai — same posture, different concern. The "zero external consumers" assertion (verified by Phase 0 preflight) means fastblocks has no third-party users.

**Note:** CLAUDE.md:220 says ARCHITECTURE.md still describes fastblocks as "ACB-based"; the codebase actually moved to Oneiric in Phase 3.1. The code is the source of truth.

## Context

FastBlocks currently ships as:

- 7 read-only MCP tools in `fastblocks/mcp/tools.py` (~18 KB single file), explicitly opted out of `mcp_common.tools.apply_tool_profile()` (per CLAUDE.md:155-190). The original "180 tools" framing in the v1 of this plan was a misattribution from Mahavishnu — corrected throughout.
- **Oneiric-based adapter pattern with a fractured registry layer** (per oneiric-specialist audit): Starlette → FastBlocks → Adapters → Oneiric. The plan asserted "Resolver is the single shared singleton"; in practice, **77 separate `Resolver()` objects** exist across the codebase, only ~8 route through `get_resolver()`. The other 69 modules do `depends = Resolver()` at module scope. **Phase 1.5 fixes this; without it, Phases 2/4/5/6 build on a broken foundation.**
- Starlette + Jinja/HTMY rendering, with `style_registry.py` conflating two distinct axes (CSS source + component model).
- Multiple broken style adapters (`kelp.py`, `webawesome.py`); `bulma` and `custom` enum entries without backing modules. All masked by `with suppress(Exception)`.
- A live RCE vector in `htmy.py:300-354, 356-399` reachable via the legacy `HTMYComponentRegistry` fallback (closed by Phase 1A's C3).
- 8 pre-existing pytest collection errors (CLAUDE.md:233 — corrected from the v1 plan's stale "19" claim).
- A multi-week ty cleanup (commits `4035bf3..6ca11b3`) that surfaced 7 real bugs as a side effect of removing type suppressions.
- ~145 Resolver API misuse diagnostics alone (most resolved in subsequent phases per the ty cleanup).
- **A live per-thread event loop in `htmx.py:50`** (per `CLAUDE.md:197`) that is fundamentally incompatible with Starlette/uvicorn's asyncio model under load. Phase 1A+ fixes this.
- **WebSocket auth reads `os.getenv` at module load** (`fastblocks/websocket/auth.py:17-24` per CLAUDE.md:230). Structural defect, not deferred feature. Phase 1A+ fixes this.

User-confirmed: **zero external users, zero websites in production, no
backwards compatibility needed**.

## Framing choice: internal infrastructure, not public framework

This plan treats fastblocks as **internal infrastructure for the Bodai ecosystem**, consistent with CLAUDE.md. Consequences:

1. The "modern Python web framework" framing (which the v1 draft leaned toward) over-promises on axes fastblocks doesn't need. This plan's vision is scoped to what internal infrastructure actually needs.
2. "Tutorial for new contributors" (Pillar 8) means **maintainer onboarding**, not external-user documentation.
3. "Modern" is redefined as: type-safe, observable, dead-code-free, internally-consistent — not feature-rich.

## Vision

A modern internal Python framework with the following characteristics at plan completion:

1. **Type-safe configuration with loud failures.** Every configuration value has a runtime-checked type. Unknown `style`, `renderer`, or adapter names fail at startup with a clear message pointing to the offending value. **No `with suppress(Exception)` in adapter boundaries** — and the gate that enforces this (Phase 2) reaches `fastblocks/core/style_registry.py` (currently missed by the glob in v1 of this plan).
2. **Two-axis rendering architecture** (`style` × `renderer`) with explicit matrix semantics, Jinja2 env contract pinned, Custom Element layer acknowledged, HTMX response-shape contract defined.
3. **One source of truth per concern.** Packages that have value outside fastblocks (`fastblocks-ui`, `htmy`) stay separate. Packages that don't (`fastblocks-htmy`) are absorbed. No self-referential dependencies. **External packages register via the documented mechanism (Pillar 3 decision); fastblocks doesn't invent a parallel string-import convention.**
4. **Tool surface organized by capability.** The 7 read-only MCP tools are tagged by capability (`template`, `component`, `adapter`). Phase 1.5 makes the resolution layer functional so the tools actually work, not just register.
5. **Observability as a first-class concern** — built on Oneiric's existing resolution events (`explain()`, `list_shadowed()`, `DecisionEvent`), not a parallel counter stack.
6. **Test infrastructure rebuilt.** Zero pre-existing collection errors, property-based testing, XSS regression matrix, axe-core a11y integration, MCP server integration canary.
7. **Dead code removed ruthlessly.** Broken adapters, fallback paths, backup files, and `with suppress(Exception)` everywhere they mask bugs.
8. **Maintainer-facing documentation.** API docs auto-generated, ADRs, onboarding doc that lets a new maintainer orient in <30 minutes.

## Architectural pillars

### Pillar 1: Type-safe configuration with loud failures

**Target state.** Configuration values are validated at app startup with runtime type checking. Adapter registration surfaces errors as exceptions, not silent no-ops.

**Two-tier scope** (clarified from oneiric-specialist audit):

**(a) Configuration values — Phase 2.** Each domain (`style`, `renderer`, app mode) declares values as `Literal[...]` types. Unknown values fail at the point of registration. The decision rule (per python-pro audit): **config-only domains use `Literal[...]`; `StrEnum` is justified only for runtime-dispatched taxonomies.** The `Styles` enum in cli.py is replaced with `Literal["vanilla", "fastblocks_ui"]`.

**(b) Adapter registration correctness — Phase 1.5 (NOT deferred).** The plan's v1 said "replace Oneiric Resolver" and deferred it as out-of-scope. The oneiric-specialist audit showed this was the wrong frame: the issue isn't that Resolver is wrong, it's that **fastblocks uses it incorrectly** (77 separate instances, ~70 disjoint registries). Phase 1.5 is a mechanical one-line substitution per file: `depends = Resolver()` → `depends = get_resolver()` (with a CI guard test). Reframed from "replace" to "use correctly," this is the same architectural posture with a different (and much smaller) scope.

**Decision rule for "absorb or wrap"** (oneiric-specialist finding ONEIRIC-10): Anything another Bodai component would also want goes upstream (Oneiric itself); anything fastblocks-specific stays local. ADR 0008.

### Pillar 2: Single-axis rendering architecture

**Target state.** `style` axis = CSS source only (`vanilla` | `fastblocks_ui`). `renderer` axis = component model only (`jinja2` | `htmy`). The 2×2 matrix is explicitly enumerated. Cells are either "supported" or "unsupported" (startup fails with a useful error).

**Critical refinement — renderer axis is more than a docstring.** Phase 1's D deliverable pins the contract for what "renderer" means in three layers:

1. **Server-side rendering component model.** Jinja2 templates with autoescape and a documented `init_envs()` registration site (singleton on `app.state.jinja_env`); HTMY components with AST-sandboxed source loader and `hx_*` kwargs contract.

2. **Client-side progressive enhancement layer.** `fastblocks-ui`'s `enhance.js` ships **3 live `extends HTMLElement` classes** (`UiTabsElement`, `UiDialogElement`, `UiMenuElement`). The Python helper layer has a `custom_element: bool = False` flag that opts into host-tag rendering. Phase 1A documents this layer explicitly.

3. **HTMX transport.** Renderer describes only what produces markup. Response shape (full page vs HTMX partial vs OOB swap vs SSE stream vs WebSocket update) is an orthogonal transport concern handled at the middleware/route layer via `HTMXResponse(HTMLResponse)`.

**Jinja2 env contract** (Phase 1A docstring pin, Phase 6 enforcement):

- `autoescape=True` for `.html`/`.htm`/`.xml` templates; autoescape-off only for `.txt` (verified by `tests/adapters/templates/test_jinja2_autoescape_contract.py`).
- **Fragment extension `[[ ]]` routes through the same autoescape as `{{ }}`** (verified by `tests/adapters/templates/test_fragment_autoescape.py` — catches a real XSS vector if `jinja2_async_environment` is patched to skip escape for fragment performance).
- `bytecode_cache`: `FileSystemBytecodeCache` to `settings.cache_dir / "jinja2_cache"` when `debug=False`, `None` otherwise.
- `auto_reload`: follows the Oneiric `debug` flag.
- `undefined`: `ChainableUndefined` for chained access; `StrictUndefined` when debug=True; `Undefined` default in prod.
- Template lookup order: `app/templates/` (user override) → `fastblocks/adapters/app/_templates/{style}/` (framework default) → Jinja2 `PackageLoader` fallback.
- Filter and globals names MUST be prefixed with `fb_`.

**Custom Element layer scope decisions** (Phase 1A docstring pin):

- Shadow DOM is **out of scope**. Encapsulation is delegated to BEM-style class prefixes.
- The existing `<ui-tabs>` / `<ui-dialog>` / `<ui-menu>` host tags stay. New CEs use `<fastblocks-*>` prefix.
- HTMX + CE sequencing rule: `enhance.js` must load synchronously (inline) or as a blocking `<script>` before any htmx swap can fire.
- HTMX swap targets vs CE: `outerHTML` on the host is safe; `innerHTML` on a parent is safe; OOB swaps that *target* the host are state-resetting.
- Form-associated CEs are out of scope for absorbed components (current model: host is decorative, inner control carries form semantics).
- `<template>` element is **not used** for deferred rendering.

### Pillar 3: One source of truth per concern

**Target state.** Each piece of fastblocks lives in exactly one place. External packages (`fastblocks-ui`, `htmy`) are upstream dependencies with version pins. `fastblocks-htmy` is absorbed. No self-referential dependencies. **External packages register via Oneiric (not via fastblocks's parallel string-import convention in `style_registry.py:76-90` — the convention is deprecated and removed in Phase 2)**.

**Approach.** Decision matrix:

- `fastblocks-ui`: stay separate.
- `htmy`: stay separate.
- `fastblocks-htmy`: absorbed.

**Registration contract for external packages** (per ONEIRIC-09): Route style adapters through `register_candidate(depends, "style", style_name)` so they inherit shadowing, `explain()`, and Phase 6 metrics. Retire the `import_module(getattr(...))` convention in `style_registry.py`. The convention works only as long as the external package's entry point stays string-stable; it bypasses Oneiric entirely.

**Verification gate (added per code-architect audit):** Phase 2's gate includes `grep -nE "import_module\(getattr" fastblocks/core/style_registry.py` returns 0 hits; the docstring's "intentionally best-effort" justification is removed in the same commit.

### Pillar 4: Tool surface organized by capability

**Target state.** The 7 read-only MCP tools are organized by capability tag (`template`, `component`, `adapter`). Tools are discoverable via a client-side `discover_tools(query)` Python helper that wraps FastMCP's `tools/list` filtered by capability tag. **The MCP server surface remains exactly 7 tools**; capability-tag filtering is a client-side concern over `tools/list`, not a new server tool.

**Approach.** Phase 4 of this master plan tags the existing 7 tools with capabilities. **Phase 1.5 prerequisite:** Phase 4 cannot tag the surviving 7 tools until the resolution layer is functional (see ONEIRIC-02 — the MCP tool module's Resolver is currently empty, so tagging work on broken tools would be vacuous). Phase 4 verification includes a **behavioral gate**: register a known adapter, then assert `check_adapter_health` returns it.

### Pillar 5: Observability as a first-class concern — built on Oneiric

**Target state.** Every adapter registration emits a structured log line. Every render emits a counter metric. Every request emits a trace span. CHANGELOG and CLAUDE.md are not the observability mechanism.

**Critical change from v1 of this plan:** Phase 6 observability is designed **as an exporter over Oneiric's existing resolution observability** (`explain()`, `list_shadowed()`, `DecisionEvent`, `traced_decision()`), not as a parallel counter stack. Oneiric 0.16.5 already produces per-resolve structured events with full candidate scoring; duplicating them in fastblocks would create the "two disagreeing sources of truth for why did this resolve to X" antipattern.

**Approach.** Add `opentelemetry` SDK init at app startup. Add `prometheus_client` counter metrics at each boundary. **Layer Oneiric resolution observability as the primary source** — fastblocks counters are derived/aggregated, not parallel.

**Pre-Phase 6 audit (must happen before Phase 6 starts):**

- Enumerate what `oneiric.logging`, `logfire`, `sentry`, `crackerjack` already provide.
- Enumerate Oneiric's resolution observability surface: `explain()`, `list_shadowed()`, `list_active()`, `DecisionEvent`.
- `list_shadowed()` becomes a startup log line AND a Grafana panel — shadowed adapter candidates are exactly the silent-misconfiguration class Pillar 1 targets.

### Pillar 6: Test infrastructure rebuilt

**Target state.** Zero pre-existing collection errors. Property-based testing for the style × renderer matrix (Hypothesis). Regression tests for escape correctness (XSS regression matrix). Configuration validation tests. axe-core a11y integration. **MCP server integration canary** that catches the NameError history at `tools.py:585-590` where `register_fastblocks_tools` previously called an undefined function (masked by `with suppress(Exception)` in `MCPServerBase._register_tools`).

**Approach.** Phase 5 of this master plan. **Current baseline is 8 pre-existing collection errors**, not 19 (corrected from the v1 plan's stale claim per ONEIRIC-related audit). Phase 5's gate is "zero collection errors." Property-based tests use `@settings(max_examples=1000, deadline=None, derandomize=True)` for matrix cells.

### Pillar 7: Dead code removed ruthlessly

**Target state.** No `with suppress(Exception)` in adapter boundaries (full-tree count currently 123; Phase 7 ratchets down to 0). No `*.backup` files in version control. No fallback paths that exist only to mask bugs.

**Approach.** Phase 1A's backup purge (security/audit hazard). Phase 7 final pass ratchets `git grep -c 'suppress(Exception)' -- fastblocks/` to a documented number per phase boundary.

### Pillar 8: Maintainer-facing documentation

**Target state.** API docs auto-generated from docstrings. ADRs under `docs/adr/`. A maintainer onboarding doc that lets a new maintainer orient in <30 minutes.

**Approach.** Phase 8. **Parallelizable from Phase 1** (docs work doesn't depend on code changes; it documents the current state at any point). Phase 8 verification includes: docs site passes axe-core with 0 violations of color-contrast, heading-order, landmark-one-main, region, skip-link, focus-order-semantics.

## Subsystem status

| Subsystem | Current state | Target state | Phase | Priority |
|---|---|---|---|---|
| **Adapter registry (Resolver)** | **77 separate Resolver() instances, ~70 disjoint registries; ~70 sites do `depends = Resolver()` at module scope; only ~8 use `get_resolver()`** | Single shared resolver via `get_resolver()`; CI guard test; behavioral resolution gates | **1.5** | **Critical** |
| Style adapters | 4 options (`kelp`, `webawesome`, `bulma`, `custom`); 2 broken, 2 enum-only; silent-failure pattern | 2 options (`vanilla`, `fastblocks_ui`); loud `unknown style` on miss | 1A | High |
| Renderer axis | Conflated under `style`; no renderer config | Separate axis; 2×2 matrix; Jinja2 env contract; CE layer; HTMX transport | 1A+6 | High |
| Configuration values | Oneiric `ResolverSettings` accepts any string; `AppBaseSettings.style: str = "vanilla"` (CLI enum diverges: has `bulma/webawesome/custom`, not `vanilla`) | Literal[...] types; CLI enum and settings Literal in sync | 2 | High |
| Configuration adapter registration | Oneiric Resolver (used incorrectly per ONEIRIC-01) | Used correctly (Phase 1.5); Literal types don't help until registry works | 1.5 | **Critical** (was Low/deferred) |
| htmx.py per-thread event loop | `_run_async_safely` via `threading.local()`; fundamentally incompatible with Starlette/uvicorn under load | Capture `app.state.main_loop` during lifespan; use `asyncio.run_coroutine_threadsafe` | 1A+ | High |
| WebSocket auth | `os.getenv` at module load; zero-downtime key rotation impossible; bypasses Starlette request lifecycle (FastblocksWebSocketServer is a separate server) | Per-connection ASGI middleware via `Starlette.WebSocketRoute` reading env at call time | 1A+ | High |
| fastblocks-ui integration | Pin `>=0.8,<0.9` as required runtime dep; pre-flight gate on `get_css_path` / `get_js_path`; pre-flight doesn't verify env can import fastblocks-ui functions | Add extended pre-flight verifying env wiring and escape correctness | 1A+ | High |
| WebSocket module + reverb bridge | CLAUDE.md:230 known tech debt; FastblocksWebSocketServer bypasses Starlette request lifecycle; observability gap | Mount via Starlette WebSocketRoute; aria-live bridge contract | 1A+/6 | High |
| MCP tool resolution (5 tools) | All 5 call `depends.resolve()` on a private, permanently-empty Resolver | After Phase 1.5: tools.py uses `get_resolver()`; registrations land in the shared registry | 1.5+4 | **Critical** |
| MCP server integration test | Missing; `register_fastblocks_tools` previously had a masked NameError | Phase 5 adds an integration test: spin up FastMCP server, assert 7-name tuple from `profiles.FASTBLOCKS_TOOLS` is registered | 5 | High |
| MCP writer functions (3 unregistered) | `create_template`, `create_component`, `configure_adapter` in `fastblocks/mcp/tools.py` reachable via direct import | Delete in Phase 1A's dead-code sweep | 1A | High |
| MCP observability | No per-tool invocation metrics | Add `fastblocks_mcp_tool_invocations_total{tool_name, status}` counter + duration histogram | 6 | Medium |
| MCP resources | 7 resources in `fastblocks/mcp/resources.py` not addressed by Pillar 4 | Same capability-tag taxonomy as tools | 4 | Medium |
| Observability | Oneiric already produces `resolver-decision` events; fastblocks plans parallel counters | Phase 6 exports from Oneiric observability surface, not parallel | 6 | Medium |
| Test infrastructure | 8 pre-existing collection errors (CLAUDE.md:233); mostly unit tests | Zero errors; property-based for matrix; MCP integration canary; axe-core integration | 5 | High |
| Backup files in repo | `_advanced_manager.py.backup`, `_htmy_components.py.backup`, etc.; security/audit hazard | Removed in Phase 1A | 1A | **High (security/audit hazard)** |
| CLI | `Styles(StrEnum)` has `bulma`, `webawesome`, `custom`; `cli.py:929, 957, 1079, 1093` use `Styles.bulma`; `cli.py.backup` exists | Replace with `Literal["vanilla", "fastblocks_ui"]`; update default args | 1A | Medium |
| starlette-csrf + HTMX composition | starlette-csrf validates `X-CSRF-Token` header or hidden form field; HTMX needs explicit `htmx.config.csrfToken` wiring | Wire in `fastblocks/middleware.py`; Phase 5 integration test asserts HTMX POSTs succeed | 1A+ | High |
| Static files serving shape | Three Starlette-compatible shapes (`StaticFiles`, `Mount`, custom) — none named | Document + test: `GET /static/ui.css` returns `Cache-Control: public, max-age=31536000, immutable` AND `Content-Encoding: br` when `Accept-Encoding: br` | 1B+ | Medium |
| Middleware order (secure/brotli/csrf) | Not pinned | Pin: OTel outermost, secure, brotli, csrf, error-handler innermost | 1A+ | Medium |
| Async model / asyncio.TaskGroup | `asyncio.gather` used throughout; no `TaskGroup` strategy | `asyncio.TaskGroup` for concurrent component rendering; structured concurrency | 5/6 | Medium |
| BackgroundTasks integration | Renderer has no `BackgroundTasks` injection | Document canonical pattern: renderer returns markup; route handler attaches `BackgroundTasks` to response | 5/8 | Medium |
| Logging schema | Not pinned; high cardinality risk on `fastblocks_style_resolve_total{style=<value>}` | Pin `LogEvent = TypedDict(...)` with bounded cardinality | 6 | Medium |
| Cardinality guards on Prometheus labels | No max-cardinality pin | Label-set is `Literal[...]` finite; add CI lint | 6 | Medium |
| `htmy.py` per-thread event loop | `_run_async_safely` masks cancellation context | Replace with `asyncio.run_coroutine_threadsafe` + trace context propagation | 1A+ | High |
| Dataclass config for absorbed components | Not specified | `@dataclass(slots=True, kw_only=True, frozen=True)` for every typed component | 1B | Medium |
| `Protocol` for adapter contracts | Not defined | `TemplateAdapter(Protocol)` + `StyleAdapter(Protocol)` with `register_candidate` decorator verifying isinstance | 2 | Medium |
| `SafeHTMLStr = NewType(...)` for trust boundaries | Not defined | Container.content and other "pre-rendered" fields typed as `SafeHTMLStr` | 1B | Medium |
| match statement exhaustiveness | Not used | Renderer dispatch uses `match` over Literal subjects | 2 | Medium |
| PEP 695 type aliases | Not used | `type XSSRow = TypedDict(...)` for snapshot schemas | 5/6 | Low |
| `ExceptionGroup` for XSS matrix | Not used | All-component aggregation via `pytest.raises(ExceptionGroup)` | 5 | Medium |
| `asyncio.run()` policy | Not pinned | Hard don't: sync helpers may NOT call `asyncio.run()`; use `loop.run_in_executor()` if blocking I/O needed | 1A+ | Low |
| Cross-checker type-suppression syntax | `# type: ignore` not pinned per checker | Per-checker directives: `# mypy:`, `# ty:`, `# pyright:` with justification comments | 1A+ | Low |
| Free-threading (PEP 703) / JIT (PEP 744) | Out of scope; need explicit note | One-paragraph note in Out-of-scope; flag globals for re-validation if enabled | 8 | Low |
| Oneiric version pin | `oneiric~=0.3` (maximally permissive; 13 minor versions admitted); 3 versions live across Bodai | Pin `oneiric>=0.16.5,<0.17`; add compat test | 1A | High |
| ADRs | `docs/adr/` does not exist; CLAUDE.md:193 says "scattered ADRs" | Create `docs/adr/0001-onerirc-integration.md`, `0002-package-boundaries.md`; per-checker ADR template | 1A+ | Medium |
| Documentation site a11y | No a11y testing | axe-core in CI for docs site; lang attribute; semantic HTML | 8 | Medium |
| Vanilla blast radius | `fastblocks-ui` becomes required dep even for `vanilla` users | Document or upgrade path for air-gapped users | 1A+ | Medium |
| WebSocket auth | See above | See above | — | — |
| Multi-pool orchestration | Working (Mahavishnu layer) | No changes needed | — | Out of scope |
| WebSocket infrastructure | Working | See WebSocket auth row above; otherwise no changes | — | (see auth) |
| Content ingestion | Working | No changes needed | — | Out of scope |
| OpenTelemetry tracing | Working; some Sentry/OTel root-span conflicts | Resolve root-span conflict in Phase 6; otherwise extend | 6 | Medium |
| Documentation | CLAUDE.md, README, scattered ADRs | Auto-generated API docs; ADRs; maintainer onboarding | 8 | Medium |

## Phase 1: Style/renderer consolidation (already specced)

Phase 1 of this master plan is fully specified in:

- **Spec**: `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-08-21-style-renderer-architecture.md`
- **Plan**: `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-21-style-renderer-architecture.md`

### Phase 1A — fastblocks 0.30.0 (independent fixes, ~4-6 weeks calendar)

- **A. Drop broken styles.** Delete `kelp.py`, `webawesome.py`. Drop `bulma`, `webawesome`, `custom` enum entries. Delete `_templates/{kelp,webawesome,bulma}/`. Loud `unknown style` on miss.
- **B. Promote fastblocks-ui.** Pin `fastblocks-ui>=0.8,<0.9` as required runtime dep. Default `AppBaseSettings.style = "fastblocks_ui"`. **Pre-flight gate** (per ONEIRIC-08): verify all three pin locations are aligned — fastblocks/pyproject.toml `[project].dependencies`, the (deleted) `fastblocks_ui = [...]` optional group, and `/Users/les/Projects/fastblocks-htmy/pyproject.toml`. Extended pre-flight (per python-pro + security-auditor): verify `fastblocks_ui.button('<script>')` and 11 other helpers escape user input.
- **MCP writer functions deletion.** Delete `create_template`, `create_component`, `configure_adapter` from `fastblocks/mcp/tools.py`. Gate: `grep -rnE '^async def (create_template|create_component|configure_adapter)' fastblocks/mcp/` returns 0 hits.
- **htmx.py per-thread event loop fix.** Replace `_run_async_safely` with a helper that captures `app.state.main_loop` during lifespan startup and uses `asyncio.run_coroutine_threadsafe(coro, app.state.main_loop)`. Fall back to `asyncio.run(coro)` only when no loop is bound. **Per-request ContextVars (request_id, trace_id) propagate via `contextvars.copy_context().run(...)`.** This is the fix for the starlette-specialist's CRITICAL finding.
- **WebSocket auth per-request.** Replace `os.getenv` at module load with a per-request lookup via Starlette WebSocketRoute + ASGI middleware. Move `FastblocksWebSocketServer` to `Mount('/ws', app=ws_asgi_app)`. **Resolves CLAUDE.md:230 tech debt AND unlocks zero-downtime JWT key rotation.**
- **Backup file purge.** All `*.backup` and `*.backup.json` files in one commit. Gate: `git ls-files | grep -E '\.backup(\.json)?$' | wc -l` returns 0.
- **Oneiric version pin.** `oneiric>=0.16.5,<0.17` instead of `oneiric~=0.3`. Add compat test asserting concrete Resolver surface (`register`, `resolve`, `explain`, `list_active`, `list_shadowed`).
- **CSRF + HTMX wiring.** Add to `fastblocks/middleware.py`: either (a) `htmx.config.csrfToken = 'csrf_token'` in enhance.js, OR (b) middleware that copies `csrf_token` form field to `X-CSRF-Token` header on `HX-Request: true`. Document the choice in the plan.
- **Middleware order pin.** Document in `fastblocks/applications.py`: OTel outermost, secure, brotli, csrf, error-handler innermost.
- **C3. Close RCE.** Delete `_load_from_cached_bytecode` and `_load_from_source` from `htmy.py`. Rewrite `get_component_class` caller to route through AST-sandboxed `load_component_from_source()` from `_htmy_components.py`. Broader regex (`importlib|__import__|exec\(|eval\(`) + Python-level guard test.
- **D. Document renderer axis.** `style_registry.py` docstring names `renderer` axis as next-iteration north star with the three-layer commitment (server, client, transport). **Document that `renderer` describes only the component model; response shape is an orthogonal transport concern handled via `HTMXResponse(HTMLResponse)` at the middleware/route layer.** Pin the Jinja2 env contract (autoescape, fragment delimiter, bytecode cache, lookup order, naming prefix) in `init_envs()` docstring. Document the Custom Element layer (3 `extends HTMLElement` classes in `enhance.js`, `<ui-*>` host tags, HTMX+CE sequencing rule, Shadow DOM out-of-scope).

### Phase 1B — fastblocks 0.31.x (absorption mechanics, ~3-4 weeks calendar + 30-day shim window)

- **C1. Pin transitive deps.** Edit `htmy[lxml]~=0.9` to `htmy[lxml]>=0.13,<0.14` (preserve `lxml` extra).
- **C2. Reconcile base classes.** `FastBlocksComponent` canonical, `ComponentBase` preserved for legacy discovery loader. NOT interchangeable. **Dataclass config** (per python-pro audit): `@dataclass(slots=True, kw_only=True, frozen=True)` on every absorbed typed component unless source explicitly mutates.
- **C3.5.** `fastblocks/adapters/templates/jinja2.py` gets explicit handling. Pin: "The `init_envs()` function is the canonical Jinja2 registration site. Renderer-axis filter/globals registration MUST live here, not in style adapters."
- **C4. Absorb source.** Move 22 source files from `fastblocks-htmy/fastblocks_htmy/` into `fastblocks/adapters/templates/htmy_components/`. Hoist `adapter.py` to top level. Replace `_check_fastblocks_ui` runtime check with a soft `warnings.warn(..., DeprecationWarning, stacklevel=2)`. **XSS regression test scope** covers: (a) `attrs` dict-key escaping, (b) CSS-context vectors, (c) aria-* attribute injection. **Jinja2 XSS matrix parallel** for `autoescape` blocks, `|safe` filter, `|e` modes, `Markup` round-trip. **`SafeHTMLStr = NewType('SafeHTMLStr', str)` for trust boundaries.** `htx_*` kwargs contract test. **PEP 561 `py.typed` markers verified at every parent package.**
- **C5. Cross-repo shim release.** `fastblocks-htmy 0.6.x` re-exports from `fastblocks`. Manual PyPI publish. Required supply-chain mitigations: PyPI 2FA, PEP 740 attestations, hash-pinned install for CI / production. 24-hour-after-fastblocks-0.31.x release ordering. Owner: `les`.

## Phase 1.5: Oneiric Adapter Registry Consolidation (NEW — blocking)

**Inserted between Phase 1 and Phase 2.** Without this phase, Phases 2/4/5/6 all build on top of a fractured registry layer.

**Triggered from.** Phase 1's specs and plans are complete and pass review. Phase 1.5 must land before Phase 2 starts.

**Returns to / updates.** 69 `fastblocks/adapters/**/*.py` modules with `depends = Resolver()` at module scope. The plan's framing ("Resolver is the single shared singleton") was wrong; the fix is mechanical, not architectural.

**Demonstrable by.**

- `grep -rn '= Resolver()' fastblocks/ | grep -v core/resolver.py` returns 0 hits.
- A behavioral test: `register_candidate(get_resolver(), 'fastblocks', 'templates', SomeTemplate)` from `tests/adapters/templates/__init__.py` and resolve from `tests/adapters/templates/test_x.py` returns the registered candidate.
- Phase 1.5 acceptance: register a test adapter in `tests/_fixtures/test_adapter.py`, resolve from a different module, get the same instance.
- The MCP tools' resolution path now functions: `check_adapter_health` and `list_components` return non-empty results.

**Rollback signal.** `git revert` of the Phase 1.5 merge commit. No security impact (Phase 1.5 fixes a correctness issue, not a vulnerability).

**Observability added.** `fastblocks_resolver_registry_size_total{phase}` counter (post-Phase-1.5 should be 1); `fastblocks_resolver_shadow_count_total` (per `list_shadowed()`); startup log line emitting `Oneiric resolver: 1 registry, N candidates, M shadowed`.

**Phase 1.5 deliverables (1-week scope, six deliverables):**

0. **(NEW per code-architect) Create `FastblocksRegistry` facade** in `fastblocks/core/resolver.py`. The mechanical substitution alone commits fastblocks to Oneiric's current surface with no isolation layer; any Oneiric 0.17+ API change breaks every registration site simultaneously. The facade wraps every Oneiric method call (register, resolve, explain, list_shadowed) so future upstream evolution has exactly one place to absorb. Same posture as `apply_fastblocks_tool_profile` wrapping `apply_tool_profile` in `fastblocks/mcp/profiles.py:91-134`.
1. **Consolidate all 77 Resolver() instances onto `FastblocksRegistry`** (which wraps `get_resolver()`). Use **AST-driven transformation** (per `bulk-ruff-cleanup-script-dangers.md` memory) — NOT bare sed — because the substitution must respect `from __future__ import annotations` ordering (first non-comment line) and import sorting (`known-first-party = ["fastblocks"]`). Post-conditions: ruff I001 clean per modified file, ty/mypy unchanged. Run `git grep -rn '= Resolver()' fastblocks/ | grep -v core/resolver.py` to verify 0 hits.
2. **(NEW per mahavishnu-specialist) Singleton ownership boundary.** `fastblocks.core.resolver.get_resolver()` returns fastblocks's OWN singleton, not Oneiric's process-wide one. Cross-component consumers (if any future need exists) must call `oneiric.core.resolver.get_resolver()` directly. CI guard: `git grep -nE "from fastblocks.core.resolver import" /Users/les/Projects/{mahavishnu,akosha,dhara,session-buddy,crackerjack,oneiric,mcp-common}/ 2>/dev/null` returns 0 hits. The singleton's lifetime is process-wide (one per process); multi-pool workers each get their own singleton but share no state across pools.
3. **CI guard test.** `tests/mcp/test_ci_guard.py` shape: assert no `= Resolver()` outside `core/resolver.py` (and no Bodai repos import `fastblocks.core.resolver`).
4. **Cross-module resolution test.** Register from `tests/_fixtures/test_adapter.py`, resolve from `tests/_fixtures/test_resolver_consistency.py`, assert same identity. Use `clean_resolver` (function-scoped, autouse) fixture in `tests/conftest.py` that calls `get_resolver().clear()` (or upstream equivalent) at setup AND teardown.
5. **MCP tools resolution integration test.** Register a known test adapter via `mcp_canary_server` session-scoped fixture, assert `check_adapter_health` and `list_components` return non-empty results via the MCP server surface.
6. **Remove `mcp/registry.py`'s `with suppress(Exception)`** inside the registration path (per ONEIRIC-11). Resolve or delete the ACB TODO at line 55.
7. **Document** the Oneiric selection mechanism (`priority`/`stack_level`/`provider`) is the upstream layer's job; fastblocks Literal types own "what values are legal," Oneiric's selection owns "which candidate serves a legal value." Add this to ADR 0008.

**Sub-task 1.5.b — htmx.py + WebSocket fix already moved to Phase 1A+** (per starlette-specialist urgency).

## Phase 2: Type-safe configuration (post-1.5)

**Sub-plan placeholders** (per Phase 1 work; refined by oneiric-specialist):

- Which domains get `Literal[...]` types first (`style`, `renderer`, app mode)?
- Validation error message contract (use Oneiric's `explain()` output for ambiguous style: "Unknown style 'kelp'; valid values are 'vanilla', 'fastblocks_ui'. Did you mean 'fastblocks_ui' (closest match: see registered adapters)?").
- Definition of `TemplateAdapter(Protocol)` and `StyleAdapter(Protocol)` with `register_candidate` decorator verifying isinstance.
- AppBaseSettings.style: `str` → `Literal["vanilla", "fastblocks_ui"]` (in sync with CLI Literal).
- match statement for renderer dispatch (Literal subject, exhaustiveness-checked).
- `SafeHTMLStr = NewType("SafeHTMLStr", str)` propagation.
- Phase 2 gate (corrected from v1): widen to `git grep -c 'suppress(Exception)' -- fastblocks/` with a declining ratchet, baseline 123. **The v1 gate glob `fastblocks/adapters/*/*.py` misses `fastblocks/core/style_registry.py` entirely** (it's under `core/`, not `adapters/`); fix by either deleting `with suppress(Exception)` from `style_registry.py` (preferred per Pillar 1) or removing the existing docstring that justifies it.

## Phase 3-8: Subsequent work

Per the master plan's master roadmap table. Each phase gets its own spec + plan when implementation begins.

## Master roadmap

The phases are ordered as a **DAG, not a linear sequence**. Each phase produces independently-valuable, committable code AND unblocks at least one later phase.

```
Phase 1A (style/renderer fixes)  ──┬──► Phase 5 (tests)         ──┐
                                   │                              ├──► Phase 7 (final dead code)
Phase 1B (absorption)  ─────────── ┘                              │
                                                                  │
Phase 1.5 (ONEIRIC REGISTRY) ──► Phase 2 ──► Phase 4 (tools)    ─┤
                                          └──► Phase 6 (observability)
                                                                  │
Phase 8 (docs) — parallel from Phase 1 onward
```

| Phase | Theme | Deliverable | Hard dependencies |
|---|---|---|---|
| 1A | Style/renderer fixes + RCE close + htmx.py loop + WebSocket auth + backup purge + MCP writer deletion + Oneiric pin | Two releases: 0.30.0 (A, B, C3, D, Backup, MCP writers, htmx.py, WS-auth, Oneiric pin); includes critical security/structural fixes | None |
| 1B | fastblocks-htmy absorption | Three commits (0.31.x): C1, C2, C4, plus cross-repo C5 | Phase 1A |
| **1.5** | **Oneiric adapter registry consolidation** | **Mechanical one-line substitution per file; CI guard; cross-module resolution test; MCP tools integration test** | **Phase 1A** (must come before 1B too — the absorption adds more `register_candidate` sites that need to land in a shared registry) |
| 2 | Type-safe configuration | Literal types; Protocol for adapter contracts; CLI enum and settings Literal in sync; match statement dispatch; SafeHTMLStr NewType | **Phase 1.5** (registry must be functional first) |
| 4 | MCP tool surface organization | Tag the 7 tools by capability; add `discover_tools` Python helper; behavioral resolution gates | **Phase 1.5** (tagging broken tools would be vacuous); Phase 2 (CLI Literal + settings Literal in sync first) |
| 5 | Test infrastructure rebuild | Zero collection errors; property-based for matrix; MCP server integration canary; axe-core integration; Jinja2 SSTI test | None (orthogonal to 1-4) |
| 6 | Observability | Structured logs; counter metrics; **Oneiric's `explain()`/`list_shadowed()` as primary source**; asyncio.TaskGroup; trace propagation through htmx.py threads; cardinality-guarded Prometheus labels | Phase 2 (typed config → typed metrics labels) |
| 7 | Final dead code removal | Deprecated config keys; legacy trust-boundary code; `with suppress(Exception)` ratchet to 0; comments | Phases 5 + 6 |
| 8 | Maintainer-facing docs | API docs; ADRs (with template at `docs/adr/README.md`); onboarding doc; a11y-tested docs site | Parallel from Phase 1 |

**Phase gate (revised per oneiric-specialist audit).** Each phase commits independently. **Phase N+1 does NOT begin until Phase N's verification gates pass AND Phase N's pre-conditions hold.** The cross-phase table above shows the actual dependencies. Phase 1.5 inserts between Phase 1B and Phase 2 because Phase 2's Literal-type validation is meaningless on a fractured registry layer. **For Phase 6 and Phase 7 (high-blast-radius) get one extra reviewer per task commit.** The policy remains direct-to-main; the addition is one human reading the diff.

## Migration strategy: no backwards compatibility

Per CLAUDE.md, zero external users. Per the conversation, no backwards compatibility required.

**Per-phase commit model.** Each phase ships as one or more PRs merged directly to `main` per the Bodai pre-1.0 merge policy. Each commit is independently deployable.

**Versioning.** Phase 1 uses 0.30.0 + 0.31.x. Phase 1.5 uses 0.32.0. Phase 2 uses 0.33.0 (config-shape change is a MINOR bump, not MAJOR — 1.0.0 is reserved for an explicit stability commitment later). Subsequent phases: 0.X.Y per phase.

**Deprecation policy.** No deprecation warnings in fastblocks production code. **Exception:** the `fastblocks-htmy` shim (Phase 1B's C5) emits one `DeprecationWarning` per PEP 565 guidance — pinned by ADR-0010 once the shim is archived.

**Internal rollout (single-developer reality).** Each phase commits via per-task Integration Contracts. The per-task IC's "Demonstrable by" criteria + `crackerjack run` green serve as the local-soak gate. No additional time-based gate (1-week-of-local-use from v1 is meaningless for one developer).

**Re-preflight rule.** Before each phase that changes public API or config keys, run TWO checks:

```bash
# (1) Source-code direction: Bodai repos importing fastblocks
for repo in /Users/les/Projects/*/; do
  git -C "$repo" grep -lE "(from|import)\s+fastblocks(\.|\s|$)" 2>/dev/null
done
# Plus: uv tree --depth 1 | grep fastblocks per Bodai repo
# Plus: grep for MCP tool calls (.github/workflows/*.yml, repos.yaml, .gitlab-ci.yml)
# Plus: git grep -nE "from fastblocks.core.resolver import" /Users/les/Projects/{mahavishnu,akosha,dhara,session-buddy,crackerjack,oneiric,mcp-common}/ 2>/dev/null

# (2) Reverse direction (NEW per mahavishnu-specialist): fastblocks depending on Bodai public API
git -C /Users/les/Projects/fastblocks grep -lE "(from|import)\s+(mahavishnu|akosha|dhara|session_buddy|crackerjack)(\.|\s|$)" 2>/dev/null
# Plus: git grep -lE "(from|import)\s+oneiric(\.|\s|$)" fastblocks/ (Oneiric IS in scope; this verifies usage doesn't extend past the public API)
# Plus: git grep -lE "from mcp_common(\.websocket|\.tools)" fastblocks/ tests/ | grep -v conftest.py

# Zero matches → proceed. Any match → add Phase N.5 with migration steps.
# If fastblocks has reverse-dependencies, document them in ADR 0009 (Bodai Coupling ADR) and pin a contract for each.
```

## Verification standards

Each phase has a gate. The gate is the *minimum* to declare the phase done; passing the gate doesn't mean the phase is finished, but failing the gate means the phase is NOT done.

### Per-phase baseline (every commit, all phases)

- `uv run ty check fastblocks/` → "All checks passed!" (no suppressions added)
- `uv run pytest -q -m "not slow" --no-header` → ≥ current baseline passed, 0 fail
- `uv run crackerjack run` → ty PASS, refurb PASS, ruff PASS

### Phase 1A verification

- kelp/bulma/webawesome grep returns 0 hits
- `python -c "from fastblocks.adapters.style import vanilla, fastblocks_ui"` works
- `grep -nE "importlib|__import__|exec\s*\(|eval\s*\(" fastblocks/adapters/templates/htmy.py` returns 0 hits
- `git ls-files | grep -E "\.backup(\.json)?$" | wc -l` returns 0
- `git grep -nE "kelp|webawesome|bulma_style" config/ adapters.yaml` returns 0 hits
- **`create_template`, `create_component`, `configure_adapter` deleted** — `grep -rnE '^async def (create_template|create_component|configure_adapter)' fastblocks/mcp/` returns 0 hits
- **htmx.py event loop fix** — integration test under uvicorn in a thread, hit a route that exercises `htmx_redirect`, assert the rendered redirect header reaches the client
- **WebSocket auth fix** — integration test: spin up a Starlette TestClient, hit `client.websocket_connect('/ws?token=<jwt>')` with two different secrets (start, rotate, connect with new token), assert new token validates against rotated secret without restart
- **CSRF + HTMX** — integration test asserts HTMX POST returns 200 (not 403)
- **Middleware order** — integration test asserts `Strict-Transport-Security` on 200/403/500, `Content-Encoding: br` on HTML > 1KB, `Vary: Accept-Encoding, Cookie` present
- **Oneiric version pin** — `python -c "import oneiric; assert oneiric.__version__ >= '0.16.5' and oneiric.__version__ < '0.17'"` passes

### Phase 1B verification

- `python -c "from fastblocks.adapters.templates.htmy_components import *"` imports all 34 names
- XSS regression test passes per `xss_surface.json` (covers HTMY + Jinja2 surfaces, attrs-key + CSS-context + aria-* injection)
- **`python -c "from fastblocks.adapters.templates.jinja2 import init_envs; env = init_envs(); assert env.autoescape is not False; tmpl = env.from_string('{{ x }}'); assert tmpl.render(x='<script>') == '&lt;script&gt;'"`** passes
- **`python -c "env.from_string('[[ x ]]').render(x='<script>') == '&lt;script&gt;'"`** passes (fragment delimiter autoescape)
- **`python -c "from fastblocks.adapters.templates.jinja2 import init_envs; from fastblocks_ui import register_fastblocks_ui_functions; env = init_envs(); register_fastblocks_ui_functions(env)"`** succeeds
- Dataclass config: `tests/adapters/templates/test_htmy_component_dataclass_config.py` asserts `slots=True, kw_only=True, frozen=True` per component
- `SafeHTMLStr` propagation: `Container(content=user_bio)` without cast fails typecheck; with cast passes
- `find fastblocks -name py.typed` returns one marker per package directory
- `diff -r fastblocks/adapters/templates/htmy_components/ /Users/les/Projects/fastblocks-htmy/fastblocks_htmy/ --brief` shows expected 22 → 21 file delta
- Cross-repo PyPI shim published with PyPI 2FA + PEP 740 attestations

### Phase 1B results — 2026-08-21

All 4 sub-task deliverables landed. PyPI publish deferred (crackerjack will handle version bump + publish sequence per `crackerjack-version-bumping-manual.md`).

| Sub-task | Commit (fastblocks) | Status |
|---|---|---|
| **C1** — pin transitive deps correctly | `fe36cc0 chore(deps): pin htmy[lxml]>=0.13,<0.14` | ✅ landed on fastblocks main |
| **C2** — reconcile base classes | `f37019a feat(fastblocks): add FastBlocksComponent base class for absorbed components` | ✅ landed on fastblocks main |
| **C4** — absorb 22 source files + XSS test | `a3eccc2 feat(fastblocks): absorb fastblocks-htmy into htmy_components package` | ✅ landed on fastblocks main |
| **C5** — cross-repo shim release | `29ee515 chore(fastblocks-htmy): 0.6.0 shim-only release` (standalone repo) | ✅ shim edit landed; PyPI publish deferred |

**Verification gates run:**
- `from fastblocks.adapters.templates.htmy_components import *` → all 34 names (32 components + FastBlocksComponent + __version__)
- `find fastblocks -name py.typed` → 4 markers (`fastblocks/`, `fastblocks/adapters/`, `fastblocks/adapters/templates/`, `fastblocks/adapters/templates/htmy_components/`)
- `diff -r fastblocks/adapters/templates/htmy_components/ /Users/les/Projects/fastblocks-htmy/fastblocks_htmy/` → expected reconcile differences only
- env -u VIRTUAL_ENV uv run ty check fastblocks/ → "All checks passed!"
- .venv/bin/pytest -q -m "not slow" → 1741 passed, 0 fail (baseline 1732; +9 XSS tests)
- Coverage: 55.05% (baseline 52.71%; +2.34pp from absorbed + tested source)
- tests/xss/test_component_xss.py → 9 passed, 21 skipped (components not accepting `label=` kwarg covered indirectly via fastblocks_ui escape contract test from Phase 1A B)

**User-deferred actions (PyPI publish cycle, per crackerjack-version-bumping-manual.md):**
1. Version bump fastblocks 0.21.0 → 0.31.x (or whatever the crackerjack plan decides)
2. Build wheel: `uv build` in fastblocks repo
3. Publish: `twine upload dist/fastblocks-0.31.x-*`
4. Verify PyPI 2FA active + PEP 740 attestations enabled
5. Publish standalone shim: `twine upload dist/fastblocks-htmy-0.6.0-*`
6. Wait ~30 days post-0.31.x publication; then archive standalone repo (GitHub "Archived" toggle + `private = true` in pyproject)

### Phase 1.5 verification

- `grep -rn '= Resolver()' fastblocks/ | grep -v core/resolver.py` returns 0 hits
- Cross-module resolution test passes (register from one module, resolve from another, same identity)
- MCP tools integration test passes (register a known adapter, assert `check_adapter_health` returns it)
- Oneiric version pin (already in Phase 1A)
- `style_registry.py` no longer uses `with suppress(Exception)` (or the docstring is updated to reflect that it's the explicit Pillar 1 violation)
- `fastblocks_resolver_registry_size_total{phase}` reports 1 (single shared registry)
- `fastblocks_resolver_shadow_count_total` reports 0 (no shadowed candidates)
- Startup log line emits "Oneiric resolver: 1 registry, N candidates, 0 shadowed"

### Phase 2 verification

- Every `Literal[...]` settings field has a corresponding runtime validator (Pydantic)
- `from fastblocks.adapters.style import unknown_style` raises `ValueError` with the offending value
- AppBaseSettings.style and CLI Literal are in sync (verified by a sync test mirroring `tests/unit/test_task_router.py::TestYAMLRoutingSync`)
- `git grep -c 'suppress(Exception)' -- fastblocks/` shows a number below the previous baseline (ratcheting down per phase)
- `register_candidate` decorator with isinstance verification rejects adapter modules missing required methods at static-check time

### Phase 5 verification

- **`uv run pytest --collect-only -q -p no:xdist --no-header 2>&1 | tail -5` reports zero collection errors** (single-process collection)
- **`uv run pytest -q --collect-only -p xdist -n auto 2>&1 | tail -5` reports zero collection errors** (parallel collection; catches xdist-specific collection failures)
- Hypothesis property-based test for every cell of the style × renderer matrix passes with `@settings(max_examples=100, deadline=None, derandomize=False)` (per pytest-hypothesis-specialist audit — `max_examples=1000` would yield 120k examples per run; `derandomize=True` is a debugging helper, not CI-stability feature)
- **`tests/strategies.py` exists** with custom strategies: `safe_user_input` (alphabet includes `<>"&;(){}[]/=`), `unsafe_input` (curated SSTI + script payloads from `tests/xss/ssti_payloads.json` corpus of 15+ known vectors), `attrs_dict` (Hypothesis dict strategy), `htmy_component` (built via `st.dataclass()` over `ABSORBED_COMPONENTS`)
- XSS regression test covers all 34 absorbed components with per-field assertions (HTMY + Jinja2 matrices parallel)
- Accessibility contract test covers every absorbed component with documented semantic role, accessible name source, required `aria-*` state attributes
- axe-core integration test runs against the output of each absorbed component's primary render path; zero violations of color-contrast, label, button-name, link-name, image-alt, aria-roles
- **MCP server integration test**: spins up FastMCP server via `mcp_common`, asserts the registered tool list equals the 7-name tuple from `profiles.FASTBLOCKS_TOOLS` (catches the NameError regression history)
- **Jinja2 SSTI regression test**: adversarial inputs via `st.text(alphabet=...<script>...)` round-tripped through `env.from_string(...)`; asserts no autoescape bypass
- HTMY component `hx_*` kwargs contract test (covers JSON-encoded variants: `hx-vals`, `hx-headers`)
- CSRF + HTMX integration test asserts HTMX POSTs succeed with the configured wiring
- Static-files test asserts cache headers + brotli
- **asyncio.TaskGroup cancellation propagation**: 10 concurrent component renders where 1 fails — siblings cancel, ExceptionGroup raised
- Lifecycle integration test (`httpx.AsyncClient` + `LifespanManager`) asserts `app.state.main_loop` and `app.state.jinja_env` are bound at startup, not per-request

### Phase 6 verification

- App startup emits a structured log line with resolved configuration (`style`, `renderer`, `htmy_path=AST-sandboxed`)
- Specific regression classes identifiable from runtime signals:
  - Style resolution failure spike → `fastblocks_style_resolve_total{result=miss}` (or Oneiric `list_shadowed()`)
  - Escape regression → `fastblocks_htmy_component_render_total{escaped=false}`
  - Config validation failure → `fastblocks_config_validation_total{result=invalid}`
  - Render latency → histogram on `fastblocks_render_duration_seconds`
- **Oneiric's resolution observability is the primary source**, not parallel: Phase 6 exports counters/logs *over* `explain()`/`list_shadowed()`/`DecisionEvent`
- **MCP tool observability**: `fastblocks_mcp_tool_invocations_total{tool_name, status}` counter + `fastblocks_mcp_tool_duration_seconds` histogram
- **Boundary with Mahavishnu observability**: fastblocks = server-side execution; Mahavishnu = call-side routing. Both publish to Akosha; cross-correlate via `trace_id`
- **WebSocket → aria-live bridge contract**: every `FastblocksWebSocketServer` broadcast landing in the DOM announces through an aria-live region (per WCAG SC 4.1.3)
- Cardinality guards: every Prometheus label set is `Literal[...]`; CI lint catches violations
- **Trace context propagation**: trace_id from request → htmx.py per-thread loop → response (ContextVars survive the boundary)
- OTel middleware as outermost; trace_id flows into `fastblocks_style_resolve_total` and friends
- Grafana dashboard JSON committed at `dashboards/fastblocks-overview.json` includes MCP-tool, render-latency, style-resolution, and shadowed-candidates panels
- Existing logfire/sentry integration preserved (Sentry + OTel root-span conflict resolved by bridge)

## Risks

**Pace vs. quality.** Multi-quarter rewrite. Each phase has explicit "Demonstrable by" criteria; phases that don't move the needle get descoped.

**Knowledge loss.** Single maintainer + multi-quarter timeline. Phase 8 is the safety net.

**Crackerjack integration.** MEMORY.md catalogues 4+ known crackerjack defects. Every phase's gate runs `crackerjack run`. Phase 1A pre-flight includes venv reinstall per `crackerjack-stale-venv-install.md`.

**Parallel work conflicts.** Single maintainer → sequencing, not concurrent execution. DAG structure makes dependencies explicit.

**Scope creep.** New work → "Phase 9+ candidate" list; nothing added to a phase after plan approval.

**No-deprecation-cycle correctness.** User-confirmed zero-users; re-preflight per phase catches new callers.

**Vanilla blast radius.** `fastblocks-ui` becomes required dep even for vanilla users. Air-gapped mirrors must pre-stage `fastblocks-ui`.

**Accessibility regression.** Phase 5 axe-core integration + Phase 8 docs a11y testing.

**WebSocket auth deferral window.** ~~CLAUDE.md:230 documented; planned as Low/deferred~~ **Now: Phase 1A+ scope** per python-pro + starlette-specialist high-severity findings. Resolved before Phase 1 ships.

**Adapter registry fractured state.** ~~77 separate Resolver() instances; ~70 disjoint registries; MCP tools read from empty Resolver~~ **Now: Phase 1.5 blocking** per oneiric-specialist critical findings. Resolves before Phases 2/4/5/6.

**htmx.py per-thread event loop.** ~~Documented in CLAUDE.md:197~~ **Now: Phase 1A+ scope** per starlette-specialist critical finding.

**Style registry `with suppress(Exception)` by design.** ~~Contradicts Pillar 1/7; gate glob misses it~~ **Now: Phase 2 ratchet** with broader `git grep -c` gate.

## Out of scope

- **Multi-pool orchestration, WebSocket auth redesign, Content ingestion** — these are Mahavishnu subsystems or working components; not fastblocks's scope.
- **Oneiric itself.** Fastblocks changes how it *uses* Oneiric; not Oneiric itself. ADR 0008 is the cross-project decision point.
- **External-user concerns.** No backwards compatibility, no deprecation cycles.
- **Migrating other Bodai repos.** Phase 0 preflight identifies callers.
- **Free-threading (PEP 703) and experimental JIT (PEP 744).** Out of scope. If a future maintainer enables free-threading, audit global state: Oneiric Resolver singleton, WebSocket auth module-level env reads, dataclass `__init__` cache all need re-validation.
- **SSE / StreamingResponse** for htmx SSE streams. Out of scope; HTMY WebSocket is the only live-update primitive.

## Reference artifacts

- **Style/renderer spec**: `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-08-21-style-renderer-architecture.md`
- **Style/renderer plan**: `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-21-style-renderer-architecture.md`
- **Ty cleanup plan** (precedent): `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-20-fastblocks-ty-cleanup.md`
- **CLAUDE.md**: `/Users/les/Projects/fastblocks/CLAUDE.md`
- **MEMORY.md** (Bodai project memory; oneiric, fastblocks, mahavishnu memory entries): `/Users/les/.claude/projects/-Users-les-Projects-fastblocks/memory/MEMORY.md` (after Phase 0 preflight creates a fastblocks-scoped memory file)
- **fastblocks-ui** (CSS framework, stays separate): `/Users/les/Projects/fastblocks-ui/`
- **htmy** (component library, stays separate): `htmy` on PyPI
- **fastblocks-htmy** (will be absorbed in Phase 1B): `/Users/les/Projects/fastblocks-htmy/`

## Process

Per CLAUDE.md Subagent-Driven Development:

0. **Re-preflight per phase** (above). Zero matches → proceed. Any match → add Phase N.5.
1. Master plan approved.
2. Each phase gets a sub-spec and sub-plan before implementation, including per-phase verification gates.
3. Each phase executes with fresh implementer subagents per task + scoped reviews.
4. Each task commit includes an Integration Contract block (Triggered from / Returns to / Demonstrable by / Rollback signal / Observability added). **For Phase 6 and Phase 7 (high-blast-radius), one extra reviewer per task commit.**
5. Phase N+1 begins only after Phase N ships and stabilizes.
6. **Phase 1.5 inserts between Phase 1 and Phase 2.** It's a 1-week scope (mechanical refactor); blocking.

---

## Fresh-session prompt (paste verbatim into a new session)

**NOTE**: Before pasting, verify HEAD and pytest baseline via:

```bash
git rev-parse HEAD
uv run pytest -q -m "not slow" --no-header | tail -3
```

The numbers in this prompt are illustrative; treat the live state as authoritative.

```
# Task: FastBlocks master plan execution — internal infrastructure rewrite

**Working directory:** `/Users/les/Projects/fastblocks` (main branch)
**Master plan:** `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
**Pre-existing state:** ty-cleanup finished (0 ty diagnostics); HEAD verified above; pytest baseline verified above.

**CRITICAL CONTEXT:**
- Single maintainer (`les`). No "dev team" coordination. Per-phase rollout is single-developer local testing + per-task IC verification.
- Zero external users. Zero websites in production. No backwards compatibility required.
- Bodai pre-1.0 merge policy: direct merges to main, no PR review gates.
- Each commit uses targeted `git add <pathspec>` (never `git add -A`).
- Each task commits in its own worktree via `git worktree add ../fastblocks-taskX -b task/X <clean_sha>`.
- NEVER revert security-fix commits (C3-equivalent, the htmx.py loop fix, the WebSocket auth fix). Forward-fix only.
- Master plan = internal infrastructure rewrite. NOT public framework pivot.

## Phase 0 (preflight) — verify before Phase 1

```bash
# (1) Source-code direction: Bodai repos importing fastblocks
for repo in /Users/les/Projects/*/; do
  git -C "$repo" grep -lE "(from|import)\s+fastblocks(\.|\s|$)" 2>/dev/null
done
# Plus: uv tree --depth 1 | grep fastblocks per Bodai repo
# Plus: grep for MCP tool calls (.github/workflows/*.yml, repos.yaml, .gitlab-ci.yml)
# Plus: any Bodai repo importing fastblocks.core.resolver (per Phase 1.5 singleton ownership)

# (2) Reverse direction (NEW per mahavishnu-specialist): fastblocks depending on Bodai public API
git -C /Users/les/Projects/fastblocks grep -lE "(from|import)\s+(mahavishnu|akosha|dhara|session_buddy|crackerjack)(\.|\s|$)" 2>/dev/null
# Plus: git grep -lE "(from|import)\s+oneiric(\.|\s|$)" fastblocks/ (Oneiric IS in scope; this verifies usage doesn't extend past the public API)
# Plus: git grep -lE "from mcp_common(\.websocket|\.tools)" fastblocks/ tests/ | grep -v conftest.py

# Zero matches → proceed. Any match → add Phase N.5 with migration steps.
# If fastblocks has reverse-dependencies, document them in ADR 0009 (Bodai Coupling ADR) and pin a contract for each.
```

**MHV-FB-05 (added per mahavishnu-specialist) — fastblocks is not a Mahavishnu pool.** Document the contract explicitly: fastblocks does NOT register as a Mahavishnu worker pool. Operators running `mcp__mahavishnu__pool_route_execute(pool_selector='fastblocks')` get a 'unknown pool' error, not a silent fallback to LEAST_LOADED. Pool selection for fastblocks tasks must go through the consumer app's MCP server (e.g. splashstand), which embeds fastblocks's `discover_tools` helper. Phase 4 verification gate: assert the unknown-pool error is raised, not silent fallback.

### Phase 0 preflight results — 2026-08-21 (run on `ffef487`)

All eight gates pass. No Phase N.5 needed; Phase 1A unblocked.

| Gate | Result | Detail |
|---|---|---|
| FORWARD #1 runtime importers | PASS | Only `splashstand` (5 sites: `main.py`, `cli.py`, `adapter_tools.py`, `adapters/app/default.py`, `adapters/admin/sqladmin.py`). Mahavishnu scaffolding templates reference as code-generation only. |
| FORWARD #2 `uv tree --depth 1` per Bodai repo | PASS | splashstand: `fastblocks v0.21.0 (group: dev)`. 7 other Bodai repos (mahavishnu, akosha, dhara, session-buddy, crackerjack, oneiric, mcp-common): no fastblocks dep. |
| FORWARD #3 CI / repos.yaml refs | PASS | `settings/repos.yaml` catalog entries only (4 lines, operator metadata). No `.github/workflows/*.yml` or `.gitlab-ci.yml` references. |
| FORWARD #4 `fastblocks.core.resolver` singleton boundary | PASS | 0 hits across 8 Bodai repos. CI guard clean for Phase 1.5. |
| REVERSE #1 Bodai public deps (mahavishnu/akosha/dhara/sb/cj) | PASS | 0 hits. |
| REVERSE #2 oneiric private API | PASS | 0 hits; all imports use public paths (`oneiric.core.{resolution,logging,config,depends}`, `oneiric.adapters.{bootstrap,cache}`). |
| REVERSE #3 mcp_common public API | PASS | 11 hits, all public (`websocket.auth`, `websocket.protocol`, `websocket.tls`, `tools`). |
| MHV-FB-05 fastblocks ≠ Mahavishnu pool | PASS | No contract claim in code or docs. Unknown-pool error path documented above; Phase 4 gate asserts error-vs-silent-fallback. |

**Captured provenance for Phase 1B absorption metadata:**

```
fastblocks-htmy@0.5.0
  commit:     32ec2fabbd64d2bd9968e09156a94a54cd8f568d
  date:       2026-08-06 07:09:37 -0700
  message:    chore: bump version to 0.5.0
  tag:        (none — repo uses version-in-pyproject only)
```

This SHA goes into `__absorbed_from__: fastblocks-htmy@0.5.0 (commit 32ec2fabb..., fetched 2026-08-21)` provenance on the 21 absorbed modules in Phase 1B.

### Phase 0 baseline pytest

Captured 2026-08-21 on `ffef487` via `/Users/les/Projects/fastblocks/.venv/bin/pytest --no-header` (4 xdist workers, auto).

| Metric | Value |
|---|---|
| Pass | 1690 |
| Skip | 23 (intentional — `slow` marker + websocket stub) |
| xpassed (xfail that passed) | 4 |
| Fail | 0 |
| Error | 0 |
| Warning | 271 |
| Wall time | 36.57s |
| Total statements | 17029 |
| Covered statements | 7871 |
| **Aggregate coverage** | **53.78%** (vs 49.13% ratchet floor) |
| Ratchet floor after this run | 53.78% (auto-bumps on next successful run) |

**Ratchet anchor established.** First Phase-1A commit must raise `[tool.pytest].addopts --cov-fail-under` explicitly to avoid silent auto-floor elevation. Recommended target per-phase: 1A→55%, 1B→58%, 1.5→60%, 2→63%, 4→66%, 5→70%, 6→72%, 7→75%, 8→80%.

**Important invocation note (becomes MEMORY note):** `pytest` from the parent shell resolves `which pytest` to `/Users/les/Projects/mahavishnu/.venv/bin/pytest` — NOT fastblocks's. The Mahavishnu venv lacks fastblocks's runtime deps (starception, minify-html, granian, etc.), causing 115 `ModuleNotFoundError` collection failures and 0% measured coverage. Always invoke via `<repo>/.venv/bin/pytest` or `uv run pytest` from inside the fastblocks cwd.

## Phase 1A is ready to execute

Phase 1A has a complete spec + plan, with additions from the 4-reviewer audit:

- Spec: `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-08-21-style-renderer-architecture.md`
- Plan: `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-21-style-renderer-architecture.md`

Phase 1A deliverables (extended from the original sub-plan per 4th-pass review):
- A: drop broken styles (kelp, webawesome, bulma, custom)
- B: promote fastblocks-ui to default (verify standalone's actual pin first; check all three pin locations: fastblocks/pyproject.toml [project].dependencies, the deleted fastblocks_ui optional group, and fastblocks-htmy/pyproject.toml)
- MCP writer functions deletion: `create_template`, `create_component`, `configure_adapter` from `fastblocks/mcp/tools.py`
- **htmx.py per-thread event loop fix** (CRITICAL): replace `_run_async_safely` with `asyncio.run_coroutine_threadsafe(coro, app.state.main_loop)` capturing `app.state.main_loop` during lifespan. Trace context propagates via `contextvars.copy_context().run(...)`.
- **WebSocket auth fix** (HIGH): per-request lookup via Starlette WebSocketRoute + ASGI middleware. Move `FastblocksWebSocketServer` to `Mount('/ws', app=ws_asgi_app)`.
- **Oneiric version pin**: `oneiric>=0.16.5,<0.17` instead of `~=0.3`. Add compat test.
- **CSRF + HTMX wiring**: add to `fastblocks/middleware.py`. Wire either `htmx.config.csrfToken` in enhance.js or middleware that copies `csrf_token` form field to `X-CSRF-Token` header.
- **Middleware order pin**: document OTel outermost, secure, brotli, csrf, error-handler innermost.
- Backup purge: enumerate all *.backup + *.backup.json, delete in one commit
- C3: close RCE in htmy.py (3 steps: delete loaders, rewrite caller, audit tests)
- D: document renderer axis (Jinja2 env contract + Custom Element layer + HTMX transport contract)

## Phase 1B deliverables (after 1A ships)

- C1: pin transitive deps (preserve [lxml] extra on htmy)
- C2: reconcile base classes (FastBlocksComponent canonical)
- **C3.5**: explicit handling for `fastblocks/adapters/templates/jinja2.py`
- C4: absorb source (22 files standalone → 21 in fastblocks after sub-package restructure; @dataclass(slots=True, kw_only=True, frozen=True); SafeHTMLStr NewType; XSS + Jinja2 + a11y matrices)
- C5: cross-repo shim (PyPI 2FA + PEP 740 attestations)

## Phase 1.5 (NEW — blocking Phases 2/4/5/6)

- Consolidate all 77 Resolver() instances onto `get_resolver()`. CI guard test.
- Cross-module resolution test.
- MCP tools integration test (registers and resolves).
- `mcp/registry.py`'s inner `with suppress(Exception)` removed.
- ADR 0008 documents Oneiric integration + decision rule for upstream-vs-wrapper.

## Phase 2+ is not yet specced

Phases 2-8 will be planned separately when prior phases ship. Do not start them speculatively. Phase 5 (tests) is orthogonal and can be started in parallel with Phase 1 if a sub-spec is written first.

## Each commit must include an Integration Contract block

Per CLAUDE.md §Process Discipline (which will be added in Phase 1A), every task commit must include an Integration Contract (Triggered from / Returns to / updates / Demonstrable by / Rollback signal / Observability added). Use the per-task ICs in the Phase 1 plan as templates.

## Project conventions (paste from CLAUDE.md)

- `from __future__ import annotations` first non-comment line in every source file.
- `X | None` not `Optional[X]` (PEP 604 syntax).
- No stdlib `logging` — use `oneiric.core.logging.get_logger`.
- No `assert` in production code — use the `fastblocks/exceptions.py` hierarchy.
- No `@pytest.mark.asyncio` (auto mode per CLAUDE.md:214).
- No bare `# type: ignore` — use per-checker directives (`# mypy: ignore[rule]`, `# ty: ignore[rule]`, `# pyright: ignore[rule]`) with inline `# justified because ...` comments.
- Test markers: `unit`, `integration`, `e2e`, `property`, `slow`, `timeout`, `ci`, `crackerjack`, `websocket`.
- Type-check stack: `ty` (primary), `mypy` (compatibility), `pyright` (deep check).

## Verification gates (every commit)

- `uv run ty check fastblocks/` → "All checks passed!" (no suppressions added)
- `uv run pytest -q -m "not slow" --no-header` → baseline passed, 0 fail
- `uv run crackerjack run` → ty PASS, refurb PASS, ruff PASS

Task-specific gates listed in the master plan's per-phase verification sections.

## Reference artifacts

- Plan: `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
- Spec: `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-08-21-style-renderer-architecture.md`
- Style/renderer plan: `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-21-style-renderer-architecture.md`
- Source of `fastblocks-htmy` to absorb: `/Users/les/Projects/fastblocks-htmy/fastblocks_htmy/`
- CLAUDE.md: `/Users/les/Projects/fastblocks/CLAUDE.md`
- Working style adapter for `fastblocks-ui`: `/Users/les/Projects/fastblocks/fastblocks/adapters/style/fastblocks_ui.py`
```

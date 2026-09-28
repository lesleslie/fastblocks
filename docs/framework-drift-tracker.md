---
status: active
role: tracking
kind: reference
date: 2026-09-28
last_reviewed: 2026-09-28
topic: framework-api-drift
source: docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-build-wave.md §Appendix A
related:
  - bd82e6b (constraint refresh commit)
  - 008499c (security caps commit)
  - 3247377 (v2 plan revision)
---

# Framework API Drift Tracker

**Purpose:** This is the single source of truth for the 12 framework API drift items (F-FW-1 through F-FW-12) surfaced by the Phase 2 build wave. Each entry identifies which upstream repo owns the fix, the severity, and the recommended remediation.

**Source of items:** The Phase 2 wave's v2 plan Appendix A (commit `3247377`) catalogues the 12 items as inputs to upstream issue trackers. The wave's per-task reports cite these items as the root causes of plan-vs-reality drift.

**Why a doc instead of filed issues:** Local-first triage. Each Bodai MCP server can read this file from a session; GitHub issues require a remote round-trip and don't survive offline. When an item moves to "filed" status, the entry should be updated here too.

**Owner convention:** Each entry's `target_repo` is the repo where the fix must land. The Bodai ecosystem repo registry (see memory `bodai-repo-registry.md`) is authoritative for repo URLs.

## Status legend

| Status | Meaning |
|---|---|
| `planned` | Identified, no upstream work started |
| `in-progress` | Someone is actively working the item |
| `filed` | GitHub issue opened upstream; link in entry |
| `done` | Fix landed upstream; pin bumped in fastblocks |
| `wontfix` | Decision made not to fix; rationale in entry |

## Items

### F-FW-1 [Major] — `HybridTemplatesManager.render_hybrid(component, layout=...)` does not exist

- **target_repo:** `fastblocks` (framework)
- **status:** planned
- **summary:** Spec §B3 promises this API. Installed class `fastblocks/adapters/templates/hybrid.py` ships only `render_fragment`, `initialize`, `validate_template`, etc. B3 works around this by composing HTMY + Jinja2 manually in `routes/greeting.py::_render_hybrid`.
- **recommendation:** Add the missing public method. Implementation pattern: compose HTMY component + Jinja2 layout using the same template-engine-resolution machinery as `render_fragment`.
- **blocks:** Examples that need true hybrid rendering (B3 currently fakes it).

### F-FW-2 [Medium] — `oneiric.core.resolution.resolve_adapters` does not exist

- **target_repo:** `oneiric`
- **status:** planned
- **summary:** B2's `/adapter-matrix` route iterates `get_resolver().registry._candidates` directly because no public list-all API exists. Verified by `python -c "from oneiric.core.resolution import resolve_adapters"` → ImportError.
- **recommendation:** Add `Resolver.list_candidates(domain: str | None = None) -> list[Candidate]` to oneiric. Migrate B2 to use the new public API once it ships.

### F-FW-3 [Medium] — `fastblocks.adapters.register_default_adapters` does not exist

- **target_repo:** `fastblocks` (framework)
- **status:** planned
- **summary:** Spec §B1 / B3 imply this function. `fastblocks/adapters/__init__.py` is a docstring. `FastBlocks()` self-registers through Oneiric.
- **recommendation:** Either add the helper for ergonomic clarity, OR document that `FastBlocks()` self-registers and the helper is not needed. **Faster:** the latter. **Recommended:** add a 1-line helper that calls into Oneiric, then update the scaffold to import it.

### F-FW-4 [Low] — `oneiric.adapters.@adapter` decorator does not exist

- **target_repo:** `oneiric`
- **status:** planned
- **summary:** The decorator pattern `from oneiric.adapters import adapter` is documented but not implemented. Real registration is `register_candidate(get_resolver(), domain=..., key=..., factory=..., metadata=...)` from `fastblocks.adapters.oneiric_helper`.
- **recommendation:** Either implement the decorator as a thin wrapper around `register_candidate`, OR update oneiric docs to remove the decorator reference. Recommended: implement the decorator for ergonomics.

### F-FW-5 [Low] — `oneiric.core.resolution.resolve_adapter` standalone import does not exist

- **target_repo:** `oneiric`
- **status:** planned
- **summary:** The standalone function isn't importable. Real API is `Resolver.resolve(domain, key)` via `get_resolver().resolve("fastblocks", "hybrid")`.
- **recommendation:** Either add a module-level `resolve_adapter(domain, key)` shortcut, OR update consumers to use `get_resolver().resolve(...)`. Recommended: shortcut.

### F-FW-6 [Medium] — `htmy.Component` is Union type, not base class

- **target_repo:** `htmy`
- **status:** planned
- **summary:** `class GreetingCard(Component)` raises `TypeError` at import. Real pattern is `@component def greeting_card(props, context) -> ...` decorator. Verified by B3 implementer's empirical work.
- **recommendation:** Update HTMY docs to lead with the `@component` decorator pattern. Consider whether to provide a `Component` class for inheritance-based use cases (would require designing what methods the class should have).

### F-FW-7 [Low] — `fastblocks.templates.get_template` does not exist

- **target_repo:** `fastblocks` (framework)
- **status:** planned
- **summary:** Spec §B3 implies this. Each example uses a local `templates/__init__.py` Jinja2 wrapper (the only working pattern).
- **recommendation:** Document the local-wrapper pattern as the canonical scaffold approach. Or add a `fastblocks.templates` module with the wrapper.

### F-FW-8 [Medium] — Oneiric registration redundancy

- **target_repo:** `fastblocks` (framework) + `oneiric`
- **status:** planned
- **summary:** `HybridTemplatesManager` is registered under three keys: `"hybrid"` (B3 example), `"hybrid_template_manager"` (framework), `"templates"` (framework). Three registrations of effectively the same factory. **Post-wave cleanup Task 3 (F3.2) drops the example's `"hybrid"` registration** — but the framework-side duplication remains.
- **recommendation:** Consolidate to one key. Or document why three exist (semantic aliasing for different use cases).

### F-FW-9 [Major] — `fastblocks-ui` `card()` / `navbar()` accept-and-ignore common kwargs via `**attrs`

- **target_repo:** `fastblocks-ui`
- **status:** planned
- **summary:** **Root cause of CF-1** in the wave. `card(title="Async", body="...")` produces a card with no `<header>` element (title absorbed as HTML attribute). `navbar(is_sticky=True)` produces a `<nav>` with no brand content (positional `brand=` arg required).
- **recommendation (highest priority):** Make fastblocks-ui helpers strict — accept only known kwargs, raise on unknown. This converts silent user-traps into loud errors. The current `**attrs` catch-all is the framework-side root cause of an entire class of consumer bugs.
- **cross-block:** Once fixed, B1 starter + B2 landing both need verification that the corrected kwargs (already applied at `6b6cb57`) still match.

### F-FW-10 [Medium] — fastblocks-ui README documentation drift

- **target_repo:** `fastblocks-ui`
- **status:** planned
- **summary:** README documents macros with `ui-` prefix (`ui-card`, `ui-button`). Actual 0.9.x exports are unprefixed (`card`, `button`). The `ui-` prefix is the CSS class name (`class="ui-card"`), not the Python identifier.
- **recommendation:** Update fastblocks-ui README to use the unprefixed Python names + show the corresponding HTML class names in usage examples. Add a one-line note: "Python identifiers are unprefixed; HTML class names retain the `ui-` prefix."

### F-FW-11 [Low] — `HTMXPartialResponse` does not exist

- **target_repo:** `fastblocks` (framework)
- **status:** planned
- **summary:** Spec §B2 / §B3 imply a dedicated partial-response class. Real pattern is `HTMLResponse(...)` with `HX-Request` header check in the route.
- **recommendation:** Either add `HTMXPartialResponse` as a thin wrapper, OR document the canonical pattern (HTMLResponse + HX-Request header check) and remove the implication from specs.

### F-FW-12 [Medium] — `apps_path = Path.cwd()` frozen at module load in `fastblocks/cli.py:48`

- **target_repo:** `fastblocks` (framework)
- **status:** planned
- **summary:** Test fragility under `pytest-xdist`. Each worker imports `fastblocks.cli` once at startup in the repo CWD; subsequent `chdir` calls don't update `apps_path`. Worked around with `monkeypatch.setattr(fastblocks.cli, "apps_path", tmp_path)` in B1 tests.
- **recommendation:** Compute `apps_path` lazily inside `_scaffold_from_starter`, e.g. `apps_path = Path.cwd()` at call time. **Post-wave Task 1 (F1.2) likely touches this code; verify after that lands.**

## Cross-repo dependency notes

- **F-FW-9 (fastblocks-ui)** is the highest-impact item because it's the root cause of the CF-1 user-visible bug. Fixing it requires no API change in fastblocks itself, but consumers (including the B1 starter + B2 landing) need a one-line verification pass after the fix.
- **F-FW-1 (fastblocks)** blocks true hybrid rendering — B3 currently fakes it.
- **F-FW-8 (fastblocks + oneiric)** is partially addressed by post-wave Task 3's drop of the example-side `"hybrid"` registration. The framework-side duplication between `"hybrid_template_manager"` and `"templates"` remains.

## Triage workflow

When picking up an item:

1. Change its `status` from `planned` to `in-progress`.
2. Reference the relevant target_repo in your branch name (e.g., `fix/fastblocks-ui-F-FW-9-strict-kwargs`).
3. Land the fix in the target_repo with a cross-reference to this doc.
4. Bump any consumer constraint in fastblocks (or other consumers) that needs the fix.
5. Update the entry here to `done` with a link to the upstream PR/commit.

When closing an item as `wontfix`:

1. Update the entry's status and add a `rationale` field.
2. If the no-fix decision affects fastblocks' docs or examples, update those too.

## Update log

- **2026-09-28** — Initial creation (17 post-wave findings + 12 framework items).

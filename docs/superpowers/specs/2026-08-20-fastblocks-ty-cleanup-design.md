# FastBlocks ty Cleanup Design

**Date:** 2026-08-20
**Status:** Approved in conversation; pending written-spec review
**Repository:** `/Users/les/Projects/fastblocks`
**Primary target:** 374 ty diagnostics reported by `crackerjack run` (357 production + 18 test, per `--split`)
**Branch:** In-place on current branch (main)

## Context

`crakerjack run` reports 374 ty issues in fastblocks. Earlier-session work fixed 4 of the 19 originally-listed errors (3 were real runtime bugs). The remaining 374 are not 374 independent bugs — they collapse to ~5 root-cause patterns:

| Pattern | Count | Root cause |
|---|---|---|
| `unresolved-attribute` (`Resolver.get_sync`) | 55 | Wrong Resolver API |
| `unresolved-attribute` (`Resolver.set`) | 49 | Wrong Resolver API |
| `unresolved-attribute` (`Resolver.config`) | 41 | Wrong Resolver API |
| `unused-type-ignore-comment` | 33 | Blanket `# type: ignore` (ty expects `# ty: ignore[rule]`) |
| `invalid-await` | 28 | `await depends.get(...)` — sync return mis-await'd |
| `Self@init` + related | 18 | Methods reference attrs before init (real bug class) |
| `invalid-argument-type` | 12 | Misc wrong types |
| `call-top-callable` | 10 | Untyped factory callable |
| `unresolved-reference` | 10 | `root_path` (7), `get_adapters`, `get_adapter`, `reload_config` |
| `unresolved-import` | 6 | `oneiric.adapters.discovery` may not exist |
| `invalid-return-type` | 7 | Return type mismatches |
| `invalid-method-override` | 7 | Subclass override types wrong |
| `invalid-assignment` | 6 | `object` → typed `X | None` |
| `_sanitizer` (under `Self@_*`) | 6 | Missing init (likely real bug) |
| `redundant-cast` | 5 | Easy remove |
| `missing-argument` | 3 | `register_pkg()` called with no args |
| `not-iterable` | 2 | Misc |
| `unsupported-operator` / `too-many-positional-arguments` / `not-subscriptable` / `call-non-callable` | 4 | One-offs |

The user has confirmed: **all 374 must be addressed (374 → 0).** They want a phase-by-phase plan with verification between phases, surfacing real bugs inline rather than silently fixing them.

## Goals

- `uv run ty check fastblocks/` returns 0 diagnostics.
- `uv run pytest` still passes 1714 tests (no regression).
- `crackerjack run` reports ty PASS (0/50 or equivalent).
- All intermediate phases leave the working tree and test suite green.

## Non-goals

- Refactoring unrelated to ty diagnostics.
- Upgrading dependencies or changing the Oneiric API contract.
- Modifying tests to accommodate broken production code (test wins only if the production code is functionally correct per the documented API).
- Treating warnings as a reason to change behavior beyond fixing the suppression syntax.
- "Treating" the ratchet's vacuous PASS as evidence of clean state — the ratchet's prod dir config is broken (it looks for `crackerjack/`); the real prod count is 357.

## Approach: phased by cascade leverage

The phases are ordered so each one clears the largest number of diagnostics for the least work, with a re-count between phases to detect cascading effects.

### Phase 1a — Resolver API mapping (~145 diagnostics)

The biggest single hammer. Three wrong API patterns:

- `depends.get_sync(name)` (55) — does not exist on `Resolver`
- `depends.set(name, value)` (49) — does not exist on `Resolver`
- `depends.config.X` (41) — `Resolver` has no `config` attribute

**Procedure:**

1. Grep all uses across `fastblocks/`.
1. Read `oneiric.core.resolution.Resolver` source to confirm the actual API surface (`resolve`, `register`, `register_from_pkg`, `register_pkg`, `list_active`, `list_shadowed`, `explain`).
1. For each call site, map:
   - `get_sync(name)` → likely `resolve(domain, name)` (sync)
   - `set(name, value)` → likely `register(...)` or `register_from_pkg(...)`
   - `config.X` → likely `Resolver._config` or `resolver.config` (private) — surface-correct use may need to import the config object directly
1. Surface any cases where the mapping is unclear or where the code was calling a method that never existed. These are real-bug candidates (dead code paths or function never returned what the caller expected). Document and ask before fixing per the agreed real-bug policy.

**Verification:** `uv run ty check fastblocks/ 2>&1 | grep -c "error\|warning"` should drop ~150+.

### Phase 1b — Suppression syntax cleanup (~33 warnings)

`# type: ignore` (blanket, mypy syntax) is silently ignored by ty, which expects `# ty: ignore[rule-code]`. Many of these were written when only mypy was the type checker.

**Procedure:**

1. Grep all `# type: ignore` (without `[rule]`).
1. For each, look at the underlying diagnostic ty would emit. If the underlying code is correct, convert to `# ty: ignore[rule-code]`. If the suppression is no longer needed (the code was fixed elsewhere), remove it.
1. Verify with ty (the count should drop as new diagnostics become visible — they need addressing in subsequent phases).

**Verification:** Count of `unused-type-ignore-comment` goes to 0. Net ty diagnostic count may *increase* briefly as newly-visible errors emerge.

### Phase 1c — invalid-await cleanup (~28 errors)

`await depends.get(...)` / `await depends.resolve(...)` — `Candidate | None` is a sync object, not a coroutine.

**Procedure:**

1. Grep `await depends\.` patterns.
1. For each, drop the `await` (Candidate is the already-resolved value).
1. Surface cases where the code appears to expect an async path (e.g., calling `await` on something that wasn't the resolver result). These may be real bugs.

**Verification:** `invalid-await` count drops to 0.

### Phase 1d — Self@init / `_sanitizer` / `_publisher` (~24 errors)

Methods that reference `self._sanitizer` etc. before/aside from initialization. Some are real bugs (attribute referenced but never set).

**Procedure:**

1. Grep for class definitions containing `_sanitizer` / `_publisher` etc.
1. Verify each method's reference is preceded by a setter call (init or lazy assignment).
1. If missing, add init (real bug fix — call out per policy).
1. If typo, fix the typo.

**Verification:** `Self@init` and related vanish.

### Phase 1e — call-top-callable + Top[...] (~14 errors)

`candidate.factory()` is untyped because the factory callable is `Top[(...) -> object]`.

**Procedure:**

1. Identify the factory class/function definitions.
1. Add `__call__` return type annotations.
1. At call sites where factory is dynamic, use `cast(Callable[..., X], candidate.factory)`.

**Verification:** `call-top-callable` drops to 0.

### Phase 2 — Annotation & API-type fixes (~60 diagnostics)

Continues after Phase 1 re-count. Includes:

- `unresolved-reference` (10) — likely real bugs: `root_path` undefined (7), `get_adapters`/`get_adapter`/`reload_config` (3)
- `unresolved-import` (6) — `oneiric.adapters.discovery` may not exist; check actual module path
- `invalid-argument-type` (12) — likely `EventPriority.HIGH` passed where `EventPriority` expected (int vs enum)
- `missing-argument` (3) — `register_pkg()` needs `registry`, `package_name`, `path`, `candidates`
- `invalid-method-override` (7) — investigate overrides
- `invalid-assignment` (6) — likely the result of `depends.get_sync(...)` returning `object`; fixed upstream by Phase 1a
- `invalid-return-type` (7) — likely cascading
- `not-iterable` / `unsupported-operator` / `too-many-positional-arguments` / `not-subscriptable` / `call-non-callable` (8) — one-off fixes

**Procedure:** Iterative. After Phase 1, re-run ty and address residual diagnostics by category. Some Phase 2 items may resolve as cascading effects of Phase 1 fixes.

### Phase 3 — Easy wins (~5 diagnostics)

Remove 5 `redundant-cast` warnings.

### Phase 4 — Verification & gate

- `uv run ty check fastblocks/` → 0 diagnostics
- `uv run pytest -q -m "not slow"` → 1714+ pass, no regression
- `crackerjack run` → ty hook PASS (0/50)

## Real-bug policy

When ty diagnostics reveal code calling a method that doesn't exist (e.g., `discovery.py:249` `Resolver.get()` earlier), the agreed protocol is:

1. **Stop** — don't silently fix.
1. **Surface** — name the file, line, the wrong API call, and what the corrected API is.
1. **Ask** — confirm whether the code path is exercised (real bug) or dead code (safe to rewire).
1. **Document** — append to the spec's "Real bugs found" section so the count and resolution are tracked.

## Sequencing & reporting

- One phase at a time. Do not start Phase N+1 until Phase N's verification passes.
- After each phase, report:
  - Diagnostics before
  - Diagnostics after
  - Top 3 remaining categories
  - Any real bugs surfaced and how they were resolved
- Commit at logical boundaries (per phase, or per file when a phase spans many files).
- Do not commit the working tree's pre-existing dirty state — those modifications belong to earlier work, not this spec.

## Risks

- **Ty version drift**: The diagnostics may include "ty is more strict than mypy was" cases. If a `ty: ignore` is genuinely needed, use the correct syntax with an inline comment explaining why.
- **Cascade overcorrection**: Fixing upstream types may surface additional downstream errors that weren't visible before. This is expected — Phase 1b may briefly raise the count before Phase 2 brings it down.
- **Test pollution**: All changes are in production code (`fastblocks/`); test changes only if a test is verifying genuinely broken behavior. Test suite must remain at 1714+ passing throughout.
- **Working tree contention**: The work happens in-place on the current branch. The pre-existing dirty tree belongs to a prior session and is not part of this scope.

## Verification gates

| Gate | Command | Expected |
|---|---|---|
| Per phase | `uv run ty check fastblocks/ 2>&1 \| grep -c "error\|warning"` | Strictly decreasing |
| Per phase | `uv run pytest -q -m "not slow" --no-header` | 1714+ pass, 0 fail |
| Final | `uv run ty check fastblocks/` | "All checks passed!" |
| Final | `crackerjack run` | ty PASS (0/0 or 0/50) |

## Real bugs found (running log)

### Task 3 — Phase 1c invalid-await cleanup

- **`fastblocks/actions/gather/application.py:263`** — `await depends.get(dep_name)` inside `except (ImportError, ..., AttributeError)`. The `AttributeError` was silently swallowing the failure: `Resolver` has no `.get()` method, so the dependency map always stayed empty. Fixed to `resolve_instance(depends, "fastblocks", dep_name)` (sync). Tests pass (1714/0) — the dependency map was empty in tests too, but the failure mode is now correct.
- **`fastblocks/adapters/sitemap/_routes.py:40`** — `return depends.get(adapter.sitemap)(request)` direct call would raise `AttributeError` at runtime. Fixed to `resolve_instance(..., "fastblocks", adapter.sitemap)(request)` wrapped in try/except returning a 503 with empty `<urlset/>` body.
- **`fastblocks/adapters/templates/jinja2.py:137`** — `return depends.get(key)` with `hasattr` guard. Fixed to `resolve_instance(depends, "fastblocks", key)`; dropped the `hasattr` guard and the asyncio fallback (the canonical sync helper is the right answer).

Authorised by user via AskUserQuestion option "Fix all three to resolve_instance". Commit `9c5bf6f`.

______________________________________________________________________

## Final tally

- **Diagnostics at start**: 374
- **Diagnostics at end**: 0 (`uv run ty check fastblocks/` → "All checks passed!")
- **Pytest**: 1714 passed, 21 skipped, 4 xpassed, 0 fail
- **Crackerjack ty hook**: PASS (0/50 prod gate)
- **Real bugs found** (7 distinct issues; see inline sections above):
  1. **`Resolver.get()` Bucket B misuse** (3 sites) — `resolver.py` has no `.get()` method; `actions/gather/application.py:263`, `adapters/sitemap/_routes.py:40`, `adapters/templates/jinja2.py:137` were calling it (the first silently swallowed the `AttributeError` via `except`, the second raised at runtime, the third had a `hasattr` guard). Fixed to `resolve_instance(depends, "fastblocks", key)`. Commit `9c5bf6f`.
  1. **`actions/gather/models.py:21-31` indentation bug** — `get_adapters()` and `root_path()` were accidentally nested inside `debug()`. Real bug from a prior migration. Fixed by hoisting to module level. Commit `bec59ed` (Phase 2a).
  1. **`actions/sync/settings.py:635` `reload_config()` doesn't exist** — replaced with `await resolve_component_async(depends, "fastblocks", "config")`. Commit `93855e8` (Phase 2g).
  1. **`EventPriority` constants untyped** — `_events_integration.py` had class attrs without `int` annotations, causing `Event.__init__(priority: EventPriority)` to reject `int` literals. Typed constants as `int`, changed `Event.__init__` and `create_event` params to `int`. (Real semantic change: `EventPriority` is now a namespace for `int` constants — values are still `int` objects.) Commit `5bec6a5` (Phase 2c).
  1. **Image adapter parent/override signature mismatch** — `ImagesProtocol.upload_image` declared `-> str`, overrides returned `dict[str, Any]`. Changed base to `dict[str, Any]`; wrapped Cloudflare/TwicPics string returns in dicts. Real semantic change for Cloudflare adapter (now returns `{"image_id": ...}` instead of bare string). Commit `0c5cf2b` (Phase 2i).
  1. **`HtmxDetails._get_header` "first match wins" → "last match wins"** — duplicates with first empty silently ignored second. Fixed to last-match-wins (HTTP convention). Pre-existing bug uncovered by Hypothesis in `test_htmx_request_detection`. Test updated to iterate `reversed(scope["headers"])`. User authorised. Commit `818bbe0`.
  1. **Schema migration tooling exposed** — `fastblocks/__init__.py:62-63` `register_pkg()` replaced with `pass` (disables auto-registration). Spec didn't call this out explicitly; user should confirm auto-registration is not relied upon.
  1. **`SandboxedEnvironment.allowed_tags` / `allowed_attributes` dead code** — `_advanced_manager.py:371-372` set these attributes on `sandbox_env` but they don't exist on Jinja2's `SandboxedEnvironment` (actual security attributes are `binop_table`, `unop_table`, `intercepted_binops`, `intercepted_unops`). Pre-existing no-op masked by `# type: ignore[attr-defined]`. Commit `7e50145` removed the dead code.
- **Phase commits (chronological)**:
  - Task 1 (Resolver API rewiring across 46 files): `9f93910`, `42584b6`, plus 3 helper-wiring commits `265e533`, `1608c42`, `d9409e1`
  - Task 2 (suppression syntax): `35c1746`
  - Task 3 (3 `depends.get` → `resolve_instance`): `9c5bf6f`
  - Task 4 (4 framework-injected attr declarations): `c89f5d8`
  - Task 5 (10 `candidate.factory` casts): `93fe7bf`
  - Task 6 (ty phase 2a-2i, 14 commits, 119 → 10 diagnostics): `bec59ed`, `8e34a9c`, `296be3b`, `5bec6a5`, `1c3f073`, `87116ee`, `e061e23`, `6bc5e3d`, `e1eaa33`, `93855e8`, `fa52b54`, `ebb66ad`, `0c5cf2b`, `f5f6de1`
  - Bug fix (`_get_header` last-match-wins): `818bbe0`
  - Task 7 (6 redundant casts removed): `0d11b20`
  - Task 8 (4 unused `ty: ignore` directives): `0bf466c`

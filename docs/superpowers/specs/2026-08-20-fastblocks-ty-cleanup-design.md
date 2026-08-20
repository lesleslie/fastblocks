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
2. Read `oneiric.core.resolution.Resolver` source to confirm the actual API surface (`resolve`, `register`, `register_from_pkg`, `register_pkg`, `list_active`, `list_shadowed`, `explain`).
3. For each call site, map:
   - `get_sync(name)` → likely `resolve(domain, name)` (sync)
   - `set(name, value)` → likely `register(...)` or `register_from_pkg(...)`
   - `config.X` → likely `Resolver._config` or `resolver.config` (private) — surface-correct use may need to import the config object directly
4. Surface any cases where the mapping is unclear or where the code was calling a method that never existed. These are real-bug candidates (dead code paths or function never returned what the caller expected). Document and ask before fixing per the agreed real-bug policy.

**Verification:** `uv run ty check fastblocks/ 2>&1 | grep -c "error\|warning"` should drop ~150+.

### Phase 1b — Suppression syntax cleanup (~33 warnings)

`# type: ignore` (blanket, mypy syntax) is silently ignored by ty, which expects `# ty: ignore[rule-code]`. Many of these were written when only mypy was the type checker.

**Procedure:**

1. Grep all `# type: ignore` (without `[rule]`).
2. For each, look at the underlying diagnostic ty would emit. If the underlying code is correct, convert to `# ty: ignore[rule-code]`. If the suppression is no longer needed (the code was fixed elsewhere), remove it.
3. Verify with ty (the count should drop as new diagnostics become visible — they need addressing in subsequent phases).

**Verification:** Count of `unused-type-ignore-comment` goes to 0. Net ty diagnostic count may *increase* briefly as newly-visible errors emerge.

### Phase 1c — invalid-await cleanup (~28 errors)

`await depends.get(...)` / `await depends.resolve(...)` — `Candidate | None` is a sync object, not a coroutine.

**Procedure:**

1. Grep `await depends\.` patterns.
2. For each, drop the `await` (Candidate is the already-resolved value).
3. Surface cases where the code appears to expect an async path (e.g., calling `await` on something that wasn't the resolver result). These may be real bugs.

**Verification:** `invalid-await` count drops to 0.

### Phase 1d — Self@init / `_sanitizer` / `_publisher` (~24 errors)

Methods that reference `self._sanitizer` etc. before/aside from initialization. Some are real bugs (attribute referenced but never set).

**Procedure:**

1. Grep for class definitions containing `_sanitizer` / `_publisher` etc.
2. Verify each method's reference is preceded by a setter call (init or lazy assignment).
3. If missing, add init (real bug fix — call out per policy).
4. If typo, fix the typo.

**Verification:** `Self@init` and related vanish.

### Phase 1e — call-top-callable + Top[...] (~14 errors)

`candidate.factory()` is untyped because the factory callable is `Top[(...) -> object]`.

**Procedure:**

1. Identify the factory class/function definitions.
2. Add `__call__` return type annotations.
3. At call sites where factory is dynamic, use `cast(Callable[..., X], candidate.factory)`.

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
2. **Surface** — name the file, line, the wrong API call, and what the corrected API is.
3. **Ask** — confirm whether the code path is exercised (real bug) or dead code (safe to rewire).
4. **Document** — append to the spec's "Real bugs found" section so the count and resolution are tracked.

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

_To be populated as cleanup proceeds._

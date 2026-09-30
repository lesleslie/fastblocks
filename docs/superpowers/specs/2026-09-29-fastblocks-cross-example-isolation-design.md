# FastBlocks Cross-Example Test Isolation Design

**Date:** 2026-09-29
**Status:** ACTIVE — diagnosis verified 2026-09-29 20:08, design scope extended to include `templates/` renames. Tasks 2 and 3 of the original plan (`main.py` / `routes/` renames) are already staged but uncommitted; the new work extends the staged set. Single atomic commit per `feedback-bodai-atomic-commit-recurring-fixes.md`.
**Repository:** `/Users/les/Projects/fastblocks`
**Primary target:** Local `main` (HEAD `db5db9e` after the diagnosis-update commit; final commit lands at HEAD `db5db9e + 1`)

## Diagnosis (verified 2026-09-29 20:08)

`pytest examples/` produces 6 failures, all in `examples/htmy-hybrid/tests/`. The pollution source is **Python `sys.modules` package-name collisions** between the two example apps. Both apps share top-level module names that pytest's `sys.path.insert(0, _APP_ROOT)` in each `conftest.py` puts on `sys.path`. When pytest collects both apps in one session:

1. landing's `conftest.py` inserts `examples/landing/` to `sys.path` and the test bodies import landing's app
2. htmy-hybrid's `conftest.py` inserts `examples/htmy-hybrid/` to `sys.path` and the test bodies import htmy-hybrid's app
3. Python's import cache (`sys.modules`) does not get cleared between tests — once a bare name like `templates` is resolved, it stays resolved
4. When htmy-hybrid's `greeting.py` runs `from templates import render_template as render_jinja`, Python returns whichever `templates` module was cached FIRST — landing's — even though htmy-hybrid is the calling app

Captured trace from the live failure:

```
examples/htmy-hybrid/htmy_hybrid_routes/greeting.py:103: in greeting_route
    body = await render_jinja(request, _JINJA_TEMPLATE, {})
examples/landing/templates/__init__.py:41: in render_template
    return _ENVIRONMENT.get_template(name).render(merged)
```

The frame `examples/landing/templates/__init__.py:41` proves that the `_ENVIRONMENT` being used is landing's. The HTMY-hybrid test is rendering through landing's Jinja2 Environment, which is pointed at `examples/landing/templates/` and therefore cannot find `greeting/jinja.html` (which lives in `examples/htmy-hybrid/templates/`).

Three collision classes exist in the examples directory:

| Top-level name | Status before fix | Fix |
|---|---|---|
| `main.py` / `app.py` | Already renamed to `landing_app.py` / `htmy_hybrid_app.py` (staged in Tasks 2/3 of the original plan). | Already staged. |
| `routes/` | Already renamed to `landing_routes/` / `htmy_hybrid_routes/` (staged in Tasks 2/3 of the original plan). | Already staged. |
| **`templates/`** | **NOT YET renamed** — the active pollution source. | This design. |

The original 5-task plan was correct in approach and 90% complete in execution (Tasks 2 and 3 already shipped the renames that fixed two collision classes; only `templates/` remained). The plan was paused before Tasks 4 and 5 because the implementer misread a trace frame and concluded the pollution was Oneiric template-loader caching. That conclusion was wrong: Oneiric has no template loader, and the actual cause was always `sys.modules` package-name collision. The 9-file rename plan is extended to include `templates/`, and the work lands as one atomic commit alongside the already-staged renames.

`★ Insight ─────────────────────────────────────`
- **Naming-as-isolation works at any scale**: the same fix that eliminated the `main.py` / `routes/` collision class works for `templates/`. The pattern is generic — any pair of apps that puts generic top-level packages on `sys.path` will collide. Naming that ends with the app-name eliminates the collision at compile time, not at test time.
- **The `templates` collision is special**: it surfaces only in tests that render templates through a `from templates import` statement. Pure-import handlers and pure-FastBlocks handlers are immune. That's why landing's tests pass (landing's routes use `from templates import render_template` but landing IS the first-loaded app, so its `templates` resolves correctly) while htmy-hybrid's tests fail (htmy-hybrid's `from templates import` resolves to landing's `templates`, which has the wrong searchpath).
- **Renames are atomic with the imports they break**: a rename without the corresponding import-site update produces `ImportError` at test collection. The renames and the 9 import-site updates must ship together. The new work extends the already-staged atomic set.
`─────────────────────────────────────────────────`

## Scope

This design extends the original rename plan to include `templates/` directories and the import statements that depend on them. The complete file set (combined with already-staged renames from Tasks 2 and 3 of the original plan):

### Already staged (Tasks 2 and 3 of the original plan)

1. `examples/landing/main.py` → `examples/landing/landing_app.py` (already staged)
2. `examples/landing/routes/` → `examples/landing/landing_routes/` (already staged)
3. `examples/htmy-hybrid/main.py` → `examples/htmy-hybrid/htmy_hybrid_app.py` (already staged)
4. `examples/htmy-hybrid/routes/` → `examples/htmy-hybrid/htmy_hybrid_routes/` (already staged)
6. `examples/landing/tests/conftest.py` already updated to import from `landing_app` (already staged)
7. `examples/htmy-hybrid/tests/conftest.py` already updated to import from `htmy_hybrid_app` (already staged)
8. `tests/htmx/test_hx_trigger_emission.py` already updated for the `landing_app` import (already staged)

### New work in this design

9. **Rename `examples/landing/templates/` → `examples/landing/landing_templates/`** (directory rename; git tracks the contents).
10. **Rename `examples/htmy-hybrid/templates/` → `examples/htmy-hybrid/htmy_hybrid_templates/`** (directory rename).
11. **Update 8 import sites in `examples/landing/landing_routes/`** that read `from templates import render_template`:
    - `landing_routes/install.py:11`
    - `landing_routes/security.py:19`
    - `landing_routes/docs.py:11`
    - `landing_routes/features.py:17`
    - `landing_routes/home.py:15`
    - `landing_routes/performance.py:18`
    - `landing_routes/demo.py:23`
    - `landing_routes/adapter_matrix.py:56`
    Each becomes `from landing_templates import render_template`.
12. **Update 1 import site in `examples/htmy-hybrid/htmy_hybrid_routes/`** that reads `from templates import render_template as render_jinja`:
    - `htmy_hybrid_routes/greeting.py:28`
    Becomes `from htmy_hybrid_templates import render_template as render_jinja`.
13. **Update `examples/landing/README.md`** if it references `templates/` paths or `from templates` in code blocks (audit during execution).
15. **Update `examples/htmy-hybrid/README.md`** similarly.

This design excludes:

- Re-execution of Tasks 2 and 3 of the original plan. Already staged, already reviewed, just need to land atomically with the new work.
- Any change to `fastblocks/core/resolver.py` or other production framework code.
- Renaming `adapters/`, `components/`, `settings/`, `tests/` — these names do not currently cause `from x import y` collisions in the example apps' code paths (audit found 0 such imports).
- A `examples/conftest.py` with autouse fixture for `sys.modules` cleanup. Brittle and unnecessary: the renames eliminate the entire collision class, so cleanup is not needed.
- `pytest-xdist --force=True` subprocess isolation. Adds ~200ms × N wall-clock cost for a problem that is now solved at the design level.
- Updates to historical plan docs.

## Solution structure

The change is a single coordinated rename across the two example apps, the import sites that depend on the renamed packages, and the README references that demonstrate the new structure. Per `feedback-bodai-atomic-commit-recurring-fixes.md`, the implementation lands as **ONE atomic commit** combining the already-staged renames (main.py / routes/) and the new work (templates/). A single `git revert` restores the entire pre-rename state.

**Commit message subject:** `refactor(fastblocks): rename example top-level packages to app-specific names`

**The commit combines:**

- 4 renames from the already-staged set (main.py / routes/ in both examples)
- 4 already-staged import-site updates (conftests + production test)
- 2 new directory renames (`templates/` → `*_templates/` in both examples)
- 9 new import-site updates (8 in landing_routes/, 1 in htmy_hybrid_routes/)
- README updates (per audit)
- Docstring comment updates if any references the renamed paths (per audit)

## Verification and integration gates

The implementation runs in `/Users/les/Projects/fastblocks` on local `main`. Use the existing project venv (`/Users/les/Projects/fastblocks/.venv/bin/pytest`); no new dependencies.

Gates (in order):

1. **Pre-rename baseline**: run `pytest examples/ --no-cov` and confirm 6 failures, all in htmy-hybrid (per the original session's Task 1 capture). Run `pytest tests/htmx/test_hx_trigger_emission.py -v` and confirm 3 passed.
2. **Per-directory rename check**: after each `templates/` rename, run `pytest examples/<app>/tests/ --collect-only --no-cov` for that app to confirm collection succeeds with the new package name.
3. **Per-directory import check**: after each example's import-site updates, run `pytest examples/<app>/tests/ --no-cov -x` to confirm the test body can `from <app>_templates import render_template` and the TestClient can dispatch.
4. **Cross-example verification**: run `pytest examples/ --no-cov` and confirm **0 failures** (was 6).
5. **Full suite regression check**: run `pytest tests/ --no-cov -m "not slow"` and confirm no NEW failures appear relative to the pre-rename baseline. The previous passing test count must not decrease.
6. **Final import audit**: `git grep -nE "from (templates|routes|main)( |\$| import)" examples/landing/ examples/htmy-hybrid/ -- ':!docs/superpowers/plans/' ':!examples/landing/README.md' ':!examples/htmy-hybrid/README.md'` must return zero hits.
7. **Final path audit**: `git grep -nE "examples/landing/(main|routes|templates)/|examples/htmy-hybrid/(main|routes|templates)/" -- ':!docs/superpowers/plans/' ':!examples/landing/README.md' ':!examples/htmy-hybrid/README.md'` must return zero hits outside of the README tree diagrams (which are updated to reflect the new layout).

## Acceptance criteria

- `pytest examples/ --no-cov` runs to completion with **0 failures** (was 6).
- `pytest examples/landing/tests/ --no-cov` passes unchanged from pre-rename baseline (16 passed + 1 skipped).
- `pytest examples/htmy-hybrid/tests/ --no-cov` passes unchanged from pre-rename baseline (10 passed).
- `pytest tests/htmx/test_hx_trigger_emission.py --no-cov` passes (3 tests).
- `pytest tests/ --no-cov -m "not slow"` shows no NEW failures vs the pre-rename baseline.
- `git grep` audit returns no stale `from templates` / `from routes` / `from main` / `examples/landing/templates/` / `examples/htmy-hybrid/templates/` references in the example apps' code paths (READMEs may keep tree diagrams).
- The production framework code (`fastblocks/core/resolver.py` and friends) is unchanged.
- The historical plan docs (`docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-*.md`) are unchanged.
- Atomic single commit per `feedback-bodai-atomic-commit-recurring-fixes.md`.
- No `Co-Authored-By` trailer per `feedback-no-claude-code-coauthor-attribution.md`.
- No push per `feedback-bodai-push-is-user-controlled.md`.

## Failure classification and safety

Each potential regression must be classified as one of:

- **Production defect**: a renamed import is wrong, a test's `sys.modules` cleanup is incomplete (none in this design — the production test at `tests/htmx/test_hx_trigger_emission.py` was already updated by Tasks 2 and 3 of the original plan and only required the application-landing-app rename).
- **Stale test expectation**: a test was passing only by accident because of module shadowing; after the rename, the test fails with a clear import error that needs a deliberate update.
- **Setup issue**: the project's venv lacks a dependency the rename introduced (no new dependencies are introduced by this design; should not occur).
- **Needs evidence**: any failure after the rename must be reproduced in isolation (`pytest examples/<app>/tests/`) before any "fix" is attempted.

The implementer must NOT "fix" failures by reverting the renames or by adding `sys.modules` mutation that papers over the underlying naming. If the rename breaks a test, the test must be updated to import from the new name — that is the entire point of the change.

## Rollback

- Single-commit rollback: revert the commit with `git revert <commit-sha>`. The renames restore the original state; no data loss.
- If the commit's test gate fails, revert immediately and re-enter design — do not amend on top of a failing gate.
- Do not split or amend the atomic commit after partial implementation; the change is conceptually one rename class, and the commit reflects that.

## Integration Contract

**Triggered from:** The 6-unit cross-example test failure (`pytest examples/` → 6 failed, all in htmy-hybrid) at local HEAD `db5db9e`, surfaced as the original session's Task 1 RED baseline and reconfirmed at the diagnosis-update time.

**Returns to / updates:** Local `main` branch with one atomic commit combining the already-staged renames (main.py / routes/) and the new work (templates/); no remote push.

**Demonstrable by:** Pre-commit `pytest examples/ --no-cov` shows 6 failures; post-commit shows 0. `pytest tests/htmx/test_hx_trigger_emission.py --no-cov` passes. `git grep` audit returns no stale `templates` / `routes` / `main` references in the example apps' code paths.

**Rollback signal:** Any post-commit test count regression, or any production framework code change (must remain bit-for-bit identical to HEAD `db5db9e`).

**Observability added:** Pre/post `pytest` outputs in the commit message body; explicit statement that production framework code is unchanged.

## Decisions captured

- **Extend the original rename plan, not replace it**: the original plan's renames (main.py / routes/) were correct hygiene work and are already staged. Adding `templates/` finishes the job. Reverting them would re-introduce 6 of the original 6 failures.
- **One atomic commit, combining staged and new work**: per `feedback-bodai-atomic-commit-recurring-fixes.md`, all renames + import updates + README updates land as a single commit. The already-staged renames stay staged until this single commit absorbs them.
- **No `clean_resolver`-style autouse fixture in `examples/conftest.py`**: tried in the previous session, regressed to 7 failures because landing tests depend on resolver state surviving across tests. The renames eliminate the collision class entirely, so no fixture is needed.
- **No `pytest-xdist --force=True`**: brute-force subprocess isolation would work but adds ~200ms × N wall-clock cost for a problem that is now solved at the design level.
- **No changes to `fastblocks/core/resolver.py`**: ADR 0008 Rule 2 forbids breaking the resolver singleton, and the framework is not the problem.
- **Do not update historical plan docs**: they are dated implementation records; their references are accurate at the time of writing.
- **Examples are not user-facing** (per user's explicit confirmation 2026-09-29): no deprecation or migration notes required.

## Memory feedback

- `~/.claude/projects/-Users-les-Projects-mahavishnu/memory/feedback-read-pytest-trace-before-planning-fix.md` — capture the actual pytest trace during RED phase, not just the failure count.
- `~/.claude/projects/-Users-les-Projects-mahavishnu/memory/feedback-git-commit-only-pathspec-with-staged-changes.md` — when staging a single file with other things staged, use `git commit --only <pathspec>`.

`★ Insight ─────────────────────────────────────`
- **Same fix, different scale**: extending the rename pattern from `main.py` / `routes/` to `templates/` is mechanical, not architectural. The architectural decision (naming-as-isolation) was made in the original spec; this design only enlarges the surface to which it applies.
- **Atomic commit absorbs both sets**: combining the already-staged renames and the new work in one commit preserves the rollback-and-review properties that drove the original design's atomicity choice. Splitting would re-introduce the broken-intermediate window the original design specifically avoided.
- **The misdiagnosis was correctable in-place**: rather than retracting the original plan wholesale, this design extends it. The original plan's evidence (Tasks 2 and 3) was valid — both renames are clean — only the GREEN gate was unreachable from those renames alone. Adding `templates/` makes the GREEN gate reachable without changing what already shipped.
`─────────────────────────────────────────────────`
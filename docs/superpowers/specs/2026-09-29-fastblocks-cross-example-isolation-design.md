# FastBlocks Cross-Example Test Isolation Design

**Date:** 2026-09-29
**Status:** Pending written-spec review
**Repository:** `/Users/les/Projects/fastblocks`
**Primary target:** Local HEAD `9c739c3` on `main`
**Predecessor work:** Commits `7a0f0f3` (conftest plugin-namespace collision) and `9c739c3` (HTMX property-test alignment) already shipped.

## Context

Cross-example invocation `pytest examples/` fails because both example apps use the same Python module name (`main`) for their FastBlocks application factory, and both use the same package name (`routes`) for their route registrations. Each example's `tests/conftest.py` does `sys.path.insert(0, _APP_ROOT)` for its own app directory; once both conftests run, whichever conftest loaded last owns the `main` slot on `sys.path`. A test that does `from main import app` returns whichever `main` got cached first, then shadowed or overwritten by subsequent registrations.

The current failure mode at local HEAD `9c739c3`:

- `pytest examples/landing/` — **passes** (no second example present to collide with).
- `pytest examples/htmy-hybrid/` — **passes** (same, in isolation).
- `pytest examples/` — **fails**: 2 of 27 tests fail; the htmy-hybrid render tests fail because the resolver state accumulated by the landing tests pollutes the htmy-hybrid app's lookup, and the `main` module-cache shadowing means htmy-hybrid's `app` may resolve to landing's instance.

The previous session (commits `7a0f0f3` and the reclassified work) addressed the *plugin-namespace* collision (two `conftest.py` files with the same Python module name) by dropping `examples/htmy-hybrid/tests/__init__.py`. That fix preserved `pytest -p no:cacheprovider examples/*/tests/ --collect-only` but did not address the deeper module-name collision that surfaces only when both apps are loaded into the same process.

A function-scope `clean_resolver` autouse fixture (the pattern in `tests/conftest.py:451-488`) was tried first as a faster fix. It regressed the suite to **7 failures** instead of 2: landing tests register routes via `FastBlocks()` at app-construction time, and a per-test resolver reset wipes those registrations before the test can dispatch. The main test suite works under the same `clean_resolver` pattern because its unit tests do not depend on route registrations surviving across tests — example apps are integration-style and do. **Lesson**: per-test reset is the wrong granularity for these tests.

This design uses naming-as-isolation: rename the colliding source files to non-colliding, app-specific names. No new infrastructure (no subprocess orchestration, no `importlib.util.spec_from_file_location` indirection), no FastBlocks framework change, and the failure mode becomes "I get a clear ImportError" if a future example forgets the convention.

## Scope

This design renames four module names in two example apps and updates the references those renames break. It includes:

- Renaming `examples/landing/main.py` → `examples/landing/landing_app.py`.
- Renaming `examples/landing/routes/` → `examples/landing/landing_routes/` (the package directory and its `__init__.py`).
- Renaming `examples/htmy-hybrid/main.py` → `examples/htmy-hybrid/htmy_hybrid_app.py`.
- Renaming `examples/htmy-hybrid/routes/` → `examples/htmy-hybrid/htmy_hybrid_routes/`.
- Updating the in-example import in each `*_app.py` (`from routes import register_routes` → `from landing_routes import register_routes` / `from htmy_hybrid_routes import register_routes`).
- Updating `examples/landing/tests/conftest.py` (`from main import app` → `from landing_app import app`).
- Updating `examples/htmy-hybrid/tests/conftest.py` (`from main import app` → `from htmy_hybrid_app import app`).
- Updating `tests/htmx/test_hx_trigger_emission.py:42` (production test that imports from the example): `from main import app` → `from landing_app import app`, plus the matching `sys.modules` cleanup at line 40 (currently `if name == "main" or name.startswith("main.")` → handle `landing_app` instead).
- Updating path references in docstrings/comments of 4 production tests (`tests/adapters/middleware/test_security_headers_boot.py:5`, `test_brotli_boot.py:5`, `test_csrf_boot.py:5`, `tests/adapters/templates/test_fastblocks_ui_boot.py:10`). These reference `examples/landing/routes/adapter_matrix.py` in comments only; updates are cosmetic.
- Updating `examples/landing/README.md:17` and `examples/htmy-hybrid/README.md:26,48` (uvicorn commands and tree diagrams).

This design excludes:

- A `examples/conftest.py` with `clean_resolver` autouse fixture. Tried and rejected (regression to 7 failures; see Context).
- A `pytest-xdist`-based subprocess-per-example workflow. Adds ~200 ms × N orchestration cost; the issue is naming, not isolation topology.
- An `importlib.util.spec_from_file_location` indirection in each conftest. Adds indirection that hides the underlying problem (generic names should be eliminated, not papered over).
- Changes to `fastblocks/core/resolver.py` or any other production framework code. ADR 0008 Rule 2 forbids breaking the resolver singleton, and the framework is not the problem — the example names are.
- Renaming other generic module names that may exist elsewhere in the examples tree (none found in scope).
- Updates to historical plan docs (`docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-*.md`). These are dated implementation records; their references to `examples/landing/main.py` are accurate at the time of writing and updating them would rewrite history. They will not be touched; readers checking current state should follow the actual files.
- User-facing changes. Confirmed by the user on 2026-09-29 that the example apps are not user-facing templates — no deprecation or migration notes required.

## Solution structure

The change is a single coordinated rename across two example apps, their tests, the dependent production test, and the cosmetic comment/README updates. Per `feedback-bodai-atomic-commit-recurring-fixes.md`, the implementation lands as **ONE atomic commit** so a single `git revert` restores the entire pre-rename state and a single diff is what the reviewer reads. Splitting into "rename file", "update imports", "update docs" would create three review surfaces, three potential rollback boundaries, and a broken-intermediate window where the renames are partially applied.

**Commit message subject:** `refactor(fastblocks): rename example main.py/routes/ to app-specific names`

**The commit contains the following file changes, applied as a single coordinated edit:**

1. **Rename `examples/landing/main.py` → `examples/landing/landing_app.py`.** Update its internal `from routes import register_routes` → `from landing_routes import register_routes`.
2. **Rename `examples/landing/routes/` → `examples/landing/landing_routes/`** (directory rename; git tracks the contents).
3. **Rename `examples/htmy-hybrid/main.py` → `examples/htmy-hybrid/htmy_hybrid_app.py`.** Update its internal `from routes import register_routes` → `from htmy_hybrid_routes import register_routes`.
4. **Rename `examples/htmy-hybrid/routes/` → `examples/htmy-hybrid/htmy_hybrid_routes/`** (directory rename).
5. **Update `examples/landing/tests/conftest.py`:** `from main import app` → `from landing_app import app`; update the leading docstring comment that says "the tests need to import it via `from main import app`."
6. **Update `examples/htmy-hybrid/tests/conftest.py`:** `from main import app` → `from htmy_hybrid_app import app`; update the leading docstring comment.
7. **Update `tests/htmx/test_hx_trigger_emission.py:42`** (production test): `from main import app` → `from landing_app import app`; update the `sys.modules` cleanup at lines 39-41 from `name == "main"` to `name == "landing_app"` (and equivalent prefix check).
8. **Update path references in docstring comments** of `tests/adapters/middleware/test_security_headers_boot.py:5`, `test_brotli_boot.py:5`, `test_csrf_boot.py:5`, `tests/adapters/templates/test_fastblocks_ui_boot.py:10`. These reference `examples/landing/routes/adapter_matrix.py` in comments; updates are cosmetic but required for the audit gate.
9. **Update `examples/landing/README.md:17`** uvicorn command from `python -m uvicorn main:app` → `python -m uvicorn landing_app:app`, and any tree diagram entries that reference `main.py` / `routes/`.
10. **Update `examples/htmy-hybrid/README.md:26,48`** uvicorn command and tree diagram entries.

## Verification and integration gates

The implementation runs in `/Users/les/Projects/fastblocks` on local `main` at HEAD `9c739c3`. Use the existing project venv (`/Users/les/Projects/fastblocks/.venv/bin/pytest`); no new dependencies.

Gates (in order):

1. **Pre-rename baseline**: run `pytest examples/` and confirm the current 2-failure state. Run `pytest tests/htmx/test_hx_trigger_emission.py -v` and confirm the test passes (it loads the example's `main` as part of its setup).
2. **Per-file rename check**: after each file rename, run `pytest examples/<app>/tests/ --collect-only` for that app to confirm collection succeeds with the new module name.
3. **Per-file import check**: after each example's `tests/conftest.py` update, run `pytest examples/<app>/tests/ -x` to confirm the test body can `from landing_app import app` / `from htmy_hybrid_app import app` and the TestClient can dispatch.
4. **Production test check**: after the `test_hx_trigger_emission.py` update, run `pytest tests/htmx/test_hx_trigger_emission.py -v` to confirm the monkeypatched `sys.modules` cleanup correctly handles the new module name.
5. **Cross-example verification**: run `pytest examples/` and confirm **0 failures** (was 2). Both example apps must coexist and dispatch correctly in a single pytest process.
6. **Full suite regression check**: run `pytest tests/` (skipping slow/marked exclusions already configured in the project) and confirm no NEW failures appear. The previous passing test count must not decrease.
7. **Coverage and coverage gate**: the project's coverage gate (per `[tool.pytest] addopts`) will fail on `pytest examples/` because example code isn't covered by the production test suite. Run the verification with `--no-cov` to bypass the gate for the verification commands; the committed code must still pass the gate for production tests.
8. **Final comment audit**: `git grep -n "examples/landing/main\|examples/landing/routes\|examples/htmy-hybrid/main\|examples/htmy-hybrid/routes" -- ':!docs/superpowers/plans/'` must return zero hits (the historical plan docs are excluded per Scope).

## Failure classification and safety

Each potential regression must be classified as one of:

- **Production defect**: a renamed import is wrong, a test's `sys.modules` cleanup is incomplete, or a route module's internal references still point at the old name.
- **Stale test expectation**: a test was passing only by accident because of module shadowing; after the rename, the test fails with a clear import error that needs a deliberate update.
- **Setup issue**: the project's venv lacks a dependency the rename introduced (no new dependencies are introduced by this design; this should not occur).
- **Needs evidence**: any failure after the rename must be reproduced in isolation (`pytest examples/landing/tests/` or `pytest tests/htmx/test_hx_trigger_emission.py`) before any "fix" is attempted.

The implementer must NOT "fix" failures by reverting the rename or by adding `sys.modules` mutation that papers over the underlying naming. If the rename breaks a test, the test must be updated to import from the new name — that is the entire point of the change.

## Rollback

- Single-commit rollback: revert the commit with `git revert <commit-sha>`. The renames restore the original state; no data loss.
- If the commit's test gate fails, revert immediately and re-enter design — do not amend on top of a failing gate.
- Do not split or amend the atomic commit after partial implementation; the change is conceptually one rename, and the commit reflects that.

## Acceptance criteria

- `pytest examples/` runs to completion with **0 failures** (was 2 at HEAD `9c739c3`).
- `pytest examples/landing/tests/` passes unchanged from HEAD `9c739c3`.
- `pytest examples/htmy-hybrid/tests/` passes unchanged from HEAD `9c739c3`.
- `pytest tests/htmx/test_hx_trigger_emission.py` passes (1 test).
- `pytest tests/` shows no NEW failures vs the pre-rename baseline.
- `git grep -n "examples/landing/main\|examples/landing/routes\|examples/htmy-hybrid/main\|examples/htmy-hybrid/routes" -- ':!docs/superpowers/plans/'` returns no hits.
- Both `examples/landing/README.md` and `examples/htmy-hybrid/README.md` reference the renamed uvicorn target.
- The production framework code (`fastblocks/core/resolver.py` and friends) is unchanged.
- The historical plan docs (`docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-*.md`) are unchanged (their references to the old paths are accurate historical snapshots).
- Atomic single commit per `feedback-bodai-atomic-commit-recurring-fixes.md`.
- No `Co-Authored-By` trailer per `feedback-no-claude-code-coauthor-attribution.md`.
- No push per `feedback-bodai-push-is-user-controlled.md` (push is user-controlled).

## Integration Contract

**Triggered from:** A pre-existing cross-example test failure (`pytest examples/`) at local HEAD `9c739c3`, surfaced as the second of the two follow-up tasks from the previous session.

**Returns to / updates:** Local `main` branch with one atomic commit; no remote push.

**Demonstrable by:** Pre-rename `pytest examples/` shows 2 failures; post-rename shows 0. `pytest tests/htmx/test_hx_trigger_emission.py` passes. `git grep` audit returns no stale path references outside the historical plan docs.

**Rollback signal:** Any post-rename test count regression, or any production framework code change (must remain bit-for-bit identical to HEAD `9c739c3`).

**Observability added:** Pre/post `pytest` outputs in the commit message body; explicit statement that production framework code is unchanged.

## Decisions captured

- Use naming-as-isolation (rename) over subprocess isolation or importlib indirection. Reasons: simplest mechanism, eliminates the underlying class of bug (generic-name collisions), no new infrastructure, future examples that copy this pattern can't reintroduce the trap.
- Rename both `main.py` AND `routes/` per the user's explicit choice on 2026-09-29 (Option B). Half-fixing the same class of bug is worse than fixing it once.
- One atomic commit, not three. The renames, import updates, README updates, and comment updates are part of a single conceptual change. Splitting creates broken-intermediate states.
- No examples-level `conftest.py` with `clean_resolver` autouse fixture. Tried and rejected (regressed to 7 failures). The integration-style tests in the examples tree depend on per-test resolver state that the function-scope reset destroys.
- No changes to `fastblocks/core/resolver.py` or any other production framework code. The framework is not the problem.
- Do not update historical plan docs. They are dated implementation records; their references are accurate at the time of writing.

`★ Insight ─────────────────────────────────────`

- **Naming-as-design**: generic module names like `main` and `routes` describe a role (`the main entry`, `the routes module`), not a specific thing. When two files in the same Python search space share a generic name, the collision is a symptom of the generic naming. Fix the name, fix the symptom — at compile time, not at test time.
- **Test-time fixes hide naming bugs**: the previous session's attempts at per-test resolver reset made the cross-example pollution appear to be a test-infrastructure problem, hiding the actual naming collision. When a fix makes a failure mode go away without addressing its cause, the cause will reappear in a different form. Naming collisions do not get less collision-y with more indirection — they only get harder to spot.
- **Atomicity is about rollback and review**: combining all the rename updates into one commit means a single `git revert` restores the entire pre-rename state, and a single diff is what the reviewer reads. Splitting into "rename file", "update imports", "update docs" would create three review surfaces, three potential rollback boundaries, and a window where the renames are partially applied.
  `─────────────────────────────────────────────────`

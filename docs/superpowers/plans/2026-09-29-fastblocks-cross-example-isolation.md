# FastBlocks Cross-Example Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix `pytest examples/` cross-example test pollution by renaming generic-name modules (`main.py`, `routes/`) in both example apps to app-specific names so they no longer collide via `sys.path` + `sys.modules`.

**Architecture:** Naming-as-isolation. Rename `examples/<app>/main.py` → `<app>_app.py` and `examples/<app>/routes/` → `<app>_routes/`. No new infrastructure (no subprocess orchestration, no `importlib.util.spec_from_file_location`). The single change eliminates the underlying class of bug — generic module names colliding in a shared Python search space.

**Tech Stack:** Python (pytest, Starlette TestClient), FastBlocks example apps, Oneiric resolver (untouched per ADR 0008 Rule 2).

**Spec:** `docs/superpowers/specs/2026-09-29-fastblocks-cross-example-isolation-design.md` (committed at `2c9b357`)

## Global Constraints

- Spec calls for **ONE atomic commit** containing all renames and updates. Intermediate tasks (Tasks 1-4) verify per-piece but do NOT commit. Task 5 contains the single commit step.
- **No `Co-Authored-By` trailer** in the commit message (per `feedback-no-claude-code-coauthor-attribution.md`).
- **No push** — push is user-controlled (per `feedback-bodai-push-is-user-controlled.md`).
- **Production framework code is unchanged.** `fastblocks/core/resolver.py` and all other `fastblocks/core/*.py` files must be bit-for-bit identical to HEAD `9c739c3` after the commit.
- **Historical plan docs** (`docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-*.md`) reference the old paths. They are NOT updated — they are dated implementation records; updating them rewrites history.
- **Run pytest with `--no-cov`** for verification commands to bypass the coverage gate (the project's coverage floor of 67.81% will fail when only running the examples tree, which has minimal production coverage).
- The project's Python interpreter is at `/Users/les/Projects/fastblocks/.venv/bin/python`; pytest at `/Users/les/Projects/fastblocks/.venv/bin/pytest`. Use the venv explicitly per `bodai-pytest-binary-cwd.md`.
- CWD for all commands is `/Users/les/Projects/fastblocks` unless otherwise noted.

---

### Task 1: Capture RED baseline

**Files:**
- Touch: none (read-only verification)

**Purpose:** Confirm the cross-example failure mode before making changes, so the GREEN gate in Task 5 has a real reference point.

- [ ] **Step 1: Run the failing test to confirm RED**

Run:
```bash
.venv/bin/pytest examples/ --no-cov -q 2>&1 | tail -20
```

Expected output: ends with `2 failed, 25 passed, 1 skipped` (or close — exact passing count may differ across runs; the 2-failure count is the invariant). Record the exact line in your reply.

The two failures should be in htmy-hybrid (`test_hybrid_render_returns_200` and `test_htmy_render_returns_200` are the known failures per the previous session's reproduction).

- [ ] **Step 2: Verify landing-only invocation passes (sanity check)**

Run:
```bash
.venv/bin/pytest examples/landing/ --no-cov -q 2>&1 | tail -5
```

Expected: `N passed, 1 skipped` (no failures).

- [ ] **Step 3: Verify htmy-hybrid-only invocation passes (sanity check)**

Run:
```bash
.venv/bin/pytest examples/htmy-hybrid/ --no-cov -q 2>&1 | tail -5
```

Expected: `M passed, 1 skipped` (no failures).

- [ ] **Step 4: Verify the production test that imports from the example still passes**

Run:
```bash
.venv/bin/pytest tests/htmx/test_hx_trigger_emission.py --no-cov -v 2>&1 | tail -10
```

Expected: `1 passed`.

**No commit at this task boundary** — this is a read-only baseline capture.

---

### Task 2: Rename landing example

**Files:**
- Rename: `examples/landing/main.py` → `examples/landing/landing_app.py`
- Rename dir: `examples/landing/routes/` → `examples/landing/landing_routes/`
- Modify: `examples/landing/landing_app.py` (update internal `from routes` import)
- Modify: `examples/landing/tests/conftest.py` (update import + docstring comment)
- Modify: `tests/htmx/test_hx_trigger_emission.py` (update import + `sys.modules` cleanup)

**Interfaces:**
- Consumes: Task 1 baseline numbers
- Produces: `examples/landing/landing_app.py` exporting `app` and `create_app`; `examples/landing/tests/conftest.py` doing `from landing_app import app`; `tests/htmx/test_hx_trigger_emission.py` doing `from landing_app import app` with `sys.modules` cleanup for `landing_app`

- [ ] **Step 1: Rename `main.py` using git mv**

Run:
```bash
git mv examples/landing/main.py examples/landing/landing_app.py
```

This preserves git rename detection. Verify with `git status` — should show `renamed: examples/landing/main.py -> examples/landing/landing_app.py`.

- [ ] **Step 2: Update internal import in `landing_app.py`**

Read `examples/landing/landing_app.py`. Find the line `from routes import register_routes` (around line 13). Replace with:
```python
from landing_routes import register_routes
```

Verify by reading the file: it should now import from `landing_routes`, not `routes`.

- [ ] **Step 3: Rename `routes/` directory using git mv**

Run:
```bash
git mv examples/landing/routes examples/landing/landing_routes
```

Verify with `git status` — the directory rename is tracked as a series of file renames (`routes/__init__.py` → `landing_routes/__init__.py`, etc.).

- [ ] **Step 4: Update `examples/landing/tests/conftest.py`**

Edit `examples/landing/tests/conftest.py`:

Change the line `from main import app as fastblocks_app` (line 25) to:
```python
from landing_app import app as fastblocks_app
```

Also update the leading docstring comment (line 16) from:
```python
# Make ``main`` importable regardless of pytest's rootdir discovery —
# the landing app lives at ``examples/landing/main.py`` and the tests
# need to import it via ``from main import app``.
```
to:
```python
# Make ``landing_app`` importable regardless of pytest's rootdir discovery —
# the landing app lives at ``examples/landing/landing_app.py`` and the tests
# need to import it via ``from landing_app import app``.
```

- [ ] **Step 5: Update `tests/htmx/test_hx_trigger_emission.py`**

Edit `tests/htmx/test_hx_trigger_emission.py`:

Change the line `from main import app` (line 42) to:
```python
from landing_app import app
```

Change the `sys.modules` cleanup block at lines 39-41 from:
```python
    for name in list(sys.modules):
        if name == "main" or name.startswith("main."):
            monkeypatch.delitem(sys.modules, name)
```
to:
```python
    for name in list(sys.modules):
        if name == "landing_app" or name.startswith("landing_app."):
            monkeypatch.delitem(sys.modules, name)
```

Also update the docstring at line 9 from:
```
The app is bootstrapped from ``examples/landing/main.py`` so the test
```
to:
```
The app is bootstrapped from ``examples/landing/landing_app.py`` so the test
```

- [ ] **Step 6: Verify landing-only tests pass after rename**

Run:
```bash
.venv/bin/pytest examples/landing/ --no-cov -q 2>&1 | tail -5
```

Expected: `N passed, 1 skipped` (same N as Task 1 Step 2). If failures appear, the rename broke something — STOP and re-read the changed files; do not proceed.

- [ ] **Step 7: Verify the production test still passes**

Run:
```bash
.venv/bin/pytest tests/htmx/test_hx_trigger_emission.py --no-cov -v 2>&1 | tail -5
```

Expected: `1 passed`. If failure, the `sys.modules` cleanup change is wrong — re-read Step 5 and verify the prefix match handles `landing_app` and `landing_app.<submodules>`.

- [ ] **Step 8: Verify cross-example invocation still shows the SAME failures (no regression from this task alone)**

Run:
```bash
.venv/bin/pytest examples/ --no-cov -q 2>&1 | tail -5
```

Expected: still `2 failed` (or similar). Landing rename alone does NOT fix cross-example — that's Task 3's job. This step confirms Task 2's changes did not regress beyond the original baseline.

**No commit at this task boundary** — the rename is half done (htmy-hybrid not yet renamed). Intermediate commits would leave a broken state.

---

### Task 3: Rename htmy-hybrid example

**Files:**
- Rename: `examples/htmy-hybrid/main.py` → `examples/htmy-hybrid/htmy_hybrid_app.py`
- Rename dir: `examples/htmy-hybrid/routes/` → `examples/htmy-hybrid/htmy_hybrid_routes/`
- Modify: `examples/htmy-hybrid/htmy_hybrid_app.py` (update internal `from routes` import)
- Modify: `examples/htmy-hybrid/tests/conftest.py` (update import + docstring comment)

**Interfaces:**
- Consumes: Task 2 completed state (landing renamed, verified)
- Produces: `examples/htmy-hybrid/htmy_hybrid_app.py` exporting `app` and `create_app`; `examples/htmy-hybrid/tests/conftest.py` doing `from htmy_hybrid_app import app`

- [ ] **Step 1: Rename `main.py` using git mv**

Run:
```bash
git mv examples/htmy-hybrid/main.py examples/htmy-hybrid/htmy_hybrid_app.py
```

Verify with `git status`.

- [ ] **Step 2: Update internal import in `htmy_hybrid_app.py`**

Read `examples/htmy-hybrid/htmy_hybrid_app.py`. Find `from routes import register_routes` (around line 13). Replace with:
```python
from htmy_hybrid_routes import register_routes
```

- [ ] **Step 3: Rename `routes/` directory using git mv**

Run:
```bash
git mv examples/htmy-hybrid/routes examples/htmy-hybrid/htmy_hybrid_routes
```

Verify with `git status`.

- [ ] **Step 4: Update `examples/htmy-hybrid/tests/conftest.py`**

Edit `examples/htmy-hybrid/tests/conftest.py`:

Change `from main import app as fastblocks_app` (line 25) to:
```python
from htmy_hybrid_app import app as fastblocks_app
```

Update the leading docstring comment (line 16) from:
```python
# Make ``main`` importable regardless of pytest's rootdir discovery —
# the htmy-hybrid app lives at ``examples/htmy-hybrid/main.py`` and the
# tests need to import it via ``from main import app``.
```
to:
```python
# Make ``htmy_hybrid_app`` importable regardless of pytest's rootdir discovery —
# the htmy-hybrid app lives at ``examples/htmy-hybrid/htmy_hybrid_app.py`` and
# the tests need to import it via ``from htmy_hybrid_app import app``.
```

- [ ] **Step 5: Verify htmy-hybrid-only tests pass after rename**

Run:
```bash
.venv/bin/pytest examples/htmy-hybrid/ --no-cov -q 2>&1 | tail -5
```

Expected: `M passed, 1 skipped` (same M as Task 1 Step 3). If failures appear, the rename broke something — STOP and re-read.

- [ ] **Step 6: Verify cross-example invocation now passes (GREEN)**

Run:
```bash
.venv/bin/pytest examples/ --no-cov -q 2>&1 | tail -5
```

Expected: `0 failed` (the GREEN gate — both apps now coexist cleanly). If failures remain, the renames did not fully resolve the pollution — STOP and re-investigate before proceeding to Task 4.

**No commit at this task boundary** — Task 4 has comment/doc updates that must land in the same commit for atomicity.

---

### Task 4: Update README commands and test docstring references

**Files:**
- Modify: `examples/landing/README.md` (uvicorn command line 17 + tree diagram if applicable)
- Modify: `examples/htmy-hybrid/README.md` (uvicorn command line 26 + tree diagram entry line 48)
- Modify: `tests/adapters/middleware/test_security_headers_boot.py` (docstring line 5)
- Modify: `tests/adapters/middleware/test_brotli_boot.py` (docstring line 5)
- Modify: `tests/adapters/middleware/test_csrf_boot.py` (docstring line 5)
- Modify: `tests/adapters/templates/test_fastblocks_ui_boot.py` (docstring line 10)

**Interfaces:**
- Consumes: Tasks 2 and 3 renames complete
- Produces: All path references in these files use the new names; `git grep` audit returns zero stale references (excluding historical plan docs)

- [ ] **Step 1: Update `examples/landing/README.md`**

Read `examples/landing/README.md` line 17. Find:
```
  python -m uvicorn main:app --host 127.0.0.1 --port 8001
```
Replace with:
```
  python -m uvicorn landing_app:app --host 127.0.0.1 --port 8001
```

Also update any tree-diagram entries that reference `main.py` or `routes/` (use `grep -n "main\|routes" examples/landing/README.md` to find them). The expected replacements:
- `main.py` → `landing_app.py`
- `routes/` → `landing_routes/` (only if the tree diagram lists it)

- [ ] **Step 2: Update `examples/htmy-hybrid/README.md`**

Read `examples/htmy-hybrid/README.md` lines 26 and 48. Find:
```
  python -m uvicorn main:app --host 127.0.0.1 --port 8002
```
Replace with:
```
  python -m uvicorn htmy_hybrid_app:app --host 127.0.0.1 --port 8002
```

Update the tree diagram entry at line 48 from `├── main.py` → `├── htmy_hybrid_app.py` and `├── routes/` → `├── htmy_hybrid_routes/`.

- [ ] **Step 3: Update `tests/adapters/middleware/test_security_headers_boot.py` docstring**

Read line 5. Find the docstring reference to `examples/landing/routes/adapter_matrix.py`. Update to `examples/landing/landing_routes/adapter_matrix.py`.

- [ ] **Step 4: Update `tests/adapters/middleware/test_brotli_boot.py` docstring**

Read line 5. Update the reference from `examples/landing/routes/adapter_matrix.py` to `examples/landing/landing_routes/adapter_matrix.py`.

- [ ] **Step 5: Update `tests/adapters/middleware/test_csrf_boot.py` docstring**

Read line 5. Update the reference from `examples/landing/routes/adapter_matrix.py` to `examples/landing/landing_routes/adapter_matrix.py`.

- [ ] **Step 6: Update `tests/adapters/templates/test_fastblocks_ui_boot.py` docstring**

Read line 10. Update the reference from `examples/landing/routes/adapter_matrix.py` to `examples/landing/landing_routes/adapter_matrix.py`.

- [ ] **Step 7: Run the git grep audit**

Run:
```bash
git grep -n "examples/landing/main\|examples/landing/routes\|examples/htmy-hybrid/main\|examples/htmy-hybrid/routes" -- ':!docs/superpowers/plans/'
```

Expected: **zero output** (no stale path references outside the excluded historical plan docs). If any line prints, STOP and fix the offending reference before proceeding to Task 5.

- [ ] **Step 8: Run the full test suite for regression check**

Run:
```bash
.venv/bin/pytest tests/ --no-cov -q 2>&1 | tail -10
```

Expected: no NEW failures vs the pre-rename baseline. The previous passing count must not decrease. If failures appear that did not exist at Task 1 baseline, STOP and re-investigate — Task 4's doc updates should not change runtime behavior, but verify before committing.

**No commit at this task boundary** — Task 5 contains the single atomic commit step.

---

### Task 5: Final verification + atomic commit

**Files:**
- Touch: `git` only — no file content changes; verify state is clean and commit.

**Interfaces:**
- Consumes: Tasks 1-4 all complete
- Produces: One atomic commit at HEAD on `main`; no push.

- [ ] **Step 1: Verify git status reflects only the renames and edits**

Run:
```bash
git status --short
```

Expected: every line is either `R` (rename), `M` (modification), or empty (already staged). There should be NO `??` (untracked) lines — every file was either renamed or edited. There should be NO `D` (deletion) followed by `??` (untracked add of the same content) — `git mv` preserves rename detection.

- [ ] **Step 2: Verify production framework code is unchanged**

Run:
```bash
git diff HEAD fastblocks/core/ | head -5
```

Expected: **empty output** (no changes in `fastblocks/core/`). This confirms ADR 0008 Rule 2 was respected.

- [ ] **Step 3: Final cross-example verification**

Run:
```bash
.venv/bin/pytest examples/ --no-cov -q 2>&1 | tail -5
```

Expected: `0 failed`. If any failure appears, STOP — the GREEN gate has not been achieved. Do not commit a known-broken state.

- [ ] **Step 4: Final full-suite regression check**

Run:
```bash
.venv/bin/pytest tests/ --no-cov -q 2>&1 | tail -10
```

Expected: no NEW failures vs Task 1 Step 4 baseline. The `test_hx_trigger_emission.py` test must still pass; the 4 docstring-updated test files must still pass; the 25-passing `tests/test_htmx_property.py` must still pass.

- [ ] **Step 5: Atomic commit**

Stage everything and commit in one shot:
```bash
git add -A
git commit -m "$(cat <<'EOF'
refactor(fastblocks): rename example main.py/routes/ to app-specific names

Fixes cross-example test pollution (``pytest examples/`` failed with 2 of
27 tests) by renaming generic-name modules that collided via sys.path +
sys.modules cache.

Both example apps used ``main.py`` for their FastBlocks app factory and
``routes/`` for route registrations. Each example's conftest did
``sys.path.insert(0, _APP_ROOT)``; whichever conftest loaded last owned
the ``main`` slot, and ``from main import app`` returned whichever cached
instance was first (or got shadowed).

Per ADR 0008 Rule 2 the resolver singleton stays as-is. The fix is
naming-as-isolation: rename ``main.py`` -> ``<app>_app.py`` and
``routes/`` -> ``<app>_routes/`` in each example app. The failure mode
for a future example that forgets the convention becomes a clear
ImportError at import time instead of silent state pollution.

Files changed:
- examples/landing/main.py -> landing_app.py
- examples/landing/routes/ -> landing_routes/
- examples/htmy-hybrid/main.py -> htmy_hybrid_app.py
- examples/htmy-hybrid/routes/ -> htmy_hybrid_routes/
- examples/{landing,htmy-hybrid}/tests/conftest.py (imports + docstring)
- tests/htmx/test_hx_trigger_emission.py (import + sys.modules cleanup)
- tests/adapters/middleware/{test_security_headers_boot,
  test_brotli_boot,test_csrf_boot}.py (docstring references)
- tests/adapters/templates/test_fastblocks_ui_boot.py (docstring ref)
- examples/{landing,htmy-hybrid}/README.md (uvicorn commands + tree)

Production framework code (fastblocks/core/) is bit-for-bit unchanged.
Historical plan docs (docs/superpowers/plans/2026-09-27-*) are unchanged
on purpose: they are dated implementation records.

Pre-rename baseline: pytest examples/ = 2 failed, 25 passed.
Post-rename:        pytest examples/ = 0 failed, 25 passed.
EOF
)"
```

The commit body uses heredoc so multi-line content is preserved. Do NOT add a `Co-Authored-By` trailer.

- [ ] **Step 6: Verify commit landed and tree is clean**

Run:
```bash
git log --oneline -5
git status
```

Expected:
- The new commit is HEAD with the subject `refactor(fastblocks): rename example main.py/routes/ to app-specific names`.
- `git status` shows `nothing to commit, working tree clean`.
- The new commit sits on top of `2c9b357` (the spec doc commit) on `main`.

- [ ] **Step 7: Final gate — confirm GREEN one more time after commit**

Run:
```bash
.venv/bin/pytest examples/ --no-cov -q 2>&1 | tail -5
```

Expected: `0 failed` (post-commit state still green).

**STOP here. Do not push.** Push is user-controlled per `feedback-bodai-push-is-user-controlled.md`. Report the commit SHA and verification results to the user; they will push when ready.

---

## Self-Review

**Spec coverage:**

| Spec requirement | Plan task |
|---|---|
| Rename `examples/landing/main.py` → `landing_app.py` | Task 2 Step 1 |
| Update internal `routes` import | Task 2 Step 2 |
| Rename `examples/landing/routes/` → `landing_routes/` | Task 2 Step 3 |
| Update landing conftest import + docstring | Task 2 Step 4 |
| Update `test_hx_trigger_emission.py` import + `sys.modules` | Task 2 Step 5 |
| Rename `examples/htmy-hybrid/main.py` → `htmy_hybrid_app.py` | Task 3 Step 1 |
| Update internal `routes` import | Task 3 Step 2 |
| Rename `examples/htmy-hybrid/routes/` → `htmy_hybrid_routes/` | Task 3 Step 3 |
| Update htmy-hybrid conftest import + docstring | Task 3 Step 4 |
| Update landing README | Task 4 Step 1 |
| Update htmy-hybrid README | Task 4 Step 2 |
| Update 4 production test docstrings | Task 4 Steps 3-6 |
| `git grep` audit gate | Task 4 Step 7 |
| Full suite regression check | Task 4 Step 8 + Task 5 Step 4 |
| Production framework unchanged gate | Task 5 Step 2 |
| Single atomic commit | Task 5 Step 5 |
| No `Co-Authored-By` trailer | Task 5 Step 5 (explicit in commit body) |
| No push | Task 5 Step 7 (explicit STOP) |
| Skip historical plan docs | Global Constraints + each task's exclude |
| Coverage gate workaround (`--no-cov`) | Global Constraints + every verification command |

All spec requirements covered.

**Placeholder scan:** No "TBD", "TODO", "implement later", or "add appropriate" patterns. Each step has explicit commands or code blocks.

**Type / name consistency:**
- `landing_app` used consistently across Task 2 (steps 1, 2, 4, 5) and Task 5 commit body.
- `landing_routes` used consistently in Task 2 (steps 2, 3).
- `htmy_hybrid_app` used consistently in Task 3 (steps 1, 2, 4) and Task 5 commit body.
- `htmy_hybrid_routes` used consistently in Task 3 (steps 2, 3).
- `sys.modules` cleanup pattern consistent: `name == "X" or name.startswith("X.")`.

**Interface contract clarity:** Each task's "Interfaces" block names the exact symbol the next task expects (e.g. Task 2 produces `landing_app.py` exporting `app` and `create_app`; Task 3 doesn't depend on those symbols but on Task 2 being complete).

No inconsistencies found. Plan is ready for execution.

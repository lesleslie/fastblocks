# FastBlocks Cross-Example Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Eliminate cross-example test pollution (`pytest examples/` → 6 failed, all in htmy-hybrid) by extending the existing rename pattern to cover the `templates/` top-level package — the third and final collision class not yet covered by Tasks 2 and 3 of the original plan. Land as ONE atomic commit combining the already-staged renames (main.py / routes/) and the new work (templates/ + 9 import-site updates + README + comment audit).

**Architecture:** Naming-as-isolation. Each example app gets app-prefixed top-level packages:

- `landing_app`, `landing_routes`, `landing_templates`
- `htmy_hybrid_app`, `htmy_hybrid_routes`, `htmy_hybrid_templates`

With all three collision classes covered, `pytest examples/` finds zero `from X import Y` statements that resolve to a sibling example's package — the cross-example pollution goes away at compile time, not at test time. No new infrastructure; pure refactor.

**Spec:** `docs/superpowers/specs/2026-09-29-fastblocks-cross-example-isolation-design.md` (superseded and re-committed at `68faa2c` with the corrected diagnosis and the extended scope).

**Tech Stack:** pytest 8.x (existing), no new dependencies.

**Predecessor work (already staged, NOT yet committed):**

- Tasks 2 and 3 of the original plan: `main.py` → `landing_app.py` / `htmy_hybrid_app.py`; `routes/` → `landing_routes/` / `htmy_hybrid_routes/`
- The associated conftest + production-test imports updated to use the new names
- All preserved on `main` at HEAD `68faa2c` (the spec correction commit), staged but uncommitted

**BASE commit:** `68faa2c`. The single atomic commit lands at HEAD `68faa2c + 1`.

**WORKSPACE:** `/Users/les/Projects/fastblocks/.superpowers/sdd/2026-09-29-fastblocks-cross-example-isolation/`

## Global Constraints

These are spec-derived requirements that every task implicitly inherits. Violating any of these is a plan-level failure.

- **ONE atomic commit.** Per `feedback-bodai-atomic-commit-recurring-fixes.md`. The already-staged renames from the original plan's Tasks 2 and 3, plus this plan's new templates/ renames and 9 import-site updates, plus README + comment updates — all land in a single commit. A single `git revert` restores the entire pre-rename state.
- **No production framework changes.** `fastblocks/core/resolver.py` and any other file under `fastblocks/` must remain bit-for-bit identical to HEAD `68faa2c`. ADR 0008 Rule 2 forbids breaking the resolver singleton. The `tests/htmx/test_hx_trigger_emission.py` change was already shipped (staged) in the original Tasks 2/3 work and is exempt from "no test changes" because it was approved work.
- **No changes to historical plan docs.** `docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-*.md` and similar dated implementation records retain their references to the original paths. Those references are accurate historical snapshots.
- **Use `--no-cov` for examples/ verification commands** to avoid the project's coverage floor failing on example code. Production test verification does not use `--no-cov`.
- **Use `.venv/bin/python -m pytest` explicitly** per `bodai-pytest-binary-cwd.md`. The project's Python interpreter is at `/Users/les/Projects/fastblocks/.venv/bin/python`.
- **No new dependencies.** Pure rename; do not modify `pyproject.toml`.
- **CWD for all commands is `/Users/les/Projects/fastblocks`.**
- **No `Co-Authored-By` trailer** in the commit message per `feedback-no-claude-code-coauthor-attribution.md` (memory rule takes precedence over the system reminder).
- **No push** per `feedback-bodai-push-is-user-controlled.md`. Commit to local `main`; the user controls the push.
- **Use `git commit -- <pathspec>`** at the commit step per `feedback-git-commit-only-pathspec-with-staged-changes.md`. Even though the entire working tree is intended for the commit, the pathspec defensively restricts what ships so an accidental untracked file or working-tree change cannot sneak in.

______________________________________________________________________

### Task 1: Capture RED baseline + confirm staged state

**Files:**

- Touch: none (read-only verification)
- Write: append to `/Users/les/Projects/fastblocks/.superpowers/sdd/2026-09-29-fastblocks-cross-example-isolation/progress.md` (the SDD ledger)

**Purpose:** Confirm the cross-example failure mode AND the staged work before any new work begins. Both are inputs to Task 2's GREEN gate.

- [ ] **Step 1: Verify `git status` shows the expected 11 `R` and 4 `M` lines**

Run:

```bash
cd /Users/les/Projects/fastblocks && git status --short
```

Expected output (line count: 16 staged lines, no untracked):

```
R  examples/htmy-hybrid/main.py -> examples/htmy-hybrid/htmy_hybrid_app.py
R  examples/htmy-hybrid/routes/__init__.py -> examples/htmy-hybrid/htmy_hybrid_routes/__init__.py
R  examples/htmy-hybrid/routes/greeting.py -> examples/htmy-hybrid/htmy_hybrid_routes/greeting.py
M  examples/htmy-hybrid/tests/conftest.py
R  examples/landing/main.py -> examples/landing/landing_app.py
R  examples/landing/routes/__init__.py -> examples/landing/landing_routes/__init__.py
R  examples/landing/routes/adapter_matrix.py -> examples/landing/landing_routes/adapter_matrix.py
R  examples/landing/routes/demo.py -> examples/landing/landing_routes/demo.py
R  examples/landing/routes/docs.py -> examples/landing/landing_routes/docs.py
R  examples/landing/routes/features.py -> examples/landing/landing_routes/features.py
R  examples/landing/routes/home.py -> examples/landing/landing_routes/home.py
R  examples/landing/routes/install.py -> examples/landing/landing_routes/install.py
R  examples/landing/routes/performance.py -> examples/landing/landing_routes/performance.py
R  examples/landing/routes/security.py -> examples/landing/landing_routes/security.py
M  examples/landing/tests/conftest.py
M  examples/landing/tests/test_adapter_matrix.py
M  tests/htmx/test_hx_trigger_emission.py
```

The spec doc (`docs/superpowers/specs/2026-09-29-fastblocks-cross-example-isolation-design.md`) was committed at `68faa2c` and should NOT appear in this `git status`.

- [ ] **Step 2: Confirm the cross-example failure mode (6 failures)**

Run:

```bash
cd /Users/les/Projects/fastblocks && .venv/bin/python -m pytest examples/ --no-cov 2>&1 | tail -10
```

Expected: ends with `6 failed, 20 passed, 1 skipped, 12 warnings in 10.xxs`. The 6 failures must be in `examples/htmy-hybrid/tests/`:

```
FAILED examples/htmy-hybrid/tests/test_render_htmy.py::test_htmy_render_returns_200
FAILED examples/htmy-hybrid/tests/test_render_htmy.py::test_htmy_render_includes_follow_button
FAILED examples/htmy-hybrid/tests/test_render_jinja.py::test_jinja_render_returns_200
FAILED examples/htmy-hybrid/tests/test_render_hybrid.py::test_all_three_modes_are_200
FAILED examples/htmy-hybrid/tests/test_render_jinja.py::test_jinja_render_includes_follow_button
FAILED examples/htmy-hybrid/tests/test_render_hybrid.py::test_all_three_modes_semantically_equivalent
```

Capture the exact failure list. Any deviation (different failure count, failure in a different file) is a STOP signal: re-investigate before proceeding.

- [ ] **Step 3: Verify per-app GREEN — both apps pass when invoked individually**

Run:

```bash
cd /Users/les/Projects/fastblocks && .venv/bin/python -m pytest examples/landing/tests/ --no-cov 2>&1 | tail -3
.venv/bin/python -m pytest examples/htmy-hybrid/tests/ --no-cov 2>&1 | tail -3
```

Expected: landing tests pass (16 passed, 1 skipped — same as the original Task 1 baseline). htmy-hybrid tests pass (10 passed — same as the original Task 1 baseline). This proves the already-staged renames are clean per-app.

- [ ] **Step 4: Verify the production test passes (importing from renamed `landing_app`)**

Run:

```bash
cd /Users/les/Projects/fastblocks && .venv/bin/python -m pytest tests/htmx/test_hx_trigger_emission.py --no-cov -v 2>&1 | tail -10
```

Expected: `3 passed` (per the original session's Task 1 baseline). This proves the staged `landing_app` rename + the `sys.modules` cleanup update in `tests/htmx/test_hx_trigger_emission.py` is correct.

- [ ] **Step 5: Append Ruling 7 + new Task 1 status to the SDD ledger**

Append to `/Users/les/Projects/fastblocks/.superpowers/sdd/2026-09-29-fastblocks-cross-example-isolation/progress.md`:

```markdown

### Ruling 7 (Diagnosis correction 2026-09-29 20:08)

The 2026-09-29 morning's WITHDRAWN hypothesis (Oneiric template-loader caching) was wrong. Fresh trace capture at the diagnosis-update time showed the actual root cause is Python `sys.modules` package-name pollution from the top-level `templates/` package shared by both examples — exactly the original plan's hypothesis, but with one collision class missed: `templates/` in addition to the `main.py` / `routes/` collisions already addressed by the original Tasks 2 and 3.

Captured trace:

```

examples/htmy-hybrid/htmy_hybrid_routes/greeting.py:103: in greeting_route
body = await render_jinja(request, \_JINJA_TEMPLATE, {})
examples/landing/templates/__init__.py:41: in render_template
return \_ENVIRONMENT.get_template(name).render(merged)

```

The frame at `examples/landing/templates/__init__.py:41` proves the `_ENVIRONMENT` is landing's. The mechanism is `sys.modules` package-name pollution from the bare name `templates`, not Oneiric (which has no template loader).

The original plan's renames were correct hygiene work and remain staged. The new work adds `templates/` → `landing_templates/` / `htmy_hybrid_templates/` and updates 9 import sites (8 in landing, 1 in htmy-hybrid). All renames land as ONE atomic commit per `feedback-bodai-atomic-commit-recurring-fixes.md`.

Spec doc updated at commit `68faa2c`. Plan rewritten at the same commit base.

### Task 1 (rerun): Capture RED baseline + confirm staged state — COMPLETE (inline by controller)

**Baseline + staged state captured at HEAD `68faa2c`:**

| Check | Result |
|---|---|
| `git status --short` | 16 staged lines (11 `R` + 5 `M`), no untracked |
| `pytest examples/ --no-cov` | 6 failed, 20 passed, 1 skipped (matches the original Task 1 baseline; failures all in htmy-hybrid) |
| `pytest examples/landing/tests/ --no-cov` | 16 passed, 1 skipped (matches baseline) |
| `pytest examples/htmy-hybrid/tests/ --no-cov` | 10 passed (matches baseline) |
| `pytest tests/htmx/test_hx_trigger_emission.py --no-cov -v` | 3 passed (matches baseline) |

Reason for inline execution (paralleling Ruling 1 from the original plan): 4 read-only pytest invocations + 2 `git status` reads, no code change, no commit, no review gate. Cost if wrong: the baseline can be re-captured from this ledger entry.
```

**No commit at this task boundary** — this is a read-only baseline capture.

______________________________________________________________________

### Task 2: Rename landing `templates/` and update 8 import sites

**Files:**

- Rename: `examples/landing/templates/` → `examples/landing/landing_templates/` (1 file: `__init__.py`)
- Modify: 8 files under `examples/landing/landing_routes/`:
  - `install.py:11`, `security.py:19`, `docs.py:11`, `features.py:17`, `home.py:15`, `performance.py:18`, `demo.py:23`, `adapter_matrix.py:56`

**Interfaces:**

- Consumes: Task 1 baseline (landing tests currently pass per-app).

- Produces: `examples/landing/landing_templates/__init__.py` exporting `render_template`; 8 files under `examples/landing/landing_routes/` doing `from landing_templates import render_template`. Per-app GREEN gate stays identical to baseline (16 passed, 1 skipped).

- [ ] **Step 1: Rename `examples/landing/templates/` via `git mv`**

Run:

```bash
cd /Users/les/Projects/fastblocks && git mv examples/landing/templates examples/landing/landing_templates
git status --short | grep -E "landing.*templates"
```

Expected: a new `R  examples/landing/templates -> examples/landing/landing_templates` line, plus `R  examples/landing/templates/__init__.py -> examples/landing/landing_templates/__init__.py`.

- [ ] **Step 2: Update 8 import sites in `examples/landing/landing_routes/`**

For each of the 8 files below, change:

```python
from templates import render_template
```

to:

```python
from landing_templates import render_template
```

| File | Line |
|---|---|
| `examples/landing/landing_routes/install.py` | 11 |
| `examples/landing/landing_routes/security.py` | 19 |
| `examples/landing/landing_routes/docs.py` | 11 |
| `examples/landing/landing_routes/features.py` | 17 |
| `examples/landing/landing_routes/home.py` | 15 |
| `examples/landing/landing_routes/performance.py` | 18 |
| `examples/landing/landing_routes/demo.py` | 23 |
| `examples/landing/landing_routes/adapter_matrix.py` | 56 |

Use the Edit tool for each file. After each Edit, run `git diff <file> | head -10` to verify only the import line changed.

- [ ] **Step 3: Verify the per-directory GREEN gate for landing**

Run:

```bash
cd /Users/les/Projects/fastblocks && .venv/bin/python -m pytest examples/landing/tests/ --no-cov 2>&1 | tail -3
```

Expected: same count as baseline (16 passed, 1 skipped). Any deviation is a regression — STOP and investigate before proceeding.

- [ ] **Step 4: Confirm the new import resolves to the renamed package, not to anything else**

Run:

```bash
cd /Users/les/Projects/fastblocks && PYTHONPATH=examples/landing .venv/bin/python -c "
import sys
sys.path.insert(0, 'examples/landing')
from landing_templates import render_template
print('render_template from:', render_template.__code__.co_filename)
"
```

Expected: `render_template from: /Users/les/Projects/fastblocks/examples/landing/landing_templates/__init__.py`. If the import resolves to a different file, STOP — the rename did not take effect.

**No commit at this task boundary** — Task 3 must complete first to enable the cross-example GREEN gate.

______________________________________________________________________

### Task 3: Rename htmy-hybrid `templates/` and update 1 import site

**Files:**

- Rename: `examples/htmy-hybrid/templates/` → `examples/htmy-hybrid/htmy_hybrid_templates/` (1 file: `__init__.py`)
- Modify: 1 file `examples/htmy-hybrid/htmy_hybrid_routes/greeting.py:28`

**Interfaces:**

- Consumes: Task 2 completed state (landing `templates/` renamed + 8 import sites updated).

- Produces: `examples/htmy-hybrid/htmy_hybrid_templates/__init__.py` exporting `render_template`; `examples/htmy-hybrid/htmy_hybrid_routes/greeting.py` doing `from htmy_hybrid_templates import render_template as render_jinja`. Per-app GREEN gate stays identical to baseline (10 passed).

- [ ] **Step 1: Rename `examples/htmy-hybrid/templates/` via `git mv`**

Run:

```bash
cd /Users/les/Projects/fastblocks && git mv examples/htmy-hybrid/templates examples/htmy-hybrid/htmy_hybrid_templates
git status --short | grep -E "htmy-hybrid.*templates"
```

Expected: a new `R  examples/htmy-hybrid/templates -> examples/htmy-hybrid/htmy_hybrid_templates` line, plus `R  examples/htmy-hybrid/templates/__init__.py -> examples/htmy-hybrid/htmy_hybrid_templates/__init__.py`.

- [ ] **Step 2: Update the 1 import site — `greeting.py:28`**

Use the Edit tool on `examples/htmy-hybrid/htmy_hybrid_routes/greeting.py` to change:

```python
from templates import render_template as render_jinja
```

to:

```python
from htmy_hybrid_templates import render_template as render_jinja
```

Verify with `git diff examples/htmy-hybrid/htmy_hybrid_routes/greeting.py | head -10`. Expected: a single line change.

- [ ] **Step 3: Verify the per-directory GREEN gate for htmy-hybrid**

Run:

```bash
cd /Users/les/Projects/fastblocks && .venv/bin/python -m pytest examples/htmy-hybrid/tests/ --no-cov 2>&1 | tail -3
```

Expected: same count as baseline (10 passed). Any deviation is a regression — STOP and investigate.

- [ ] **Step 4: Confirm the new import resolves to the renamed package AND the bare `templates` name no longer resolves**

Run:

```bash
cd /Users/les/Projects/fastblocks && PYTHONPATH=examples/htmy-hybrid .venv/bin/python -c "
import sys
sys.path.insert(0, 'examples/htmy-hybrid')
from htmy_hybrid_templates import render_template
print('render_template from:', render_template.__code__.co_filename)
"
```

Expected: `render_template from: /Users/les/Projects/fastblocks/examples/htmy-hybrid/htmy_hybrid_templates/__init__.py`.

Then verify the bare name `templates` no longer resolves (this is what was causing the original pollution):

```bash
cd /Users/les/Projects/fastblocks && PYTHONPATH=examples/htmy-hybrid .venv/bin/python -c "
import sys
sys.path.insert(0, 'examples/htmy-hybrid')
try:
    from templates import render_template
    print('POLLUTION: still resolved to', render_template.__code__.co_filename)
except ImportError as e:
    print('CLEAN: ImportError raised:', e)
"
```

Expected: `CLEAN: ImportError raised: ...` with a message indicating no module named `templates`. This confirms the rename eliminated the bare-name collision.

**No commit at this task boundary** — Task 4 (cross-example verification) + Task 5 (README audit) must complete first to enable the atomic commit.

______________________________________________________________________

### Task 4: Cross-example GREEN gate

**Files:** None (verification only).

**Purpose:** Verify that the cross-example pollution is now fixed. With all three collision classes addressed, `pytest examples/` should go from 6 failed → 0 failed.

- [ ] **Step 1: Run `pytest examples/` and confirm 0 failures**

Run:

```bash
cd /Users/les/Projects/fastblocks && .venv/bin/python -m pytest examples/ --no-cov 2>&1 | tail -10
```

Expected: ends with `26 passed, 1 skipped, 0 failures in 10.xxs` (or similar — the 6 failures must be 0). Capture the exact numbers for the commit body.

Any failure is a regression — STOP and investigate the trace before proceeding.

- [ ] **Step 2: Confirm the production test still passes**

Run:

```bash
cd /Users/les/Projects/fastblocks && .venv/bin/python -m pytest tests/htmx/test_hx_trigger_emission.py --no-cov -v 2>&1 | tail -10
```

Expected: `3 passed`. Any failure is a regression.

- [ ] **Step 3: Confirm full-suite regression — no NEW failures**

Run:

```bash
cd /Users/les/Projects/fastblocks && .venv/bin/python -m pytest tests/ --no-cov -m "not slow" 2>&1 | tail -10
```

Expected: passing test count is unchanged from the baseline; no NEW failures attributable to this rename. A pre-existing failure that was in the baseline is acceptable; a new failure attributable to the renames is not.

**No commit at this task boundary** — Task 5 (audit + cleanup) is required before the atomic commit.

______________________________________________________________________

### Task 5: README + comment audit + clean up stale paths

**Files:**

- Possibly `examples/landing/README.md`, `examples/htmy-hybrid/README.md` (only if they reference renamed paths).
- Possibly `tests/adapters/middleware/test_security_headers_boot.py`, `test_brotli_boot.py`, `test_csrf_boot.py`, `tests/adapters/templates/test_fastblocks_ui_boot.py` (only if their docstrings reference renamed paths).

**Purpose:** Per the original plan's Task 4, audit and update any stale references. Since the original plan's Task 4 was paused, this task combines the audit + the new plan's audit for the templates/ renames.

- [ ] **Step 1: Audit for stale path references**

Run:

```bash
cd /Users/les/Projects/fastblocks && git grep -nE "examples/landing/(main|routes|templates)/|examples/htmy-hybrid/(main|routes|templates)/" \
  -- ':!docs/superpowers/plans/' \
  ':!examples/landing/README.md' \
  ':!examples/htmy-hybrid/README.md'
```

Expected: zero hits. Any hit is a stale reference in a non-excluded file — fix it before the commit.

- [ ] **Step 2: Audit for stale import-style references**

Run:

```bash
cd /Users/les/Projects/fastblocks && git grep -nE "from (templates|routes|main)( |\$| import)" \
  examples/landing/ \
  examples/htmy-hybrid/ \
  tests/ \
  -- ':!docs/superpowers/plans/' \
  ':!examples/landing/README.md' \
  ':!examples/htmy-hybrid/README.md' \
  ':!examples/landing/landing_templates/' \
  ':!examples/htmy-hybrid/htmy_hybrid_templates/' \
  ':!examples/landing/landing_routes/' \
  ':!examples/htmy-hybrid/htmy_hybrid_routes/'
```

Expected: zero hits. Any hit means a file still imports from a generic name — fix it.

- [ ] **Step 3: Update READMEs (only if they reference the renamed paths)**

Check each README:

```bash
cd /Users/les/Projects/fastblocks && git grep -nE "(main\.py|routes/|templates/)" \
  examples/landing/README.md examples/htmy-hybrid/README.md
```

If the READMEs contain `from templates import`, `python -m uvicorn main:app`, or tree diagrams that show `routes/` / `templates/` / `main.py` at the top level, update them to use the new names:

- `main.py` → `landing_app.py` (or `htmy_hybrid_app.py`)
- `routes/` → `landing_routes/` (or `htmy_hybrid_routes/`)
- `templates/` → `landing_templates/` (or `htmy_hybrid_templates/`)

If the READMEs contain no such references (the audit returns empty), no README changes required.

- [ ] **Step 4: Update docstrings in production tests (only if they reference renamed paths)**

Run:

```bash
cd /Users/les/Projects/fastblocks && git grep -nE "examples/landing/(main|routes|templates)/" \
  tests/adapters/middleware/test_security_headers_boot.py \
  tests/adapters/middleware/test_brotli_boot.py \
  tests/adapters/middleware/test_csrf_boot.py \
  tests/adapters/templates/test_fastblocks_ui_boot.py
```

If hits appear, update the references:

- `examples/landing/main.py` → `examples/landing/landing_app.py`
- `examples/landing/routes/adapter_matrix.py` → `examples/landing/landing_routes/adapter_matrix.py`

(No `templates/` references are expected in these test docstrings, but audit defensively.)

If the audit returns empty, no docstring changes required.

- [ ] **Step 5: Verify the production framework code is unchanged**

Run:

```bash
cd /Users/les/Projects/fastblocks && git diff 68faa2c HEAD -- fastblocks/ 2>&1 | head -5
```

Expected: empty output (no production framework changes since `68faa2c`).

**No commit at this task boundary** — Task 6 contains the single atomic commit step.

______________________________________________________________________

### Task 6: Atomic commit

**Files:** All staged renames + import-site updates + README + docstring updates, combined into one commit.

**Purpose:** Land the entire renames as a single atomic commit per `feedback-bodai-atomic-commit-recurring-fixes.md`.

- [ ] **Step 1: Stage all unstaged changes**

Run:

```bash
cd /Users/les/Projects/fastblocks && git add -A
git status --short
```

Expected: only `R` and `M` lines, no `??` (untracked) lines, no ` M` (working-tree-only) lines. The commit should be ready.

- [ ] **Step 2: Confirm the staged file set matches the plan**

Run:

```bash
cd /Users/les/Projects/fastblocks && git status --short
```

Expected file set (count varies with README/docstring audit results):

- 2 fresh `R` lines for the new `templates/` renames (landing + htmy-hybrid)
- 8 `M` lines for the 8 import-site updates in landing_routes/
- 1 `M` line for the 1 import-site update in htmy_hybrid_routes/greeting.py
- Plus the already-staged: 8 `R` lines (original main.py + routes/ renames), 5 `M` lines (original conftests + production test + adapter_matrix test)
- Plus any `M` lines for README / docstring updates from Task 5

Total: ~24 staged file changes. Exact count depends on Task 5's audit results.

- [ ] **Step 3: Commit atomically with pathspec**

Per `feedback-git-commit-only-pathspec-with-staged-changes.md`, the safe pattern when the index holds the working tree is to pass an explicit pathspec. The pathspec restricts the commit to the example renames + import updates + (possibly) README/docstring updates.

Run:

```bash
cd /Users/les/Projects/fastblocks && git commit \
  -m "refactor(fastblocks): rename example top-level packages to app-specific names

The cross-example pytest failure (6 failures in pytest examples/, all in
htmy-hybrid) was caused by Python sys.modules package-name pollution
from three shared top-level names: main.py, routes/, templates/. Two
example apps inserting their own directory to sys.path caused whichever
package got cached first to shadow later resolutions — most visibly
when htmy-hybrid's greeting.py did 'from templates import
render_template' and resolved to landing's templates/, which had its
searchpath pointed at examples/landing/templates/ instead of
examples/htmy-hybrid/templates/.

This commit eliminates the entire collision class by app-prefixing every
shared top-level name:

  examples/landing/main.py         -> examples/landing/landing_app.py
  examples/landing/routes/         -> examples/landing/landing_routes/
  examples/landing/templates/      -> examples/landing/landing_templates/
  examples/htmy-hybrid/main.py     -> examples/htmy-hybrid/htmy_hybrid_app.py
  examples/htmy-hybrid/routes/     -> examples/htmy-hybrid/htmy_hybrid_routes/
  examples/htmy-hybrid/templates/  -> examples/htmy-hybrid/htmy_hybrid_templates/

Eight import sites in landing_routes/ and one in htmy_hybrid_routes/
that read 'from templates import render_template' are updated to point
at the app-prefixed packages. The conftest sys.path inserts in both
examples remain unchanged — the renames make the bare names unique.

Pre-rename  baseline: pytest examples/                  = 6 failed, 20 passed, 1 skipped
Post-rename verified: pytest examples/                  = 0 failed
                      pytest examples/landing/tests/   = 16 passed, 1 skipped (unchanged)
                      pytest examples/htmy-hybrid/...  = 10 passed (unchanged)
                      pytest tests/htmx/test_hx_trigger_emission.py = 3 passed
                      pytest tests/ -m 'not slow'      = no NEW failures

Production framework code (fastblocks/) is bit-for-bit unchanged
(verified git diff against 68faa2c). Historical plan docs
(docs/superpowers/plans/2026-09-27-*) are unchanged on purpose: they
are dated implementation records.

Single atomic commit per feedback-bodai-atomic-commit-recurring-fixes.md.
No push per feedback-bodai-push-is-user-controlled.md." \
  -- examples/ tests/htmx/ tests/adapters/middleware/ tests/adapters/templates/ examples/landing/README.md examples/htmy-hybrid/README.md
```

The pathspec `-- examples/ tests/htmx/ tests/adapters/middleware/ tests/adapters/templates/ examples/landing/README.md examples/htmy-hybrid/README.md` captures every staged change. If Task 5 found additional files needing updates, extend the pathspec accordingly.

Expected:

```
[main <new-sha>] refactor(fastblocks): rename example top-level packages to app-specific names
 N files changed, M insertions(+), K deletions(-)
```

- [ ] **Step 4: Verify the commit is atomic — only intended files**

Run:

```bash
cd /Users/les/Projects/fastblocks && git log -1 --stat | head -50
git status --short
```

Expected:

- `git log -1 --stat` shows the new commit with exactly the renamed + modified files for the example apps + (potentially) the production tests + READMEs. No production framework files.
- `git status --short` is empty (clean) — no uncommitted changes.

______________________________________________________________________

### Task 7: Final verification + SDD ledger closure

**Files:**

- Append to `/Users/les/Projects/fastblocks/.superpowers/sdd/2026-09-29-fastblocks-cross-example-isolation/progress.md`

**Purpose:** Re-verify the GREEN gate post-commit and close the SDD ledger.

- [ ] **Step 1: Re-run the cross-example GREEN gate post-commit**

Run:

```bash
cd /Users/les/Projects/fastblocks && .venv/bin/python -m pytest examples/ --no-cov 2>&1 | tail -5
```

Expected: 0 failures. Confirms the post-commit state matches Task 4's GREEN gate.

- [ ] **Step 2: Verify the commit is reachable and atomic**

Run:

```bash
cd /Users/les/Projects/fastblocks && git log --oneline -5
git show --stat HEAD | head -20
```

Expected:

- `git log --oneline -5` shows the new atomic commit at HEAD, sitting on top of `68faa2c`.

- `git show --stat HEAD` shows all renames + import updates + (potentially) README/docstring updates in one commit. No `fastblocks/` files.

- [ ] **Step 3: Append completion entries to the SDD ledger**

Append to `/Users/les/Projects/fastblocks/.superpowers/sdd/2026-09-29-fastblocks-cross-example-isolation/progress.md`:

```markdown

### Task 2 (extended): Rename landing templates/ + 8 import-site updates — IMPLEMENTER DONE
### Task 3 (extended): Rename htmy-hybrid templates/ + 1 import-site update — IMPLEMENTER DONE
### Task 4: Cross-example GREEN gate — VERIFIED (0 failed)
### Task 5: README + comment audit — VERIFIED (see report)
### Task 6: Atomic commit — VERIFIED (commit at <new-sha>)
### Task 7: Final verification — VERIFIED

PLAN COMPLETE. Acceptance criteria met:
- pytest examples/                          = 0 failed (was 6 failed)
- pytest examples/landing/tests/            = 16 passed, 1 skipped (unchanged)
- pytest examples/htmy-hybrid/tests/        = 10 passed (unchanged)
- pytest tests/htmx/test_hx_trigger_emission.py = 3 passed (unchanged)
- pytest tests/ -m 'not slow'               = no NEW failures
- git grep audit                            = no stale references
- production framework code                 = unchanged
- single atomic commit                      = yes (per feedback-bodai-atomic-commit-recurring-fixes.md)
```

______________________________________________________________________

## Pre-flight scan

| Pair / item | What one produces | What the other consumes | Verdict |
|---|---|---|---|
| Task 2 ↔ Task 3 | Task 2 renames `examples/landing/templates/` + 8 imports | Task 3 renames `examples/htmy-hybrid/templates/` + 1 import | Clean — disjoint file sets |
| Task 2 ↔ Task 4 | Task 2 updates 8 landing imports | Task 4 verifies `pytest examples/` GREEN | Clean — Task 4's verification depends on Task 2's renames being correct |
| Task 3 ↔ Task 4 | Task 3 updates 1 htmy-hybrid import | Task 4 verifies `pytest examples/` GREEN | Clean |
| Task 4 ↔ Task 5 | Task 4 confirms GREEN gate | Task 5 audits and updates stale references | Clean — Task 5 is post-GREEN cleanup, no functional change |
| Task 5 ↔ Task 6 | Task 5 may update README or docstring files | Task 6 commits atomically | Clean — pathspec defensively restricts commit |
| Task 6 ↔ Global Constraints "production framework unchanged" | Task 6 commit must not include `fastblocks/` | Conflict if implementer accidentally adds `fastblocks/` files | Clean — pathspec excludes `fastblocks/` (not in the pathspec list) |
| Task 6 ↔ Global Constraints "single atomic commit" | Already-staged renames from original Tasks 2/3 + new templates/ work | Combined commit | Clean — single commit per plan |
| Task 1 ↔ Global Constraints "no commit at task boundary" | Task 1 is read-only baseline capture | Conflict if implementer accidentally commits | Clean — Task 1 explicitly states no commit |
| Task 6 Step 3 pathspec ↔ feedback-git-commit-only-pathspec-with-staged-changes | The `//- <pathspec>` form limits commit to intended scope | The commit must capture all intended files | Clean — pathspec includes all expected directories |
| Task 7 ↔ Task 6 | Task 7 re-verifies GREEN post-commit | Task 6 commits | Clean — re-verification after commit confirms stability |
| Pre-flight cross-cutting: the original Tasks 2/3 work | main.py + routes/ renames + conftest + production test updates | The new tasks extend with templates/ renames + 9 import-site updates | Clean — same naming pattern, same atomicity |

Scan: clean. No rulings needed before execution.

______________________________________________________________________

## Decisions captured (binding for execution)

- **Extend the original rename plan, not replace it.** Tasks 2 and 3 of the original plan already shipped (staged) two collision classes. This plan adds the third (`templates/`) and atomically with the staged set.
- **One atomic commit** combining already-staged renames + new templates/ renames + 9 import-site updates + (potentially) README/docstring updates. Per `feedback-bodai-atomic-commit-recurring-fixes.md`.
- **`git commit -- <pathspec>`** at the commit step per `feedback-git-commit-only-pathspec-with-staged-changes.md`. The pathspec defensively restricts what ships.
- **No production framework changes** (verified by `git diff 68faa2c HEAD -- fastblocks/` post-commit). ADR 0008 Rule 2.
- **No README rewrites** unless the READMEs contain stale references (Task 5 audit determines).
- **No push.** User controls the push per `feedback-bodai-push-is-user-controlled.md`.
- **No `Co-Authored-By` trailer** per `feedback-no-claude-code-coauthor-attribution.md`.
- **Inline Task 1** (baseline capture) per Ruling 1 from the original plan: 4 read-only pytest invocations + git status reads, no code change, no commit, no review gate.

______________________________________________________________________

## Self-Review

**Spec coverage:**

| Spec requirement | Plan task |
|---|---|
| Rename `examples/landing/templates/` → `landing_templates/` | Task 2 Step 1 |
| Update 8 landing import sites | Task 2 Step 2 |
| Rename `examples/htmy-hybrid/templates/` → `htmy_hybrid_templates/` | Task 3 Step 1 |
| Update 1 htmy-hybrid import site | Task 3 Step 2 |
| Cross-example GREEN gate (0 failed) | Task 4 Step 1 |
| Production test still passes | Task 4 Step 2 |
| Full suite regression check | Task 4 Step 3 |
| README + comment audit | Task 5 Steps 1-4 |
| Production framework unchanged gate | Task 5 Step 5 |
| Single atomic commit (already-staged + new) | Task 6 |
| No `Co-Authored-By` trailer | Task 6 Step 3 (explicit in commit body) |
| No push | Task 7 (explicit STOP) |
| Skip historical plan docs | Global Constraints + every task's exclude |
| Coverage gate workaround (`--no-cov`) | Global Constraints + every verification command |

All spec requirements covered.

**Placeholder scan:** No "TBD", "TODO", "implement later", or "add appropriate" patterns. Each step has explicit commands or code blocks.

**Type / name consistency:**

- `landing_templates` used consistently across Task 2 (Steps 1, 2, 4).
- `htmy_hybrid_templates` used consistently across Task 3 (Steps 1, 2, 4).
- `landing_app`, `htmy_hybrid_app`, `landing_routes`, `htmy_hybrid_routes` (from the original Tasks 2/3 work) used consistently throughout.
- Pathspec `examples/landing/templates/` → `examples/landing/landing_templates/` mapping is exact and matches the import-site updates.

**Interface contract clarity:** Each task's "Interfaces" block names the exact symbol the next task expects (e.g. Task 2 produces `landing_templates/__init__.py` exporting `render_template`; Task 3 doesn't depend on those symbols but on Task 2 being complete).

No inconsistencies found. Plan is ready for execution.

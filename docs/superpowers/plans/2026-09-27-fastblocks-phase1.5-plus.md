# Phase 1.5+ (Deferred-Minors) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear all 7 Phase 1.5 deferred-minors so Phase 2 (build wave) lands on a fully-cleaned test foundation — green suite, coverage gate honored at 67.81%, no test-variance across runs, fresh spec failure inventory.

**Architecture:** 5 dependent waves executed in dependency order. Wave A (cleanup + spec regen) runs first because #1's output feeds Wave E and #4/#6 bundle as trivial. Wave B (force-reload guard refactor) precedes Wave C (xdist hybrid) in case the refactor incidentally resolves some pollution. Wave C is the longest (investigation + treatment) and stabilizes test counts Wave D needs for accurate coverage measurement. Wave E goes last so the fresh inventory + Wave C's pollution treatment are both in place. Each wave ships independently; one SDD task per wave.

**Tech Stack:** Python 3.14+, pytest, pytest-xdist, pytest-asyncio, FastBlocks framework internals, Oneiric resolver

**Spec:** `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-09-27-fastblocks-phase1.5-plus-design.md` (read this before executing any task)

**This is Plan 1 of 1.** Phase 2 (build wave) gets its own spec/plan/SDD cycle after Phase 1.5+ ships.

---

## Global Constraints

- **Python:** 3.14+ (matches `pyproject.toml` `requires-python = ">=3.14"`)
- **Coverage floor:** 67.81% (current: 67.6% measured; 0.21% slip is the work). Floor NOT raised in this cycle.
- **Direct commits to `main`** per Bodai pre-1.0 policy; no PRs
- **No new test infrastructure** — only fix what's deferred; no new pytest plugins/hooks/markers beyond what's already in `tests/conftest.py`
- **Serial marker** (`@pytest.mark.serial`): use the existing hook at `tests/conftest.py:131-153`. Each new serial mark requires a 1-line rationale in `tests/conftest.py`
- **No `acb` imports** anywhere (Phase 1.5 D2 carryover)
- **No `kelp` / `webawesome` references** anywhere (Phase 1.5 D9 carryover)
- **Tests:** TDD discipline — write failing test, verify it fails, implement, verify pass, commit
- **No placeholders** in any step
- **SDD workspace:** `.superpowers/sdd/2026-09-27-fastblocks-phase1.5-plus/` per Phase 1.5 pattern
- **SDD ledger** preserved at `docs/superpowers/sdd-logs/2026-09-27-phase1.5-plus-ledger.md` after execution

---

## File Structure

**New files (across tasks):**

```
docs/
├── spec-failure-inventory.md                                [Task 1, Wave A #1 — NEW]
├── known-test-gaps.md                                       [Task 4, Wave D — NEW (only if carve-outs needed)]
└── superpowers/sdd-logs/2026-09-27-phase1.5-plus-ledger.md   [post-execution — NEW]

scripts/
└── phase1.5-plus-gate.sh                                    [Task 5 — NEW, audit-cleared gate]

tests/adapters/templates/
└── conftest.py                                               [Task 2, Wave B — possibly NEW shared fixture; existing one is minimal]
```

**Modified files:**

```
fastblocks/exceptions.py                                     [Task 1, Wave A #4 — line 155]
tests/a11y/conftest.py                                       [Task 1, Wave A #6 — trailing newline]
tests/adapters/templates/test_jinja2.py                     [Task 2, Wave B — module-level sys.modules → fixture]
tests/adapters/templates/test_rendering_jinja2.py            [Task 2, Wave B — module-level sys.modules → fixture]
tests/conftest.py                                            [Tasks 3, Wave C — serial-mark rationale comment block]
<multiple test files>                                        [Task 3, Wave C — @pytest.mark.serial additions]
<multiple test files>                                        [Task 4, Wave D — new test files for coverage]
docs/known-claim-gaps.md                                     [Task 5, Wave E — only if items are punted]
```

**Each task's expected commit count:**
- Task 1 (Wave A): 3 commits (#1 spec, #4 exception, #6 newline) — one SDD dispatch
- Task 2 (Wave B): 1 commit — one SDD dispatch
- Task 3 (Wave C): 1-2 commits (serial-marks, then optional root-cause fixes) — one SDD dispatch
- Task 4 (Wave D): N commits (one per low-coverage module's test addition) — one SDD dispatch
- Task 5 (Wave E): 1-3 commits (fixes, serial-marks, claim-gap updates) — one SDD dispatch

---

## Task Order (dependencies)

Tasks execute in this order. Each task is independently testable; later tasks depend on earlier ones only at the test-stability level (later tasks must keep earlier tests green).

1. **Task 1: Wave A** — Spec regen + cleanup (3 small commits, no dependencies)
2. **Task 2: Wave B** — Force-reload guard refactor (1 commit, no dependencies; runs before Wave C in case refactor incidentally resolves pollution)
3. **Task 3: Wave C** — xdist hybrid (1-2 commits, depends on Wave B settling force-reload guard; stabilizes test counts for Wave D)
4. **Task 4: Wave D** — Coverage gate slip (N commits, depends on Wave C for stable test counts)
5. **Task 5: Wave E** — Deferred test failures (1-3 commits, depends on Wave A's spec inventory + Wave C's pollution treatment)

After Task 5: **Phase 1.5+ gate** is enforced (per acceptance criteria in spec). Phase 2 plan authoring can begin.

---

### Task 1: Wave A — Spec regen + Cleanup

**Files:**
- Create: `docs/spec-failure-inventory.md` (#1)
- Modify: `fastblocks/exceptions.py:155` (#4)
- Modify: `tests/a11y/conftest.py` (#6, trailing newline)

**Interfaces:**
- Consumes: `pytest --no-cov -v --tb=line` output; current state of `fastblocks/exceptions.py:155`; current state of `tests/a11y/conftest.py`
- Produces: fresh `docs/spec-failure-inventory.md`; `(Exception,)` tuple at line 155; trailing newline at end of `tests/a11y/conftest.py`

**One SDD dispatch** handles all three commits. Implementer applies them in order; reviewer validates all three.

---

#### Sub-step 1A: Spec failure inventory regeneration

- [ ] **Step 1: Run pytest to capture current failures**

Run from `/Users/les/Projects/fastblocks`:
```bash
.venv/bin/pytest --no-cov -v --tb=line 2>&1 | tee /tmp/phase1.5-plus-failures.txt
```

Expected output: list of FAILED tests with file paths and short tracebacks.

- [ ] **Step 2: Categorize each failure**

For each FAILED test, assign one of these categories:
- **(a) currently-failing** — fails every run regardless of mode
- **(b) xdist-only-intermittent** — fails with `--dist=loadfile` but passes with `-p no:xdist`
- **(c) dep-pin-related** — caused by the D8 dep-pin machinery (e.g., `tests/test_dep_pins.py` fixture rotation)
- **(d) a11y-browser-bin-related** — falls under `tests/a11y/` skipped subtree

Skip categories (c) and (d) — they're known-skip sets per existing infrastructure.

- [ ] **Step 3: Write `docs/spec-failure-inventory.md`**

```markdown
# FastBlocks Spec Failure Inventory

**Last regenerated:** YYYY-MM-DD against `main` @ <sha>
**Generated by:** Phase 1.5+ Wave A, Sub-step 1A

## Summary

- **Total failures:** N (currently-failing) + M (xdist-only)
- **Categories:** currently-failing (N), xdist-only (M)
- **Skipped sets:** dep-pin-related, a11y-browser-bin (known-skip, not counted)

## Currently failing (every run)

| Test path | Category | Brief description |
|---|---|---|
| `tests/path/to/test_X.py::test_y` | (a) | one-line description |

## Xdist-only intermittent (fails under xdist, passes serial)

| Test path | Category | Brief description |
|---|---|---|
| `tests/path/to/test_Z.py::test_w` | (b) | one-line description |

## Notes

- (c) dep-pin-related failures: see `tests/test_dep_pins.py` for the broken-release regression set; intentionally skipped here.
- (d) a11y-browser-bin failures: see `tests/a11y/conftest.py` `pytest_ignore_collect`; subtree is skipped when no Playwright browser is available.
- This inventory is regenerated at the start of each plan cycle to avoid drift.
```

Replace `YYYY-MM-DD` with today's date and `<sha>` with `git rev-parse HEAD` output.

- [ ] **Step 4: Verify the inventory is accurate**

Run:
```bash
grep -c "^| " docs/spec-failure-inventory.md
```

Expected: count of table rows matches the FAILED test count from Step 1 minus (c) and (d) categories.

- [ ] **Step 5: Commit**

```bash
git add docs/spec-failure-inventory.md
git commit -m "docs(fastblocks): Phase 1.5+ regen spec failure inventory

Wave A, sub-step 1A. Regenerates docs/spec-failure-inventory.md
against current main HEAD. Used by Wave E to triage the 3
originally-deferred test failures from Phase 1.5."
```

---

#### Sub-step 1B: Exception tuple redundancy

- [ ] **Step 1: Verify baseline — current tuple at `fastblocks/exceptions.py:155`**

Run:
```bash
grep -n "except (" fastblocks/exceptions.py | head -10
```

Expected: line 155 shows `(ImportError, AttributeError, RuntimeError, TypeError, ValueError, Exception)`.

- [ ] **Step 2: Verify tests still pass BEFORE the change**

Run:
```bash
.venv/bin/pytest tests/test_safe_depends_get.py -v --no-cov
```

Expected: PASS (the test that prompted Phase 1.5 Task 4's original widening). If FAIL, the change is not safe — investigate before proceeding.

- [ ] **Step 3: Collapse the tuple**

In `fastblocks/exceptions.py:155`, replace:

Find:
```python
        except (ImportError, AttributeError, RuntimeError, TypeError, ValueError, Exception):
```

Replace:
```python
        except (Exception,):
```

- [ ] **Step 4: Verify tests still pass AFTER the change**

Run:
```bash
.venv/bin/pytest tests/test_safe_depends_get.py -v --no-cov
```

Expected: PASS. If FAIL, revert and investigate (some test depends on a specific exception TYPE).

- [ ] **Step 5: Commit**

```bash
git add fastblocks/exceptions.py
git commit -m "refactor(fastblocks): collapse safe_depends_get exception tuple

Wave A, sub-step 1B. The 5 subclasses (ImportError, AttributeError,
RuntimeError, TypeError, ValueError) are redundant with Exception.
Collapses the tuple to (Exception,) while preserving the contract
that any resolver failure falls back to default.

Phase 1.5 Task 4 originally widened this tuple to catch bare
Exception (the kelp-style XSS regression). Tests still pass;
no test depends on a specific exception type."
```

---

#### Sub-step 1C: Trailing newline on a11y conftest

- [ ] **Step 1: Check current trailing-byte state**

Run:
```bash
tail -c 1 tests/a11y/conftest.py | xxd
```

Expected: shows `0a` (newline) OR something else (e.g., the last byte of the `return True` line if file doesn't end in newline).

If `0a`: skip this sub-step entirely (file already has trailing newline; nothing to commit).
If anything else: continue to Step 2.

- [ ] **Step 2: Append newline**

Run:
```bash
printf '\n' >> tests/a11y/conftest.py
```

- [ ] **Step 3: Verify**

Run:
```bash
tail -c 1 tests/a11y/conftest.py | xxd
```

Expected: `0a`.

- [ ] **Step 4: Commit**

```bash
git add tests/a11y/conftest.py
git commit -m "chore(fastblocks): trailing newline on tests/a11y/conftest.py

Wave A, sub-step 1C. Write-tool artifact from Phase 1.5 Task 7."
```

---

#### Task 1 done criteria

- 3 commits on `main` (one per sub-step)
- `git log --oneline 0b9d849..HEAD` shows 3 commits with the exact messages above
- `docs/spec-failure-inventory.md` exists and matches Step 1.4's verification
- `fastblocks/exceptions.py:155` shows `(Exception,)`
- `tail -c 1 tests/a11y/conftest.py | xxd` shows `0a`
- Reviewer verifies all three sub-steps independently

---

### Task 2: Wave B — Force-reload guard refactor

**Files:**
- Read first: `tests/adapters/templates/conftest.py` (existing — uses `pytest_ignore_collect` only, NOT a fixture)
- Read first: `tests/adapters/templates/test_jinja2.py` (lines 1-60; module-level sys.modules mocking)
- Read first: `tests/adapters/templates/test_rendering_jinja2.py` (lines 1-50; similar module-level mocking)
- Modify: both test files (move sys.modules stubs into a `scope="module"` autouse fixture with explicit `try/finally` teardown)
- Possibly Create: new `tests/adapters/templates/conftest.py` fixture (if shared between test files)
- Possibly Modify: `tests/conftest.py` if a hook is needed for cleanup ordering

**Interfaces:**
- Consumes: existing module-level `sys.modules["jinja2_async_environment"] = types.ModuleType(...)` patterns at the top of both test files
- Produces: a `scope="module"` autouse fixture in the test directory's conftest.py that sets up the stub and tears it down via explicit `try/finally` (not `monkeypatch`, per Bodai memory note `monkeypatch-inline-import-target.md`)

**Why `try/finally` not `monkeypatch`:** `monkeypatch` cannot undo `sys.modules` insertions (Bodai memory note). Use explicit teardown.

- [ ] **Step 1: Locate the `not hasattr(...)` brittle check**

Run:
```bash
grep -rn "not hasattr" tests/adapters/templates/
```

Expected output: 1-2 lines in `test_jinja2.py` and/or `test_rendering_jinja2.py`. These are the brittle checks to remove.

If no hits found: the brittle check has already been removed (the spec assumed it was still there; verify by inspecting the test files directly).

- [ ] **Step 2: Locate the module-level sys.modules stubs**

Run:
```bash
grep -n "sys.modules\[.jinja2_async_environment.\]" tests/adapters/templates/*.py
```

Expected output: lines in `test_jinja2.py` (around line 31-37) and/or `test_rendering_jinja2.py`. These are the module-level stubs to move into a fixture.

- [ ] **Step 3: Write the failing test (TDD: behavior preservation)**

Create `tests/adapters/templates/conftest.py` (overwrite the existing minimal one):

```python
"""Conftest for templates test configuration.

Per Phase 1.5+ Wave B: replaces module-level sys.modules mocking
in test_jinja2.py and test_rendering_jinja2.py with a scope="module"
autouse fixture that uses explicit try/finally teardown. The
not hasattr(...) brittle check is replaced with the fixture's
guarantee.

WHY try/finally not monkeypatch: per Bodai memory note
monkeypatch-inline-import-target.md, monkeypatch cannot undo
sys.modules insertions.
"""
from __future__ import annotations

import sys
import types

import pytest


@pytest.fixture(autouse=True, scope="module")
def _jinja2_async_environment_stub():
    """Provide the jinja2_async_environment stub for tests in this directory.

    Set up before any test in the module runs; torn down after the
    module's last test, regardless of pass/fail. Replaces the previous
    module-level sys.modules stub in test_jinja2.py / test_rendering_jinja2.py
    which leaked across modules.
    """
    # Save current state for teardown
    saved_keys = {}
    for key in [
        "jinja2_async_environment",
        "jinja2_async_environment.loaders",
        "starlette_async_jinja",
    ]:
        if key in sys.modules:
            saved_keys[key] = sys.modules[key]
        else:
            saved_keys[key] = None

    # Set up the stub
    try:
        # starlette_async_jinja stub (synchronous MockAsyncJinja2Templates)
        mock_async_jinja2_templates_module = types.ModuleType("starlette_async_jinja")

        class _MockAsyncJinja2Templates:
            def __init__(self, *args, **kwargs) -> None:
                from unittest.mock import MagicMock
                self.env = MagicMock()
                self.TemplateResponse = MagicMock()
                self.render_block = MagicMock()

        mock_async_jinja2_templates_module.AsyncJinja2Templates = _MockAsyncJinja2Templates
        sys.modules["starlette_async_jinja"] = mock_async_jinja2_templates_module

        # jinja2_async_environment stub
        mock_jinja2_async_env = types.ModuleType("jinja2_async_environment")
        sys.modules["jinja2_async_environment"] = mock_jinja2_async_env

        mock_loaders = types.ModuleType("jinja2_async_environment.loaders")
        mock_jinja2_async_env.loaders = mock_loaders
        sys.modules["jinja2_async_environment.loaders"] = mock_loaders

        class _MockAsyncBaseLoader:
            def __init__(self, *args, **kwargs):
                self.searchpath = args[0] if args else []

            async def get_source(self, environment, template):
                return None, None, None

        mock_loaders.AsyncBaseLoader = _MockAsyncBaseLoader
        mock_loaders.SourceType = tuple

        yield  # tests run here

    finally:
        # Explicit teardown: restore the saved state
        for key, saved_value in saved_keys.items():
            if saved_value is None:
                sys.modules.pop(key, None)
            else:
                sys.modules[key] = saved_value
```

- [ ] **Step 4: Remove module-level sys.modules stubs from test files**

In `tests/adapters/templates/test_jinja2.py`:
- Delete lines 14-37 (the module-level `sys.modules["starlette_async_jinja"] = ...` and `sys.modules["jinja2_async_environment"] = ...` block)
- Delete the `MockAsyncJinja2Templates` class (lines 19-23)
- Delete `mock_jinja2_async_env` and `mock_loaders` variables (lines 31-37)
- Delete `MockAsyncBaseLoader` class (lines 40-48)
- Keep `import sys`, `import typing as t`, `import types` only if they're used elsewhere in the file

In `tests/adapters/templates/test_rendering_jinja2.py`:
- Same removals (lines vary; inspect first)

- [ ] **Step 5: Remove `not hasattr(...)` brittle checks**

In both test files, replace any:

Find:
```python
if not hasattr(some_object, "some_attr"):
    # ad-hoc stub setup
```

Replace:
```python
# Removed per Phase 1.5+ Wave B — the conftest.py fixture
# guarantees the stub is in place.
```

- [ ] **Step 6: Run tests in serial mode**

Run:
```bash
.venv/bin/pytest tests/adapters/templates/ -p no:xdist -v --no-cov
```

Expected: PASS. The fixture's setup runs before any test; teardown runs after.

If FAIL: revert the changes (git checkout -- tests/adapters/templates/) and investigate. Common failure mode: a test imports something at module level that depends on the stub, but the fixture runs at function scope, not module level. The fix is to keep the fixture at `scope="module"` (already set) — verify pytest is using it.

- [ ] **Step 7: Run tests in xdist mode**

Run:
```bash
.venv/bin/pytest tests/adapters/templates/ --dist=loadfile -v --no-cov
```

Expected: PASS, same test count as serial mode.

If a test fails ONLY in xdist mode: that test was depending on shared module state; the fixture is correctly scoped but a specific test still leaks. Investigate with `pytest tests/path/to/test.py --dist=loadfile -v`.

- [ ] **Step 8: Run 5 consecutive times in both modes**

Serial:
```bash
for i in 1 2 3 4 5; do
    .venv/bin/pytest tests/adapters/templates/ -p no:xdist -q --no-cov || { echo "FAIL: serial run $i"; exit 1; }
done
```

Xdist:
```bash
for i in 1 2 3 4 5; do
    .venv/bin/pytest tests/adapters/templates/ --dist=loadfile -q --no-cov || { echo "FAIL: xdist run $i"; exit 1; }
done
```

Expected: all 10 runs PASS.

- [ ] **Step 9: Verify `hasattr` check is gone**

Run:
```bash
grep -rn "not hasattr" tests/adapters/templates/ || echo "OK: hasattr check gone"
```

Expected: `OK: hasattr check gone`.

- [ ] **Step 10: Commit**

```bash
git add tests/adapters/templates/conftest.py tests/adapters/templates/test_jinja2.py tests/adapters/templates/test_rendering_jinja2.py
git commit -m "refactor(fastblocks): Wave B force-reload guard fixture

Moves module-level sys.modules stubs from test_jinja2.py and
test_rendering_jinja2.py into a scope=module autouse fixture in
tests/adapters/templates/conftest.py. Replaces the not hasattr(...)
brittle check with the fixture's guarantee. Uses explicit
try/finally teardown (not monkeypatch) per Bodai memory note
monkeypatch-inline-import-target.md.

Verified: 5 consecutive runs in both -p no:xdist and --dist=loadfile
modes all pass."
```

---

### Task 3: Wave C — xdist-order-pollution hybrid

**Files:**
- Read: `tests/conftest.py:131-153` (existing serial hook from Phase 1.5 final fix wave)
- Possibly Modify: `tests/conftest.py` (extend the serial-mark rationale comment block)
- Multiple Modify: test files where xdist-polluting tests live (the delta set discovered in Step 3)
- Possibly Create: per-test `@pytest.mark.serial` additions + `try/finally` sys.modules guards for genuinely nondeterministic tests

**Interfaces:**
- Consumes: 5-run baseline in serial mode (`-p no:xdist`) + 5-run baseline in xdist mode (`--dist=loadfile`)
- Produces: a delta set of xdist-polluting tests; for each, one of: `@pytest.mark.serial` (genuine pollution), root-cause fix (test-design defect), or punt-to-Wave-E (pre-existing bug)

- [ ] **Step 1: Establish serial-mode baseline**

Run 5 times:
```bash
for i in 1 2 3 4 5; do
    .venv/bin/pytest --no-cov -p no:xdist -q 2>&1 | tee /tmp/phase1.5-plus-serial-$i.txt
done
```

Expected: 5 runs, all green (same set of tests, possibly varying xpassed/xfailed counts but zero FAILED/ERROR).

- [ ] **Step 2: Establish xdist-mode baseline**

Run 5 times:
```bash
for i in 1 2 3 4 5; do
    .venv/bin/pytest --no-cov --dist=loadfile -q 2>&1 | tee /tmp/phase1.5-plus-xdist-$i.txt
done
```

Expected: 5 runs, may have failures (this is the pollution we're fixing).

- [ ] **Step 3: Compute the delta set**

For each test ID that appears as FAILED or ERROR in any of the 5 xdist runs:
- If the test ID appears in ALL 5 xdist runs as failed → consistently-polluting-in-xdist
- If the test ID appears in some xdist runs as failed but not others → flaky-in-xdist (likely nondeterministic; punt)
- If the test ID does NOT appear in any of the 5 serial runs as failed → confirmed xdist-only pollution

The set of "confirmed xdist-only pollution" tests is the delta set.

- [ ] **Step 4: Categorize each delta test**

For each test in the delta set, choose ONE treatment:

| Treatment | Criterion |
|---|---|
| `@pytest.mark.serial` | The test shares module-level state (a module-level fixture, a singleton registry, a global cache) that another test in another file mutates |
| Root-cause fix | The test mutates global state without restoring it; add `try/finally` teardown in the test or extract to a fixture with teardown |
| Punt to Wave E | The test is flaky in BOTH serial and xdist modes (genuine nondeterminism); document with target date |

If unsure between treatments, default to serial-mark (safest; can be revisited).

- [ ] **Step 5: Apply serial-marks**

For each test designated "serial-mark":

In the test file, find:
```python
def test_name():
```

Replace:
```python
@pytest.mark.serial
def test_name():
```

If the test file does not import `pytest`, add `import pytest` (or extend an existing `import pytest as pytest` if it's aliased).

- [ ] **Step 6: Apply root-cause fixes (if any)**

For each test designated "root-cause fix":
- Identify the shared state mutation
- Add teardown via explicit `try/finally` OR extract to a `scope="function"` fixture with proper teardown
- Run the test in isolation (`pytest tests/path/to/test.py::test_name -v`) to verify the fix
- Run the test under `--dist=loadfile` 5 times to verify no regression

- [ ] **Step 7: Extend the serial-mark rationale comment in `tests/conftest.py`**

In `tests/conftest.py`, find the existing rationale comment block (around line 131-146). Add a new section listing each serial mark added in Wave C:

```python
    # Phase 1.5+ Wave C serial-marks (added YYYY-MM-DD):
    # - tests/path/to/test_X.py::test_y — [brief rationale: "shares singleton X"]
    # - tests/another/test_Z.py::test_w — [brief rationale: "mutates module-level cache Y"]
```

The comment block stays in `tests/conftest.py` adjacent to the hook that consumes the marker.

- [ ] **Step 8: Run 5 consecutive xdist runs**

```bash
for i in 1 2 3 4 5; do
    .venv/bin/pytest --no-cov --dist=loadfile -q || { echo "FAIL: xdist run $i"; exit 1; }
done
```

Expected: all 5 runs PASS. If any run still has xdist-only failures, revisit Step 4's categorization — likely an under-categorized genuine-pollution test.

- [ ] **Step 9: Run 5 consecutive serial runs (regression check)**

```bash
for i in 1 2 3 4 5; do
    .venv/bin/pytest --no-cov -p no:xdist -q || { echo "FAIL: serial run $i"; exit 1; }
done
```

Expected: all 5 runs PASS.

- [ ] **Step 10: Commit**

```bash
git add tests/ tests/conftest.py
git commit -m "fix(fastblocks): Wave C xdist-order-pollution hybrid

Investigation: ran pytest -p no:xdist 5x and pytest --dist=loadfile
5x, computed delta set of xdist-only-polluting tests.

Treatments applied (see tests/conftest.py rationale block):
- @pytest.mark.serial on N tests (genuine shared-state pollution)
- Root-cause fixes on M tests (try/finally teardown or fixture extraction)

Punted to Wave E: K tests (genuine nondeterminism, both modes flaky).

Verified: 5 consecutive --dist=loadfile runs all green; 5
consecutive -p no:xdist runs all green (regression check)."
```

---

### Task 4: Wave D — Coverage gate slip (0.21%)

**Files:**
- Read: `.coverage-ratchet.json` (current floor is 67.81)
- Read: `pyproject.toml` (`--cov-fail-under=67.81`)
- Possibly Create: multiple new test files in `tests/` for uncovered modules
- Possibly Create: `docs/known-test-gaps.md` (only if carve-outs needed)

**Interfaces:**
- Consumes: `pytest --cov=fastblocks --cov-report=term-missing` output
- Produces: 5 consecutive `--cov=fail_under=67.81` passes; optionally, carve-out documentation

- [ ] **Step 1: Re-measure coverage (post-Wave-C stable test counts)**

Run:
```bash
.venv/bin/pytest --cov=fastblocks --cov-report=term-missing --no-cov -q 2>&1 | tail -100
```

(Note: the `--no-cov` after `--cov=fastblocks` disables any extra coverage; we're explicitly using `--cov-report=term-missing` to see line-level gaps.)

Expected: total coverage 67.6% (or similar). The output's bottom shows the lowest-coverage modules with missing line numbers.

- [ ] **Step 2: Identify the lowest-coverage modules with the most missing lines**

From the report, list the 5 modules with the lowest coverage and most "Missing" lines. Focus on `fastblocks/*.py` (not test files).

- [ ] **Step 3: Pick the highest-marginal-value module**

Choose ONE module from Step 2's list. Criterion: smallest number of uncovered lines that closes the largest coverage gap.

If multiple modules tie, prefer the one with the simplest API surface (easiest to test).

- [ ] **Step 4: Write the failing test (TDD)**

For the chosen module, identify 1-3 functions/methods with uncovered lines. Write a test that exercises each.

Example (illustrative — actual target depends on Step 3's choice):
```python
"""Wave D coverage tests for fastblocks/<module>.py."""
import pytest

# Import the target
from fastblocks.<module> import <thing>


def test_<thing>_covers_uncovered_branch():
    # Exercise the code path that coverage report shows as missing
    result = <thing>(<inputs that hit the uncovered branch>)
    assert <expected>


def test_<thing>_<other_branch>():
    result = <thing>(<inputs>)
    assert <expected>
```

- [ ] **Step 5: Run the test to verify it passes (TDD reverse)**

Since this is closing a coverage gap, the test may already pass if the code is correct. Verify:
```bash
.venv/bin/pytest tests/path/to/new_test.py -v --no-cov
```

Expected: PASS (the test exercises the previously-uncovered code path; no production code change needed).

If FAIL: the uncovered code path has a bug. STOP. Surface to the reviewer — this is a real defect, not just a coverage gap. Don't fix the production code in this task; punt to a separate cycle.

- [ ] **Step 6: Re-measure coverage**

Run:
```bash
.venv/bin/pytest --cov=fastblocks --cov-report=term-missing --no-cov -q 2>&1 | tail -5
```

Expected: total coverage increased. If still below 67.81%, repeat Steps 3-5 with the next module.

- [ ] **Step 7: Verify 5 consecutive coverage-gate runs**

```bash
for i in 1 2 3 4 5; do
    .venv/bin/pytest --cov=fail_under=67.81 -q || { echo "FAIL: coverage run $i"; exit 1; }
done
```

Expected: all 5 runs PASS.

- [ ] **Step 8: If any code remains untestable, document in `docs/known-test-gaps.md`**

Create `docs/known-test-gaps.md`:
```markdown
# Known Test Gaps

Coverage gate is enforced at 67.81% per `.coverage-ratchet.json`.
Code that is genuinely untestable (platform-specific, requires
external services, etc.) is documented here for transparency.

| File:Line | Reason | Removal plan |
|---|---|---|
| `fastblocks/foo.py:42` | Requires network access; mocked in tests but uncovered in branch X | Add a vcr.py cassette, target Phase 1.5++ |
```

Each entry requires a removal plan. No "TBD" entries.

- [ ] **Step 9: Commit**

If new test files were added:
```bash
git add tests/
git commit -m "test(fastblocks): Wave D close coverage gap to 67.81%

Adds tests for previously-uncovered code in fastblocks/<modules>:
- <module 1>: <brief>
- <module 2>: <brief>

Coverage now at 67.81%+ (verified 5 consecutive --cov=fail_under=67.81
runs). .coverage-ratchet.json floor unchanged.

If carve-outs: see docs/known-test-gaps.md."
```

If only known-test-gaps.md was created:
```bash
git add docs/known-test-gaps.md
git commit -m "docs(fastblocks): Wave D coverage carve-outs documented

Coverage gate now at 67.81% with carve-outs for genuinely
untestable code paths. Each entry has a removal plan."
```

(Or both, in separate commits.)

---

### Task 5: Wave E — Deferred test failures + Gate script

**Files:**
- Read: `docs/spec-failure-inventory.md` (from Task 1 sub-step 1A)
- Possibly Modify: multiple test files (Wave C punts + Wave E triages)
- Possibly Modify: `docs/known-claim-gaps.md`
- Create: `scripts/phase1.5-plus-gate.sh`

**Interfaces:**
- Consumes: `docs/spec-failure-inventory.md` from Task 1
- Produces: 3 originally-deferred failures each with a disposition (fix/serial/punt-with-date); `scripts/phase1.5-plus-gate.sh` audit script

- [ ] **Step 1: Read the fresh spec failure inventory**

Run:
```bash
cat docs/spec-failure-inventory.md
```

Locate the 3 originally-deferred test failures (per the Phase 1.5
ledger: at minimum `test_no_broken_release_in_dep_specs` and
`test_jinja2_environment_default_autoescape_is_true`; the third
is whatever the fresh inventory surfaces).

- [ ] **Step 2: Triage each originally-deferred failure**

For each test, choose ONE disposition:

| Disposition | When to apply | Implementation |
|---|---|---|
| **Quick fix** (≤30 min OR ≤20 lines of test change) | The test's failure has an obvious cause; the fix is bounded | Edit the test, run it locally, commit |
| **Mark serial** | The test is genuinely xdist-polluting (Wave C missed it) | Add `@pytest.mark.serial` and update `tests/conftest.py` rationale comment |
| **Punt to Phase 1.5++** | The test is broken for reasons that don't fit this cycle's scope | Add entry to `docs/known-claim-gaps.md` with target date |

If unsure, default to "punt with target date" — preserves the work item without blocking Phase 2.

- [ ] **Step 3: Apply quick fixes (if any)**

For each "quick fix":
- Read the failing test
- Identify the root cause (assertion failure? ImportError? AttributeError?)
- Make the minimal change
- Verify: `.venv/bin/pytest tests/path/to/test.py::test_name -v --no-cov` PASSES
- Commit separately per fix

- [ ] **Step 4: Apply serial-marks (if any)**

For each "mark serial":
- Add `@pytest.mark.serial` decorator above the test function
- Update `tests/conftest.py` rationale comment block with the test name + rationale
- Commit

- [ ] **Step 5: Document punts in `docs/known-claim-gaps.md`**

For each punt, add an entry:
```markdown
| `<test path>::<test name>` | Punt to Phase 1.5++ | <one-line reason> | Target: YYYY-MM-DD |
```

Commit the `known-claim-gaps.md` update.

- [ ] **Step 6: Write `scripts/phase1.5-plus-gate.sh`**

Create `scripts/phase1.5-plus-gate.sh`:
```bash
#!/usr/bin/env bash
# Phase 1.5+ audit-cleared gate. Exits 0 iff all checks pass.
# Usage: bash scripts/phase1.5-plus-gate.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Phase 1.5+ gate ==="

# Wave A: spec failure inventory exists
test -f docs/spec-failure-inventory.md \
    || { echo "FAIL: docs/spec-failure-inventory.md missing (Wave A #1)"; exit 1; }
echo "OK: spec failure inventory present"

# Wave A: trailing newline on a11y conftest
LAST_BYTE=$(tail -c 1 tests/a11y/conftest.py | xxd -p)
[ "$LAST_BYTE" = "0a" ] \
    || { echo "FAIL: tests/a11y/conftest.py missing trailing newline (Wave A #6)"; exit 1; }
echo "OK: a11y conftest has trailing newline"

# Wave A: exception tuple collapsed
grep -q "except (Exception,):" fastblocks/exceptions.py \
    || { echo "FAIL: exception tuple not collapsed (Wave A #4)"; exit 1; }
echo "OK: exception tuple collapsed"

# Wave B: hasattr check gone from templates tests
if grep -rq "not hasattr" tests/adapters/templates/; then
    echo "FAIL: hasattr check still present in templates tests (Wave B #5)"
    exit 1
fi
echo "OK: templates tests clean of hasattr brittleness"

# Wave C: serial-marks documented
grep -q "Phase 1.5+ Wave C serial-marks" tests/conftest.py \
    || { echo "FAIL: no Wave C serial-marks rationale in tests/conftest.py"; exit 1; }
echo "OK: Wave C serial-marks documented"

# 5 consecutive serial runs
echo "Running 5 consecutive serial pytest runs..."
for i in 1 2 3 4 5; do
    .venv/bin/pytest --no-cov -p no:xdist -q \
        || { echo "FAIL: serial run $i"; exit 1; }
done
echo "OK: 5/5 serial runs passed"

# 5 consecutive xdist runs
echo "Running 5 consecutive xdist pytest runs..."
for i in 1 2 3 4 5; do
    .venv/bin/pytest --no-cov --dist=loadfile -q \
        || { echo "FAIL: xdist run $i"; exit 1; }
done
echo "OK: 5/5 xdist runs passed"

# 5 consecutive coverage-gate runs
echo "Running 5 consecutive coverage-gate runs..."
for i in 1 2 3 4 5; do
    .venv/bin/pytest --cov=fail_under=67.81 -q \
        || { echo "FAIL: coverage run $i"; exit 1; }
done
echo "OK: 5/5 coverage-gate runs passed"

echo "=== Phase 1.5+ gate: ALL CHECKS PASSED ==="
```

Make executable:
```bash
chmod +x scripts/phase1.5-plus-gate.sh
```

- [ ] **Step 7: Run the gate**

Run:
```bash
bash scripts/phase1.5-plus-gate.sh
```

Expected: exits 0, prints "Phase 1.5+ gate: ALL CHECKS PASSED".

If FAIL: address the failing check (typically by returning to the wave that owns it; do NOT add workarounds to the gate script).

- [ ] **Step 8: Commit the gate script**

```bash
git add scripts/phase1.5-plus-gate.sh
git commit -m "ci(fastblocks): Wave E Phase 1.5+ audit-cleared gate

Adds scripts/phase1.5-plus-gate.sh enforcing:
- docs/spec-failure-inventory.md present
- a11y conftest trailing newline
- exception tuple collapsed
- templates tests clean of hasattr brittleness
- Wave C serial-marks documented
- 5/5 serial pytest runs
- 5/5 xdist pytest runs
- 5/5 --cov=fail_under=67.81 runs

Run: bash scripts/phase1.5-plus-gate.sh
Exit 0 iff Phase 1.5+ is done; Phase 2 build wave is unblocked."
```

---

## Post-Task 5: Phase 1.5+ Gate

After Task 5, run the gate one final time:

```bash
cd /Users/les/Projects/fastblocks
bash scripts/phase1.5-plus-gate.sh
```

When ALL checks pass:
- Phase 1.5+ is complete
- Phase 2 (build wave) plan authoring can begin
- SDD ledger preservation follows Phase 1.5 pattern (`docs/superpowers/sdd-logs/2026-09-27-phase1.5-plus-ledger.md`)

---

## Self-Review

**1. Spec coverage:**
- #1 Spec failure inventory regen — Task 1 sub-step 1A ✓
- #2 Coverage gate slip — Task 4 ✓
- #3 xdist-order-pollution hybrid — Task 3 ✓
- #4 Exception tuple redundancy — Task 1 sub-step 1B ✓
- #5 Force-reload guard refactor — Task 2 ✓
- #6 Missing trailing newline — Task 1 sub-step 1C ✓
- #7 Deferred test failures — Task 5 ✓
- All 7 deferred-minors covered; 5 waves sequenced by dependency; gate script enforces 5/5 runs in each mode

**2. Placeholder scan:**
- "≤30 min" / "≤20 lines" in Task 5 Step 2 — these are triage thresholds, not placeholders for code; reviewer flag is the right discipline
- "TBD" / "TODO" / "implement later" — none
- "Fill in details" — none

**3. Type consistency:**
- `try/finally` teardown pattern used consistently in Task 2 and Task 3 (root-cause fixes)
- `@pytest.mark.serial` referenced consistently in Task 3 and Task 5 (carryover from Phase 1.5 hook)
- `.venv/bin/pytest` used consistently across all tasks (per Bodai memory `bodai-pytest-binary-cwd.md`)
- `--cov=fail_under=67.81` floor value used consistently in Task 4, Task 5 gate, and spec

**4. Spec cross-references:**
- Wave A → spec section "Wave A — Spec regen + Cleanup" — matched
- Wave B → spec section "Wave B — Force-reload guard refactor" — matched (with explicit `try/finally` rationale from Bodai memory note)
- Wave C → spec section "Wave C — xdist-order-pollution hybrid" — matched (5x serial + 5x xdist + delta computation + 3-category treatment)
- Wave D → spec section "Wave D — Coverage gate slip" — matched (TDD-style test additions + carve-out docs)
- Wave E → spec section "Wave E — Deferred test failures" — matched (3-category disposition + gate script)

**Gaps:** None identified. The plan covers all 7 deferred-minors, the 5-wave sequencing, the gate criteria, and the cross-initiative touchpoints the spec flags.

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-27-fastblocks-phase1.5-plus.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. Matches the Phase 1.5 SDD pattern.
2. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?

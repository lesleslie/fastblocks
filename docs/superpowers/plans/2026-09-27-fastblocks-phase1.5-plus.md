# Phase 1.5+ (Deferred-Minors) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clear all 7 Phase 1.5 deferred-minors so Phase 2 (build wave) lands on a fully-cleaned test foundation — green suite, coverage gate honored at 67.81%, no test-variance across runs, fresh spec failure inventory.

**Architecture:** 5 dependent waves executed in dependency order. Wave A (cleanup + spec regen) runs first because #1's output feeds Wave E and #4/#6 bundle as trivial. Wave B (force-reload guard refactor) precedes Wave C (xdist hybrid) in case the refactor incidentally resolves some pollution. Wave C is the longest (investigation + treatment) and stabilizes test counts Wave D needs for accurate coverage measurement. Wave E goes last so the fresh inventory + Wave C's pollution treatment are both in place. Each wave ships independently; one SDD task per wave.

**Tech Stack:** Python 3.14+, pytest, pytest-xdist, pytest-asyncio, FastBlocks framework internals, Oneiric resolver

**Spec:** `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-09-27-fastblocks-phase1.5-plus-design.md` (read this before executing any task)

**This is Plan 1 of 1.** Phase 2 (build wave) gets its own spec/plan/SDD cycle after Phase 1.5+ ships.

______________________________________________________________________

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

______________________________________________________________________

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

______________________________________________________________________

## Task Order (dependencies)

Tasks execute in this order. Each task is independently testable; later tasks depend on earlier ones only at the test-stability level (later tasks must keep earlier tests green).

1. **Task 1: Wave A** — Spec regen + cleanup (3 small commits, no dependencies)
1. **Task 2: Wave B** — Force-reload guard refactor (1 commit, no dependencies; runs before Wave C in case refactor incidentally resolves pollution)
1. **Task 3: Wave C** — xdist hybrid (1-2 commits, depends on Wave B settling force-reload guard; stabilizes test counts for Wave D)
1. **Task 4: Wave D** — Coverage gate slip (N commits, depends on Wave C for stable test counts)
1. **Task 5: Wave E** — Deferred test failures (1-3 commits, depends on Wave A's spec inventory + Wave C's pollution treatment)

After Task 5: **Phase 1.5+ gate** is enforced (per acceptance criteria in spec). Phase 2 plan authoring can begin.

______________________________________________________________________

### Task 1: Wave A — Spec regen + Cleanup

**Files:**

- Create: `docs/spec-failure-inventory.md` (#1)
- Modify: `fastblocks/exceptions.py:155` (#4)
- Modify: `tests/a11y/conftest.py` (#6, trailing newline)

**Interfaces:**

- Consumes: `pytest --no-cov -v --tb=line` output; current state of `fastblocks/exceptions.py:155`; current state of `tests/a11y/conftest.py`
- Produces: fresh `docs/spec-failure-inventory.md`; `(Exception,)` tuple at line 155; trailing newline at end of `tests/a11y/conftest.py`

**One SDD dispatch** handles all three commits. Implementer applies them in order; reviewer validates all three.

______________________________________________________________________

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

______________________________________________________________________

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
.venv/bin/pytest tests/test_exceptions.py::test_safe_depends_get_cached tests/test_exceptions_comprehensive.py::TestSafeDependsGet -v --no-cov
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
.venv/bin/pytest tests/test_exceptions.py::test_safe_depends_get_cached tests/test_exceptions_comprehensive.py::TestSafeDependsGet -v --no-cov
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

______________________________________________________________________

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

______________________________________________________________________

#### Task 1 done criteria

- 3 commits on `main` (one per sub-step)
- `git log --oneline 0b9d849..HEAD` shows 3 commits with the exact messages above
- `docs/spec-failure-inventory.md` exists and matches Step 1.4's verification
- `fastblocks/exceptions.py:155` shows `(Exception,)`
- `tail -c 1 tests/a11y/conftest.py | xxd` shows `0a`
- `tests/test_exceptions.py::test_safe_depends_get_cached` and `tests/test_exceptions_comprehensive.py::TestSafeDependsGet` still pass
- Reviewer verifies all three sub-steps independently

______________________________________________________________________

### Task 2: Wave B — Force-reload guard refactor

**Files:**

- Modify: `tests/adapters/templates/conftest.py` (rewrite — preserve existing `pytest_ignore_collect`; add `pytest_sessionstart` + `pytest_sessionfinish` hooks for the stub)
- Modify: `tests/adapters/templates/test_jinja2.py` (lines 14-48 area; remove module-level `sys.modules` stubs + `MockAsyncJinja2Templates` class + `MockAsyncBaseLoader` class)
- Modify: `tests/adapters/templates/test_rendering_jinja2.py` (lines 14-49 area; same removals)

**Interfaces:**

- Consumes: existing module-level `sys.modules["jinja2_async_environment"] = types.ModuleType(...)` patterns at the top of both test files; existing `pytest_ignore_collect` in `tests/adapters/templates/conftest.py` (8 lines)
- Produces: `pytest_sessionstart` hook in `tests/adapters/templates/conftest.py` that installs the complete stub (including top-level `jinja2_async_environment.AsyncRedisBytecodeCache` per `fastblocks/adapters/templates/jinja2.py:96`, plus `jinja2_async_environment.bccache.AsyncRedisBytecodeCache` alias, plus `jinja2_async_environment.loaders.AsyncBaseLoader` + `SourceType`); `pytest_sessionfinish` hook that restores the original `sys.modules` entries; module-level stubs removed from both test files

**Why `pytest_sessionstart` not a fixture:** 7 test files in `tests/adapters/templates/` do `from fastblocks.adapters.templates.jinja2 import ...` at module level (collection time), and `fastblocks/adapters/templates/jinja2.py:96` does `from jinja2_async_environment import AsyncRedisBytecodeCache` at its own module load. The stub MUST be in `sys.modules` before pytest even starts collecting test files. A `scope="module"` autouse fixture runs AFTER collection, too late. Mirrors the existing `_install_mcp_common_websocket_stub()` pattern at `tests/conftest.py:154-157` (called from `pytest_collection_modifyitems` in `tests/conftest.py:131-153`).

**Why explicit teardown not `monkeypatch`:** pytest's `monkeypatch.setattr` does not track dict insertions to `sys.modules`. Use the `pytest_sessionstart` / `pytest_sessionfinish` hook pair (standard pytest contract).

- [ ] **Step 1: Verify the `not hasattr(...)` brittle guard does NOT exist (vacuous-work check)**

Per the Phase 1.5 ledger entry on Task 5: "guard condition uses `not hasattr(...)` — brittle to future refactors". Run:

```bash
grep -rn "if not hasattr" tests/adapters/templates/ || echo "OK: no stub-guard hasattr patterns"
```

**Distinguish guards from assertions:**

- `assert not hasattr(HTMYTemplates, "_load_from_cached_bytecode")` at `test_htmy_loader_safety.py:116,119` — XSS-defense regression assertions on REMOVED methods. LEGITIMATE, must NOT be removed.
- `assert not hasattr(mock_env, "variable_start_string")` at `test_filters_comprehensive.py:538` — delimiter preservation assertion. LEGITIMATE, must NOT be removed.

Only `if not hasattr(...) # ad-hoc stub setup` patterns (defensive guards around stub installation) are in scope. Expected: `OK: no stub-guard hasattr patterns`. If 1+ hits found: STOP — real guard exists and needs removal; surface to reviewer.

- [ ] **Step 2: Replace `tests/adapters/templates/conftest.py` with the sessionstart/sessionfinish hook version**

Replace the existing 8-line conftest (which only has `pytest_ignore_collect`) with:

```python
"""Conftest for templates test configuration.

Per Phase 1.5+ Wave B: installs the jinja2_async_environment stub at
SESSION START (not fixture time), because 7 test files in this
directory do module-level imports of
fastblocks.adapters.templates.jinja2 which transitively imports
jinja2_async_environment.AsyncRedisBytecodeCache at module-load.
A scope="module" autouse fixture runs AFTER collection, too late
to satisfy the import.

Mirrors the existing _install_mcp_common_websocket_stub() pattern
at tests/conftest.py:154-157 (called from pytest_collection_modifyitems
in tests/conftest.py:131-153).

WHY pytest_sessionstart not pytest_collection_start: sessionstart
fires once at the very start of the pytest run, before any
collection. It is the safest hook to guarantee the stub is in place
before any test file is even imported.

WHY pytest_sessionfinish for teardown: standard pytest contract; fires
once at session end after all tests complete.
"""
from __future__ import annotations

import sys
import types
from pathlib import Path
from unittest.mock import MagicMock


def pytest_ignore_collect(collection_path: Path, config):
    """Ignore collection of test_components directory (preserved from prior conftest)."""
    return "test_components" in str(collection_path)


_SAVED_SYS_MODULES: dict[str, object | None] = {}


def pytest_sessionstart(session):
    """Install jinja2_async_environment stub before any test file is collected.

    Without this, the 7 test files in tests/adapters/templates/ that
    import fastblocks.adapters.templates.jinja2 at module level would
    fail with "cannot import name 'AsyncRedisBytecodeCache' from
    'jinja2_async_environment'" — see test_rendering_jinja2.py:39-44
    for the production-side rationale and test_rendering_jinja2.py:220-234
    for the regression test that enforces this stub shape.
    """
    keys = [
        "jinja2_async_environment",
        "jinja2_async_environment.loaders",
        "jinja2_async_environment.bccache",
        "starlette_async_jinja",
    ]
    for key in keys:
        _SAVED_SYS_MODULES[key] = sys.modules.get(key)

    # starlette_async_jinja stub
    mock_async_jinja2_templates_module = types.ModuleType("starlette_async_jinja")

    class _MockAsyncJinja2Templates:
        def __init__(self, *args, **kwargs) -> None:
            self.env = MagicMock()
            self.TemplateResponse = MagicMock()
            self.render_block = MagicMock()

    mock_async_jinja2_templates_module.AsyncJinja2Templates = _MockAsyncJinja2Templates
    sys.modules["starlette_async_jinja"] = mock_async_jinja2_templates_module

    # jinja2_async_environment stub (top-level)
    mock_jinja2_async_env = types.ModuleType("jinja2_async_environment")
    sys.modules["jinja2_async_environment"] = mock_jinja2_async_env

    # AsyncRedisBytecodeCache MUST be on the top-level module
    # (production code at fastblocks/adapters/templates/jinja2.py:96
    # imports from the top-level package, not from .bccache).
    # The regression test at test_rendering_jinja2.py:220-234 enforces this.
    mock_jinja2_async_env.AsyncRedisBytecodeCache = MagicMock

    # jinja2_async_environment.loaders submodule
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

    # jinja2_async_environment.bccache submodule (also reachable via
    # the bccache.AsyncRedisBytecodeCache alias; see
    # test_rendering_jinja2.py:228-232).
    mock_bccache = types.ModuleType("jinja2_async_environment.bccache")
    mock_bccache.AsyncRedisBytecodeCache = MagicMock
    mock_jinja2_async_env.bccache = mock_bccache
    sys.modules["jinja2_async_environment.bccache"] = mock_bccache


def pytest_sessionfinish(session, exitstatus):
    """Restore sys.modules state installed by pytest_sessionstart."""
    for key, saved_value in _SAVED_SYS_MODULES.items():
        if saved_value is None:
            sys.modules.pop(key, None)
        else:
            sys.modules[key] = saved_value
    _SAVED_SYS_MODULES.clear()
```

- [ ] **Step 3: Remove module-level sys.modules stubs from test files**

In `tests/adapters/templates/test_jinja2.py`:

- Delete lines 14-48 (the module-level `sys.modules["starlette_async_jinja"] = ...`, `sys.modules["jinja2_async_environment"] = ...`, `sys.modules["jinja2_async_environment.loaders"] = ...` block; plus the `MockAsyncJinja2Templates` class at lines 19-23; plus `mock_jinja2_async_env` and `mock_loaders` at lines 31-37; plus `MockAsyncBaseLoader` class at lines 40-48)
- Keep `import sys`, `import typing as t`, `import types` only if they're used elsewhere in the file

In `tests/adapters/templates/test_rendering_jinja2.py`:

- Same removals (line numbers vary — `grep -n "sys.modules\[" tests/adapters/templates/test_rendering_jinja2.py` to locate; inspect first)

- [ ] **Step 4: Run tests in serial mode**

Run:

```bash
.venv/bin/pytest tests/adapters/templates/ -p no:xdist -v --no-cov
```

Expected: PASS. The `pytest_sessionstart` hook installs the stub before any test is collected; module-level imports in test files succeed.

If FAIL: check that the conftest hook actually ran — `pytest --collect-only tests/adapters/templates/test_boot.py` should succeed without `ImportError`.

- [ ] **Step 5: Run tests in xdist mode**

Run:

```bash
.venv/bin/pytest tests/adapters/templates/ --dist=loadfile -v --no-cov
```

Expected: PASS, same test count as serial mode.

If FAIL: investigate with `pytest tests/path/to/test.py --dist=loadfile -v`.

- [ ] **Step 6: Verify test_components collection is still skipped**

Run:

```bash
.venv/bin/pytest tests/adapters/templates/ --collect-only -q 2>&1 | grep -c test_components || true
```

Expected: 0 (the `pytest_ignore_collect` for `test_components` still works; preserved from the prior conftest).

- [ ] **Step 7: Run 5 consecutive times in both modes**

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

- [ ] **Step 8: Verify module-level sys.modules stubs are gone from test files**

Run:

```bash
grep -n "sys.modules\[.jinja2_async_environment.\]\s*=" tests/adapters/templates/test_jinja2.py tests/adapters/templates/test_rendering_jinja2.py 2>/dev/null || echo "OK: module-level stubs gone"
```

Expected: `OK: module-level stubs gone`.

- [ ] **Step 9: Commit**

```bash
git add tests/adapters/templates/conftest.py tests/adapters/templates/test_jinja2.py tests/adapters/templates/test_rendering_jinja2.py
git commit -m "refactor(fastblocks): Wave B sessionstart sys.modules stub

Moves module-level sys.modules stubs from test_jinja2.py and
test_rendering_jinja2.py into a pytest_sessionstart hook in
tests/adapters/templates/conftest.py. Restoration via
pytest_sessionfinish.

Stub shape matches production requirements: top-level
jinja2_async_environment.AsyncRedisBytecodeCache (per
fastblocks/adapters/templates/jinja2.py:96), plus
jinja2_async_environment.bccache.AsyncRedisBytecodeCache alias,
plus jinja2_async_environment.loaders.AsyncBaseLoader.

WHY pytest_sessionstart not a scope=module fixture: 7 test files
in this directory do module-level imports of
fastblocks.adapters.templates.jinja2 at collection time, which
transitively imports jinja2_async_environment.AsyncRedisBytecodeCache.
A fixture runs AFTER collection, too late.

WHY explicit teardown not monkeypatch: pytest's monkeypatch.setattr
does not track dict insertions to sys.modules.

Preserves existing pytest_ignore_collect for test_components/ subdir.

Verified: 5 consecutive runs in both -p no:xdist and --dist=loadfile
modes all pass; test_components/ collection still skipped.

Note on the Phase 1.5 ledger's claimed 'not hasattr(...) brittle
check': no such guard exists in the codebase today (verified via
grep -rn 'if not hasattr' tests/adapters/templates/). Ledger entry
was inaccurate or already resolved."
```

______________________________________________________________________

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
| **Root-cause fix** | The test mutates global state without restoring it AND the fix is localized to one test file. Add `try/finally` teardown in the test or extract to a fixture with teardown. |
| `@pytest.mark.serial` | The pollution source is across files (shared module-level state, singleton registry, global cache that another test in another file mutates). The fix is harder than marking one test serial. |
| Punt to Wave E | The test is flaky in BOTH serial and xdist modes (genuine nondeterminism) AND requires >30 min to root-cause. Document with target date. |

**Default order when unsure** (fix-first, serial-only-if-needed):

1. Root-cause fix (if localized to one test file)
1. `@pytest.mark.serial` (if the pollution source is across files)
1. Punt (only if neither fix is tractable in this cycle)

If both "root-cause fix" and "serial-mark" fit, prefer the root-cause fix — over-marking serial undermines xdist's parallelism benefit (the 5-runs gate's "non-serial-marked tests pass" criterion makes the cost visible).

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

______________________________________________________________________

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
.venv/bin/pytest --cov=fastblocks --cov-report=term-missing -q 2>&1 | tail -100
```

(Note: `--no-cov` would disable coverage measurement and produce no missing-line info. Omit it.)

Expected: total coverage 67.6% (or similar). The output's bottom shows the lowest-coverage modules with missing line numbers.

- [ ] **Step 2: Identify the lowest-coverage modules with the most missing lines**

From the report, list the 5 modules with the lowest coverage and most "Missing" lines. Focus on `fastblocks/*.py` (not test files).

- [ ] **Step 3: Pick the highest-marginal-value module**

Choose ONE module from Step 2's list. Criterion: smallest number of uncovered lines that closes the largest coverage gap.

If multiple modules tie, prefer the one with the simplest API surface (easiest to test).

- [ ] **Step 4: Write the test (coverage backfill — NOT TDD, since no production code change)**

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

- [ ] **Step 5: Run the test to verify it passes (backfill: expect pass; no production code change)**

Since this is closing a coverage gap, the test should pass if the existing production code is correct. Verify:

```bash
.venv/bin/pytest tests/path/to/new_test.py -v --no-cov
```

Expected: PASS (the test exercises the previously-uncovered code path; no production code change needed).

If FAIL: the uncovered code path has a bug. STOP. Surface to the reviewer — this is a real defect, not just a coverage gap. Don't fix the production code in this task; punt to a separate cycle.

- [ ] **Step 6: Re-measure coverage**

Run:

```bash
.venv/bin/pytest --cov=fastblocks --cov-report=term-missing -q 2>&1 | tail -5
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

______________________________________________________________________

### Task 5: Wave E — Deferred test failures + Gate script

**Files:**

- Read: `docs/spec-failure-inventory.md` (from Task 1 sub-step 1A)
- Possibly Modify: multiple test files (Wave C punts + Wave E triages)
- Possibly Modify: `docs/known-claim-gaps.md`
- Create: `scripts/phase1.5-plus-gate.sh`

**Interfaces:**

- Consumes: `docs/spec-failure-inventory.md` from Task 1

- Produces: 3 originally-deferred failures each with a disposition (fix/serial/punt-with-date); `scripts/phase1.5-plus-gate.sh` audit script

- [ ] **Step 1: Verify the spec failure inventory is fresh; read it**

Run:

```bash
# Check inventory freshness (regenerated >24h ago is stale)
last_regen=$(grep -oE "Last regenerated: [0-9-]+" docs/spec-failure-inventory.md | head -1)
echo "Inventory header: $last_regen"
# If the date is >24h old or the file is missing, regenerate first
# (re-run the entire Wave A sub-step 1A flow)

cat docs/spec-failure-inventory.md
```

**Reconciliation with Phase 1.5 ledger's "Deferred-minors" section:**

Expected reconciliation:

- Tests **serial-marked in Phase 1.5 final fix wave** (e.g., `test_jinja2_environment_default_autoescape_is_true`) will NOT appear in the inventory (the inventory only counts FAILED/ERROR, not skipped). Verify these tests are still skipped via the serial hook and the rationale still applies; if not, remove the serial mark and re-evaluate.
- Tests addressed by Wave C (xdist-order-pollution) and Wave D (coverage gate slip) should be absent from the inventory.
- Remaining deferred tests (per the Phase 1.5 ledger) need fresh disposition in Wave E Steps 2-5.

The 3 originally-deferred test failures (per the Phase 1.5 ledger: at minimum `test_no_broken_release_in_dep_specs` and `test_jinja2_environment_default_autoescape_is_true`; the third is whatever the fresh inventory surfaces) — note the second is serial-marked and will not appear in the fresh inventory; handle it explicitly in Step 2 (verify the serial mark still applies; if yes, document that it was already addressed in Phase 1.5's final fix wave).

- [ ] **Step 2: Triage each originally-deferred failure**

**Default triage order when unsure (fix-first, punt-last):**

1. **Quick fix** — if the failure has an obvious cause and ≤30 min OR ≤20 lines of test change. Edit the test, run it locally, commit.
1. **Mark serial** — if the test is xdist-polluting and Wave C missed it (verify by running `pytest -p no:xdist` and confirming the test passes). Add `@pytest.mark.serial`; update `tests/conftest.py` rationale comment.
1. **Root-cause fix** — if the test has a real defect (e.g., the test asserts behavior that production code doesn't implement, OR the test is testing an aspirational claim that should be marked as such). Surface to reviewer; do not silently punt.
1. **Punt to Phase 1.5++** — only if NONE of the above fit this cycle's scope. Add entry to `docs/known-claim-gaps.md` with a target date within 6 months (the gate enforces this horizon).

**Punting is the LAST resort.** Phase 1.5's "punt items pile up" risk already manifested as the 7-item deferred-minors list this initiative exists to clear — defaulting to punt here reproduces the same anti-pattern.

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

# Sanity: venv exists (otherwise pytest fails cryptically)
[ -x .venv/bin/pytest ] \
    || { echo "FAIL: .venv/bin/pytest missing — run uv sync first"; exit 1; }
echo "OK: venv present"

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

# Wave B: module-level sys.modules stubs gone from templates test files
# (The "not hasattr(...) brittle check" described in the Phase 1.5 ledger
# does not exist in the codebase today — verified via grep -rn 'if not
# hasattr' tests/adapters/templates/ returns nothing. The legitimate
# `assert not hasattr` patterns at test_htmy_loader_safety.py:116,119 and
# test_filters_comprehensive.py:538 are XSS-defense regression assertions
# and are NOT in scope for removal.)
if grep -l "sys.modules\[.jinja2_async_environment.\]\s*=" \
        tests/adapters/templates/test_jinja2.py \
        tests/adapters/templates/test_rendering_jinja2.py 2>/dev/null; then
    echo "FAIL: module-level sys.modules stub still present in templates tests (Wave B #5)"
    exit 1
fi
echo "OK: module-level sys.modules stubs gone from templates tests"

# Wave C: serial-marks documented (rationale comment block)
grep -q "Phase 1.5+ Wave C serial-marks" tests/conftest.py \
    || { echo "FAIL: no Wave C serial-marks rationale in tests/conftest.py"; exit 1; }
echo "OK: Wave C serial-marks documented"

# Wave E: punt horizon check (target date within 6 months from today)
if [ -f docs/known-claim-gaps.md ]; then
    TODAY=$(date +%Y-%m-%d)
    SIX_MONTHS_OUT=$(date -v+6m +%Y-%m-%d 2>/dev/null || date -d "+6 months" +%Y-%m-%d)
    # Extract Target: YYYY-MM-DD rows; check each is in range
    BAD_PUNT=$(awk -F'|' '/Target: [0-9]{4}-[0-9]{2}-[0-9]{2}/ {
        match($0, /Target: ([0-9]{4}-[0-9]{2}-[0-9]{2})/, arr)
        target = arr[1]
        if (target < "'"$TODAY"'" || target > "'"$SIX_MONTHS_OUT"'") print NR": "$0
    }' docs/known-claim-gaps.md)
    if [ -n "$BAD_PUNT" ]; then
        echo "FAIL: punt target date outside 6-month window (today=$TODAY, horizon=$SIX_MONTHS_OUT):"
        echo "$BAD_PUNT"
        exit 1
    fi
    echo "OK: punt target dates within 6-month horizon"
fi

# 5 consecutive serial runs
echo "Running 5 consecutive serial pytest runs..."
for i in 1 2 3 4 5; do
    .venv/bin/pytest --no-cov -p no:xdist -q \
        || { echo "FAIL: serial run $i"; exit 1; }
done
echo "OK: 5/5 serial runs passed"

# 5 consecutive xdist runs
# Note: PASS = all non-serial-marked tests pass; serial-marked tests
# are SKIPPED under xdist per the pytest_collection_modifyitems hook at
# tests/conftest.py:131-153. Serial-marked tests are verified in the
# serial-mode regression check above.
echo "Running 5 consecutive xdist pytest runs..."
for i in 1 2 3 4 5; do
    .venv/bin/pytest --no-cov --dist=loadfile -q \
        || { echo "FAIL: xdist run $i (non-serial tests); exit 1; }
done
echo "OK: 5/5 xdist runs passed (non-serial tests; serial-marked tests skipped per hook)"

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

______________________________________________________________________

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

______________________________________________________________________

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

______________________________________________________________________

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-27-fastblocks-phase1.5-plus.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration. Matches the Phase 1.5 SDD pattern.
1. **Inline Execution** — execute tasks in this session using executing-plans, batch execution with checkpoints.

Which approach?

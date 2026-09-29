# Phase 1.5+ (Deferred-Minors) — Design Spec

**Date:** 2026-09-27
**Status:** Approved (brainstorm complete; awaiting writing-plans handoff)
**Owner:** TBD (this initiative)
**Repos affected:** `/Users/les/Projects/fastblocks`

______________________________________________________________________

## Summary

Clear all 7 Phase 1.5 deferred-minors (per the Phase 1.5 SDD ledger at
`docs/superpowers/sdd-logs/2026-09-27-phase1.5-ledger.md`) so that
Phase 2 (build wave) lands on a fully-cleaned test foundation. The
work is non-trivial but bounded: ~1 week of focused effort, organized
into 5 dependent waves.

The deferred-minors came from the Phase 1.5 ledger's "Deferred-minors
(Phase 1.5+ / Phase 2 workstream)" section. Phase 1.5 deliberately
absorbed what it could in scope and ruled the rest "deferred." This
initiative finishes that work.

**Out of scope:** Phase 2 build deliverables (B1 starter, B2 landing,
B3 HTMY demo); raising the coverage gate above 67.81%; new test
infrastructure beyond what's already in `tests/conftest.py`.

______________________________________________________________________

## Context / motivation

Phase 1.5 (audit pass + test gate tightening) shipped 9 commits on
`main` ending at `0b9d849` (the SDD ledger preservation commit). The
ledger recorded 7 deferred-minors that Phase 1.5 either couldn't fix
in scope or deliberately punted:

1. **Spec failure inventory regeneration** — recommended before
   Phase 2 so the next plan starts from real data, not stale
   inventory
1. **Coverage gate slip** — measured 67.6% vs 67.81% floor (0.21%
   gap)
1. **xdist-order-pollution flakes** — 7-21 failing tests per run
   (varying across runs; measured range per Phase 1.5 ledger); affects
   `test_htmy_*`, `test_actions/sync/*`, `test_register_candidate_strict`,
   `test_consumer_pattern_wiring`, `test_integration_contracts`
1. **Exception tuple redundancy** — `fastblocks/exceptions.py:155`
   has 5 redundant subclasses alongside `Exception`
1. **Force-reload guard brittleness** — `not hasattr(...)` check
   in template tests; refactor to `scope="module"` fixture
1. **Missing trailing newline** — `tests/a11y/conftest.py` Write-tool
   artifact
1. **3 deferred test failures from original spec failure inventory**
   that Phase 1.5 didn't address

The user explicitly chose "Address deferred-minors first, then Phase 2"
when Phase 2 was unblocked. The deferred-minors must be cleared before
Phase 2's build wave can ship on a clean foundation.

______________________________________________________________________

## Scope

### In scope

- All 7 deferred-minors (#1 through #7)
- 5 waves of work, sequenced by dependency
- New file: `docs/spec-failure-inventory.md` (Wave A, #1)
- New file: `scripts/phase1.5-plus-gate.sh` (the audit-cleared gate
  per acceptance criteria)
- Update `docs/known-claim-gaps.md` if any Wave E items are punted
  (with target dates)
- Update `docs/known-test-gaps.md` if any Wave D coverage carve-outs
  are needed (with removal plans)
- SDD ledger preserved per Phase 1.5 pattern

### Out of scope

- Phase 2 build work (separate cycle with its own spec/plan/SDD)
- Raising the coverage gate above 67.81% (this cycle honors the floor;
  does not raise it)
- New test infrastructure (only fix what's deferred; no new pytest
  plugins, hooks, or markers beyond what's already in `tests/conftest.py`)
- Refactoring beyond what's needed (no "while we're here" cleanup)
- Re-litigating Phase 1.5 rulings (the exception tuple's deliberate
  widening stays; this cycle just collapses the redundant subclass
  entries, not re-decides the policy)

______________________________________________________________________

## Architecture

Five waves, sequenced by dependency:

```
Wave A (~Day 1, 2-4 hrs)
  ├─ #1 Spec failure inventory regen     (read-only + docs)
  ├─ #4 Exception tuple redundancy      (1 line in fastblocks/exceptions.py:155)
  └─ #6 Missing trailing newline         (1 line in tests/a11y/conftest.py)

Wave B (~Day 1-2, half-day)
  └─ #5 Force-reload guard refactor      (tests/adapters/templates/{test_jinja2,test_rendering_jinja2}.py)

Wave C (~Day 2-4, 2-3 days)              BLOCKS Wave D
  └─ #3 xdist-order-pollution hybrid    (multiple test files; possibly tests/conftest.py)

Wave D (~Day 4-5, half-day to day)       DEPENDS ON Wave C
  └─ #2 Coverage gate slip              (targeted test additions; possibly known-test-gaps.md carve-outs)

Wave E (~Day 5-6, 1 day)                 DEPENDS ON Wave A
  └─ #7 Deferred test failures          (uses fresh spec-failure-inventory.md from Wave A)
```

### Why this order

- **Wave A first** because #1's output (fresh failure inventory)
  feeds Wave E; #4 + #6 bundle because they're trivial
- **Wave B before C** in case the force-reload guard fix incidentally
  resolves some xdist pollution (Wave B's scope is bounded: 1
  fixture pattern)
- **Wave C longest** because it's the largest item AND stabilizes
  test counts Wave D needs for accurate coverage measurement
- **Wave D depends on C** — coverage on flaky test counts is noise
- **Wave E last** so the failure inventory is fresh AND Wave C's
  pollution treatment is already in place (some Wave E fixes may be
  redundant with Wave C's root-cause treatments; that's fine — the
  Wave E pass is the safety net)

### Per-wave detail

#### Wave A — Spec regen + Cleanup

**#1 — Spec failure inventory regeneration**

- **Files:** create/overwrite `docs/spec-failure-inventory.md`
- **Approach:** Run `pytest --no-cov -v --tb=line 2>&1 | tee /tmp/current-failures.txt`.
  Categorize each failure: (a) currently failing on main,
  (b) xdist-only intermittent, (c) dep-pin-related (skip per existing
  `test_dep_pins.py` machinery), (d) a11y browser-bin-related (skip per
  existing `tests/a11y/conftest.py`). Format matches the original
  Phase 1.5 inventory's row schema: test path, status, category, brief
  description.
- **Done:** `docs/spec-failure-inventory.md` exists; ≥3 categories;
  matches Phase 1.5 formatting; "Last regenerated: YYYY-MM-DD against
  `main` @ <sha>" header present.
- **Risk:** snapshot rots immediately. Mitigation: re-run before each
  future plan's spec authoring.

**#4 — Exception tuple redundancy**

- **Files:** `fastblocks/exceptions.py:155`
- **Approach:** collapse `(ImportError, AttributeError, RuntimeError, TypeError, ValueError, Exception)` to `(Exception,)`. The 5
  subclasses are redundant with `Exception`. Verify
  `tests/test_exceptions.py::test_safe_depends_get_cached` and
  `tests/test_exceptions_comprehensive.py::TestSafeDependsGet`
  (the tests that prompted the original widening in Phase 1.5
  Task 4) still pass.
- **Done:** line is shorter; tests still pass; diff is 1 file / 1 line.
- **Risk:** low — tests don't depend on specific exception types.

**#6 — Missing trailing newline**

- **Files:** `tests/a11y/conftest.py`
- **Approach:** append `\n` if missing. Confirm via `tail -c 1 < file | xxd`.
- **Done:** file ends with `\n`.
- **Risk:** none.

#### Wave B — Force-reload guard refactor

**#5 — Force-reload guard refactor**

- **Files:** `tests/adapters/templates/conftest.py` (rewrite — preserve
  existing `pytest_ignore_collect`; add `pytest_sessionstart` +
  `pytest_sessionfinish` hooks for the stub); `tests/adapters/templates/test_jinja2.py`
  (lines 1-60 area; remove module-level `sys.modules` stubs);
  `tests/adapters/templates/test_rendering_jinja2.py` (lines 1-60 area;
  remove module-level `sys.modules` stubs)
- **Approach:** install the `sys.modules["jinja2_async_environment"] = ...`
  stub at **session start** (via `pytest_sessionstart` in
  `tests/adapters/templates/conftest.py`) — NOT in a fixture. Reason:
  7 test files in `tests/adapters/templates/` do
  `from fastblocks.adapters.templates.jinja2 import ...` at module
  level (collection time), and `fastblocks/adapters/templates/jinja2.py:96`
  does `from jinja2_async_environment import AsyncRedisBytecodeCache`
  at its own module load. The stub MUST be in `sys.modules` before
  pytest even starts collecting test files. A `scope="module"` autouse
  fixture runs AFTER collection, too late. Mirrors the existing
  `_install_mcp_common_websocket_stub()` pattern at
  `tests/conftest.py:154-157`. Teardown via `pytest_sessionfinish` hook
  restores the original `sys.modules` entries. Explicit `try/finally`
  not needed — `pytest_sessionstart`/`pytest_sessionfinish` pair is
  the standard pytest hook contract.
- **Stub shape (MUST match what production code expects):**
  - `starlette_async_jinja.AsyncJinja2Templates` (synchronous mock class)
  - `jinja2_async_environment.AsyncRedisBytecodeCache` (top-level —
    production imports from here at `jinja2.py:96`; regression test at
    `test_rendering_jinja2.py:220-234` enforces this)
  - `jinja2_async_environment.loaders.AsyncBaseLoader` + `SourceType`
  - `jinja2_async_environment.bccache.AsyncRedisBytecodeCache`
    (also reachable via the `bccache` submodule alias)
- **Note on the `not hasattr(...)` brittle check from the Phase 1.5
  ledger:** per implementation review (2026-09-27), no such guard
  currently exists in `tests/adapters/templates/`. The Phase 1.5 ledger
  entry on Task 5 described the guard as a fragility concern, but
  either it was already resolved in Phase 1.5 itself or the ledger
  was inaccurate. Wave B's `not hasattr` removal step is therefore
  a no-op verification: grep the tree, confirm no such guard exists,
  document in the report.
- **Done:** module-level `sys.modules` stubs removed from
  `test_jinja2.py` and `test_rendering_jinja2.py`; conftest installs
  the stub at session start; tests pass 5 consecutive runs in both
  `--dist=loadfile` and `-p no:xdist` modes; existing
  `pytest_ignore_collect` for `test_components/` is preserved.
- **Risk:** pytest_sessionstart is run once per session; if any test
  mutates `sys.modules["jinja2_async_environment"]` after session
  start, the teardown in `pytest_sessionfinish` restores to the
  pre-session value. Acceptable trade-off; pytest's contract is that
  test code shouldn't mutate module-level singletons outside fixtures.

#### Wave C — xdist-order-pollution hybrid

**#3 — xdist-order-pollution hybrid (the load-bearing decision)**

- **Files:** various test files; potentially `tests/conftest.py` for
  additional hooks; new `@pytest.mark.serial` markers on offending
  tests
- **Approach:**
  1. Run `pytest -p no:xdist 5x` — record baseline (which tests
     consistently pass without xdist)
  1. Run `pytest --dist=loadfile 5x` — record which tests fail
     consistently across runs
  1. Diff the two lists → the **delta** is the xdist-pollution set
  1. For each delta test:
     - **Genuine pollution** (order-dependent): `@pytest.mark.serial`
       (existing Phase 1.5 hook at `tests/conftest.py:131-153` handles
       it)
     - **Test-design defect** (e.g., shared mutable state):
       root-cause fix in the test file itself
     - **Pre-existing bug** (flaky regardless of xdist): punt to
       Wave E
  1. Commit 1: serial-marks (1 file per test, max)
  1. Commit 2 (if needed): root-cause fix(es)
- **Done:** 5 consecutive `pytest --dist=loadfile` runs all green;
  zero failures varying per run; serial-marks documented in
  `tests/conftest.py` rationale comment (test name + brief rationale
  per mark).
- **Risk:** some tests are genuinely nondeterministic, not pollution.
  The "punt to Wave E" branch handles them explicitly (xfail or skip
  with target date).

#### Wave D — Coverage gate slip

**#2 — Coverage gate slip (0.21%)**

- **Files:** targeted test additions; possibly carve-outs in
  `docs/known-test-gaps.md`
- **Approach:**
  1. After Wave C settles test counts: `pytest --cov=fastblocks --cov-report=term-missing`
  1. Identify uncovered lines (focus on `fastblocks/*.py`, not tests)
  1. For each uncovered block, write a test that exercises it (TDD:
     failing first)
  1. Re-measure; iterate until `--cov-fail-under=67.81` passes
  1. If uncovered code is genuinely untestable (e.g.,
     platform-specific), document carve-out in `docs/known-test-gaps.md`
     with `{file:line, reason, removal_plan}`
- **Done:** 5 consecutive `--cov=fail_under=67.81` runs all pass.
  `.coverage-ratchet.json` `current_minimum` unchanged at 67.81.
- **Risk:** uncovered code may be untestable. Carve-out docs
  prevent this from becoming a hidden bypass.

#### Wave E — Deferred test failures

**#7 — Deferred test failures from original spec failure inventory**

- **Files:** depends on Wave A's `docs/spec-failure-inventory.md` output
- **Approach:**
  1. Read the fresh spec failure inventory
  1. For each test still failing that's NOT covered by Wave C (xdist)
     or Wave D (coverage):
     - **Quick fix** (≤30 min): apply, commit
     - **Mark serial** (genuine pollution that Wave C missed):
       `@pytest.mark.serial`
     - **Punt to Phase 1.5++** (genuine bug, too big for this cycle):
       document in `docs/known-claim-gaps.md` with target date
  1. Commit 1: fixes (if any)
  1. Commit 2: serial-marks (if any)
  1. Commit 3: `docs/known-claim-gaps.md` updates (if any)
- **Done:** every originally-deferred failure has a documented
  disposition (fix / serial-mark / punt-with-target-date). 5
  consecutive `pytest` runs all pass.
- **Risk:** punted items pile up. Mitigation: each punted entry
  requires a target date (no "TBD").

______________________________________________________________________

## Acceptance Criteria (audit-cleared gate)

Phase 1.5+ ships when ALL of the following hold for 5 consecutive
runs:

```bash
# From /Users/les/Projects/fastblocks — run the audit-cleared gate
bash scripts/phase1.5-plus-gate.sh
```

The gate internally runs:

- 5 consecutive `.venv/bin/pytest --no-cov -p no:xdist -q` (serial baseline)
- 5 consecutive `.venv/bin/pytest --no-cov --dist=loadfile -q` (xdist baseline; non-serial-marked tests pass; serial-marked tests skipped per hook)
- 5 consecutive `.venv/bin/pytest --cov=fail_under=67.81 -q` (coverage gate)
- 4 sanity checks: `docs/spec-failure-inventory.md` exists; `tests/a11y/conftest.py` ends with `\n`; `fastblocks/exceptions.py` has `except (Exception,):`; no module-level `sys.modules` stubs in `tests/adapters/templates/test_jinja2.py` or `test_rendering_jinja2.py`; punt target dates in `docs/known-claim-gaps.md` within 6-month horizon.

The 5-consecutive-runs gate catches any pollution regression from
Wave C's serial-marks, Wave B's fixture change, or Wave D's coverage
work. If any single run fails, Phase 1.5+ is not done.

### Per-wave success criteria

| Wave | Pass criterion |
|---|---|
| A | `docs/spec-failure-inventory.md` exists; `tests/test_exceptions.py::test_safe_depends_get_cached` and `tests/test_exceptions_comprehensive.py::TestSafeDependsGet` pass; `tail -c 1 tests/a11y/conftest.py` returns `\n` |
| B | 5 consecutive pytest runs in both serial + xdist pass for `tests/adapters/templates/`; `hasattr` check gone |
| C | 5 consecutive `pytest --dist=loadfile` runs all green; serial-marks documented in conftest rationale |
| D | 5 consecutive `pytest --cov=fail_under=67.81` runs all pass; carve-outs in `known-test-gaps.md` if any |
| E | Every originally-deferred failure has a disposition; `docs/known-claim-gaps.md` lists punted items with target dates |

______________________________________________________________________

## Integration Contract (per `wire-up-contract.md`)

| Field | Value |
|---|---|
| **Triggered from** | Completion of Phase 1.5 (commit `0b9d849` ledger preservation) + user's "address deferred-minors first" directive. Direct commits to `main` per Bodai pre-1.0 policy. |
| **Returns to / updates** | `fastblocks/` repo. New files: `docs/spec-failure-inventory.md`, `scripts/phase1.5-plus-gate.sh`. Updated files: `fastblocks/exceptions.py`, `tests/a11y/conftest.py`, `tests/adapters/templates/{test_jinja2,test_rendering_jinja2}.py`, possibly `tests/conftest.py`, possibly `docs/known-claim-gaps.md`, possibly `docs/known-test-gaps.md`. |
| **Demonstrable by** | `bash scripts/phase1.5-plus-gate.sh` exits 0 with: 5/5 green pytest runs (serial + xdist) AND 5/5 `--cov=fail_under=67.81` passes AND `docs/spec-failure-inventory.md` exists AND every originally-deferred failure has a disposition. |
| **Rollback signal** | Each wave is 1-2 commits; revert the wave's commits if a regression is discovered. Pre-wave state (`0b9d849`) is the ultimate fallback. |
| **Observability added** | `docs/spec-failure-inventory.md` includes "Last regenerated" header; coverage report shows missing lines; `tests/conftest.py` serial-mark rationale comment is the public log of every quarantine; SDD ledger preserved per Phase 1.5 pattern (`docs/superpowers/sdd-logs/2026-09-27-phase1.5-plus-ledger.md`). |

______________________________________________________________________

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| xdist "fix" introduces new pollution (the serial-mark / root-cause fix changes test order in a way that breaks an unrelated test) | Medium | Medium | Each Wave C commit runs `pytest` once in isolation (no xdist) + once with `--dist=loadfile` to catch both modes |
| Coverage gap proves uncloseable (the 0.21% slip is real, not noise) | Low | Medium | Carve-out documentation with removal plan; do not lower the floor |
| Nondeterministic tests in Wave C pollute the pollution set (genuine randomness, not order-dependence) | Medium | Low | Punt to Wave E with `xfail` or explicit skip; not serial-mark |
| Spec inventory regen takes longer than expected | Low | Low | Read-only + categorization is mechanical; 1-2 hours max |
| Punted items pile up (if Wave E has >3 punts, Phase 1.5++ becomes a real cycle) | Medium | Medium | Each punt requires target date; if >3 punts, evaluate whether to extend Phase 1.5+ scope |
| Wave B's `monkeypatch` can't undo `sys.modules` (pytest's `monkeypatch.setattr` does not track dict insertions to `sys.modules`) | High | Low | Use `pytest_sessionstart` + `pytest_sessionfinish` hook pair (standard pytest contract) for stub install + teardown |

______________________________________________________________________

## Cross-initiative touchpoints (flagged, not in scope)

- **Phase 2 build wave** — depends on Phase 1.5+ completing; cannot
  start until all 7 deferred-minors are cleared
- **Mahavishnu observability** — `docs/spec-failure-inventory.md`
  is a good Akosha hook candidate; not blocking
- **SplashStand consumer SaaS** — uses the new starter once Phase 2
  ships; not affected by Phase 1.5+

______________________________________________________________________

## Glossary

- **Phase 1.5+** — this initiative. The "plus" suffix denotes the
  post-Phase-1.5 follow-up cycle that clears the 7 deferred-minors.
- **xdist** — pytest-xdist, the parallel test runner. xdist-order-
  pollution is order-dependent test failure caused by tests sharing
  mutable state when xdist reorders execution.
- **serial** — `@pytest.mark.serial`, a custom marker registered
  in `tests/conftest.py`. The Phase 1.5 final fix wave added a
  `pytest_collection_modifyitems` hook that skips serial-marked
  tests when xdist is active.
- **Deferred-minors** — Phase 1.5 ledger's "Deferred-minors (Phase
  1.5+ / Phase 2 workstream)" section, 7 items
- **Audit-cleared gate** — the Phase 1 → Phase 2 transition criteria;
  Phase 1.5+ must pass a similar gate before Phase 2 can begin

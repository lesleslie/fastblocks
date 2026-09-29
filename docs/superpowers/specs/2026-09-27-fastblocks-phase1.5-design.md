# Phase 1.5 — Test Gate Tightening & C3 Framework Fix Design (v2)

> **For agentic workers:** Phase 1.5 is the bridge between the audit pass
> (Phase 1) and the build wave (Phase 2). It converts pre-existing test
> failures into a known-green baseline AND investigates the one framework
> surface that the audit surfaced as a blocker for Phase 2.

**Goal:** Make `uv run pytest tests/ --no-cov -q` exit 0 with `--cov-fail-under=67.81` enforced, AND investigate+fix (if needed) the `register_fastblocks_ui_functions` wiring so Phase 2 lands on a clean baseline.

**Architecture:** Two streams, ordered — Tests first (then C3). Tests stream ratchets the gate criteria that the audit pass established; C3 stream investigates the wiring surface flagged by the audit (and only fixes if investigation reveals an actual bug, per multi-agent review).

**Tech Stack:** Same as audit pass (uv, pytest, fastblocks-ui, oneiric, fastblocks adapters).

**Spec source:** [2026-09-27-fastblocks-dogfood-readiness-design.md](2026-09-27-fastblocks-dogfood-readiness-design.md) (Phase 1 spec; Phase 1.5 is its follow-up)

**Plan source:** TBD (writing-plans skill produces the plan after this spec is approved)

**Review history (v2):** 4-agent multi-lens review on v1 surfaced 4 BLOCKERs + 4 IMPORTANTs + 2 single-lens findings. All 14 issues addressed in this revision. Key revisions: corrected dep pin version lines (httpx2 is 2.x, oneiric is 0.25.x), rewrote C3 fix as investigation-first (wiring already exists at `jinja2.py:978`), expanded coverage ratchet fix to 4 edit sites, replaced `@pytest.mark.skip` with `pytest.importorskip` for a11y, corrected `FASTBLOCKS_TOOL_PROFILE` env var name.

## Global Constraints

These apply to every task in Phase 1.5:

- **Git workflow:** Bodai pre-1.0 merge policy (direct to `main`); commit per logical fix; descriptive commit message per fix area.
- **Coverage ratchet target:** `--cov-fail-under=67.81` (current actual post-audit-pass; ~68% when rounded by term:skip-covered). Floor cannot drop below this without an explicit ADR; do not silently lower it.
- **Scope guard:** Tractable fixes only (Q1=1). The 29 a11y axe-core parametrize errors are OUT OF SCOPE — they require `@axe-core/playwright` install + browser deps; deferred to Phase 1.5+ or Phase 2.
- **No backwards compat** (Bodai pre-1.0): fix forward, don't add deprecation shims.
- **Test-first discipline:** When fixing a failing test, prefer test rewrite over test skip; if you must skip, document the reason in the test docstring.
- **A11y axe-core tests:** keep them in tree (don't delete) — documented as known-broken in `docs/known-claim-gaps.md` so the audit pass claim remains honest.
- **Investigation before fix (TDD discipline):** Per pytest reviewer + architecture reviewer — for failures where the root cause is ambiguous (Fix 3 tool profile, Fix 4 exceptions, Fix 5 collection errors, Fix 8 C3), the spec REQUIRES an investigation step that reproduces the failure before any code change. "Investigate" is the action; "fix" only follows if investigation confirms the diagnosis.

## Failure Inventory (from `uv run pytest tests/ --no-cov -q`)

**Total:** 12 failed + 34 errors = **46 non-passing** (per pytest header). Table sums to 43; 3-test gap explained by pytest collection filter that deselects 3 of the 32 POSTURES components before parametrization runs (per multi-agent review finding — components requiring browser deps). Reconcile gap during Fix 7 implementation.

| # | Test | Category | Likely side | Disposition |
|---|---|---|---|---|
| 1 | `tests/test_exceptions_comprehensive.py::TestSafeDependsGet::test_resolution_error_returns_default` | Exceptions | UNKNOWN | Investigate → fix |
| 2 | `tests/test_exceptions_comprehensive.py::TestSafeDependsGet::test_resolution_error_no_default` | Exceptions | UNKNOWN | Investigate → fix |
| 3 | `tests/test_dep_pins.py::test_no_loose_pins_on_critical_deps` | D8a | TEST | Fix (pin tighten in spec) |
| 4 | `tests/test_dep_pins.py::test_no_broken_release_in_dep_specs` | D8a | TEST | Fix (pin tighten in spec) |
| 5 | `tests/unit/test_tool_profile.py::test_full_profile_registers_eight_tools` | Tool profile | UNKNOWN | Investigate → fix (5 failing of 14 in this file) |
| 6 | `tests/unit/test_tool_profile.py::test_standard_profile_registers_eight_tools` | Tool profile | UNKNOWN | Investigate → fix |
| 7 | `tests/unit/test_tool_profile.py::test_minimal_profile_registers_only_discover_tools` | Tool profile | UNKNOWN | Investigate → fix |
| 8 | `tests/unit/test_tool_profile.py::test_mandatory_tools_subset_holds_at_all_profiles` | Tool profile | UNKNOWN | Investigate → fix |
| 9 | `tests/unit/test_tool_profile.py::test_unset_env_var_falls_back_to_full` | Tool profile | UNKNOWN | Investigate → fix |
| 10 | `tests/adapters/templates/test_boot.py::test_templates_adapter_env_has_autoescape_on` | D3 xdist flake | TEST | Investigate (`--dist=loadfile` bisect; `@pytest.mark.serial` if xdist-only) |
| 11 | `tests/security/test_autoescape_regression.py::test_jinja2_environment_default_autoescape_is_true` | D6 (autoescape) | UNKNOWN | Investigate (passes in isolation per Task 6; possible xdist race) |
| 12 | `tests/pyproject/test_dependency_groups.py::test_mcp_common_pin_below_0_4_for_tool_pydantic_workaround` | D8 | TEST | Fix (mcp-common pin edit + test substring update + observability group) |
| 13-41 | `tests/a11y/test_components_a11y.py::test_component_passes_axe_core[*]` (29 variants) | A11y env | IMPL | **OUT OF SCOPE** (Q1=1) |
| 42 | `tests/adapters/routes/test_routes.py` (collection error) | Import | UNKNOWN | Investigate (`--collect-only`; root cause likely in test's collection-time mocking at lines 65–86) |
| 43 | `tests/perf/test_async_rendering.py` (collection error) | Import | UNKNOWN | Investigate (`--collect-only`; likely missing transitive dep `jinja2_async_environment`) |

**Tool profile env var name (Fix 3):** Tests gate on `FASTBLOCKS_TOOL_PROFILE` (NOT `MAHAVISHNU_TOOL_PROFILE` — that's the Mahavishnu project's env var; this is fastblocks). v1 spec had this wrong.

## Stream A: Test Fixes (ordered; do C3 after all green)

### Fix 1: D8a — Tighten dep pins (CORRECTED VERSION LINE)

**Files:** `pyproject.toml` (lines 47, 51, 53, 106), `uv.lock` (regenerate), `tests/test_dep_pins.py` (lines 141, 146 stale fixtures), `tests/pyproject/test_dependency_groups.py` (line 33 substring)

**Change (corrected per dependency-manager + framework reviewers):**

| Package | Current | New | Why |
|---|---|---|---|
| `httpx2` (line 47) | `>=0.28.1` | `>=2.13.1,<3` | httpx2 is on the **2.x line**, currently 2.13.1. v1 spec's `<0.30` would have rejected all real versions. |
| `mcp-common` (line 51) | `>=0.30.0` | `>=0.30.1,<0.31` | Skips broken 0.30.0 release per `tests/dep_broken_releases.yaml` (fix_release: "0.30.1"). |
| `mcp-common` (line 106, observability group) | `>=0.30.0` | `>=0.30.1,<0.31` | Same as line 51 — duplicate occurrence must also be tightened. |
| `oneiric` (line 53) | `>=0.20` | `>=0.25,<0.26` | oneiric is currently at **0.25.0**. v1 spec's `<0.21` would have downgraded 5 minor versions. |

**Test fixture refresh (in same commit, per dependency-manager reviewer):**

- `tests/test_dep_pins.py:141` — `("httpx2~=0.28", False)` → `("httpx2~=2.13", False)` (stale fixture encodes wrong version line)
- `tests/test_dep_pins.py:146` — `("oneiric>=0.20,<0.21", False)` → `("oneiric>=0.25,<0.26", False)` (stale fixture)

**Test #12 (mcp-common substring) reconciliation:**

- Test asserts: `"<0.4" in entry`
- New pin: `mcp-common>=0.30.1,<0.31` — the substring `<0.31` does NOT contain `<0.4`, so test would still fail.
- **Resolution:** Update `tests/pyproject/test_dependency_groups.py:33` substring check from `"<0.4"` to `"<0.31"` to match the actual pin policy intent. Document the change in commit message.

**Why `httpx2<3` (not `<2.14`):** httpx2 has no 3.x announced. The 2.x line is the production target. Capping at `<3` allows all 2.x patches while blocking the next major bump (which would force a test re-run).

**Verification (per dep reviewer):**

```bash
uv lock                              # regenerate lockfile with new pins
uv lock --check                      # gate that pin changes are consistent
uv run pytest tests/test_dep_pins.py tests/pyproject/test_dependency_groups.py -v
# Confirm lockfile resolves to: httpx2==2.13.1, mcp-common==0.30.2 (NOT 0.30.0), oneiric==0.25.0
```

### Fix 2: D3 — xdist flake (autoescape race) — INVESTIGATE FIRST

**Files:**

- `tests/adapters/templates/test_boot.py` (line 54: `test_templates_adapter_env_has_autoescape_on`)
- `tests/security/test_autoescape_regression.py` (line 22: `test_jinja2_environment_default_autoescape_is_true`)

**Investigation steps (per pytest reviewer — verify before marking):**

1. `cd /Users/les/Projects/fastblocks && uv run pytest tests/adapters/templates/test_boot.py -v` (serial) — confirm passes
1. `cd /Users/les/Projects/fastblocks && uv run pytest tests/adapters/templates/test_boot.py -n auto -v` (xdist parallel) — confirm fails
1. `cd /Users/les/Projects/fastblocks && uv run pytest tests/adapters/templates/test_boot.py -p no:xdist -v` (no xdist at all) — confirm passes
1. If serial+no-xdist pass AND xdist fails → `@pytest.mark.serial` is correct remedy. If all three fail, the assertion is wrong and `serial` masks a real bug — investigate the `Templates.env.autoescape` mutation hypothesis.

**Why `@pytest.mark.serial` may not be enough (per pytest reviewer):** The marker is NOT registered in `pyproject.toml [tool.pytest].markers` (lines 226–234 only list `unit`, `performance`, `integration`, `websocket`, `a11y`, `property`, `slow`). pytest-xdist auto-recognizes it, but defensive practice is to add it:

- Add `"serial: mark test as serial (run without xdist parallelization)"` to `[tool.pytest.ini_options].markers` in `pyproject.toml`.

**Apply (after investigation confirms xdist-only flake):**

```python
@pytest.mark.serial  # xdist flake: env mutation race; see Phase 1.5 spec Fix 2
def test_templates_adapter_env_has_autoescape_on():
    ...
```

**Tests affected:** #10, possibly #11

### Fix 3: Tool profile (5 tests) — INVESTIGATE FIRST

**Files:** `tests/unit/test_tool_profile.py` (5 failing of 14 total), `fastblocks/...` (impl if env handling is wrong)

**Investigation step (per pytest reviewer — verify before fixing):**

1. Read `fastblocks/.../_apply_tool_profile` (or wherever profile handling lives) — confirm profile definitions
1. Read `tests/unit/test_tool_profile.py` — confirm what tests assert (env var is `FASTBLOCKS_TOOL_PROFILE`, NOT `MAHAVISHNU_TOOL_PROFILE`)
1. Reconcile: either fix the profile implementation OR update the tests to match new ground truth (with a comment explaining the ground truth change)

**Verification (after fix):**

```bash
cd /Users/les/Projects/fastblocks
FASTBLOCKS_TOOL_PROFILE=full uv run pytest tests/unit/test_tool_profile.py -v
FASTBLOCKS_TOOL_PROFILE=standard uv run pytest tests/unit/test_tool_profile.py -v
FASTBLOCKS_TOOL_PROFILE=minimal uv run pytest tests/unit/test_tool_profile.py -v
unset FASTBLOCKS_TOOL_PROFILE && uv run pytest tests/unit/test_tool_profile.py -v
```

**Tests affected:** #5–#9

### Fix 4: Exceptions (TestSafeDependsGet, 2 tests) — INVESTIGATE FIRST

**Files:** `tests/test_exceptions_comprehensive.py`, `fastblocks/.../safe_depends_get.py` (or wherever `safe_depends_get` function lives)

**Investigation step:**

1. Locate `safe_depends_get` definition (snake_case function tested by `class TestSafeDependsGet`)
1. Read the 2 failing test bodies (lines 481–527) — understand expected behavior
1. Decide: fix implementation to match tests (preferred) OR fix tests to match new ground truth (if intentional behavior change)

**Tests affected:** #1, #2

**Verification:**

```bash
uv run pytest tests/test_exceptions_comprehensive.py::TestSafeDependsGet -v
```

### Fix 5: Collection errors — INVESTIGATE FIRST (ROOT CAUSE NOT WHAT V1 SPEC SAID)

**Files:** `tests/adapters/routes/test_routes.py`, `tests/perf/test_async_rendering.py`

**Per pytest + architecture reviewers, v1's hypothesis (add `__init__.py`, rename files, change `import_mode`) was WRONG:**

- `tests/adapters/templates/` has NO `__init__.py` and works fine — adding `__init__.py` elsewhere is not the project pattern
- `import_mode=prepend` is pytest's DEFAULT, not explicitly configured in `pyproject.toml`

**Actual root cause hypotheses (per pytest reviewer):**

- `tests/adapters/routes/test_routes.py:65-86` does collection-time `sys.modules` mocking of `acb.*` modules then imports `from acb.config import Config` at lines 79-80. This mock-then-import dance can fail under modern Python import semantics (mock-then-import race).
- `tests/perf/test_async_rendering.py:44` imports `from jinja2_async_environment import AsyncEnvironment` — likely a missing transitive dep of `starlette-async-jinja`.

**Investigation steps (mandatory before any code change):**

```bash
cd /Users/les/Projects/fastblocks
uv run pytest --collect-only tests/adapters/routes/test_routes.py -v 2>&1 | tail -20
uv run pytest --collect-only tests/perf/test_async_rendering.py -v 2>&1 | tail -20
python -c "import jinja2_async_environment"  # confirm if dep is missing
```

**Then choose fix based on actual error:**

- If `ImportError: jinja2_async_environment` → add dep to `pyproject.toml` [project.dependencies]
- If `AttributeError` from acb mock → move collection-time mocking into a conftest fixture scoped at session/module level
- If `ModuleNotFoundError` for axe_playwright_python (a11y) → already addressed by Fix 7

**DO NOT add `__init__.py` to `tests/adapters/routes/` or `tests/perf/`** — diverges from project's curated pattern.

**Tests affected:** #42, #43

### Fix 6: D1b — Coverage gate enforcement (4 EDIT SITES)

**Files (corrected per pytest + architecture + framework reviewers — was 2 sites, is actually 4):**

| File | Field | Current | New |
|---|---|---|---|
| `pyproject.toml` line 240 | `addopts[--cov-fail-under]` | `62` | `67.81` |
| `pyproject.toml` line 268 | `[tool.coverage.report].fail_under` | `62` | `67.81` |
| `.coverage-ratchet.json` line 3 | `current_minimum` | `49.13%` | `67.81%` |
| `.github/workflows/quality.yml` line 194 | pytest arg | `--no-cov` | remove `--no-cov` so addopts' `--cov-fail-under=67.81` applies (per pytest SUGGESTION 1) |

**Why all 4 sites:** Local `uv run pytest tests/` reads from addopts; CI reads from workflow arg; ratchet JSON is the single source of truth for the floor; coverage.report is for standalone `coverage report` calls. If any one is stale, the ratchet is silently weakened.

**Verification:**

```bash
cd /Users/les/Projects/fastblocks
uv run pytest --cov=fastblocks --cov-report=term  # exits 0 with --cov-fail-under=67.81
cat .coverage-ratchet.json                          # shows current_minimum: 67.81%
grep -n "cov-fail-under\|fail_under" pyproject.toml .github/workflows/quality.yml
```

### Fix 7: A11y axe-core — `pytest.importorskip` in conftest (CORRECTED FROM V1)

**Files:** `tests/a11y/conftest.py` (NEW), `docs/known-claim-gaps.md` (UPDATE)

**Per pytest reviewer, v1's `@pytest.mark.skip` was wrong:**

- "Skip" leaks a static "known broken" message into the test count and obscures the real failure mode (missing runtime dep)
- The project pattern is dependency-driven skip via `pytest.importorskip` in conftest (matches `tests/adapters/templates/conftest.py`, `tests/security/conftest.py`, `tests/observability/conftest.py`)
- Tests are ALREADY in `tests/a11y/`; "move to `tests/a11y/`" was moot

**Create `tests/a11y/conftest.py`:**

```python
"""A11y test dependency gating.

Per Phase 1.5 spec Fix 7: skip axe-core tests when runtime deps missing.
The framework decides the skip based on import availability; this
matches the project pattern (see tests/security/conftest.py etc.).

Deferred to Phase 1.5+ or Phase 2: actual axe-core + browser deps install.
"""
from __future__ import annotations

import pytest


pytest.importorskip("axe_playwright_python", reason="axe-core integration deps missing")
pytest.importorskip("playwright.async_api", reason="Playwright async API missing")
```

**Update `docs/known-claim-gaps.md` with new row:**

```
| A11y axe-core tests (29) | tests/a11y/test_components_a11y.py | Requires @axe-core/playwright + browser binary | Phase 1.5+ environment work |
```

## Stream B: C3 Framework Fix — INVESTIGATION-FIRST (CORRECTED FROM V1)

### Fix 8: C3 — Investigate `register_fastblocks_ui_functions` wiring, then fix if needed

**Status:** v1 spec proposed adding wiring at `FastBlocksApp.init()` — but **3 reviewers independently flagged this is wrong**. The wiring already exists at `fastblocks/adapters/templates/jinja2.py:974-978`:

```python
with suppress(Exception):
    from fastblocks.core.style_registry import register_style_functions
    style_name = getattr(getattr(self.config, "app", None), "style", None)
    register_style_functions(templates.env, style_name)
```

`register_style_functions` (defined at `fastblocks/core/style_registry.py:42`) dynamically resolves via `getattr(module, f"register_{style_name}_functions", None)` → `register_fastblocks_ui_functions` for `style="fastblocks_ui"` (defined at `fastblocks/adapters/style/fastblocks_ui.py:140`).

**Three viable hypotheses for what C3 actually is:**

1. **C3 = bug is the `with suppress(Exception):` wrapper** — silently masks failures when `fastblocks-ui` deps missing or env is wrong type. Fix: un-suppress (or un-suppress one level) + add regression test asserting `ui_button`/`ui_card`/`ui_alert`/etc. appear in `env.globals` after `Templates.init()`.
1. **C3 = wiring works but undocumented** — fix is just the smoke test, no production code change.
1. **C3 = different bug** — needs concrete repro (e.g., "landing page `/` renders `<UndefinedError>` for `ui_button`" → run `uv run python -c "..."` showing failure → file location of broken call).

**Investigation steps (mandatory):**

```bash
cd /Users/les/Projects/fastblocks
# Confirm wiring path exists
grep -rn "register_fastblocks_ui_functions\|register_style_functions" fastblocks/
# Confirm what happens when style="fastblocks_ui" is configured
uv run python -c "
from fastblocks.adapters.templates.jinja2 import Templates
templates = Templates()
templates.init()
print('globals:', list(templates.env.globals.keys())[:20])
print('ui_button in globals:', 'ui_button' in templates.env.globals)
"
# Reproduce the landing page symptom (if available)
# uv run python -c "from fastblocks.adapters.app.default import FastBlocksApp; app = FastBlocksApp(); ..."
```

**Then choose fix:**

- If hypothesis 1: un-suppress `with suppress(Exception):` in `jinja2.py:974-978`, add regression test
- If hypothesis 2: just add the regression test
- If hypothesis 3: file location of the actual broken call

**Integration Contract (per Mahavishnu `wire-up-contract.md` policy):**

- **Triggered from:** `Templates.init()` (called during app lifespan or templates adapter initialization)
- **Returns to / updates:** `templates.env.globals` populated with `ui_button`, `ui_card`, `ui_field`, `ui_alert`, `ui_container`, plus filter `fastblocks_ui_class` (per `fastblocks/adapters/style/fastblocks_ui.py`)
- **Demonstrable by:** `tests/integration/test_fastblocks_ui_wiring.py::test_ui_helpers_registered_on_env` asserting `assert "ui_button" in templates.env.globals` and `assert "ui_card" in templates.env.globals` after `Templates().init()`
- **Rollback signal:** page-render failure in `examples/landing/` for `ui_button` / `ui_card` (deferred to Phase 2 verification)
- **Observability added:** structured log line at the wiring call site (`jinja2.py:978`) naming the style + count of globals/filters registered

## Execution Order

```
Fix 1 (D8a pins — 4 sites + test fixtures) ──┐
Fix 2 (D3 xdist — investigate first)         ──┤
Fix 3 (tool profile — investigate first)      ──┤
Fix 4 (exceptions — investigate first)        ──┼─→ Fix 6 (coverage gate — 4 sites) → Fix 7 (a11y importorskip)
Fix 5 (collection errors — investigate first) ──┘                                          │
                                                                                            │
                                              (all 12 + 2 errors green + 29 a11y skipped)  │
                                                                                            ▼
                                                                              Fix 8 (C3 — investigate first)
                                                                                            │
                                                                                            ▼
                                                                          Phase 2 unblocked
```

Fixes 1-5 can be parallelized (independent files). Fix 6 must come after all of them (coverage ratchet needs green tests). Fix 7 is independent of test fixes (conftest change only). Fix 8 (C3) is the last step — must come after tests are green to avoid masking failures.

## Acceptance Criteria

When ALL of the following are true, Phase 1.5 is complete:

1. `uv run pytest tests/ --no-cov -q` exits 0 (with 51 skipped + 0 failed + 0 errors; the 29 a11y are now silently skipped via `pytest.importorskip`)
1. `uv run pytest --cov=fastblocks` exits 0 (uses addopts `--cov-fail-under=67.81`)
1. `uv lock --check` exits 0 (dep pins tightened, lockfile consistent; resolves to httpx2==2.13.1, mcp-common==0.30.2, oneiric==0.25.0)
1. C3 root cause identified; fix applied if needed; smoke test exists at `tests/integration/test_fastblocks_ui_wiring.py`
1. **All 4 coverage edit sites** read `67.81`: `pyproject.toml [tool.pytest].addopts`, `pyproject.toml [tool.coverage.report].fail_under`, `.coverage-ratchet.json`, `.github/workflows/quality.yml`
1. `docs/known-claim-gaps.md` documents the 29 axe-core tests as Phase 1.5+ scope
1. Each fix has its own commit on `main` (Bodai pre-1.0 policy)
1. `tests/a11y/conftest.py` exists with `pytest.importorskip` for `axe_playwright_python` and `playwright.async_api`

## Out of Scope (deferred to Phase 1.5+ or Phase 2)

- 29 a11y axe-core tests (need `@axe-core/playwright` install + browser deps; deferred via `pytest.importorskip` per Fix 7)
- Coverage push from 67.81% → 85% (the aspirational audit-pass target; deferred to Phase 2)
- Framework-side blocking-IO detector (per Task 8 Ruling — needs separate spec)
- The 3-test gap between table (43) and pytest header (46) — explained by pytest collection filter that deselects 3 POSTURES components; reconcile in implementation if needed

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Tool profile ground truth changed intentionally; tests are wrong | Medium | Low | Update tests with comment; document in commit message |
| xdist flake is actually a real race in production code | Low | High | Investigate before marking serial; reproduce with `--dist=loadfile` bisect |
| `mcp-common>=0.30.1,<0.31` breaks another repo | Low | Medium | Coordinate with oneiric; document the upper bound as soft |
| Coverage ratchet update masks future regression if only some sites updated | Low | Medium | All 4 sites updated in same commit |
| C3 is a no-op (wiring already works); spec still prescribes a fix | Medium | Medium | Investigate first; only fix if hypothesis confirmed |
| Tool profile env var name drift between docs and code | Low | Low | v2 spec corrected to `FASTBLOCKS_TOOL_PROFILE`; verification commands updated |
| httpx2 3.x lands before Phase 2 | Low | Medium | `<3` upper bound blocks it; revisit at Phase 2 |

## Self-Review (v2)

**Multi-lens review coverage:**

- pytest-hypothesis-specialist: 4 BLOCKERs + 4 IMPORTANTs → all addressed
- code-architect: 3 BLOCKERs + 4 IMPORTANTs → all addressed
- dependency-manager: 2 BLOCKERs + 2 IMPORTANTs → all addressed
- fastblocks-specialist: 3 BLOCKERs + 5 IMPORTANTs → all addressed

**Placeholder scan:** None — every fix references concrete files and test names. C3 fix's smoke test path is now concrete (`tests/integration/test_fastblocks_ui_wiring.py::test_ui_helpers_registered_on_env`).

**Internal consistency:**

- Fix 1 (D8a) now has 4 edit sites (pyproject 2x + ratchet JSON + observability group)
- Fix 6 (coverage gate) now has 4 edit sites (pyproject addopts + coverage.report + ratchet + workflow)
- Tool profile env var: `FASTBLOCKS_TOOL_PROFILE` (NOT `MAHAVISHNU_TOOL_PROFILE`)
- C3 fix is investigation-first, not blind wiring
- Failure inventory has "Likely side" column (TEST/IMPL/UNKNOWN) per pytest reviewer

**Scope check:** Single coherent follow-up to Phase 1; no decomposition needed.

**Ambiguity check:** All 4 reviews surfaced at least 1 finding; 6 of 14 findings had 2+ reviewer corroboration. C3 fix has explicit Investigation → Decision → Fix flow. Collection errors have explicit `--collect-only` diagnostic step.

## Handoff

When this spec is approved:

1. Invoke `superpowers:writing-plans` skill to produce a task-by-task implementation plan
1. Then invoke `superpowers:subagent-driven-development` (per ledger's established pattern) to execute
1. Multi-agent review per fix (TDD rigor + API correctness lenses); per-fix commit on `main`

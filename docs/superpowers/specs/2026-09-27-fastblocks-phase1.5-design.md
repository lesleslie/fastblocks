# Phase 1.5 — Test Gate Tightening & C3 Framework Fix Design

> **For agentic workers:** Phase 1.5 is the bridge between the audit pass
> (Phase 1) and the build wave (Phase 2). It converts pre-existing test
> failures into a known-green baseline AND fixes the one framework bug
> that blocks Phase 2 (C3: fastblocks-ui function registration).

**Goal:** Make `uv run pytest tests/ --no-cov -q` exit 0 with `--cov-fail-under=67.81` enforced, AND wire `register_fastblocks_ui_functions(env)` into `FastBlocksApp.init()`, so Phase 2 lands on a clean baseline.

**Architecture:** Two streams, ordered — Tests first (then C3). Tests stream ratchets the gate criteria that the audit pass established; C3 stream is the one framework-level fix the audit surfaced that blocks Phase 2 (landing page CSS won't load without it).

**Tech Stack:** Same as audit pass (uv, pytest, fastblocks-ui, oneiric, fastblocks adapters).

**Spec source:** [2026-09-27-fastblocks-dogfood-readiness-design.md](2026-09-27-fastblocks-dogfood-readiness-design.md) (Phase 1 spec; Phase 1.5 is its follow-up)

**Plan source:** TBD (writing-plans skill produces the plan after this spec is approved)

## Global Constraints

These apply to every task in Phase 1.5:

- **Git workflow:** Bodai pre-1.0 merge policy (direct to `main`); commit per logical fix; descriptive commit message per fix area.
- **Coverage ratchet target:** `--cov-fail-under=67.81` (current actual post-audit-pass). Floor cannot drop below this without an explicit ADR; do not silently lower it.
- **Scope guard:** Tractable fixes only (Q1=1). The 29 a11y axe-core parametrize errors are OUT OF SCOPE — they require `@axe-core/playwright` install + browser deps; deferred to Phase 1.5+ or Phase 2.
- **No backwards compat** (Bodai pre-1.0): fix forward, don't add deprecation shims.
- **Test-first discipline:** When fixing a failing test, prefer test rewrite over test skip; if you must skip, document the reason in the test docstring.
- **A11y axe-core tests:** keep them in tree (don't delete) — they're documented as known-broken in `docs/known-claim-gaps.md` so the audit pass claim remains honest.

## Failure Inventory (from `uv run pytest tests/ --no-cov -q`)

**Total:** 12 failed + 34 errors = **46 non-passing** (2780 passing, 51 skipped).

| # | Test | Category | Disposition |
|---|---|---|---|
| 1 | `tests/test_exceptions_comprehensive.py::TestSafeDependsGet::test_resolution_error_returns_default` | Exceptions | Fix |
| 2 | `tests/test_exceptions_comprehensive.py::TestSafeDependsGet::test_resolution_error_no_default` | Exceptions | Fix |
| 3 | `tests/test_dep_pins.py::test_no_loose_pins_on_critical_deps` | D8a | Fix (pin tighten) |
| 4 | `tests/test_dep_pins.py::test_no_broken_release_in_dep_specs` | D8a | Fix (mcp-common bump) |
| 5 | `tests/unit/test_tool_profile.py::test_full_profile_registers_eight_tools` | Tool profile | Fix (5 tests in this file) |
| 6 | `tests/unit/test_tool_profile.py::test_standard_profile_registers_eight_tools` | Tool profile | Fix |
| 7 | `tests/unit/test_tool_profile.py::test_minimal_profile_registers_only_discover_tools` | Tool profile | Fix |
| 8 | `tests/unit/test_tool_profile.py::test_mandatory_tools_subset_holds_at_all_profiles` | Tool profile | Fix |
| 9 | `tests/unit/test_tool_profile.py::test_unset_env_var_falls_back_to_full` | Tool profile | Fix |
| 10 | `tests/adapters/templates/test_boot.py::test_templates_adapter_env_has_autoescape_on` | D3 xdist flake | Fix (`@pytest.mark.serial` or fixture isolation) |
| 11 | `tests/security/test_autoescape_regression.py::test_jinja2_environment_default_autoescape_is_true` | D6 (autoescape) | Investigate (passes in isolation per Task 6; investigate xdist race) |
| 12 | `tests/pyproject/test_dependency_groups.py::test_mcp_common_pin_below_0_4_for_tool_pydantic_workaround` | D8 | Likely resolves with D8a |
| 13-41 | `tests/a11y/test_components_a11y.py::test_component_passes_axe_core[*]` (29 variants) | A11y env | **OUT OF SCOPE** (Q1=1) |
| 42 | `tests/adapters/routes/test_routes.py` (collection error) | Import collision | Fix (filename deviation, add `__init__.py`, or fix import path) |
| 43 | `tests/perf/test_async_rendering.py` (collection error) | Import collision | Fix (same root cause as 42) |

## Stream A: Test Fixes (ordered; do C3 after all green)

### Fix 1: D8a — Tighten dep pins

**Files:** `pyproject.toml`, `uv.lock` (regenerate)

**Change:**
- `httpx2>=0.28.1` → `httpx2>=0.28.1,<0.30`
- `mcp-common>=0.30.0` → `mcp-common>=0.30.1,<0.31` (skips broken 0.30.0 release)
- `oneiric>=0.20` → `oneiric>=0.20,<0.21`

**Why these specific bounds:**
- `httpx2<0.30`: 0.30 has breaking API changes we don't want to chase pre-launch
- `mcp-common<0.31`: 0.30.0 was a broken release (per ledger); 0.30.1+ is correct
- `oneiric<0.21`: 0.21+ may have breaking changes (cross-repo); pin until we verify

**Tests affected:** Fix #3, #4, #12 (auto-resolves via pin change)

**Verification:**
```bash
uv lock --check                        # existing CI gate stays green
uv run pytest tests/test_dep_pins.py tests/pyproject/test_dependency_groups.py -v
```

### Fix 2: D3 — xdist flake (autoescape race)

**Files:**
- `tests/adapters/templates/test_boot.py` — add `@pytest.mark.serial` to `test_templates_adapter_env_has_autoescape_on`
- `tests/security/test_autoescape_regression.py` — same if reproduction confirms shared fixture state

**Root cause hypothesis:** The templates adapter test mutates `Templates.env.autoescape` (or related) and another test reads it. Under pytest-xdist (parallel workers), mutations don't serialize.

**Investigation step:** Run the test in isolation AND under xdist; if isolation passes + xdist fails, mark serial; if both fail, the underlying assertion is wrong (rare since Task 5 verified boot tests).

**Tests affected:** Fix #10, possibly #11

**Verification:**
```bash
uv run pytest tests/adapters/templates/test_boot.py -v              # serial
uv run pytest tests/adapters/templates/test_boot.py -n auto -v      # parallel
uv run pytest tests/security/test_autoescape_regression.py -v
```

### Fix 3: Tool profile (5 tests)

**Files:** `tests/unit/test_tool_profile.py`, `mahavishnu/mcp/tools/profiles.py` (if env handling is wrong)

**Root cause hypothesis:** `MAHAVISHNU_TOOL_PROFILE` env var handling changed. Tests assume specific behavior (e.g., `unset` falls back to `full`); if recent profile-gated tool changes altered the count or fallback, tests fail.

**Investigation step:**
1. Read `mahavishnu/mcp/tools/profiles.py` — confirm profile definitions
2. Read `tests/unit/test_tool_profile.py` — confirm what tests assert
3. Reconcile: either fix the profile implementation OR update the tests to match new ground truth (with a comment explaining the ground truth change)

**Tests affected:** Fix #5–#9

**Verification:**
```bash
MAHAVISHNU_TOOL_PROFILE=full uv run pytest tests/unit/test_tool_profile.py -v
MAHAVISHNU_TOOL_PROFILE=standard uv run pytest tests/unit/test_tool_profile.py -v
MAHAVISHNU_TOOL_PROFILE=minimal uv run pytest tests/unit/test_tool_profile.py -v
unset MAHAVISHNU_TOOL_PROFILE && uv run pytest tests/unit/test_tool_profile.py -v
```

### Fix 4: Exceptions (TestSafeDependsGet, 2 tests)

**Files:** `tests/test_exceptions_comprehensive.py`, `fastblocks/.../exceptions.py` (or wherever SafeDependsGet lives)

**Root cause hypothesis:** `SafeDependsGet` behavior changed — possibly raised vs returned-default semantics, or default-value handling.

**Investigation step:**
1. Locate `SafeDependsGet` definition
2. Read the 2 failing test bodies — understand expected behavior
3. Decide: fix implementation to match tests (preferred) OR fix tests to match new ground truth (if intentional behavior change)

**Tests affected:** Fix #1, #2

**Verification:**
```bash
uv run pytest tests/test_exceptions_comprehensive.py::TestSafeDependsGet -v
```

### Fix 5: Collection errors (test_routes.py + test_async_rendering.py)

**Files:** `tests/adapters/routes/test_routes.py`, `tests/perf/test_async_rendering.py`

**Root cause hypothesis:** pytest `import_mode=prepend` (from `pyproject.toml`) collides with same-named production modules. `fastblocks/adapters/routes/` (production) shadowed by `tests/adapters/routes/test_routes.py` (test). Same for `tests/perf/test_async_rendering.py` vs `fastblocks/perf/...` if it exists.

**Investigation step:**
1. Verify: `python -c "import tests.adapters.routes.test_routes"` — see if import error reproduces
2. Check `pyproject.toml` `[tool.pytest.ini_options]` for `import_mode`
3. Fix options (in order of preference):
   a. Add `tests/adapters/routes/__init__.py` and `tests/perf/__init__.py` if missing
   b. Rename test files to avoid collision (e.g., `test_routes_adapter.py`)
   c. Change `import_mode` to `importlib` (last resort — affects entire test suite)

**Tests affected:** Fix #42, #43

**Verification:**
```bash
uv run pytest tests/adapters/routes/ -v
uv run pytest tests/perf/test_async_rendering.py -v
```

### Fix 6: D1b — Coverage gate enforcement

**Files:**
- `.coverage-ratchet.json` — update `current_minimum` from `49.13%` to `67.81%`
- `.github/workflows/quality.yml` — change pytest job `--no-cov` to `--cov-fail-under=67.81`

**Why:** The audit pass landed at 67.81% actual coverage but the ratchet still says 49.13% (pre-audit baseline). Update both to match reality so future regressions are caught.

**Verification:**
```bash
uv run pytest --cov=fastblocks --cov-report=term --cov-fail-under=67.81
cat .coverage-ratchet.json
```

### Fix 7 (post-tests): A11y axe-core — mark with documented skip

**Files:** `tests/a11y/test_components_a11y.py` (NOT removed; documented as Phase 1.5+ scope)

**Why:** Q1=1 (tractable only) excludes axe-core. To prevent this from masking future regressions AND to make the 29 errors visible in CI summary, add `@pytest.mark.skip(reason="Requires @axe-core/playwright + browser deps; deferred to Phase 1.5+ per 2026-09-27 spec")` to each parametrized test, OR a single module-level `pytestmark = pytest.mark.skip(...)`.

**Add to `docs/known-claim-gaps.md`** with row:
```
| A11y axe-core tests (29) | tests/a11y/test_components_a11y.py | Requires @axe-core/playwright + browser binary | Phase 1.5+ environment work |
```

## Stream B: C3 Framework Fix

### Fix 8: C3 — Wire `register_fastblocks_ui_functions(env)` into `FastBlocksApp.init()`

**Files:**
- `fastblocks/applications.py` (or wherever `FastBlocksApp.init()` lives)
- `fastblocks-ui` — confirm export of `register_fastblocks_ui_functions`

**Why:** Audit pass surfaced that without this wiring, the landing page CSS won't load (functions never registered into Jinja2 env). Phase 2 needs this working.

**Investigation step (during implementation):**
1. Locate `register_fastblocks_ui_functions` in fastblocks-ui
2. Locate `FastBlocksApp.init()` in fastblocks
3. Confirm where Jinja2 env is constructed (likely in templates adapter init)
4. Wire: after env construction, call `register_fastblocks_ui_functions(env)`

**Verification:**
```bash
uv run pytest tests/adapters/templates/ tests/htmx/ -v    # existing tests still green
uv run python -c "
from fastblocks.applications import FastBlocks
from jinja2 import Environment
app = FastBlocks()
# After init, env should have fastblocks_ui functions registered
# (Specific assertion depends on what functions exist; discover during impl)
"
```

## Execution Order

```
Fix 1 (D8a pins)          ──┐
Fix 2 (D3 xdist)           ──┤
Fix 3 (tool profile)       ──┤
Fix 4 (exceptions)         ──┼─→ Fix 6 (coverage gate) → Fix 7 (a11y skip)
Fix 5 (collection errors)  ──┘                                          │
                                                                          │
                                              (all 12 + 2 errors green) │
                                                                          ▼
                                                                Fix 8 (C3 framework)
                                                                          │
                                                                          ▼
                                                              Phase 2 unblocked
```

Fixes 1-5 can be parallelized (independent files). Fix 6 must come after all of them (coverage ratchet needs green tests). Fix 7 is a 1-line skip; can go anywhere. Fix 8 (C3) is the last step — must come after tests are green to avoid masking failures.

## Acceptance Criteria

When ALL of the following are true, Phase 1.5 is complete:

1. `uv run pytest tests/ --no-cov -q` exits 0 (or shows 51 skipped + 0 failed + 0 errors)
2. `uv run pytest --cov=fastblocks --cov-fail-under=67.81` exits 0
3. `uv lock --check` exits 0 (dep pins tightened, lockfile consistent)
4. `FastBlocksApp.init()` registers fastblocks-ui functions (verified by a smoke test)
5. `.coverage-ratchet.json` `current_minimum` is `67.81%`
6. `.github/workflows/quality.yml` pytest job uses `--cov-fail-under=67.81` (no longer `--no-cov`)
7. `docs/known-claim-gaps.md` documents the 29 axe-core tests as Phase 1.5+ scope
8. Each fix has its own commit on `main` (Bodai pre-1.0 policy)

## Out of Scope (deferred to Phase 1.5+ or Phase 2)

- 29 a11y axe-core tests (need `@axe-core/playwright` install + browser deps)
- Coverage push from 67.81% → 85% (the aspirational audit-pass target; deferred to Phase 2)
- Framework-side blocking-IO detector (per Task 8 Ruling — needs separate spec)

## Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Tool profile ground truth changed intentionally; tests are wrong | Medium | Low | Update tests with comment; document in commit message |
| xdist flake is actually a real race in production code | Low | High | Investigate before marking serial; report to user |
| `mcp-common>=0.30.1,<0.31` breaks another repo | Low | Medium | Coordinate with oneiric; document the upper bound as soft |
| Coverage ratchet update masks future regression | Low | Medium | `--cov-fail-under=67.81` is floor, not target; 85% remains aspirational |

## Self-Review

**Placeholder scan:** None — every fix references concrete files and test names.

**Internal consistency:**
- Fix 1 affects tests 3, 4, 12 — clear
- Fix 6 depends on all prior fixes — explicit ordering
- Fix 7 (a11y skip) is orthogonal; can land anywhere
- Fix 8 (C3) is independent of test fixes; can technically run earlier, but ordered last for safety

**Scope check:** Single coherent follow-up to Phase 1; no decomposition needed.

**Ambiguity check:** Fix 3 (tool profile) and Fix 4 (exceptions) require investigation during implementation — spec acknowledges this; plan/impl will surface specifics.

## Handoff

When this spec is approved:

1. Invoke `superpowers:writing-plans` skill to produce a task-by-task implementation plan
2. Then invoke `superpowers:subagent-driven-development` (per ledger's established pattern) to execute
3. Multi-agent review per fix (TDD rigor + API correctness lenses)

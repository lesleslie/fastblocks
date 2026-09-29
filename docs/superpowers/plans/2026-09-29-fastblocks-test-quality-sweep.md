# FastBlocks Test-Quality Sweep Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address the 5 fixable pre-existing test failures + the `test_cardinality_guard.py` global structlog pollution that surfaced during the Phase 1.5 verify rerun. Track the multi-week Tier 5 follow-up separately.

**Architecture:** Mechanical fixes (pyproject pins + test parser bug + env var doc removal) for the pre-existing failures; architectural choice (test-side teardown vs production-side kwargs-only) for the structlog pollution. All changes scope-local, all back to green in canonical `.venv/bin/pytest`.

**Tech Stack:** Python 3.14, pytest, uv-managed pyproject.toml, structlog.

**Spec:** `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` §Phase 1→2 gate + Phase 3 verify report + Plan 5 verify-rerun (commit `152f7d4`).

## Global Constraints

- **Bodai pre-1.0 replace-not-deprecate discipline** (per `feedback-no-backwards-compat-pre-1.0.md`)
- **No version bump** in `pyproject.toml` — upper caps are NOT version bumps (they're constraint tightening within the existing floor)
- **No `Co-Authored-By: Claude Code` trailer** in commit messages
- **No `git push`** — user-controlled
- **Scope-only staging:** `git add <specific-paths>`, never `git add .` or `git add -A`
- **Git author:** `lesleslie <les@wedgwoodwebworks.com>`
- **drift-bundling-recovery** discipline: stay in scope; do not bundle unrelated fixes

---

## Task A: Pyproject.toml pin-shape tightening (#1, #4, #5)

**Files:**
- Modify: `pyproject.toml`
- Modify: `uv.lock` (auto-generated)

**Current state (per grep):**
- `[project].dependencies`: 4 loose pins — `brotli-asgi>=1.6.0`, `granian[reload]>=2.8.3`, `minify-html>=0.18.1`, `starlette-async-jinja>=1.15.0`
- `[dependency-groups].observability`: 5 pins using floor-only `>=X.Y.Z` — `prometheus-client>=0.26.0`, `opentelemetry-sdk>=1.44.0`, `opentelemetry-exporter-otlp-proto-http>=1.44.0`, `sentry-sdk[opentelemetry]>=3.0.0a7,<3.0.0a8`, `structlog>=26.1.0,<27`. (Test #6 explicitly asserts `~=` for opentelemetry-exporter-otlp-proto-http; Test #5 explicitly asserts `~=` for structlog.)

- [ ] **Step 1: Add upper caps to the 4 critical deps**

In `pyproject.toml [project].dependencies`:
```toml
# Before
"brotli-asgi>=1.6.0",
"granian[reload]>=2.8.3",
"minify-html>=0.18.1",
"starlette-async-jinja>=1.15.0",

# After (caps chosen to allow one major-version bump before breaking)
"brotli-asgi>=1.6.0,<2",
"granian[reload]>=2.8.3,<3",
"minify-html>=0.18.1,<0.19",
"starlette-async-jinja>=1.15.0,<2",
```

- [ ] **Step 2: Tighten observability-group pins to `~=` (compatible-release)**

```toml
# Before (floor-only or bounded-range)
"prometheus-client>=0.26.0",
"opentelemetry-sdk>=1.44.0",
"opentelemetry-exporter-otlp-proto-http>=1.44.0",
"sentry-sdk[opentelemetry]>=3.0.0a7,<3.0.0a8",
"mcp-common>=0.30.2,<0.31",  # Δ47 — KEEP as-is (test_observability_group_present_with_correct_pins asserts <0.31)
"structlog>=26.1.0,<27",     # Δ40 — change per Global Constraint line 25

# After
"prometheus-client~=0.26.0",
"opentelemetry-sdk~=1.44.0",
"opentelemetry-exporter-otlp-proto-http~=1.44.0",
"sentry-sdk[opentelemetry]~=3.0.0a7",
"mcp-common>=0.30.2,<0.31",  # KEEP — test requires <0.31
"structlog~=26.1.0",
```

- [ ] **Step 3: Refresh lockfile**

```bash
cd /Users/les/Projects/fastblocks
uv lock
git status --short  # expect pyproject.toml + uv.lock modified
```

- [ ] **Step 4: Verify `uv lock --check` is clean**

```bash
uv lock --check
```

Expected: clean (no drift).

- [ ] **Step 5: Verify the 3 affected tests now pass**

```bash
.venv/bin/pytest tests/test_dep_pins.py::test_no_loose_pins_on_critical_deps \
               tests/observability/test_tracer.py::test_otel_sdk_pinned_in_observability_dep_group \
               tests/observability/test_loggers.py::test_structlog_pinned_in_observability_dep_group \
               --no-cov
```

Expected: 3/3 PASSED.

- [ ] **Step 6: Commit (scope-only)**

```bash
git add pyproject.toml uv.lock
git commit -m "fix(fastblocks): tighten dep pins to ~=X.Y and add critical-dep upper caps (F1.5-D8-T3)"
```

**Integration Contract:** `test_no_loose_pins_on_critical_deps`, `test_otel_sdk_pinned_in_observability_dep_group`, `test_structlog_pinned_in_observability_dep_group` all PASS. `uv lock --check` clean.

---

## Task B: Test parser bug fix (#6)

**File:** `tests/pyproject/test_dependency_groups.py`

**Diagnosis:** The parser at lines 5-15 splits each dep entry on `[`, `~`, `=` and takes `[0]`. For `"prometheus-client>=0.26.0"` the splits produce `"prometheus-client>"` (the `>` survives the `=` split). So `members` is `{'prometheus-client>', 'opentelemetry-sdk>', ...}` — but the assertions check for `'prometheus-client'` (without `>`), which is never in the set.

- [ ] **Step 1: Fix the assertions to match the parser output**

In `tests/pyproject/test_dependency_groups.py`:
```python
# Before
members = {
    entry.split("[")[0].split("~")[0].split("=")[0].strip()
    for entry in group
}
assert "prometheus-client" in members
assert "opentelemetry-sdk" in members
assert "opentelemetry-exporter-otlp-proto-http" in members
assert "sentry-sdk" in members

# After — strip the trailing '>' to match the parser's first-split-segment output
members = {
    entry.split("[")[0].split("~")[0].split("=")[0].rstrip(">").strip()
    for entry in group
}
assert "prometheus-client" in members
assert "opentelemetry-sdk" in members
assert "opentelemetry-exporter-otlp-proto-http" in members
assert "sentry-sdk" in members
```

The `rstrip(">")` addition is the load-bearing change; `sentry-sdk` passes either way because `entry.split("[")[0]` gives `"sentry-sdk"` (no `>` survives).

- [ ] **Step 2: Verify the test now passes**

```bash
.venv/bin/pytest tests/pyproject/test_dependency_groups.py::test_observability_group_present_with_correct_pins --no-cov
```

Expected: PASSED.

- [ ] **Step 3: Commit (scope-only)**

```bash
git add tests/pyproject/test_dependency_groups.py
git commit -m "test(fastblocks): fix dep-name parser to match assertion expectations"
```

**Integration Contract:** `test_observability_group_present_with_correct_pins` PASSES.

---

## Task C: Remove `FASTBLOCKS_PORT` env var doc references (#2)

**Diagnosis:** Plan 5 implementer noted: "Brief used `FASTBLOCKS_PORT=8001` env var; uvicorn doesn't honor env var." The env var was a brief-author mistake — it appears in docs but no source reads it. The right fix is to remove the doc reference (alternative: add source-side support, but that's drift-bundling beyond this sweep).

- [ ] **Step 1: Find all doc references to `FASTBLOCKS_PORT`**

```bash
grep -rn "FASTBLOCKS_PORT" docs/ 2>&1 | grep -v "docs/superpowers/"
```

- [ ] **Step 2: Remove each reference, replacing with the actual uvicorn invocation**

Wherever the doc says "set `FASTBLOCKS_PORT=...`" or similar, replace with the actual uvicorn flag form (e.g., `uvicorn main:app --port 8001 --host 127.0.0.1`).

- [ ] **Step 3: Verify the test now passes**

```bash
.venv/bin/pytest tests/docs/test_doc_accuracy.py::test_env_var_names_match_source --no-cov
```

Expected: PASSED.

- [ ] **Step 4: Commit (scope-only)**

```bash
git add docs/<each-modified-file>
git commit -m "docs(fastblocks): remove FASTBLOCKS_PORT env var reference (env var is not honored)"
```

**Integration Contract:** `test_env_var_names_match_source` PASSES. No source code touched.

---

## Task D: Global structlog mutation fix (test_cardinality_guard.py:141-149)

**Files:** TBD based on user's architectural choice (see below).

**Diagnosis:** `tests/observability/test_cardinality_guard.py:141-149` calls `structlog.configure(wrapper_class=structlog.BoundLogger)` — the GENERIC `BoundLogger` from `structlog._generic`. Its `__getattr__` wraps `_proxy_to_logger` with `partial(method_name)` that does NOT consume positional substitution args. After this test runs in an xdist worker, any subsequent `_log.exception("...%s...", x, y)` call in that worker overflows `_proxy_to_logger`'s signature and raises `TypeError`. The 3 production sites at risk:
- `fastblocks/adapters/templates/_advanced_manager.py:1013`
- `fastblocks/adapters/templates/_advanced_manager.py:1028`
- `fastblocks/adapters/templates/_async_renderer.py:196`

The 3 Phase 1.5 tests were already isolated via `patch.object(_module, "_log")` (commit `941e4c1`); this task addresses the **latent** pollution for any other test in the same worker.

**Architectural choice (user decision required):**

- **Choice A — Test-side fix (recommended, smaller scope):** Add fixture teardown in `tests/observability/test_cardinality_guard.py` to capture and restore structlog config around the `structlog.configure(...)` call.
- **Choice B — Production-side fix:** Make the 3 production `_log.exception` calls kwargs-only (`_log.exception("...", name=x)` instead of `_log.exception("...", x)`) so they're compatible with the generic `BoundLogger`.
- **Choice C — Both.** Defensive but expands scope.

**Recommendation: Choice A** — keeps the fix at the source of the problem (the polluting test) rather than papering over it in production code. Choice B is broader (3 production sites + uv.lock regression) and risks masking other future pollution.

- [ ] **Step 1: Choice A — add fixture teardown to test_cardinality_guard.py**

```python
# tests/observability/test_cardinality_guard.py (around line 141-149)

@pytest.fixture
def reset_structlog_config():
    """Snapshot structlog.configure() state before each test, restore after.
    
    test_cardinality_guard.py reconfigures structlog to the generic
    BoundLogger (wrapper_class=structlog.BoundLogger). The generic
    BoundLogger uses __getattr__ to wrap _proxy_to_logger with a
    partial(method_name) that does not consume positional substitution
    args, so any subsequent _log.exception('...%s...', x, y) call
    in the same xdist worker overflows _proxy_to_logger's signature
    and raises TypeError. This fixture prevents cross-test pollution
    of the structlog global state.
    """
    import structlog
    saved = structlog.get_config()
    yield
    structlog.configure(**saved)

@pytest.mark.usefixtures("reset_structlog_config")
def test_..._configures_structlog_correctly():
    # existing test body unchanged
```

Apply `@pytest.mark.usefixtures("reset_structlog_config")` to ALL tests in `tests/observability/test_cardinality_guard.py` that call `structlog.configure(...)`.

- [ ] **Step 2: Verify the fix works**

```bash
.venv/bin/pytest tests/observability/test_cardinality_guard.py tests/adapters/templates/test_hybrid_render.py tests/adapters/templates/test_async_renderer_boot.py --no-cov
```

Expected: All PASS.

- [ ] **Step 3: Verify the full suite is no worse than before**

```bash
.venv/bin/pytest --no-cov 2>&1 | tail -3
```

Expected: 5 failed (down from 6) — `test_coverage_target_consistency` remains as the only pre-existing failure.

- [ ] **Step 4: Commit (scope-only)**

```bash
git add tests/observability/test_cardinality_guard.py
git commit -m "test(fastblocks): restore structlog config after cardinality-guard test (prevent xdist pollution)"
```

**Integration Contract:** `test_cardinality_guard.py` tests still PASS; structlog global state is restored after each test; no other tests in the same xdist worker experience the latent `BoundLogger` TypeError.

---

## Out of scope (tracked separately)

- **#3 `test_coverage_target_consistency`** (test_doc_accuracy.py:290) — historical ledger file `docs/superpowers/sdd-logs/2026-09-27-phase1.5-plus-ledger.md` claims coverage 65.0%, but `pyproject.toml` floor is 67.81%. Explicitly tied to F1.5-D1-T1 multi-week Tier 5 work (coverage ratchet 68.19% → 85%). Per user direction, this is multi-week work and not in this sweep.

---

## Verification (final, after all 4 tasks)

```bash
.venv/bin/pytest 2>&1 | tail -3
```

Expected: 1 failed, 28xx passed (only `test_coverage_target_consistency` remains as the sole pre-existing failure, due to F1.5-D1-T1 Tier 5 work).

5 commits, scope-only per Bodai discipline, no Co-Authored-By, no version bump, no push.

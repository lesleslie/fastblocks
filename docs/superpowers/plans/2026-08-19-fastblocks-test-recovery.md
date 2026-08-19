# FastBlocks Test Recovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce the current FastBlocks dirty-WIP baseline from 117 test failures to zero unexpected failures without discarding the user's existing changes.

**Architecture:** Repair the current dirty WIP inside the isolated FastBlocks recovery worktree. Use bounded waves: establish and classify the baseline, settle shared resolver/initialization behavior with one owner, make non-overlapping production fixes, migrate only proven stale mocks/assertions, and finish with isolated, full-suite, warning, and clean-HEAD verification. The coordinator owns integration and shared-file conflicts; implementation agents own disjoint file sets and return commit SHAs.

**Tech Stack:** Python 3.13, pytest, pytest-asyncio, Oneiric resolver, FastBlocks application and adapter modules, existing project virtual environment, git worktrees and commit-based integration.

## Global Constraints

- Preserve the 91 modified tracked files and 3 untracked files copied from the current FastBlocks checkout; never reset, clean, stash, or discard them.
- Run implementation from `/Users/les/.claude/worktrees/fastblocks-test-recovery-2026-08-19`; the original checkout is read-only for this recovery.
- Do not install dependencies, run `uv sync`, or modify lockfiles. Use the existing `.venv/bin/pytest` and `.venv/bin/python`.
- Do not use `--no-cov` as a substitute for a product behavior fix; it is used only to keep the test run read-only and to avoid coverage artifacts.
- Do not remove or weaken security assertions, adapter behavior assertions, or regression tests merely to make a test pass.
- Assign exactly one owner to `fastblocks/initializers.py`, `fastblocks/main.py`, and their direct dependency-contract tests. Stop on a shared-file conflict.
- Do not perform the deferred 20+ `Resolver()` consolidation, `root_path()` unification, or adapter base-class refactor.
- Every implementation commit must contain only the files owned by its domain and include a focused test result in the agent report.
- Any generated test artifact must be reported; agents must not delete user-owned or WIP files.
- Existing project rules remain authoritative: use typed Python, `pathlib`, project logging conventions, and focused test markers; do not add `Any`, production `assert`, or broad exception swallowing.

## File map and ownership

| Path | Responsibility | Ownership |
|---|---|---|
| `fastblocks/initializers.py` | Shared dependency initialization and sync/async bridge | Resolver owner only |
| `fastblocks/main.py` | Application dependency access mirrors initializer behavior | Resolver owner only |
| `fastblocks/_validation_integration.py` | Validation/sanitizer singleton wiring | Sanitizer domain |
| `fastblocks/htmx.py` | HTMX publish fallback and coroutine lifecycle | Async-runtime domain |
| Affected caching/runtime path | Existing unawaited-coroutine behavior called by HTMX tests | Async-runtime domain, only if reproduced |
| `fastblocks/adapters/templates/jinja2.py` | ChoiceLoader source-loading contract | Template-loader domain |
| `tests/security/test_input_validation.py` | Async validation and traversal tests | Security-test domain |
| `tests/test_cli_comprehensive.py` | CLI setup, resolver mocks, output assertions | CLI-test domain |
| `tests/test_validation_integration.py` | Sanitizer and validation integration behavior | CLI-test domain |
| `tests/adapters/templates/test_filters_comprehensive.py` | Template filter dependency mocks and rendered outputs | Template-filter-test domain |
| `tests/test_initializers_comprehensive.py` | Initializer dependency and tuple/registration expectations | Resolver owner only |
| `tests/test_main_comprehensive.py` | Application dependency and registration expectations | Resolver owner only |
| `tests/adapters/templates/test_rendering_jinja2.py` | Rendering collection/import path | Rendering-test domain, only if collection audit reproduces it |
| `tests/adapters/admin/test_sqladmin_comprehensive.py` | Admin model registration expectation | Admin-test domain |
| `fastblocks/stubs/oneiric/core/resolution.pyi` | Existing untracked Oneiric type stub; do not modify unless the resolver owner proves it is the failing surface | Resolver owner only after permission |

---

### Task 1: Lock the dirty-WIP baseline and ownership manifest

**Files:**
- Create: `docs/superpowers/plans/2026-08-19-fastblocks-test-recovery-baseline.md`
- Read: `pyproject.toml`, `CLAUDE.md`, `AGENTS.md`, and the current git status

**Interfaces:**
- Consumes: The current original checkout at `/Users/les/Projects/fastblocks`.
- Produces: A durable baseline containing HEAD, WIP file counts, test command, failure counts, and domain ownership rules for later tasks.

- [ ] **Step 1: Verify the isolated worktree snapshot**

Run from the recovery worktree:

```bash
git -C /Users/les/.claude/worktrees/fastblocks-test-recovery-2026-08-19 status --porcelain=v1
git -C /Users/les/.claude/worktrees/fastblocks-test-recovery-2026-08-19 rev-parse HEAD
```

Expected: `94` WIP status entries remain, with 91 modified tracked entries and 3 untracked entries, and the HEAD remains `4a9fab62bc654c7b31054d24c90c2e8a41f56310`.

- [ ] **Step 2: Record the canonical read-only test command**

Run:

```bash
cd /Users/les/.claude/worktrees/fastblocks-test-recovery-2026-08-19
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected before repair: the recorded baseline is the previously measured 1,553 passed, 117 failed, 21 skipped, 4 xpassed, and 318 warnings in approximately 49 seconds. If the state differs, record the new counts and stop to reconcile the snapshot.

- [ ] **Step 3: Write the baseline manifest**

Create `docs/superpowers/plans/2026-08-19-fastblocks-test-recovery-baseline.md` with exact output fields:

```markdown
# FastBlocks Recovery Baseline

- HEAD: 4a9fab62bc654c7b31054d24c90c2e8a41f56310
- WIP entries: 94 (91 modified tracked, 3 untracked)
- Initial counts: 1695 collected, 1553 passed, 117 failed, 21 skipped, 4 xpassed, 318 warnings
- Canonical command: PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
- Shared ownership lock: initializers.py, main.py, direct dependency tests = one owner
- Notes: later diagnosis found possible rendering collection issue; verify it explicitly.
```

Replace the angle-bracket value with the actual SHA; do not leave placeholders.

- [ ] **Step 4: Commit the baseline manifest**

```bash
git add docs/superpowers/plans/2026-08-19-fastblocks-test-recovery-baseline.md
git commit -m "docs(fastblocks): record test recovery baseline"
```

---

### Task 2: Settle the resolver/initialization contract with one owner

**Files:**
- Read: `fastblocks/initializers.py`, `fastblocks/main.py`, `fastblocks/adapters/oneiric_helper.py`, `tests/test_initializers_comprehensive.py`, `tests/test_main_comprehensive.py`
- Modify: only those direct resolver/initialization files listed above
- Test: `tests/test_initializers_comprehensive.py` and `tests/test_main_comprehensive.py`

**Interfaces:**
- Consumes: The shared ownership lock from Task 1.
- Produces: One canonical sync/async resolver contract consumed by later CLI, filter, security, and adapter tests.

- [ ] **Step 1: Inspect the installed Oneiric API before changing code**

Run from the recovery worktree:

```bash
cd /Users/les/.claude/worktrees/fastblocks-test-recovery-2026-08-19
.venv/bin/python - <<'PY'
import asyncio
import inspect
from oneiric.core.resolution import Resolver

print(inspect.signature(Resolver.resolve))
print("is_coroutine_function=", inspect.iscoroutinefunction(Resolver.resolve))
print("isinstance_async_callable=", asyncio.iscoroutinefunction(Resolver.resolve))
PY
```

Record the output in the agent report. The diagnosis must distinguish a synchronous `Resolver.resolve` from a coroutine-returning mock.

- [ ] **Step 2: Reproduce the four dependency-contract failures**

Run:

```bash
.venv/bin/pytest \
  tests/test_initializers_comprehensive.py::TestDependencyResolution \
  tests/test_initializers_comprehensive.py::TestConcurrencySafety::test_get_dependency_async \
  tests/test_main_comprehensive.py::TestGetDependency \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected before repair: the four `'coroutine' object has no attribute 'factory'` failures or the current equivalent.

- [ ] **Step 3: Add a focused contract regression test**

Use the installed API to write a regression in the direct dependency test file. The test must assert the actual contract, not a generic mock behavior:

```python
def test_resolver_candidate_is_consumed_without_coroutine_leak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    candidate = MagicMock()
    candidate.factory = object()
    resolver = MagicMock()
    resolver.resolve.return_value = candidate
    monkeypatch.setattr(_resolver, "resolve", resolver.resolve)
    result = _get_dependency_sync("example", "key")
    assert result is candidate.factory
```

Adapt the exact function name and import from the current file after reading it; do not add an unused test helper or duplicate an existing test.

- [ ] **Step 4: Implement the minimal contract correction**

Use the evidence from Steps 1–3:

- If the installed resolver is synchronous and the production code already consumes a `Candidate`, replace stale `AsyncMock`/coroutine-shaped tests with a synchronous resolver mock. Do not alter production code merely to satisfy an incorrect test mock.
- If the production code is called from a genuinely async context and `Resolver.resolve` is asynchronous, make the bridge explicitly await the coroutine and add a sync helper only if an existing public sync API requires it. The implementation must not silently discard a coroutine or pass it where a value is required.
- Keep the existing return type and public names unchanged unless the test proves a stale API.
- Do not edit the shared files from any other task.

- [ ] **Step 5: Run the resolver-focused tests**

```bash
.venv/bin/pytest \
  tests/test_initializers_comprehensive.py \
  tests/test_main_comprehensive.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected: all targeted dependency-resolution, registration, and concurrency tests pass; no unawaited coroutine warning is emitted by the changed path.

- [ ] **Step 6: Commit the resolver domain**

```bash
git add fastblocks/initializers.py fastblocks/main.py \
  tests/test_initializers_comprehensive.py tests/test_main_comprehensive.py
git commit -m "fix(fastblocks): align dependency resolver contract"
```

If the production files are unchanged, the commit may contain only the direct test and any required contract documentation.

---

### Task 3: Repair validation/sanitizer wiring

**Files:**
- Modify: `fastblocks/_validation_integration.py`
- Test: `tests/test_validation_integration.py`

**Interfaces:**
- Consumes: The singleton initialization behavior expected by the validation tests.
- Produces: An initialized validation/sanitizer instance whose instance-level state is visible to `__init__` and reused by subsequent calls.

- [ ] **Step 1: Run the security validation failures in isolation**

```bash
.venv/bin/pytest tests/test_validation_integration.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected before repair: the sanitizer-related XSS and integration failures. Record the exact failing test IDs.

- [ ] **Step 2: Inspect the singleton declaration and initializer**

Confirm the failing class declares `_initialized` or equivalent state as `ClassVar` while `__init__` assigns it per instance. Preserve the existing class API.

- [ ] **Step 3: Write a focused singleton regression test**

Add or adjust a test that calls the validation integration twice and asserts the second call uses initialized sanitizer state. The test must fail before the production change and must exercise the public validation path, not private attributes only.

- [ ] **Step 4: Make the minimal wiring correction**

Remove the class-level `ClassVar` markers from instance state that is assigned and checked in `__init__`. Keep the `hasattr` guard and initialization ordering intact. Do not add a second sanitizer, change sanitizer algorithms, or weaken payload assertions.

- [ ] **Step 5: Run the validation tests**

```bash
.venv/bin/pytest tests/test_validation_integration.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected: all XSS, form, API, and validation-decorator tests pass.

- [ ] **Step 6: Commit the validation domain**

```bash
git add fastblocks/_validation_integration.py tests/test_validation_integration.py
git commit -m "fix(fastblocks): initialize validation sanitizer state"
```

---

### Task 4: Repair HTMX async fallback and correlated caching behavior

**Files:**
- Modify: `fastblocks/htmx.py` and only the caching/runtime file proven by the targeted test
- Test: `tests/test_htmx.py` and the exact affected caching test file

**Interfaces:**
- Consumes: The existing `_run_publish_event` coroutine and the documented async/sync boundary in FastBlocks `CLAUDE.md`.
- Produces: Every fallback either awaits the coroutine on a safe loop or explicitly raises/uses a native async path; no coroutine is silently lost.

- [ ] **Step 1: Run the HTMX and caching tests**

```bash
.venv/bin/pytest tests/test_htmx.py tests/test_caching.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Record every `RuntimeWarning` reporting an unawaited coroutine and the exact test ID. Do not modify caching until a failure demonstrates the same boundary.

- [ ] **Step 2: Add a regression for fallback coroutine completion**

Add a focused test around the three existing HTMX decorator paths (`htmx_trigger`, `htmx_redirect`, and `htmx_refresh`) that asserts the publish event is delivered and no coroutine is left unawaited. Preserve existing event payloads and error behavior.

- [ ] **Step 3: Implement the safe async boundary**

Use the repository-documented `_run_async_safely`/`run_async_native` pattern. The sync fallback must execute the coroutine to completion and close its event loop; an async caller must not run a blocking loop. If the current decorators are sync-only, use a helper with the following contract:

```python
import asyncio
from collections.abc import Coroutine
from concurrent.futures import ThreadPoolExecutor
from typing import TypeVar

T = TypeVar("T")


def _run_async_safely(coro: Coroutine[object, object, T]) -> T:
    """Run an awaitable from a synchronous fallback without leaking its loop."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        with ThreadPoolExecutor(max_workers=1) as executor:
            return executor.submit(asyncio.run, coro).result()
    raise RuntimeError("use the native async path inside an active event loop")
```

Define `_run_async_safely` in `fastblocks/htmx.py` unless an existing project helper with the same contract is found; do not create a new helper file for this recovery. Add focused coverage for sync fallback and “already in an event loop” behavior. Do not add broad thread-pool or loop refactors.

- [ ] **Step 4: Re-run HTMX and caching tests**

```bash
.venv/bin/pytest tests/test_htmx.py tests/test_caching.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected: no `RuntimeWarning` from the changed HTMX paths and no regression in caching.

- [ ] **Step 5: Commit the async-runtime domain**

```bash
git add fastblocks/htmx.py tests/test_htmx.py
git commit -m "fix(fastblocks): complete async htmx fallbacks"
```

If Step 1 proves a production caching defect, make a separate follow-up commit for `fastblocks/caching.py` and `tests/test_caching.py`; do not include unrelated WIP changes in that commit.

---

### Task 5: Align the Jinja ChoiceLoader call contract

**Files:**
- Modify: `fastblocks/adapters/templates/jinja2.py`
- Test: `tests/adapters/templates/test_jinja2.py`

**Interfaces:**
- Consumes: The Jinja loader `get_source_async` contract and the existing `ChoiceLoader` fallback tests.
- Produces: A loader call that passes the documented template argument and handles `TemplateNotFound` as the existing API requires.

- [ ] **Step 1: Run the two failing ChoiceLoader tests**

```bash
.venv/bin/pytest \
  tests/adapters/templates/test_jinja2.py::test_choice_loader_fallback \
  tests/adapters/templates/test_jinja2.py::test_choice_loader_template_not_found \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected before repair: argument-shape or template-not-found assertion failures.

- [ ] **Step 2: Write a focused loader contract test**

Assert the actual arguments passed to a child loader and assert that a missing child falls through to the next child. Do not test private implementation details beyond the loader call required by the existing contract.

- [ ] **Step 3: Apply the minimal loader correction**

Prefer the single-argument contract reported by the current test intent:

```python
source = loader.get_source_async(str(template))
```

Retain the existing fallback and exception handling. Update child mock loaders only if the current test proves they reject the single-argument call; do not alter all loader implementations speculatively.

- [ ] **Step 4: Run the template loader tests**

```bash
.venv/bin/pytest tests/adapters/templates/test_jinja2.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected: all loader and rendering tests pass without changing unrelated Jinja behavior.

- [ ] **Step 5: Commit the template-loader domain**

```bash
git add fastblocks/adapters/templates/jinja2.py tests/adapters/templates/test_jinja2.py
git commit -m "fix(fastblocks): honor ChoiceLoader source contract"
```

---

### Task 6: Migrate CLI and validation test expectations

**Files:**
- Modify: `tests/test_cli_comprehensive.py`
- Modify: `tests/test_validation_integration.py` only for CLI-facing fixture changes after the production sanitizer is integrated
- Test: both files

**Interfaces:**
- Consumes: The resolver contract from Task 2 and sanitizer behavior from Task 3.
- Produces: CLI tests that mock the canonical async/sync resolver surface and retain output/adapter assertions.

- [ ] **Step 1: Run the CLI file and capture the 16 failures**

```bash
.venv/bin/pytest tests/test_cli_comprehensive.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Record each failure as adapter-not-found, message-shape drift, dataclass/config error, `hx-get` output error, syntax error, or not-available branch.

- [ ] **Step 2: Add focused resolver/CLI regression tests**

For each unique CLI setup path, add a test that patches the canonical resolver surface and asserts the command succeeds. Use the installed Oneiric API from Task 2; prefer patching the async helper if the CLI path is async, otherwise patch the synchronous resolver return with a real `Candidate(factory=adapter)` shape.

- [ ] **Step 3: Update stale mocks without weakening output assertions**

Replace only obsolete mock names and coroutine-shaped values. Preserve assertions about:

- component names,
- adapter-not-found diagnostics,
- HTMY output,
- `hx-get` attributes,
- syntax errors,
- unavailable dependency diagnostics,
- list/info/scaffold/validate output.

Do not simply change “not found” to a string that makes the assertion pass.

- [ ] **Step 4: Run both CLI and validation files**

```bash
.venv/bin/pytest tests/test_cli_comprehensive.py tests/test_validation_integration.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected: all CLI and validation integration tests pass; no new warnings are introduced.

- [ ] **Step 5: Commit the CLI-test domain**

```bash
git add tests/test_cli_comprehensive.py tests/test_validation_integration.py
git commit -m "test(fastblocks): align CLI resolver and validation fixtures"
```

---

### Task 7: Migrate template filter dependency mocks

**Files:**
- Modify: `tests/adapters/templates/test_filters_comprehensive.py`
- Test: the complete filter file

**Interfaces:**
- Consumes: The canonical resolver surface from Task 2.
- Produces: Filter tests that verify rendered output against a real dependency value, not a leaked `MagicMock`.

- [ ] **Step 1: Run the filter file and classify failures**

```bash
.venv/bin/pytest tests/adapters/templates/test_filters_comprehensive.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected before repair: 20 failures, primarily `MagicMock` returned where a string was expected.

- [ ] **Step 2: Add focused output regressions for adapter-backed filters**

For `test_imgtag_with_adapter` and each adapter-backed filter, assert the exact expected HTML/attribute output while mocking only the dependency lookup boundary.

- [ ] **Step 3: Replace leaked resolver mocks**

Use the canonical resolver contract. If the helper returns a `Candidate`, set `Candidate.factory` to the expected string; if the helper is async, use an `AsyncMock` whose awaited result is a real string. Do not patch a method at the wrong module path.

- [ ] **Step 4: Run the filter file**

```bash
.venv/bin/pytest tests/adapters/templates/test_filters_comprehensive.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected: sync filters, async filters, registration, and integration tests pass.

- [ ] **Step 5: Commit the filter-test domain**

```bash
git add tests/adapters/templates/test_filters_comprehensive.py
git commit -m "test(fastblocks): return real values from template filters"
```

---

### Task 8: Make security tests independent of implicit event-loop state

**Files:**
- Modify: `tests/security/test_input_validation.py`
- Test: the complete security test file

**Interfaces:**
- Consumes: The async validation APIs exercised by the test file.
- Produces: Tests with explicit event-loop ownership and deterministic pass/fail behavior in full-suite order.

- [ ] **Step 1: Reproduce the five missing-loop failures in full suite order**

```bash
.venv/bin/pytest tests/security/test_input_validation.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Record the five path-traversal form-input cases that fail only when the loop is absent.

- [ ] **Step 2: Add one lifecycle regression test**

Add a test that calls the same form validation through an explicit async runner and verifies the traversal payload is rejected. This must fail before the test migration if the current implicit-loop code is used.

- [ ] **Step 3: Convert only the affected tests to explicit async lifecycle**

Use one of these exact patterns, selected from the existing test fixture shape:

```python
result = asyncio.run(_validate_form(payload))
```

or:

```python
@pytest.mark.asyncio
async def test_path_traversal_generates_error_in_form_input(payload: str) -> None:
    result = await _validate_form(payload)
```

Do not add a new global event-loop fixture and do not weaken the payload assertions.

- [ ] **Step 4: Run the security file in isolation and with a preceding async test**

```bash
.venv/bin/pytest tests/security/test_input_validation.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Then run the security file together with the validation integration file:

```bash
.venv/bin/pytest \
  tests/security/test_input_validation.py tests/test_validation_integration.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected: both runs pass, with no missing-loop or unawaited-coroutine warnings.

- [ ] **Step 5: Commit the security-test domain**

```bash
git add tests/security/test_input_validation.py
git commit -m "test(fastblocks): isolate security async lifecycle"
```

---

### Task 9: Repair proven application, initializer, and adapter expectations

**Files:**
- Modify: only the direct file proven by each exact failure:
  - `tests/test_initializers_comprehensive.py` and `tests/test_main_comprehensive.py` for dependency expectations
  - `tests/test_initializers_comprehensive.py` for the removed `register_pkg` expectation and tuple length
  - `tests/adapters/admin/test_sqladmin_comprehensive.py` for the model-count expectation
  - `fastblocks/initializers.py` only through the Task 2 resolver owner
- Test: the exact affected test file or node

**Interfaces:**
- Consumes: The central resolver contract from Task 2.
- Produces: Registration, dependency, and adapter behavior that matches the current public API without deleting meaningful coverage.

- [ ] **Step 1: Run the remaining application/adapter failures individually**

```bash
.venv/bin/pytest \
  tests/test_initializers_comprehensive.py::TestLoadAcbModules \
  tests/test_main_comprehensive.py::TestGetApp \
  tests/test_main_comprehensive.py::TestHandleRegistration \
  tests/test_main_comprehensive.py::TestGetDependency \
  tests/adapters/admin/test_sqladmin_comprehensive.py::test_admin_init_with_admin_models \
  tests/test_integration_contracts.py::test_sanitizer_failure_rejects_input \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Record each exact result before editing.

- [ ] **Step 2: Add or adjust focused registration regressions**

For each failure, assert the current public registration result and preserve a test for the missing dependency/error branch. Do not add a broad fixture that makes all tests pass without exercising the real registration function.

- [ ] **Step 3: Correct only proven stale expectations or production defects**

Handle these exact categories:

- If `register_pkg` no longer exists in `fastblocks.initializers`, update the test to assert the supported registration API; do not restore a dead public symbol.
- If the tuple count is 6 because a registration was removed, update the test to assert the six current registrations and the contract that the tuple is non-empty and unique.
- If SQLAdmin models are registered under the current supported configuration, fix the test to inspect the actual registered model set; do not force a count of seven.
- If sanitizer failure does not raise because the sanitizer intentionally records a warning, assert the documented current behavior; do not remove the failure-path test.
- If a registration genuinely fails, fix the production path and keep the error-path assertion.

- [ ] **Step 4: Run the application and adapter subsets**

```bash
.venv/bin/pytest \
  tests/test_initializers_comprehensive.py \
  tests/test_main_comprehensive.py \
  tests/test_integration_contracts.py \
  tests/adapters/admin/test_sqladmin_comprehensive.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected: all registration, dependency, sanitizer-contract, and admin tests pass.

- [ ] **Step 5: Commit the application/adapter domain**

```bash
git add tests/test_initializers_comprehensive.py tests/test_main_comprehensive.py tests/test_integration_contracts.py tests/adapters/admin/test_sqladmin_comprehensive.py
git commit -m "fix(fastblocks): align application and adapter contracts"
```

Use only the files listed in the Step 3 diagnosis; if only tests changed, the commit message is `test(fastblocks): align application and adapter contracts` instead.

---

### Task 10: Verify rendering collection and admin behavior, then resolve proven collection issues

**Files:**
- Modify: `tests/adapters/templates/test_rendering_jinja2.py` and/or `fastblocks/adapters/templates/_advanced_manager.py` only if collection fails
- Modify: `tests/adapters/admin/test_sqladmin_comprehensive.py` only if Task 9 did not own it
- Test: exact collection and affected test nodes

**Interfaces:**
- Consumes: The collection baseline from Task 1.
- Produces: A test suite that can collect all intended modules and runs the renderer/admin contract.

- [ ] **Step 1: Run collection-only for the rendering and admin modules**

```bash
.venv/bin/pytest \
  --collect-only -q \
  tests/adapters/templates/test_rendering_jinja2.py \
  tests/adapters/admin/test_sqladmin_comprehensive.py \
  --no-cov -p no:cacheprovider -o addopts=''
```

If collection passes, do not edit rendering files. If it fails, record the exact import path and trace the import target.

- [ ] **Step 2: Add a focused collection regression if an import defect is real**

Import the failing symbol in a standalone test and assert that the public module exposes it. If the import is stale, remove only the stale import; if a production symbol is missing, restore it with a minimal test covering its intended behavior.

- [ ] **Step 3: Run the rendering/admin files**

```bash
.venv/bin/pytest \
  tests/adapters/templates/test_rendering_jinja2.py \
  tests/adapters/admin/test_sqladmin_comprehensive.py \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Expected: collection succeeds and all renderer/admin tests pass.

- [ ] **Step 4: Commit the rendering/admin domain**

```bash
If collection fails, modify only the exact files diagnosed in Step 1, then run:
git add tests/adapters/templates/test_rendering_jinja2.py fastblocks/adapters/templates/_advanced_manager.py tests/adapters/admin/test_sqladmin_comprehensive.py
git commit -m "test(fastblocks): verify renderer and admin collection"
```

---

### Task 11: Run Wave 1/2 integration gates and commit any residual fixes

**Files:**
- Modify: only files owned by a previously failed domain; no new structural refactor files
- Test: the full non-websocket suite and the separately supported websocket subset

**Interfaces:**
- Consumes: All domain commits from Tasks 2–10.
- Produces: Integrated recovery branch with a measured failure delta.

- [ ] **Step 1: Confirm the integrated worktree status and commit graph**

```bash
git status --short
git log --oneline --decorate -20
```

Expected: 91 modified WIP entries and 3 untracked entries remain accounted for; the recovery spec, baseline manifest, and domain commits are present; no agent commit contains files outside its ownership set.

- [ ] **Step 2: Run the full non-websocket suite**

```bash
.venv/bin/pytest tests/ --ignore=tests/websocket \
  --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Record collected, passed, failed, skipped, xpassed, warning, duration, and exit-code values. Any remaining failed test must be assigned to one domain before editing.

- [ ] **Step 3: Run the separately supported websocket subset**

Use the repository's documented marker/skip behavior; do not enable websocket services or install packages merely to force a green run. Record the exact command and result.

- [ ] **Step 4: Run a clean-HEAD comparison without copying WIP**

Create a separate clean worktree at local HEAD using the existing repo tooling. Run the same read-only non-websocket command there and record its counts. Do not merge clean-HEAD results into the recovery branch automatically.

- [ ] **Step 5: Review the final failure delta**

For every remaining failure, classify it as production defect, stale expectation, environment blocker, or needs evidence. Do not mark the task complete if an unexpected failure remains.

- [ ] **Step 6: Commit only proven residual fixes**

Use a follow-up commit per domain. Never amend a previous commit, reset the worktree, or merge clean-HEAD changes into the dirty-WIP repair.

---

### Task 12: Final verification, review, and handoff

**Files:**
- Create: `docs/superpowers/plans/2026-08-19-fastblocks-test-recovery-results.md`
- Read: all changed files, the design spec, baseline manifest, and domain reports

**Interfaces:**
- Consumes: Integrated commits and final test outputs from Task 11.
- Produces: Reproducible handoff with exact commands, counts, remaining blockers, and commit SHAs.

- [ ] **Step 1: Re-read the final diff and check WIP preservation**

```bash
git diff --stat
git status --short
git diff --check
```

Confirm the 91 modified tracked files and 3 untracked files from the original checkout are still represented, with no generated artifacts or unrelated refactors.

- [ ] **Step 2: Re-run the exact targeted gates**

Run the focused commands from Tasks 2–10 for every committed domain. A green final suite without these targeted gates is insufficient.

- [ ] **Step 3: Run the complete read-only suite one final time**

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
```

Record the final counts and exit code. Compare warning count to the baseline and call out warning changes.

- [ ] **Step 4: Write the results handoff**

Document:

- recovery worktree path and branch;
- original HEAD and current branch HEAD;
- every domain commit SHA;
- targeted commands and pass/fail counts;
- full-suite final counts and exit code;
- clean-HEAD comparison;
- WIP preservation manifest;
- remaining blockers with exact test IDs;
- deferred structural follow-up.

- [ ] **Step 5: Commit the results handoff**

```bash
git add docs/superpowers/plans/2026-08-19-fastblocks-test-recovery-results.md
git commit -m "docs(fastblocks): record test recovery results"
```

- [ ] **Step 6: Request final code review**

Invoke the project’s code-review workflow on the recovery diff. Reviewers must be read-only; they may run tests but must not edit, stash, reset, commit, or alter the WIP. Require verification of resolver ownership, test weakening, WIP preservation, and final counts before declaring completion.

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-19-fastblocks-test-recovery.md` in the isolated FastBlocks recovery worktree.

Two execution options:

1. **Subagent-Driven (recommended):** dispatch a fresh agent per task, review between tasks, and maintain the domain ledger. This directly matches the user’s fan-out request.
2. **Inline Execution:** execute tasks in this session with checkpoints, using the same ownership and verification gates.

Which approach should be used for implementation?

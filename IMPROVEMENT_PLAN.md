# FastBlocks Improvement Plan

**Created**: 2025-11-18
**Target Completion**: 12 weeks
**Current Health Score**: 58/100
**Target Health Score**: 85/100

---

## Progress Overview

### Phase Completion
- [ ] **Phase 1**: Immediate Actions (Week 1-2) - 0/6 tasks
- [ ] **Phase 2**: Type System Recovery (Week 3-4) - 0/4 tasks
- [ ] **Phase 3**: Coverage & Quality (Week 5-8) - 0/5 tasks
- [ ] **Phase 4**: Polish & Optimization (Week 9-12) - 0/4 tasks

### Metrics Tracking

| Metric | Baseline | Current | Target | Status |
|--------|----------|---------|--------|--------|
| Pyright Errors | 501 | 501 | <50 | 🔴 |
| Test Coverage | 15.52% | 15.52% | 40% | 🔴 |
| Test Pass Rate | 72% | 72% | 95% | 🔴 |
| Type Ignores | 222 | 222 | <111 | 🔴 |
| Overall Health | 58/100 | 58/100 | 85/100 | 🔴 |

---

## Phase 1: Immediate Actions (Week 1-2)

**Goal**: Fix critical blockers and quick wins
**Priority**: CRITICAL
**Estimated Time**: 2 weeks

### Task 1.1: Remove Unreachable Dead Code
**Priority**: HIGH | **Effort**: 2 hours | **Status**: ⬜ Not Started

- [ ] Fix `fastblocks/applications.py:189-190` - Remove unreachable code after early return
- [ ] Fix `fastblocks/caching.py:106` - Remove unreachable code after return
- [ ] Fix `fastblocks/caching.py:128` - Remove unreachable code after return
- [ ] Fix `fastblocks/adapters/fonts/squirrel.py:99` - Remove unreachable code after return
- [ ] Fix `fastblocks/actions/gather/components.py:326` - Remove unreachable code after return
- [ ] Run vulture to verify all dead code removed
- [ ] Run tests to ensure no breakage: `uv run pytest -v`

**Success Criteria**: Vulture reports 0 unreachable code instances

---

### Task 1.2: Remove Unused Imports and Variables
**Priority**: MEDIUM | **Effort**: 1 hour | **Status**: ⬜ Not Started

- [ ] Remove `fastblocks/_events_integration.py:22` - Unused import `event_handler`
- [ ] Remove `fastblocks/_health_integration.py:20` - Unused import `HealthCheckType`
- [ ] Remove `fastblocks/actions/gather/components.py:348` - Unused variable `include_templates`
- [ ] Remove `fastblocks/adapters/templates/_block_renderer.py:513` - Unused variable `placeholder_content`
- [ ] Remove `fastblocks/adapters/templates/htmy.py:593` - Unused variable `inherit_context`
- [ ] Remove `fastblocks/cli.py:601` - Unused variable `format_output`
- [ ] Run ruff to verify: `uv run ruff check fastblocks`

**Success Criteria**: No unused import/variable warnings from ruff or vulture

---

### Task 1.3: Fix 4 Legacy ACB Injection Patterns
**Priority**: CRITICAL | **Effort**: 3 hours | **Status**: ⬜ Not Started

- [ ] Fix `fastblocks/_health_integration.py:42` - Change `config: Inject[t.Any] = depends()` to `config: Inject[t.Any]`
- [ ] Fix `fastblocks/_events_integration.py:123` - Change `cache: Inject[t.Any] = depends()` to `cache: Inject[t.Any]`
- [ ] Fix `fastblocks/_events_integration.py:342` - Change `config: Inject[t.Any] = depends()` to `config: Inject[t.Any]`
- [ ] Fix `fastblocks/adapters/admin/sqladmin.py:35` - Change `templates: t.Any = depends()` to `templates: Inject[Templates]`
- [ ] Run tests for affected modules: `uv run pytest tests/ -k "health or events or admin" -v`
- [ ] Verify ACB compliance: Check no `= depends()` with `Inject[Type]`

**Success Criteria**: All 4 files use modern ACB 0.25.1+ pattern, tests pass

---

### Task 1.4: Fix Async Sleep Loop in CLI
**Priority**: MEDIUM | **Effort**: 1 hour | **Status**: ⬜ Not Started

- [ ] Review `fastblocks/cli.py:907-908` - Current inefficient sleep loop
- [ ] Implement event-based approach using `asyncio.Event()`
- [ ] Replace `while True: await asyncio.sleep(1)` with `await stop_event.wait()`
- [ ] Add proper shutdown signal handling
- [ ] Test CLI startup and shutdown: `python -m fastblocks --help`
- [ ] Verify no CPU burning during idle

**Success Criteria**: CLI uses event-based shutdown, no busy-wait loop

---

### Task 1.5: Fix Fire-and-Forget Task Registration
**Priority**: CRITICAL | **Effort**: 2 hours | **Status**: ⬜ Not Started

- [ ] Review `fastblocks/initializers.py:163-167` - Current race condition
- [ ] Replace individual `loop.create_task()` calls with `asyncio.gather()`
- [ ] Add proper error handling with try/except
- [ ] Add logging for successful/failed registrations
- [ ] Test startup sequence: `uv run pytest tests/ -k "initializer" -v`
- [ ] Verify all integrations register before app starts

**Code Change**:
```python
# Replace:
loop.create_task(register_fastblocks_event_handlers())
loop.create_task(register_fastblocks_health_checks())
loop.create_task(register_fastblocks_validation())
loop.create_task(register_fastblocks_workflows())

# With:
try:
    await asyncio.gather(
        register_fastblocks_event_handlers(),
        register_fastblocks_health_checks(),
        register_fastblocks_validation(),
        register_fastblocks_workflows(),
    )
    if self.logger:
        self.logger.info("All FastBlocks integrations registered")
except Exception as e:
    if self.logger:
        self.logger.warning(f"Some integrations failed: {e}")
```

**Success Criteria**: No race conditions, proper error handling, integrations complete before startup

---

### Task 1.6: Fix Critical Test Failures
**Priority**: CRITICAL | **Effort**: 8 hours | **Status**: ⬜ Not Started

- [ ] Run tests and capture all failures: `uv run pytest --tb=short --maxfail=5 > test_failures.txt`
- [ ] Fix `tests/actions/gather/test_components.py::test_gather_components_no_adapter`
  - [ ] Review assertion: `assert result.success is False`
  - [ ] Fix expected vs actual behavior
- [ ] Address performance test errors (10 errors):
  - [ ] `test_resource_pool_performance`
  - [ ] `test_stream_processing_performance`
  - [ ] `test_performance_monitoring_accuracy`
  - [ ] `test_optimization_recommendations`
- [ ] Fix highest-impact test failures (focus on core functionality)
- [ ] Target: Reduce failures from 226 to <50 (80%+ pass rate)
- [ ] Run full suite: `uv run pytest -v`

**Success Criteria**:
- Test pass rate >80% (680+ passing)
- 0 critical functionality test failures
- Performance tests either fixed or skipped with issue tickets

---

## Phase 2: Type System Recovery (Week 3-4)

**Goal**: Fix type system to enable proper IDE support and catch real bugs
**Priority**: HIGH
**Estimated Time**: 2 weeks

### Task 2.1: Audit and Document depends.get() Behavior
**Priority**: CRITICAL | **Effort**: 4 hours | **Status**: ⬜ Not Started

- [ ] Create test file to determine when `depends.get()` returns coroutine vs instance
- [ ] Document findings in `docs/ACB_DEPENDS_PATTERNS.md`
- [ ] Test both string-based: `depends.get("config")`
- [ ] Test type-based: `depends.get(Config)`
- [ ] Determine async context requirements
- [ ] Create helper function for consistent usage
- [ ] Add type stubs if needed

**Success Criteria**: Clear documentation of when to await `depends.get()`

---

### Task 2.2: Fix Coroutine Access Pattern Issues (Priority: Integration Files)
**Priority**: CRITICAL | **Effort**: 12 hours | **Status**: ⬜ Not Started

**Files to Fix** (~150 errors total):

- [ ] `fastblocks/_health_integration.py` (30+ errors)
  - [ ] Lines 104, 109, 113, 125, 205, 271, 317, 325, 331, 368, 372-375, 400, 413
  - [ ] Pattern: Add `await` before `depends.get()` calls
  - [ ] Pattern: Access attributes after awaiting
- [ ] `fastblocks/_events_integration.py` (15+ errors)
  - [ ] Lines 147, 153-154, 187, 193-194, 254-255, 261-262, 297, 303-304, 375, 415, 447, 481, 549-550
  - [ ] Fix parameter calls and coroutine access
- [ ] `fastblocks/_validation_integration.py` (10+ errors)
  - [ ] Lines 724-725, 773, 836-837, 948-949
  - [ ] Fix coroutine comparisons and attribute access
- [ ] `fastblocks/_workflows_integration.py` (15+ errors)
  - [ ] Lines 75-76, 130-131, 142-143, 154-155, 165, 234, 246, 258-259, 269, 338, 349-350, 362-363, 373, 424, 429, 475, 477
  - [ ] Fix parameter mismatches and coroutine access
- [ ] Run tests after each file: `uv run pytest tests/ -v`
- [ ] Run pyright to track progress: `uv run pyright fastblocks/_*_integration.py`

**Success Criteria**: Integration files have 0 coroutine access errors

---

### Task 2.3: Fix Coroutine Access Pattern Issues (Priority: Actions)
**Priority**: HIGH | **Effort**: 10 hours | **Status**: ⬜ Not Started

**Files to Fix**:

- [ ] `fastblocks/actions/gather/middleware.py` (2 errors)
- [ ] `fastblocks/actions/gather/routes.py` (2 errors)
- [ ] `fastblocks/actions/gather/templates.py` (5 errors)
- [ ] `fastblocks/actions/gather/application.py` (2 errors)
- [ ] `fastblocks/actions/query/parser.py` (6 errors)
- [ ] `fastblocks/actions/sync/cache.py` (10 errors)
- [ ] `fastblocks/actions/sync/settings.py` (1 error)
- [ ] `fastblocks/actions/sync/static.py` (3 errors)
- [ ] `fastblocks/actions/sync/templates.py` (5 errors)
- [ ] Run targeted tests: `uv run pytest tests/actions/ -v`
- [ ] Verify pyright: `uv run pyright fastblocks/actions/`

**Success Criteria**: Actions module has 0 coroutine access errors

---

### Task 2.4: Fix Coroutine Access Pattern Issues (Priority: Adapters)
**Priority**: HIGH | **Effort**: 8 hours | **Status**: ⬜ Not Started

**Files to Fix**:

- [ ] `fastblocks/middleware.py` (15 errors, lines 401-412)
- [ ] `fastblocks/adapters/admin/sqladmin.py` (1 error, line 51)
- [ ] `fastblocks/adapters/app/default.py` (10 errors)
- [ ] `fastblocks/adapters/auth/_base.py` (2 errors)
- [ ] `fastblocks/adapters/auth/basic.py` (4 errors)
- [ ] `fastblocks/adapters/icons/*.py` (50+ errors - type stubs needed)
  - [ ] Create proper type stubs for icon adapters
  - [ ] Fix undefined variable errors (MaterialIconsAdapter, PhosphorAdapter, etc.)
- [ ] Run adapter tests: `uv run pytest tests/adapters/ -v`
- [ ] Verify pyright: `uv run pyright fastblocks/adapters/`

**Success Criteria**: Adapter modules have <20 coroutine access errors (excluding icon stubs)

---

## Phase 3: Coverage & Quality (Week 5-8)

**Goal**: Increase test coverage and fix remaining test failures
**Priority**: MEDIUM
**Estimated Time**: 4 weeks

### Task 3.1: Increase CLI Test Coverage (0% → 30%)
**Priority**: HIGH | **Effort**: 12 hours | **Status**: ⬜ Not Started

- [ ] Create `tests/test_cli.py` if not exists
- [ ] Test CLI commands:
  - [ ] `fastblocks create` - Project creation
  - [ ] `fastblocks version` - Version display
  - [ ] `fastblocks components` - Component listing
  - [ ] `fastblocks dev` - Dev server startup (mock)
  - [ ] `fastblocks run` - Production server (mock)
- [ ] Mock server startup to avoid actual server running
- [ ] Test error conditions
- [ ] Run coverage: `uv run pytest tests/test_cli.py --cov=fastblocks/cli.py --cov-report=term`
- [ ] Target: 30%+ coverage

**Success Criteria**: CLI module has >30% coverage, critical paths tested

---

### Task 3.2: Increase MCP Test Coverage (0-22% → 30%)
**Priority**: MEDIUM | **Effort**: 16 hours | **Status**: ⬜ Not Started

**Files to Test**:

- [ ] `fastblocks/mcp/tools.py` (0% → 30%)
  - [ ] Test template creation
  - [ ] Test component scaffolding
  - [ ] Test adapter discovery
- [ ] `fastblocks/mcp/cli.py` (0% → 30%)
  - [ ] Test MCP CLI commands
- [ ] `fastblocks/mcp/config_*.py` (0% → 20%)
  - [ ] Test configuration management
  - [ ] Test health checks
  - [ ] Test migrations
- [ ] `fastblocks/mcp/env_manager.py` (0% → 25%)
  - [ ] Test environment management
- [ ] Run coverage: `uv run pytest tests/mcp/ --cov=fastblocks/mcp/ --cov-report=term`

**Success Criteria**: MCP module average coverage >30%

---

### Task 3.3: Increase Actions Test Coverage (20-50% → 40%)
**Priority**: MEDIUM | **Effort**: 12 hours | **Status**: ⬜ Not Started

- [ ] `fastblocks/actions/gather/` (current ~30% → 40%)
  - [ ] Add tests for edge cases in component gathering
  - [ ] Test error conditions
- [ ] `fastblocks/actions/sync/` (current ~25% → 40%)
  - [ ] Test template synchronization
  - [ ] Test cache synchronization
  - [ ] Test static file sync
- [ ] `fastblocks/actions/query/` (current ~20% → 40%)
  - [ ] Test query parser with various models
  - [ ] Test query parameter parsing
- [ ] Run coverage: `uv run pytest tests/actions/ --cov=fastblocks/actions/ --cov-report=term`

**Success Criteria**: Actions module average coverage >40%

---

### Task 3.4: Fix Remaining Test Failures
**Priority**: HIGH | **Effort**: 16 hours | **Status**: ⬜ Not Started

- [ ] Run full test suite and categorize remaining failures
- [ ] Fix functional test failures (business logic)
- [ ] Fix integration test failures
- [ ] Address or skip flaky tests (document why)
- [ ] Fix or document expected failures
- [ ] Target: <5% failure rate (40 or fewer failures)
- [ ] Run: `uv run pytest -v --maxfail=100`

**Success Criteria**: Test pass rate >95% (800+ passing out of 851)

---

### Task 3.5: Overall Coverage to 31%+ (Minimum Required)
**Priority**: CRITICAL | **Effort**: 20 hours | **Status**: ⬜ Not Started

**Current**: 15.52% | **Target**: 31%+ | **Stretch**: 40%

**Priority Modules** (by criticality):

1. [ ] `fastblocks/middleware.py` (37% → 50%)
2. [ ] `fastblocks/caching.py` (27% → 40%)
3. [ ] `fastblocks/htmx.py` (32% → 50%)
4. [ ] `fastblocks/exceptions.py` (57% → 70%)
5. [ ] `fastblocks/initializers.py` (20% → 40%)
6. [ ] `fastblocks/applications.py` (31% → 50%)
7. [ ] Adapter modules (19-40% → 35%+)

**Strategy**:
- [ ] Focus on critical paths first
- [ ] Test error conditions
- [ ] Test async flows
- [ ] Mock external dependencies
- [ ] Run coverage check: `uv run pytest --cov=fastblocks --cov-report=term --cov-report=html`
- [ ] Review HTML report for gaps: `open htmlcov/index.html`

**Success Criteria**: Overall coverage >31%, stretch goal 40%

---

## Phase 4: Polish & Optimization (Week 9-12)

**Goal**: Achieve production-ready quality
**Priority**: LOW-MEDIUM
**Estimated Time**: 4 weeks

### Task 4.1: Type System Cleanup - Target <50 Errors
**Priority**: MEDIUM | **Effort**: 20 hours | **Status**: ⬜ Not Started

- [ ] Review all remaining pyright errors: `uv run pyright fastblocks > pyright_errors.txt`
- [ ] Categorize errors by type
- [ ] Fix parameter mismatch errors (highest priority)
- [ ] Add proper type stubs for icon adapters
- [ ] Fix undefined variable errors
- [ ] Address constant redefinition warnings
- [ ] Fix unnecessary isinstance/comparison errors
- [ ] Target: <50 total errors
- [ ] Track: Run `uv run pyright fastblocks --stats` regularly

**Success Criteria**: Pyright reports <50 errors, strict mode enabled successfully

---

### Task 4.2: Reduce Type Ignores by 50%
**Priority**: MEDIUM | **Effort**: 16 hours | **Status**: ⬜ Not Started

**Current**: 222 type ignores in 60 files | **Target**: <111 type ignores

- [ ] Audit all `# type: ignore` comments
- [ ] Categorize by reason:
  - [ ] Legitimate (external library issues)
  - [ ] Fixable (our code issues)
  - [ ] Temporary (need investigation)
- [ ] Fix underlying issues instead of suppressing
- [ ] Add explanatory comments to remaining ignores
- [ ] Track progress: `grep -r "# type: ignore" fastblocks --include="*.py" | wc -l`

**Success Criteria**: <111 type ignore comments, all have justification comments

---

### Task 4.3: Documentation Updates
**Priority**: LOW | **Effort**: 8 hours | **Status**: ⬜ Not Started

- [ ] Add `docs/ACB_DEPENDS_PATTERNS.md` with coroutine behavior documentation
- [ ] Update `CLAUDE.md` with new type system guidelines
- [ ] Document MCP integration features
- [ ] Add migration guide for type system changes
- [ ] Update architecture docs for recent changes
- [ ] Add "Lessons Learned" document
- [ ] Update README with new quality metrics

**Success Criteria**: All new patterns documented, migration guides complete

---

### Task 4.4: Security Hardening
**Priority**: MEDIUM | **Effort**: 12 hours | **Status**: ⬜ Not Started

- [ ] Run full Bandit scan without skips: `uv run bandit -r fastblocks -ll`
- [ ] Address any high-severity findings
- [ ] Add detect-secrets to pre-commit hooks
- [ ] Run detect-secrets baseline: `uv run detect-secrets scan > .secrets.baseline`
- [ ] Increase test coverage of security features:
  - [ ] CSRF protection tests
  - [ ] Session management tests
  - [ ] Authentication tests
  - [ ] Input validation tests
- [ ] Target: 80%+ coverage for security modules
- [ ] Document security architecture

**Success Criteria**:
- No high-severity Bandit findings
- Secrets detection in CI
- Security modules >80% coverage

---

## Verification & Validation

### Pre-Commit Checklist
Run before each commit:

```bash
# Code quality
uv run ruff check --fix fastblocks
uv run ruff format fastblocks

# Type checking
uv run pyright fastblocks

# Tests
uv run pytest -v

# Coverage
uv run pytest --cov=fastblocks --cov-report=term

# Dead code
uv run vulture fastblocks --min-confidence 86

# Security
uv run bandit -r fastblocks -ll
```

### Phase Completion Checklist

Before marking a phase complete:

- [ ] All tasks in phase completed
- [ ] Tests passing at target rate
- [ ] Coverage at target percentage
- [ ] Pyright errors reduced per target
- [ ] Documentation updated
- [ ] Changes committed and pushed
- [ ] Metrics table updated in this document

---

## Success Metrics

### Completion Criteria

**Phase 1 Complete When**:
- [ ] 0 unreachable code warnings
- [ ] 4 ACB legacy patterns fixed
- [ ] Test pass rate >80%
- [ ] Critical test failures resolved
- [ ] Async issues fixed

**Phase 2 Complete When**:
- [ ] Integration files have 0 coroutine errors
- [ ] Actions module has 0 coroutine errors
- [ ] Adapters have <20 coroutine errors
- [ ] depends.get() behavior documented

**Phase 3 Complete When**:
- [ ] Overall coverage >31% (required), >40% (stretch)
- [ ] CLI coverage >30%
- [ ] MCP coverage >30%
- [ ] Test pass rate >95%

**Phase 4 Complete When**:
- [ ] Pyright errors <50
- [ ] Type ignores <111
- [ ] Security hardening complete
- [ ] Documentation updated

**Project Complete When**:
- [ ] Overall health score >85/100
- [ ] Test pass rate >95%
- [ ] Coverage >40%
- [ ] Pyright errors <50
- [ ] All critical issues resolved
- [ ] Documentation complete

---

## Risk Management

### Known Risks

1. **Type System Complexity**
   - Risk: Coroutine access issues more widespread than identified
   - Mitigation: Start with integration files, learn patterns, apply broadly
   - Contingency: Consider async helper wrapper if too complex

2. **Test Failures Root Causes**
   - Risk: Failures indicate deeper architectural issues
   - Mitigation: Investigate thoroughly before fixing
   - Contingency: May need to refactor core components

3. **Coverage Target Achievability**
   - Risk: 40% may be difficult given async nature
   - Mitigation: Focus on critical paths, mock aggressively
   - Contingency: Adjust target to 35% if needed

4. **Time Estimates**
   - Risk: Tasks may take longer than estimated
   - Mitigation: Track actuals, adjust plan weekly
   - Contingency: Extend timeline or reduce scope

---

## Notes & Updates

### 2025-11-18 - Plan Created
- Initial comprehensive audit completed
- Baseline metrics established
- 12-week improvement plan created
- 501 pyright errors, 15.52% coverage, 72% test pass rate

### [Add updates as plan progresses]

---

## Quick Reference Commands

```bash
# Run all quality checks
uv run ruff check --fix fastblocks && \
uv run ruff format fastblocks && \
uv run pyright fastblocks && \
uv run pytest --cov=fastblocks --cov-report=term

# Track progress
uv run pyright fastblocks --stats
uv run pytest --cov=fastblocks --cov-report=term | grep "TOTAL"
uv run pytest -v --tb=no | grep -E "passed|failed"
grep -r "# type: ignore" fastblocks --include="*.py" | wc -l
uv run vulture fastblocks --min-confidence 86

# Focus testing
uv run pytest tests/actions/ -v
uv run pytest tests/adapters/ -v
uv run pytest tests/ -k "health or events" -v

# Coverage deep dive
uv run pytest --cov=fastblocks --cov-report=html
open htmlcov/index.html
```

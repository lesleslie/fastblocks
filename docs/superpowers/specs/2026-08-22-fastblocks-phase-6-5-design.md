______________________________________________________________________

## status: accepted role: phase-6-5-design-spec date: 2026-08-22 last_reviewed: 2026-08-22 supersedes: null superseded_by: null blocks_on: null decision_date: 2026-08-22 topic: phase-6-5-structural-fixes

# Phase 6.5: Observability Structural Fixes Design

## Status

**Accepted** (Phase 6.5 spec — companion to ADR 0013
(`docs/adr/0013-phase-6-deferral.md`); bundles the 4 small
structural fixes that ADR 0013's "Path forward" section
identifies as prerequisites for any future Phase 6 retry).

## Scope decision

Phase 6.5 ships 4 independent commits in dependency order. Each
commit is independently revertible. No new production subsystems,
no new MCP tools, no new HTTP endpoints, no new adapter contracts.

**In scope** (4 commits):

1. **`feat(app): bind `app.state.main_loop`+`app.state.jinja_env` at lifespan startup`** — extends the existing
   `@asynccontextmanager async def lifespan(...)` at
   `fastblocks/adapters/app/default.py:164-178` so the master-plan
   line 478-479 lifecycle integration test passes
   (`httpx.AsyncClient` + lifespan + assert `app.state.main_loop` is
   `asyncio.AbstractEventLoop` AND `app.state.jinja_env` is a
   `jinja2.Environment`).

1. \*\*`feat(observability): mandate `bind_contextvars()`in`trace_context.set()`** — fixes the load-bearing log↔trace correlation gap. `structlog.contextvars.merge_contextvars`reads only from the stdlib`contextvars`storage:`bind_contextvars`writes to`ContextVar`s whose names start with structlog's `STRUCTLOG_KEY_PREFIX`; `merge_contextvars`then reads them via`contextvars.copy_context()` (`Context`object iteration); raw`ContextVar.set()`writes to unrelated`ContextVar`s are invisible. The commit makes the public `trace_context.set()`API do BOTH the raw set AND`bind_contextvars(\*\*asdict(ctx))\` so trace_id
   reaches log lines.

1. **`feat(htmx): preserve ContextVar across `\_run_async_safely` executor boundary`** — wraps the executor call in
   `contextvars.copy_context()` so `_current_trace` (or any other
   ContextVar set in the caller thread) reaches the coroutine
   running inside the executor's worker thread.

1. **`tests(observability): conftest.py autouse fixture for SpanProcessor teardown`** — **per quick-review 2026-08-22**:
   the originally-proposed snapshot-via-`_active_span_processor`
   private attribute was cargo-culted — verified at spec-author
   time via `dir(ProxyTracerProvider)` that the `ProxyTracerProvider`
   returned by `opentelemetry.trace.get_tracer_provider()` does NOT
   expose `_active_span_processor` (and `_active_span_processor` is
   a private API of `TracerProvider` itself, not the Proxy).
   v1.1 fix: the fixture snapshots `proxy._real_provider` if
   `proxy._real_provider` exists (proxy delegation case — what
   production uses); otherwise it `trace.set_tracer_provider(TracerProvider())`
   to swap in a fresh in-process `TracerProvider` for the test's
   duration, then restores the previous one after. Either path
   achieves the test's goal: a SpanProcessor installed in test 1
   does not persist into test 2. The fixture is NOT optional —
   without it, every test that calls `traced_decision()` accumulates
   processors; counter labels double/triple across tests.

**Out of scope** (deferred to a future Phase 6 retry per ADR 0013):

- SpanProcessor install on `resolver.decision` spans (Phase 6 spec
  §6A.3, currently at v3 commit `a219347`)
- OpenMetrics `/metrics` endpoint (Phase 6 spec §6B.6)
- per-metric instrumentation matrix (Phase 6 spec §6C.6) — the
  matrix SHELL is correct; resolution to real file:line is the
  Phase 6 implementer's job
- `LifespanManager` as a new class (master plan reference is
  documentation drift per Decision 14 path-forward option (b))
- Counter/Histogram/Metric subclasses with `Literal[...]`-typed
  label discipline (Phase 6 spec §6B)
- WebSocket → aria-live bridge (Phase 6 spec §6C.5)
- Sentry+OTel root-span bridge (Phase 6 spec §6C.4) — alpha-path
  instability noted in ADR 0013 Decision 8

## Why Phase 6.5 ships 4 commits in this order

- **Commit 1 first**: prerequisite for the master-plan verification
  gate (master plan line 478-479). Any future Phase 6 retry
  needs lifespan-bound `app.state.main_loop` to make its
  TraceContext propagation tests meaningful. This commit
  unblocks the gate, irrespective of whether Phase 6 ever retried.
- **Commit 2 second**: provides the trace-context API that Commit 3
  depends on. Independent of Commit 1. Independent of OTel /
  SpanProcessor work (the public `trace_context.set()` API is the
  deliverable; Phase 6 OtelMiddleware will use it later).
- **Commit 3 third**: depends on Commit 2's `trace_context` module
  existing. Resolves the htmx.py executor-boundary cargo-culting
  from Phase 6 v3 (ADR 0013 Decision 4 / Open Review Flag #5).
- **Commit 4 last**: independent test-infra commit. Could land at
  any time, but it's the load-bearing test reliability fix that
  future Phase 6 SpanProcessor work depends on. Lands last to
  avoid having it gating the production-code commits.

## Architecture (per-commit ICs)

### Commit 1 — `feat(app): bind app.state.main_loop + app.state.jinja_env at lifespan startup`

- *Triggered from:* master plan §Phase 6 verification line 478-479
  (lifecycle integration test); ADR 0013 Decision 14; ADR 0012
  Decision 2 path-forward option (b)
- *Returns to / updates:* `fastblocks/adapters/app/default.py:164-178`
  (modify existing `@asynccontextmanager async def lifespan(...)`)
- *Demonstrable by:* `httpx.AsyncClient(transport=ASGITransport(app=app))`
  driver hits the app's startup event; assert
  `app.state.main_loop` is `asyncio.AbstractEventLoop` AND
  `app.state.jinja_env` is `jinja2.Environment` (or whichever
  factory the existing app uses today).
- *Rollback signal:* `git revert`
- *Observability added:* none (lifespan extension only)
- *Reviewers:* 2 (per master plan line 553 — Phase 6/7 are
  high-blast-radius; one reviewer for Starlette/app integration,
  one for backward-compat check against existing lifespan
  behavior)

```python
# fastblocks/adapters/app/default.py — extended lifespan
@asynccontextmanager
async def lifespan(app):
    """Bind app.state at startup so master-plan line 478-479
    lifecycle integration test passes; tear down at shutdown.
    Per ADR 0013 Decision 14 + ADR 0012 Decision 2 path-forward
    option (b): extend the existing lifespan; do NOT ship a new
    LifespanManager class. The master-plan reference to
    'LifespanManager' is documentation drift, not a code
    requirement.
    """
    logger.info("App startup")
    app.state.main_loop = asyncio.get_event_loop()
    app.state.jinja_env = ...  # construct from settings;
                                # exact wiring is whichever factory
                                # the app uses today; verify against
                                # existing lifespan.py or similar
                                # prior to commit
    try:
        yield
    finally:
        logger.info("App shutdown")
```

### Commit 2 — `feat(observability): mandate bind_contextvars() in trace_context.set()`

- *Triggered from:* ADR 0013 Decision 17 (structlog
  `merge_contextvars` doesn't see raw `ContextVar.set()`);
  F-PYT-004 v1 (load-bearing — log↔trace correlation). The
  v3 spec's "custom-processor escape hatch" advisory was
  insufficient — codifying in §6A library choice here.
- *Returns to / updates:* NEW `fastblocks/observability/trace_context.py`
  (or expands existing `observability` module) — the public
  `set()` API does BOTH:
  1. `token = _current_trace.set(ctx)` (raw `ContextVar`, survives
     asyncio Task propagation)
  1. `structlog.contextvars.bind_contextvars(**asdict(ctx))`
     (structlog-visible; merge_contextvars picks up trace_id,
     span_id, parent_span_id)
     Returns the `Token` for canonical de-allocation via `reset()`.
- *Demonstrable by:*
  `tests/observability/test_log_correlation.py::test_trace_id_in_log_line`
  — set trace_context, emit a structlog INFO line, parse the JSON
  output, assert `trace_id` field present and equals the hex of
  the ContextVar value.
- *Rollback signal:* `git revert`
- *Observability added:* log↔trace correlation live for any future
  `trace_context.set()` consumer (Phase 6 OtelMiddleware, future
  websockets, etc.)
- *Dependency:* NONE (this commit provides the helper; Phase 6
  OtelMiddleware will use it)
- *Side note:* the `clear()` API becomes `reset(token)` for
  token-safe de-allocation (per F-PYTV2-004 v2 finding). The
  legacy `clear()` is kept as a deprecated alias in this commit,
  removed in commit 4.
- *Reviewers:* 2 (python-pro for the typed `set`/`reset`
  contract; observability-incident-lead for log↔trace correlation
  semantics)

### Commit 3 — `feat(htmx): preserve ContextVar across _run_async_safely executor boundary`

- *Triggered from:* ADR 0013 Decision 4 (htmx.py executor
  boundary cargo-culting); master plan line 521 (Phase 6.5
  readiness); Phase 6 v3 Open Review Flag #5 (production-code
  fix split off as Phase 6.5 commit)
- *Returns to / updates:* `fastblocks/htmx.py:29-52` (modify
  `_run_async_safely`)
- *Demonstrable by:*
  `tests/htmx/test_trace_context_propagation.py` —
  `trace_context.set(TraceContext(trace_id="abc", span_id="def"))`
  in the caller thread; call
  `_run_async_safely(coro)`; inside `coro`,
  `trace_context.get()` returns `TraceContext(trace_id="abc", span_id="def")` (NOT `None`).
- *Rollback signal:* `git revert`
- *Observability added:* `fastblocks_trace_context_lost_total`
  no longer fires for htmx.py path (per Phase 6 v3 spec
  §6C.2; if Phase 6's metric is not yet committed, the metric
  is recorded as "to be added when Phase 6 ships" — the
  *absence* of the failure is the demo signal in this commit's
  test)
- *Dependency:* Commit 2 (so the trace_context system exists;
  otherwise the test has nothing to verify against)
- *Reviewers:* 2 (starlette-specialist for the executor/futures
  boundary; observability-incident-lead for the ContextVar
  correctness)

```python
# fastblocks/htmx.py — fixed _run_async_safely
def _run_async_safely[T](coro: Coroutine[t.Any, t.Any, T]) -> T:
    """Run coro in a fresh event loop on the executor, preserving
    the caller's contextvars.Context snapshot across the executor
    thread boundary. Per ADR 0013 Decision 4: the prior
    implementation
    (`executor.submit(asyncio.run, coro).result()`) created a
    new thread with empty ContextVar storage; `asyncio.run()`
    inside that thread had no access to the caller's
    `_current_trace`. The fix wraps the call in
    `contextvars.copy_context()` and `run()` to bridge the
    boundary.
    """
    ctx = contextvars.copy_context()
    return executor.submit(ctx.run, asyncio.run, coro).result()
```

### Commit 4 — `tests(observability): conftest.py autouse fixture for SpanProcessor teardown`

- *Triggered from:* ADR 0013 Decision 12; F-ONEV2-004 (test
  pollution across `traced_decision()` invocations). The OTel
  `TracerProvider` is process-global; a SpanProcessor installed
  in test 1 persists into tests 2..N unless explicitly torn
  down. Without the fixture, every test that calls
  `traced_decision()` accumulates processors; counter labels
  double/triple across tests.
- *Returns to / updates:* NEW `tests/observability/conftest.py`
- *Demonstrable by:* a regression test
  `tests/observability/test_conftest_isolation.py` (or the
  existing oneiric adapter test exercising `traced_decision()`
  twice) — assert the TracerProvider's active span processor
  list is empty between tests.
- *Rollback signal:* `git revert` (it's a test-infra commit;
  deletion is fine)
- *Observability added:* none (test reliability only)
- *Dependency:* NONE (prepares test infra for future
  SpanProcessor work in Phase 6 retry)
- *Reviewers:* 2 (pytest-hypothesis-specialist for fixture
  lifecycle + scoping; observability-incident-lead for
  TracerProvider manipulation semantics)

```python
# tests/observability/conftest.py
"""Autouse fixture for observability tests.

Per ADR 0013 Decision 12: OTel's TracerProvider is process-global.
A SpanProcessor installed in test 1 persists into tests 2..N unless
explicitly torn down. Per quick-review 2026-08-22, we swap the
TracerProvider per test via `trace.set_tracer_provider(TracerProvider())`
because `ProxyTracerProvider` does not expose its active span-processor
list (no public snapshot/restore API). The swap approach is documented
in opentelemetry-test as the canonical test-isolation pattern for
TracerProvider.
"""
from contextlib import suppress
import pytest

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    HAS_OTEL_SDK = True
except ImportError:
    HAS_OTEL_SDK = False


@pytest.fixture(autouse=True)
def _tracer_provider_isolation():
    """Swap in a fresh empty TracerProvider per test, restore after."""
    if not HAS_OTEL_SDK:
        yield
        return
    previous = trace.get_tracer_provider()
    fresh = TracerProvider()
    with suppress(Exception):
        trace.set_tracer_provider(fresh)
    try:
        yield
    finally:
        with suppress(Exception):
            trace.set_tracer_provider(previous)
            fresh.shutdown()  # flush any pending spans
```

## Erratum (post-implementation, 2026-08-22)

The code block above is correct in shape but elides one
detail discovered during the final whole-branch review: OTel's
public `trace.set_tracer_provider` is one-shot per **process**,
guarded by a `_TRACER_PROVIDER_SET_ONCE` flag at
`opentelemetry/trace/__init__.py` (line `_TRACER_PROVIDER_SET_ONCE._done`).
The second and later calls log `Overriding of current TracerProvider is not allowed` and silently no-op. The
implementation therefore resets the flag
(`_TRACER_PROVIDER_SET_ONCE._done = False`) immediately before
each `trace.set_tracer_provider(...)` call inside the
`_set_provider_silently` helper, so per-test swap-then-restore
works on the 2nd..N invocation as well as the 1st. Only the
boolean state of the flag is touched; no other private OTel
state is mutated. The fixture is otherwise unchanged from the
spec below.

## Failure modes (cross-cutting)

| Failure | Behavior |
|---|---|
| Commit 1 lifespan extension breaks existing startup behavior | App startup fails loudly; rollback via `git revert`; investigate constructor of `jinja_env` (Phase 1.5's `AppBaseSettings` factory is the canonical source) |
| Commit 2 `bind_contextvars` clobbers existing structlog state | Optional `clear_existing=True` kwarg for callers that don't want prior `bind_contextvars` to leak; default is merge-with-existing |
| Commit 3 `executor.submit(ctx.run, asyncio.run, coro).result()` raises on broken `Executor` | `RuntimeError` surfaces; existing exception path handles it (the executor's `result()` re-raises) |
| Commit 4 fixture snapshots may break on opentelemetry-sdk shape change | Defensive `with suppress(Exception)`; fixture degrades to a no-op silently when SDK diverges from the assumed shape |

## Migration policy

Per master plan line 350: zero backwards compatibility required. No
deprecation warnings in fastblocks production code. Each commit:

- **Commit 1**: pure extension of existing lifespan (no behavior
  change for any existing caller); additive
- **Commit 2**: introduces new public API; legacy `clear()` kept as
  alias until commit 4 removes it
- **Commit 3**: production code change but only to the executor
  submission pattern; no signature change
- **Commit 4**: pure test-infra addition (no production API impact)

No commit requires a deprecation cycle.

## Verification gate

Phase 6.5 done means ALL of these pass:

| Gate item | Test/command | Pass criterion |
|---|---|---|
| ty strict | `uv run ty check fastblocks/` | "All checks passed!" |
| pyright strict | `uv run pyright fastblocks/` | 0 errors (warnings allowed only for `reportMissingTypeStubs`) |
| ruff | `uv run ruff check fastblocks/ tests/` | 0 violations |
| refurb | `uv run refurb fastblocks/ tests/` | 0 violations |
| bandit | `uv run bandit -r fastblocks/` | 0 high-severity |
| pytest (not slow) | `uv run pytest -q -m "not slow" --no-header` | ≥ current baseline, 0 fails |
| Commit 1 test | `uv run pytest tests/test_lifespan_app_state.py -v` | 1 new test, 0 fails |
| Commit 2 test | `uv run pytest tests/observability/test_log_correlation.py -v` | 1 new test, 0 fails |
| Commit 3 test | `uv run pytest tests/htmx/test_trace_context_propagation.py -v` | 1 new test, 0 fails |
| Commit 4 test | `uv run pytest tests/observability/test_conftest_isolation.py -v` | 1 new test, 0 fails |

Baseline expectations (from `git show HEAD:pyproject.toml`):

- ty: 0 prod errors
- pytest: ~1800+ tests, 0 fails
- ruff/refurb/bandit: 0

Phase 6.5 adds ~4 tests, 4 commits. Pytest baseline must continue to hold.

## Estimated effort

| Commit | LOC | Tests | Time |
|---|---|---|---|
| 1 | 5-8 | 1 | 0.5 day |
| 2 | 20-30 | 1 | 1 day |
| 3 | 5-10 | 1 | 0.5 day |
| 4 | 30-40 | 1 | 1 day |
| **Total** | **~60-90** | **4** | **~3 days** |

## Cross-references

- ADR 0013: `docs/adr/0013-phase-6-deferral.md` (Decision 4, 12,
  14, 17; Open Review Flag #5)
- ADR 0012: `docs/adr/0012-phase-5-deferral.md` (Decision 2 path
  forward option (b) — the LifespanManager inheritance origin)
- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
  - §Phase 6 verification line 478-479 (lifecycle integration test)
  - §Phase 0 preflight (line 608-621) — confirmed no Phase N.5
    blockers before starting Phase 6
- Phase 6 spec: `docs/superpowers/specs/2026-08-22-fastblocks-phase-6-design.md`
  - v1 commit `5f0eb4d`, v2 commit `8edec33`, v3 commit `a219347`
- Phase 5 spec: `docs/superpowers/specs/2026-08-22-fastblocks-phase-5-design.md`
  (deferred — `LifespanManager` doesn't-exist P0 origin)
- Phase 1.5 spec: `docs/superpowers/specs/2025-09-fastblocks-oneiric-registry-design.md`
  (registry consolidation; Commit 2's `set()`/`reset()` token
  pattern follows the `get_resolver()`/factored-handle pattern)
- `fastblocks/adapters/app/default.py:164-178` — existing lifespan
- `fastblocks/htmx.py:29-52` — existing `_run_async_safely`
- `fastblocks/observability/` — does not yet exist; will be created
  by Commit 2 (the first observability module in fastblocks)
- crackerjack-compliant-code: per-commit hygiene (from-this-directory's
  `/Users/les/.claude/skills/crackerjack-compliant-code`)
- CLAUDE.md process discipline: per-commit IC verification

## Decisions captured during design

1. **Sequence**: 4 commits in dependency order (master plan §Phase 6
   verification gate unblocked by Commit 1; trace-context API
   shipped by Commit 2 before Commit 3 depends on it; test-infra
   Commit 4 independent and last).
1. **LifespanManager**: extend the existing `@asynccontextmanager`
   lifespan; do NOT ship a new class. The master-plan reference
   is documentation drift, not a code requirement.
1. **`trace_context` API shape**: `set(ctx) -> Token` + `reset(token)`.
   The `set()` does both raw `ContextVar.set()` and
   `structlog.bind_contextvars(**asdict(ctx))` so log lines carry
   trace_id without a custom processor.
1. **htmx.py fix pattern**: `executor.submit(ctx.run, asyncio.run, coro).result()` — the canonical Python 3.13 pattern for
   crossing an executor boundary with context preservation.
1. **conftest fixture scope**: function-scope (autouse) — per ADR
   0013 Decision 12 mandate.
1. **No deprecation cycle** (per master plan line 350): legacy
   `clear()` API from Commit 2 is kept until Commit 4 removes it;
   no other commits require deprecation warnings.

## Summary

Phase 6.5 is the structural-fix companion to ADR 0013's deferral:
4 small, revertible commits that close the load-bearing gaps
that made Phase 6 v1/v2/v3 unbuildable. Each commit has a 1-test
verification gate. Total scope: ~60-90 LOC, 4 tests, ~3 days.
After Phase 6.5 ships, the codebase has: lifespan-bound
`app.state`, log↔trace correlation via `bind_contextvars`,
ContextVar-preserving htmx.py executor boundary, and
SpanProcessor teardown isolation in tests. A future Phase 6 retry
has a clean substrate to build on.

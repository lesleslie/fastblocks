______________________________________________________________________

status: accepted
role: phase-6-design-spec-v4
date: 2026-08-24
last_reviewed: 2026-08-24
supersedes: 2026-08-22-fastblocks-phase-6-design.md
supersedes_v3_in_part: null
decision_date: 2026-08-24
topic: phase-6-observability-v4-retry
version: v4
blocks_on:

- phase-1.5 (registry facade shipped)
- phase-2 (Literal types shipped)
- phase-2.5 (AppSettings wiring shipped)
- phase-4-v2.1 (register_fastblocks_tools non-orphan per ADR 0015)
- phase-5-v4 (test infra rebuild, ADR 0014)
- phase-6.5 (LifespanManager + trace_context shipped)

______________________________________________________________________

# Phase 6: Observability Design — v4 Retry

## Status

**Accepted** (v4 retry — refresh-and-execute vs v3's Accepted spec).
Supersedes `2026-08-22-fastblocks-phase-6-design.md` (v3). The v3 spec's
body of work remains correct; v4's purpose is to capture the **delta
vs v3** that emerged from Phase 5 v4 + Phase 6.5 closures and from
verifying v3's library-stack assumptions against today's `pip show`
state.

This is a **delta + commit IC** doc (Approach C from brainstorming). The
v3 spec's body of work is referenced, not re-stated. Where v3 said
"Counter/Histogram wrappers", v4 reads the same; the v4 deltas are
explicitly tabulated.

## Scope decision (carried from v3 §"Scope decision")

In scope:

1. **6A** — Foundational observability layer.
1. **6B** — Cardinality-safe metrics.
1. **6C** — Trace propagation + a11y bridges.

Out of scope (deferred):

- `asyncio.TaskGroup` migration (Phase 6.5; structural refactor; addressed separately).
- Cardinality budget tuning per metric (depends on real Prometheus data; Phase 7+).
- HTMY XSS for Jinja2-rendered components (master plan §Phase 5 v580+).
- A11y regression tests via axe-core (Phase 5 deferred).

## Why v4 (the four deltas vs v3)

v3 was comprehensive and Accepted on 2026-08-22. v4's purpose is
**not** to redesign — it's to register what closed and what shipped
between v3's spec date and today (2026-08-24):

| Δ | v3 assumed | Today's reality | v4 fix |
|---|-----------|-----------------|--------|
| **Δ1: Dependency posture** | `prometheus-client`, `opentelemetry-sdk`, `opentelemetry-exporter-otlp`, `sentry-sdk` all available as core deps | Only `structlog` 26.1.0 and `opentelemetry-api` 1.44.0 are core; 4 missing libs absent. `playwright` 1.62.0 already present | Add new `[observability]` optional dep group per CLAUDE.md §"Optional Dependency Groups" (alongside `ai`/`gpu`/`content-ingest`/`storage-pg`). Lean installs opt out; dev installs pull it via `{include-group = "observability"}` |
| **Δ2: ExceptionMiddleware structural fix** | OtelMiddleware is "outermost AMONG USER MIDDLEWARE" — qualified claim that 5xx errors fall outside OTel root scope | `fastblocks/applications.py:368-374` hardcodes ExceptionMiddleware as outermost. The qualified outermost claim in v3 §6C.3 stands | Commit 0c (NEW): move ExceptionMiddleware out of hardcoded slot to user-controllable position with `outermost` default; opt-out flag in settings. Enables OtelMiddleware to be TRULY outermost in Commit 11 |
| **Δ3: Open Review Flags** | Flag #1 (`register_fastblocks_tools` orphan per ADR 0011 Decisions 6/11), Flag #5/6 (LifespanManager prerequisite) | Phase 4 v2.1 made `register_fastblocks_tools` a non-orphan path (commit `01eee00`); Phase 6.5 bound `app.state.main_loop` + `app.state.jinja_env` at lifespan (commit `8c5c117`) | Both flags CLOSED. v4 marks them closed; Commit 8 ships without flag annotations |
| **Δ4: Library version verification** | v3 anchored on `sentry-sdk=3.0.0a7` (alpha path) at one unspecified date | sentry-sdk 26.x installed; OTel SDK **not installed** (only OTel API 1.44.0) | v4 mandates a pre-implementation smoke check on `import sentry_sdk.opentelemetry; print(opentelemetry.__file__)` captured as Commit 13's precondition artifact |

## Architecture (carried from v3, with v4 deltas inline)

Three stages, each producing a layer the next consumes. No parallel
paths; no duplication; no alternative observability stack.

### Sequence (17 commits — was 15 in v3)

```
[NEW] pyproject.toml: add [observability] optional dep group                (Commit 0a)
[NEW] pyproject.toml: include 'observability' group in 'dev'                (Commit 0b)
[NEW] refactor(applications): ExceptionMiddleware → user-controllable slot  (Commit 0c)
[6A]   Foundations: Counter/Histogram + structlog + OTel + Oneiric bridge    (Commits 1-4)
[6B]   Cardinality: typed wrappers + allowlist + CI lint + MCP + /metrics   (Commits 5-9)
[6C]   Bridges: trace_context + OtelMiddleware (now truly outermost) + Sentry + a11y + Grafana
                                                                             (Commits 10-15)
```

Total: 17 commits. **Wall-clock estimate unchanged** from v3: ~5 weeks
(Commits 0a/0b are tiny; Commit 0c is structural but small).

### Layer model (carried from v3)

| Layer | Provides | Consumes |
|-------|----------|----------|
| Counters/Histograms (6A.1) | `Counter("name", labelnames=(...))`, `Histogram.observe(value, exemplar={trace_id})` | `prometheus_client` (dep group) |
| Structured logs (6A.2) | `get_logger(name)` → JSON line via `structlog.merge_contextvars` | `structlog` (already core) |
| OTel Tracer (6A.3) | `tracer.start_as_current_span(...)` | `opentelemetry-sdk` + `opentelemetry-exporter-otlp` (dep group) |
| Oneiric adapter (6A.4) | Bridges `traced_decision()` → counter + log line | Oneiric OTel `resolver.decision` span attrs (bare names) |
| CardinalityGuard (6B.2) | Per-metric allowlist; `Literal["enforce","warn","off"]` | 6A.1 |
| MCP tool instrumentation (6B.5) | `instrument_tool` decorator → counter + histogram | 6A.1 |
| `/metrics` endpoint (6B.6) | OpenMetrics text format on `:8680/metrics` | 6A.1 + Starlette route |
| `trace_context` (6C.1) | `get`/`set`/`clear` ContextVar binding | 6A.3 |
| OtelMiddleware (6C.3) | Per-request OTel root span; binds + clears `trace_context` | 6A.3 + 6C.1 + **Commit 0c** |
| Sentry bridge (6C.4) | `sentry_sdk.init(...)` + `OpenTelemetryIntegration` | 6A.3 + `sentry-sdk` (dep group) |
| a11y bridge (6C.5) | `render_broadcast_as_a11y(...)` → aria-live DOM region | WebSocket broadcasts + Jinja helper |

### Failure-degradation policy (carried from v3)

Pattern across all failure modes: **observability failures degrade to
less observability; never to app failure.** The v4 delta is the new
`RuntimeError` wrapper for missing dep-group libraries: lazy import
catches the absence and raises a clear `RuntimeError` with the
`uv sync --group observability` hint. The app refuses to start with
incomplete observability rather than running with partial counters.

## Δ-vs-v3 changelog (the spec's load-bearing table)

| Section | v3 status | v4 status | Reason |
|---------|-----------|-----------|--------|
| §6A.1 file structure | proposed NEW | NEW (Commit 1) | unchanged |
| §6A.2 file structure | proposed NEW | NEW (Commit 2) | unchanged |
| §6A.3 `trace_context.py` | NEW deliverable | ALREADY SHIPPED (post-6.5 commit) | referenced, not re-shipped |
| §6A.3 `tracer.py` | NEW deliverable | NEW (Commit 3) — depends on Commit 0a/0b | unchanged |
| §6A.4 adapter | NEW | NEW (Commit 4) | unchanged; precondition artifact from `scripts/verify_oneiric_otel_attrs.py` added |
| §6A.4 `tests/observability/conftest.py` | NEW deliverable | ALREADY SHIPPED | referenced |
| §6B.1-4 typed counters | NEW | NEW (Commit 5) | unchanged |
| §6B.5 `_label_allowlist.py` | NEW | NEW (Commit 6) | unchanged |
| §6B.6 `scripts/check_metric_cardinality.py` | NEW | NEW (Commit 7) | unchanged |
| §6B.7 `fastblocks/mcp/observability.py` | NEW (depends on register_fastblocks_tools non-orphan) | NEW (Commit 8) — Flag #1 CLOSED | Flag #1 closure noted in IC |
| §6B.8 `/metrics` endpoint | NEW | NEW (Commit 9) | unchanged |
| §6C.1 `trace_context` public API | NEW | ALREADY SHIPPED (post-6.5) | referenced |
| §6C.3 OtelMiddleware | "outermost AMONG USER MIDDLEWARE" — qualified | TRULY outermost after Commit 0c (Commit 11) | Δ2 |
| §6C.2 htmx.py boundary test | NEW test | NEW test (Commit 12) | unchanged |
| §6C.4 Sentry bridge | NEW with α-pin | NEW (Commit 13) — smoke-check precondition per Δ4 | depends on Commit 0a/0b for `sentry-sdk` |
| §6C.5 a11y bridge | NEW | NEW (Commit 14) | unchanged |
| §6C.6 Grafana dashboard | NEW (Grafana 10.x pin) | NEW (Commit 15) | unchanged |
| NEW: Commit 0a/0b dep group | (n/a) | NEW | Δ1 |
| NEW: Commit 0c ExceptionMiddleware decouple | (n/a) | NEW | Δ2 |

## Open review flags (carried + delta-closed)

| Flag | v3 status | v4 status |
|------|-----------|-----------|
| #1 (Commit 8 dependency on `register_fastblocks_tools` non-orphan) | OPEN with risk | **CLOSED** — Phase 4 v2.1 made `register_fastblocks_tools` non-orphan; tools registered via `register_fastblocks_tools` call to capabilities primitives |
| #2 (LifespanManager inheritance) | OPEN with P0 risk | **CLOSED** — Phase 6.5 commit `8c5c117` binds `app.state.main_loop` and `app.state.jinja_env` at lifespan startup |
| #3 (Oneiric `Decisions.events()` API) | CLOSED in v2 | **CLOSED** — unchanged. SpanProcessor consumes actual OTel spans emitted by `traced_decision()` |
| #4 (Grafana version pin) | OPEN (Grafana 10.x) | **OPEN, ACCEPTED** — Grafana 10.x pin acknowledged; schema-validation test catches drift; treat as known limitation. **v4 verification gate** keeps `tests/dashboards/test_fastblocks_dashboard_schema.py` |
| #5 (Commit 12 boundary fix) | OPEN | **CLARIFIED IN v4** — Commit 12 ships regression-test-only per v3; the production-code fix (`executor.submit(copy_context().run, asyncio.run, coro)`) is **explicitly deferred to a separate post-Phase-6 phase** (call it `Phase 6.5b` for traceability). `fastblocks_trace_context_lost_total` is observability-OF the gap. Commit 0c (ExceptionMiddleware decouple) is unrelated to Flag #5. |
| #6 (LifespanManager inheritance) | OPEN | **CLOSED** — see Flag #2 |
| NEW: Flag #7 (dep-group import guard) | (n/a) | **OPEN, MITIGATED** — Commit 1's `RuntimeError` wrapper + dep-group README note; CI verification: lean install fails `python -c "from fastblocks.observability.counters import Counter; ..."` with install hint |
| NEW: Flag #8 (Sentry alpha path) | (n/a) | **OPEN, MITIGATED** — Commit 13's smoke-check precondition artifact; if `sentry_sdk.opentelemetry` import path differs from the smoke-checked location, the bridge fails fast and `observability.sentry.disabled_on_import_error: bool = true` lets operators ship without Sentry |

## Per-task Integration Contracts

Per master plan line 553: for Phase 6 (high-blast-radius) each commit
gets **2 reviewers**; pre-commits 0a/0b/0c get 1 reviewer each.

### Commit 0a — `chore(pyproject): [observability] optional dep group (prometheus-client, opentelemetry-sdk, opentelemetry-exporter-otlp, sentry-sdk)`

- *Triggered from:* Δ1; CLAUDE.md §"Optional Dependency Groups"
- *Returns to / updates:* `pyproject.toml` adds `[dependency-groups]` entry `observability = ["prometheus-client", "opentelemetry-sdk", "opentelemetry-exporter-otlp", "sentry-sdk"]`
- *Demonstrable by:*
  1. `uv sync` (lean) does NOT install the group; `python -c "import fastblocks.observability.counters"` raises `RuntimeError` with install hint
  1. `uv sync --group observability` installs; the same import succeeds
- *Rollback signal:* `git revert`; pure pyproject edit
- *Reviewers:* 1 (python-pro for dep-group conformance to CLAUDE.md pattern)

### Commit 0b — `chore(pyproject): include 'observability' in 'dev' via include-group`

- *Triggered from:* Commit 0a
- *Returns to / updates:* `pyproject.toml` `[dependency-groups].dev` gets `{include-group = "observability"}`
- *Demonstrable by:* `uv sync` (dev install) installs all 4 libs; `python -c "import fastblocks.observability.counters"` succeeds
- *Rollback signal:* `git revert`; pure pyproject edit
- *Reviewers:* 1 (python-pro)

### Commit 0c — `refactor(applications): ExceptionMiddleware → user-controllable position (default outermost)`

- *Triggered from:* Δ2; enables Commit 11's "truly outermost" claim
- *Returns to / updates:*
  - `fastblocks/applications.py:368-374` — `build_middleware_stack` no longer hardcodes `ExceptionMiddleware` at the outermost position
  - NEW `fastblocks/applications.py::register_user_exception_middleware(app, *, position="outermost")` — opt-out path with `position` Literal
  - NEW `tests/observability/test_exception_middleware_position.py` — proves ordering for both `outermost_default` and `innermost_opt_out` cases
- *Demonstrable by:*
  1. `tests/observability/test_exception_middleware_position.py::test_outermost_default` passes (default behavior preserved)
  1. `tests/observability/test_exception_middleware_position.py::test_innermost_opt_out` passes (opt-out works)
  1. `pytest -q -m "not slow"` baseline ≥ current 2290 tests, 0 fails
- *Rollback signal:* `git revert`; restore hardcoded `ExceptionMiddleware` position
- *Reviewers:* 1 (starlette-specialist — high blast radius on 5xx handling)

### Commit 1 — `feat(observability): package skeleton + Counter/Histogram wrappers`

- *Triggered from:* v3 §6A.1; depends on Commit 0a
- *Returns to / updates:* NEW `fastblocks/observability/{__init__.py, counters.py}`; `__init__.py` re-exports `Counter`, `Histogram`, `trace_context`, `ObservabilityRegistry`
- *Demonstrable by:* `python -c "from fastblocks.observability import Counter; Counter(name='demo', labelnames=('r',))"` works (after `uv sync --group observability`)
- *Rollback signal:* `git revert`; pure addition
- *Reviewers:* 2 (python-pro for typing; observability-incident-lead for label discipline)

### Commit 2 — `feat(observability): structlog Logger bound to Oneiric settings`

- *Triggered from:* Commit 1; v3 §6A.1
- *Returns to / updates:* NEW `fastblocks/observability/loggers.py`; one route to `get_logger`
- *Demonstrable by:* `get_logger("mymod").info("event", request_id="abc")` emits JSON line with `event`, `request_id`, `level`, `timestamp`
- *Rollback signal:* `git revert`
- *Reviewers:* 2 (python-pro; observability-incident-lead)

### Commit 3 — `feat(observability): OTel Tracer + tracer.py`

- *Triggered from:* Commit 1; v3 §6A.1; depends on Commit 0a/0b for OTel SDK
- *Returns to / updates:* NEW `fastblocks/observability/tracer.py`; references already-shipped `trace_context.py`
- *Demonstrable by:* `tracer = get_tracer("test"); with tracer.start_as_current_span("test") as span: assert hex(span.get_span_context().trace_id)` produces non-zero IDs
- *Rollback signal:* `git revert`
- *Reviewers:* 2 (python-pro; observability-incident-lead)

### Commit 4 — `feat(adapters): Oneiric observability adapter — SpanProcessor on `resolver.decision` spans`

- *Triggered from:* Commits 1+2; v3 §6A.3 (real contract per F-ONEV2-001)
- *Returns to / updates:*
  - NEW `fastblocks/adapters/oneiric/observability.py` (SpanProcessor installs on OTel global `TracerProvider`)
  - NEW `scripts/verify_oneiric_otel_attrs.py` (precondition smoke check with bare attribute names)
  - **References**: already-shipped `tests/observability/conftest.py` (autouse fixture for SpanProcessor teardown)
- *Precondition artifact (commit message body):* output of `python -c "import oneiric; from fastblocks.adapters.oneiric.observability import DecisionSpanProcessor; ..."` showing BARE `domain`, `key`, `provider`, `decision` attribute names on emitted spans
- *Demonstrable by:*
  1. `scripts/verify_oneiric_otel_attrs.py` exits 0 with all 4 attribute names verified
  1. Unit test triggers Oneiric resolution; SpanProcessor emits structlog line and increments counter
  1. The autouse fixture in `tests/observability/conftest.py` tears down SpanProcessor; next test sees clean `TracerProvider`
- *Rollback signal:* `git revert`
- *Reviewers:* 2 (oneiric-specialist; observability-incident-lead)

### Commit 5 — `feat(observability): Typed Counter/Histogram wrappers + CardinalityGuard`

- *Triggered from:* Commit 1; v3 §6B.2
- *Returns to / updates:* refactor `fastblocks/observability/counters.py`
- *Demonstrable by:* `Counter("foo", labelnames=("result",))` rejects `inc(result="bogus")` per `cardinality_mode` setting
- *Rollback signal:* `git revert`
- *Reviewers:* 2 (python-pro; observability-incident-lead)

### Commit 6 — `feat(observability): _label_allowlist.py + Literal binding registry`

- *Triggered from:* Commit 5; v3 §6B.4
- *Returns to / updates:* NEW `fastblocks/observability/_label_allowlist.py`
- *Demonstrable by:* `KNOWN_LABELS["result"]` resolves to `StyleResult` Literal
- *Rollback signal:* `git revert`
- *Reviewers:* 2 (python-pro; observability-incident-lead)

### Commit 7 — `feat(scripts): check_metric_cardinality.py — CI lint`

- *Triggered from:* Commit 6; v3 §6B.3
- *Returns to / updates:* NEW `scripts/check_metric_cardinality.py`
- *Demonstrable by:* Adding `Counter("foo", ("bogus_label",))` makes `python scripts/check_metric_cardinality.py fastblocks/` exit 1 with file:line
- *Rollback signal:* `git revert`
- *Reviewers:* 2 (python-pro for AST; observability-incident-lead for false-positive review)

### Commit 8 — `feat(mcp): observability wrapper around tool dispatch (instrument_tool decorator)`

- *Triggered from:* Commits 5+7; v3 §6B.5; **Δ3 Flag #1 CLOSED**
- *Returns to / updates:* NEW `fastblocks/mcp/observability.py`; `fastblocks/mcp/server.py` registered tools wrapped via `register_fastblocks_tools` (non-orphan per Phase 4 v2.1)
- *Demonstrable by:* `validate_template(...)` call increments `fastblocks_mcp_tool_invocations_total{tool_name="validate_template", status="ok"}`
- *Rollback signal:* `git revert`; tools return to un-instrumented
- *Reviewers:* 2 (mcp-integration-expert; observability-incident-lead)

### Commit 9 — `feat(app): /metrics endpoint mounted in default app`

- *Triggered from:* Commits 1+5; v3 §6B.6
- *Returns to / updates:* `fastblocks/adapters/app/default.py` mounts `/metrics` route using OpenMetrics content type (preserves exemplars per F-PYTV2-001)
- *Demonstrable by:* `curl :8680/metrics` returns `application/openmetrics-text; version=1.0.0` with named counter names
- *Rollback signal:* `git revert`
- *Reviewers:* 2 (starlette-specialist; observability-incident-lead)

### Commit 10 — `feat(observability): trace_context get/set/clear public API`

- *Triggered from:* Commit 3 expansion; v3 §6C.1
- *Returns to / updates:* **MOSTLY ALREADY SHIPPED** (post-6.5). v4 IC documents the pre-implemented state and explicitly references `fastblocks/observability/trace_context.py` at HEAD
- *Demonstrable by:* frozen `TraceContext` rejects direct mutation; `get`/`set`/`clear` API only; trace_id surfaces in structlog via `merge_contextvars` (verified by already-shipped `tests/observability/test_log_correlation.py`)
- *Rollback signal:* `git revert`
- *Reviewers:* 2 (python-pro for frozen dataclass; observability-incident-lead)

### Commit 11 — `feat(observability): OtelMiddleware + trace_id binding into context (TRULY outermost)`

- *Triggered from:* Commit 10; v3 §6C.3; **Δ2 commit 0c prerequisite**
- *Returns to / updates:* NEW `fastblocks/observability/otel_middleware.py`; mounted as the LAST entry in `user_middleware` after Commit 0c decoupled `ExceptionMiddleware`
- *Demonstrable by:*
  1. Request through the app → OTel root span created → `trace_context.get()` non-None inside handler
  1. `Manager.get_middleware_stack()["user_middleware"][-1]["class"] == "OtelMiddleware"` (per v3 F-STRV2-2 correction — manager returns dict, not list)
  1. NEW `tests/observability/test_otel_middleware_outermost.py` confirms positioning + 5xx-with-OTel-trace coverage
  1. `try/finally` clears `trace_context` even on handler exception (regression test asserts)
- *Rollback signal:* `git revert`
- *Reviewers:* 2 (starlette-specialist; observability-incident-lead)

### Commit 12 — `feat(observability): htmx.py per-thread loop context-capture test (regression-only)`

- *Triggered from:* Commits 10+11; v3 §6C.2; **Δ3 Flag #5 CLARIFIED**
- *Returns to / updates:* NEW `tests/htmx/test_trace_context_propagation.py` (regression test only)
- *Demonstrable by:* Test passes — trace context is **lost** under current `executor.submit(asyncio.run, coro)` pattern; `fastblocks_trace_context_lost_total` is observability-OF the gap. The production-code fix (`executor.submit(copy_context().run, asyncio.run, coro)`) is **explicitly out of v4 scope** and lands in a separate `Phase 6.5b` (post-Phase-6 phase, not in this spec's 17 commits)
- *Rollback signal:* test-only commit; rollback is delete
- *Reviewers:* 2 (starlette-specialist; observability-incident-lead)

### Commit 13 — `feat(observability): Sentry+OTel bridge (OpenTelemetryIntegration wiring)`

- *Triggered from:* Commit 11; v3 §6C.4; **Δ4 smoke-check precondition**
- *Returns to / updates:* NEW `fastblocks/observability/sentry_bridge.py`; called from app startup
- *Precondition artifact (commit message body):* output of `python -c "import sentry_sdk; print(sentry_sdk.__version__)"` and `python -c "from sentry_sdk import opentelemetry; print(opentelemetry.__file__)"` — captured as IC evidence
- *Demonstrable by:*
  1. With `SENTRY_DSN` set, single span tree in both Sentry and OTel collector
  1. Without `SENTRY_DSN`, no-op
  1. `observability.sentry.disabled_on_import_error: bool = true` lets operators ship if import path drifts
- *Rollback signal:* `git revert`
- *Reviewers:* 2 (observability-incident-lead; oneiric-specialist)

### Commit 14 — `feat(websocket): a11y_bridge — broadcast → aria-live region routing`

- *Triggered from:* Commits 1+5; v3 §6C.5
- *Returns to / updates:*
  - NEW `fastblocks/websocket/a11y_bridge.py`
  - NEW `fastblocks/websocket/static/a11y_bridge.css` (namespaced `.sr-only--fastblocks-a11y-bridge` with modern `clip-path: inset(50%)` per F-A11YV2-001/003/008)
  - Rendered in default HTMY template; `:8680/static/a11y_bridge.css` mount point in default app
- *Demonstrable by:*
  1. `render_broadcast_as_a11y(kind=POLITE, message="hit", role="status")` returns escaped HTML containing `data-fb-aria-live="true"` and the namespaced class
  1. Playwright test boots app + WebSocket adapter; assertion (a) finds the node via `[data-fb-aria-live="true"]`, (b) asserts `classList` contains `"sr-only--fastblocks-a11y-bridge"`, (c) asserts `getComputedStyle(el).clipPath === 'inset(50%)'`, (d) asserts `getComputedStyle(el).width === '1px'`
- *Rollback signal:* `git revert`
- *Reviewers:* 2 (accessibility-auditor; websocket-specialist)

### Commit 15 — `feat(dashboards): fastblocks-overview.json + schema-validation test`

- *Triggered from:* Commits 8+11+13; v3 §6C.6; **Flag #4 OPEN, ACCEPTED at Grafana 10.x pin**
- *Returns to / updates:* NEW `dashboards/fastblocks-overview.json`; NEW `tests/dashboards/test_fastblocks_dashboard_schema.py`
- *Demonstrable by:*
  1. Dashboard JSON parses against Grafana 10.x schema
  1. Per-dashboard ground-truth test scans each panel's `targets[].expr`, extracts metric name, asserts metric appears in per-metric instrumentation matrix
- *Rollback signal:* `git revert`
- *Reviewers:* 2 (observability-incident-lead; python-pro for schema assertion)

## Migration policy

Per master plan line 350: no backwards compatibility required. Per
master plan line 356: no deprecation warnings. Per v3 §"Migration
policy": every replacement commit leaves the prior mechanism functional
but unused; if both paths coexist for a transition window, the unused
path is removed in the SAME commit.

v4-specific migration: Commit 0a/0b's `[observability]` dep-group
means any project that depends on `fastblocks` and uses counters must
either: (a) include `observability` in their own `[dependency-groups]`,
or (b) install the group's libraries independently. The
`RuntimeError` import guard makes this transition loud — no silent
degradation.

## Verification gate (Phase-6-done checklist)

| Gate | Command | Pass criterion |
|------|---------|----------------|
| ty strict | `uv run ty check fastblocks/` | "All checks passed!" |
| pyright strict | `uv run pyright fastblocks/` | 0 errors (warnings allowed for `reportMissingTypeStubs`) |
| ruff | `uv run ruff check fastblocks/ tests/` | 0 violations |
| refurb | `uv run refurb fastblocks/ tests/` | 0 violations |
| bandit | `uv run bandit -r fastblocks/` | 0 high-severity |
| pytest (not slow) | `uv run pytest -q -m "not slow" --no-header` | ≥ current 2290 baseline, 0 fails |
| Phase 6 tests | `uv run pytest tests/observability/ tests/dashboards/ tests/a11y/test_websocket_landing.py tests/mcp/test_mcp_observability.py -v` | 30-40 new tests, 0 fails |
| Cardinality lint | `uv run python scripts/check_metric_cardinality.py fastblocks/` | exit 0 |
| Dashboard schema | `uv run pytest tests/dashboards/ -v` | Grafana 10.x schema validates |
| WCAG SC 4.1.3 | `uv run pytest tests/a11y/test_websocket_landing.py -v` | Playwright test passes; aria-live region observed |
| Manual smoke | `fastblocks mcp serve` then `curl :8680/metrics` | OpenMetrics output exported; named counters present |
| Dep-group import guard | `python -c "from fastblocks.observability.counters import Counter"` (lean install) | `RuntimeError` with install hint |

## Estimated effort

| Section | Commits | New tests | Estimated time |
|---------|---------|-----------|----------------|
| Pre-commit (0a/0b/0c) | 3 | 2 (Commit 0c) | 2-3 days |
| 6A | 4 (1-4) | ~10 | 1.5 weeks |
| 6B | 5 (5-9) | ~12 | 1.5 weeks |
| 6C | 6 (10-15) | ~12 | 2 weeks |
| **Total** | **17** | **~36** | **~5-6 weeks** |

## Cross-references (carried from v3 + delta additions)

- Master plan: §Pillar 6 (lines 174-180), §Phase 6 (line 342), §Phase 6 verification (lines 481-498)
- v3 spec (superseded): `docs/superpowers/specs/2026-08-22-fastblocks-phase-6-design.md`
- ADR 0008: Oneiric selection mechanism (SpanProcessor pattern)
- ADR 0011: Phase 4 deferral (Commit 8 dependency — **CLOSED in v4**)
- ADR 0012: Phase 5 deferral (LifespanManager P0 — **CLOSED in v4**)
- ADR 0014: Phase 5 coverage ratchet (test infrastructure rebuild context)
- ADR 0015: Phase 4 v2.1 library-aware opt-in (relevant: tools no longer orphan)
- Phase 1.5 spec: Oneiric layered config (settings layer)
- Phase 2 spec: Literal types (Phase 6's Literal labelnames pattern)
- Phase 2.5 spec: AppSettings wiring
- Phase 5 v4 spec: test infrastructure rebuild (gates Phase 6's test execution environment)
- Phase 6.5 commit `8c5c117`: `app.state.main_loop` + `app.state.jinja_env` binding (closes LifespanManager P0)
- Phase 6.5 commit `fb74d13`: `trace_context.set()` mandates `bind_contextvars()` (closes Commit 3 partial)
- Phase 6.5 commit `a102f68`: autouse SpanProcessor teardown (closes Commit 4 partial)
- crackerjack-compliant-code: per-commit hygiene
- CLAUDE.md: process discipline, hard limits, optional dependency group pattern

## Decisions captured during design (v4-specific additions only)

**Carried from v3 without re-statement**: Decisions 1-7 (single coherent design, hybrid test boundary, primitives + HTMY migration, bridge in 6C via Playwright, `prometheus_client`+`structlog`+`opentelemetry-sdk` stack, `Literal[...]` + AST lint + per-metric allowlist, HTMY XSS for Jinja2 deferred).

**v4-specific decisions**:

8. **17-commit sequence adds 2 pre-commits (Δ1+Δ2)**: dep-group + ExceptionMiddleware decouple. v3's 15 commits remain unchanged; the pre-commits are load-bearing for v3's own deliverables (Commit 1 needs the dep group; Commit 11 needs ExceptionMiddleware out of the way).
1. **Delta-vs-v3 doc structure (Approach C)**: v4 is a delta + commit ICs; v3 is referenced, not re-stated. Phase 5 v4 retry used this same shape.
1. **Open Review Flags #1, #5, #6 are CLOSED**: Phase 4 v2.1 made `register_fastblocks_tools` non-orphan; Phase 6.5 bound `app.state.main_loop` at lifespan. Flag #7 (dep-group import guard) and Flag #8 (Sentry alpha path) are NEW and mitigated.
1. **`[observability]` dep group, NOT core deps**: matches CLAUDE.md §"Optional Dependency Groups" pattern. Lean installs opt out; dev installs pull it. Commit 1's `RuntimeError` wrapper handles the loud-failure transition.

## Spec self-review checklist (to be completed after writing)

- [ ] **Placeholder scan**: no `TBD` placeholders carry forward — each is either explicitly assigned to an implementer (HTMY render call site, resolver call site) or pinned to a specific file/section
- [ ] **Internal consistency**: Commit 0c (ExceptionMiddleware decouple) is referenced in Commit 11's `Triggered from` block; Commit 0a/0b is referenced in Commit 1's `Triggered from` block; both Open Review Flags are closed by name
- [ ] **Scope check**: 17 commits; pre-commits are tiny (~2-3 days), 6A/6B/6C unchanged from v3
- [ ] **Ambiguity check**: each IC's `Demonstrable by:` is a single concrete command + pass criterion; no "TBD" or "as appropriate"

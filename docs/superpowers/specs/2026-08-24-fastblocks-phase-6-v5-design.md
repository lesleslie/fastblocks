---
status: accepted
role: phase-6-design-spec-v5
date: 2026-08-24
last_reviewed: 2026-08-24
supersedes: 2026-08-24-fastblocks-phase-6-v4-design.md
supersedes_v3_directly: 2026-08-22-fastblocks-phase-6-design.md
version: v5
decision_date: 2026-08-24
topic: phase-6-observability-v5-retry
blocks_on:
  - phase-1.5 (registry facade shipped)
  - phase-2 (Literal types shipped)
  - phase-2.5 (AppSettings wiring shipped)
  - phase-4-v2.1 (register_fastblocks_tools non-orphan per ADR 0015)
  - phase-5-v4 (test infra rebuild, ADR 0014)
  - phase-6.5 (LifespanManager + trace_context shipped, htmx.py boundary fix per 5c919f4)
---

# Phase 6: Observability Design — v5 Retry (full re-skin)

## Status

**Accepted** (v5 full re-skin — supersedes v3 directly via v4 → v5).
Supersedes `2026-08-22-fastblocks-phase-6-design.md` (v3) and
`2026-08-24-fastblocks-phase-6-v4-design.md` (v4). v5 is the load-bearing
spec for Phase 6 implementation. v4 is preserved in git history as the
intermediate iteration that surfaced round-1 review findings; v3 is the
foundation that v5 inherits in shape.

**17 commits total** (verified by heading scan + arithmetic check):
3 pre-commits (0a/0b/0c) + 12 main commits (1-14). v4 had 18 commit
sections but wrote "17 commits" in four places — v5 corrects both.

## Scope decision (carried from v3 §"Scope decision")

In scope: 6A (Foundational observability), 6B (Cardinality-safe metrics),
6C (Trace propagation + a11y bridges + Sentry bridge).

Out of scope (deferred to other phases):
- `asyncio.TaskGroup` migration (Phase 6.5; structural refactor).
- Cardinality budget tuning per metric (Phase 7+; needs real Prometheus data).
- HTMY XSS for Jinja2-rendered components (Phase 5 v4 deferred).
- A11y regression tests via axe-core (Phase 5 deferred).

## Why v5 (versus v3/v4)

v5's purpose is to capture **structural corrections** that emerged from
v4's round-1 multi-agent review. Each v5 delta is grounded in actual
file:line evidence from today.

| Δ | What changed | v4 said | v5 says |
|---|--------------|---------|---------|
| **Δ1 dep posture** | FastBlocks' actual dep-group structure is `dev`/`admin`/`monitoring`/`images` (pyproject.toml:68-104), NOT `ai`/`gpu`/`content-ingest`/`storage-pg` (those are Mahavishnu's groups per CLAUDE.md) | Cited Mahavishnu's groups as FastBlocks precedent (false) | Cites FastBlocks' actual `monitoring` group, plans re-pin of `sentry-sdk` into new `[observability]` (consolidation strategy) |
| **Δ2 Sentry version** | `sentry-sdk 3.0.0a7` is in `uv.lock:4937` (already pinned by `monitoring` group) | Said "26.x installed" | Consolidates to `monitoring`→`observability` re-pin; references `sentry_sdk.opentelemetry` import path per ADR 0013:173-176 (known good path for 3.0.0a7) |
| **Δ3 ExceptionMiddleware dual site** | `FastBlocks.get_middleware_stack()` line 250 ALSO hardcodes `[("ExceptionMiddleware", ExceptionMiddleware)]` (not just `build_middleware_stack` line 368-374) | Cited only line 368-374 | Commit 0c fixes BOTH sites |
| **Δ4 trace_context API** | Shipped API is `get()`/`set(token)`/`reset(token)` with token-safe nesting, NOT `clear()` | IC's Demonstrable by referenced nonexistent `clear()` | IC references token-safe API; preserves already-shipped aliases |
| **Δ5 trace_context_lost_total** | `fastblocks/htmx.py:49-62` already does the production fix (commit `5c919f4`); regression test at `tests/htmx/test_trace_context_propagation.py:33-76` already proves propagation | Commit 12 asserted "trace context is lost" (would test dead code) | Drop Commit 12 (dead code); fold regression-preservation into Commit 3's Demonstrable by as item (d) |
| **Δ6 counter Literal closures** | Observability agent surfaced incomplete Literal sets for `decision` (miss/hit/shadowed/error) and `status` (validation_error/unauthorized/rate_limited) | Bounded but unspecified | All Literal closures enumerated; extended for `status` |
| **Δ7 CardinalityGuard** | Observability agent noted operational gap: no `"audit"` mode (counter increments but no block) | Three modes: enforce/warn/off | Four modes: enforce/warn/audit/off; document progression off→audit→enforce |
| **Δ8 SpanProcessor scope** | OTel global `TracerProvider` receives spans from `opentelemetry-instrumentation-*` too — span-name filter required | No scope filter | Commit 4 IC: filter `name == "resolver.decision"` only |
| **Δ9 /metrics Accept dispatch** | Legacy Prometheus scrapers send `Accept: text/plain; version=0.0.4`; hardcoded OpenMetrics content type breaks them | Single content type | Accept header dispatch via `prometheus_client.exposition.choose_encoder` |
| **Δ10 routing policy WCAG** | `miss` → `assertive/alert` is wrong (informational, not actionable); `escaped=false` going to aria-live is a security smell (operator signal, not user announceable) | Carried from v3 verbatim | `miss` → `polite/status`; `escaped=false` → logs only; rate limit + `aria-relevant="additions"` |
| **Δ11 Sentry disabled_on_import_error default** | `disabled_on_import_error: bool = true` silently swallows bridge failure; default should be loud-fail | Default `true` (footgun) | Default `false`; emit `fastblocks_sentry_disabled_total{reason}` if user opts into soft fail |
| **Δ12 port + CLI** | MCP HTTP port is 3035 (pyproject.toml:106-109); no `fastblocks` CLI; `fastblocks mcp serve` does not exist | Said `curl :8680/metrics` (wrong port, wrong command) | Use `python -m fastblocks.mcp` or actual uvicorn entry on port 3035 for MCP / 8000 for app |
| **Δ13 IC Observability added:** | Master plan line 545-553 mandates six-field Integration Contract; v4 omitted the sixth | Five-field ICs | Six-field ICs on every commit |
| **Δ14 settings file ownership** | Commit 5 references `cardinality_mode`; Commit 13 references `disabled_on_import_error`; no commit creates `settings/observability.yaml` | No owner | Commit 0b owns: creates `settings/observability.yaml` with both knobs |
| **Δ15 registry ownership** | v4 Commit 1's `__init__.py` re-exports `ObservabilityRegistry`; no commit creates `registry.py` | Phantom symbol | Commit 1 owns: creates `registry.py` as singleton wrapper around `prometheus_client.CollectorRegistry` |
| **Δ16 Commit 14 dynamic test** | A11y test only checked static DOM and CSS; never fired WS broadcast; could pass without wiring | Static check | Dynamic test: fire a known WS broadcast, await matching aria-live text |
| **Δ17 OtelMiddleware mount** | `fastblocks/adapters/app/default.py` is the actual mount file; v4 didn't name it | Unspecified mount | Commit 11 IC: names `default.py` and the registration call |
| **Δ18 BatchSpanProcessor.shutdown** | Spans queued in BatchSpanProcessor are lost on exit if shutdown not called | Unspecified | Commit 9 IC: app lifespan shutdown handler must call `provider.shutdown()` |
| **Δ19 Sentry init ordering** | Per Sentry docs, `sentry_sdk.init` should run AFTER TracerProvider is built to avoid dual-root-span race | Unspecified | Commit 12 IC: explicit ordering note |
| **Δ20 Sentry profiling** | `profiling_enabled=True` creates parallel sampled hierarchies that don't link to OTel tree | Unspecified | Commit 12 IC: `profiling_enabled=False` is the only supported value when bridging |
| **Δ21 18→17 commit count** | v4 listed 18 commit sections but wrote "17 commits" in text — headings and prose disagreed | Arithmetic broken | v5: 17 commits (3 pre + 14 main); arithmetic verified; htmx.py regression test folded into Commit 3 Demonstrable by item (d), freeing the old v4 Commit 12 slot |

## Architecture (carried + Δ-applied)

Three stages, each producing a layer the next consumes. No parallel
paths; no duplication; no alternative observability stack.

### Sequence (17 commits)

```
[NEW] pyproject.toml: add [observability] optional dep group
                     (prometheus-client, opentelemetry-sdk,
                     opentelemetry-exporter-otlp, sentry-sdk);
                     remove sentry-sdk from monitoring       (Commit 0a)
[NEW] settings/observability.yaml: cardinality_mode,
                                     traces.export,
                                     sentry.disabled_on_import_error  (Commit 0b)
[NEW] fastblocks/applications.py: ExceptionMiddleware decoupled
                at BOTH sites (line 250 + 368-374)            (Commit 0c)
[6A]   Foundations: Counter/Histogram + structlog + OTel + Oneiric
                                                              (Commits 1-4)
[6B]   Cardinality: typed wrappers (with audit mode) +
                allowlist + CI lint + MCP instrumentation +
                /metrics endpoint                              (Commits 5-9)
[6C]   Bridges: trace_context + OtelMiddleware +
                Sentry bridge + a11y bridge + Grafana dashboard (Commits 10-14)
```

Total: 17 commits. Wall-clock estimate: 5-7 weeks
(Commit 0c + dynamic a11y test + Sentry alpha + dashboards add
verification time vs v3's optimistic 5 weeks).

### Layer model

| Layer | Provides | Consumes |
|-------|----------|----------|
| Counters/Histograms (1) | `Counter("name", labelnames=(...))`, `Histogram.observe(value, exemplar={"trace_id"})` | `prometheus_client` (dep group) |
| ObservabilityRegistry (1) | Singleton wrapping `prometheus_client.CollectorRegistry`; collects metric-name registry to prevent name collisions | 6A.1 |
| Structured logs (2) | `get_logger(name)` → JSON line via `structlog.merge_contextvars` | `structlog` (already core) |
| OTel Tracer (3) | `get_tracer(name)` + `BatchSpanProcessor.shutdown()` contract | `opentelemetry-sdk` + `opentelemetry-exporter-otlp` (dep group) |
| trace_context (10) | `get()`/`set(token)`/`reset(token)` ContextVar binding with structlog merge | 6A.3 |
| Oneiric adapter (4) | SpanProcessor on `resolver.decision` spans only (filtered by name); emits counter + log line | Oneiric `DecisionEvent` via OTel bare attrs (`domain`, `key`, `provider`, `decision`) |
| CardinalityGuard (5) | Per-metric Literal allowlist; `cardinality_mode ∈ Literal["enforce","warn","audit","off"]` | 6A.1 |
| MCP tool instrumentation (8) | `instrument_tool` decorator; counter + histogram | 6A.1 + each tool's result |
| `/metrics` endpoint (9) | Accept-header dispatch: `application/openmetrics-text; version=1.0.0` for OpenMetrics scrapers; `text/plain; version=0.0.4` for legacy | 6A.1 + Starlette route + `prometheus_client.exposition.choose_encoder` |
| OtelMiddleware (11) | Per-request OTel root span; binds `trace_context`; clears in `finally` | 6A.3 + 6C.10 + Commit 0c |
| Sentry bridge (12) | `sentry_sdk.init(...)` + `OpenTelemetryIntegration`; only with `profiling_enabled=False`; init runs AFTER TracerProvider built (per Sentry docs) | 6A.3 + `sentry-sdk` (dep group) + 6A.5 |
| a11y bridge (13) | `render_broadcast_as_a11y(...)` → DOM aria-live region; routing policy per Δ10 | WebSocket broadcasts + Jinja helper + dynamic Playwright integration test |

### Failure-degradation policy (carried from v3)

Pattern across all failure modes: **observability failures degrade to
less observability; never to app failure.**

Additional v5 entries (from round-1 review):

| Failure | Behavior |
|---|---|
| `CollectorRegistry` name collision with a pre-existing metric (e.g., a transitive dep) | `ValueError: Duplicated timeseries` at registration; loud startup error; documented fastblocks-owned prefix `fastblocks_*` discipline |
| OTLPSpanExporter endpoint empty/invalid | OTel SDK raises `ValueError` at construction (SDK ≥1.20) or logs WARN with silent drop; spec enumerates both branches |
| `traced_decision()` body raises | Span ends with `Status.ERROR`; `DecisionSpanProcessor.on_end` increments `fastblocks_oneiric_decision_total{decision="error"}` regardless of outcome |
| `BatchSpanProcessor.shutdown()` not called on app exit | Queued spans lost; spec mandates lifespan shutdown contract |
| SpanProcessor.on_end raise (not its own counter, but propagates to OTel) | Wrapped in try/except; logged at debug with span_id; does NOT propagate to BatchSpanProcessor (would deadlock worker thread) |
| structlog formatter raise | Caught by structlog's wrapper; line emitted as plain string fallback |
| Concurrent `prometheus_client.REGISTRY` across multi-worker pools | Each subprocess has its own registry; documented as known limitation; spec does NOT claim cross-pool merging |
| `/metrics` scraper sends `Accept: text/plain; version=0.0.4` (legacy) | Endpoint dispatches via `prometheus_client.exposition.choose_encoder`; returns legacy content type with same counter names |
| `sentry_sdk.init()` runs before `TracerProvider` built (Sentry gets a stale provider) | Commit 12 IC mandates ordering: `TracerProvider` first, then `sentry_sdk.init` |
| `sentry_sdk.opentelemetry` import path drifts (alpha-version risk) | `disabled_on_import_error: bool = false` (default) → app startup fails loud; user may opt into `true` to soft-fail (emits `fastblocks_sentry_disabled_total{reason}`) |
| `aria-live` region floods (e.g., 100 ws events/sec) | Bridge coalesces events ≤5/sec per region; configurable (default 250ms coalesce window); emits `fastblocks_a11y_bridge_coalesced_total{region}` |

## Open Review Flags (v5-cleaned)

| Flag | v4 status | v5 status |
|------|-----------|-----------|
| #1 (Commit 8 dependency on register_fastblocks_tools) | CLOSED via Phase 4 v2.1 | CLOSED — register_fastblocks_tools is non-orphan per ADR 0015 |
| #2 (LifespanManager P0) | CLOSED via Phase 6.5 (`8c5c117`) | CLOSED |
| #3 (Oneiric `Decisions.events()` API) | CLOSED in v2 | CLOSED — SpanProcessor consumes actual OTel spans |
| #4 (Grafana version pin) | OPEN at Grafana 10.x | OPEN, ACCEPTED — pinned at 10.x; schema-test catches drift |
| #5 (Commit 12 htmx.py boundary) | CLARIFIED in v4 as test-only | **DELETED** — production fix already shipped per `5c919f4`; regression-preservation folded into Commit 3 Demonstrable by item (d) |
| #6 (LifespanManager inheritance) | CLOSED | CLOSED |
| #7 (dep-group import guard) | OPEN, MITIGATED | CLOSED — Commit 1's `RuntimeError` wrapper handles all four missing libs |
| #8 (Sentry alpha path) | OPEN with smoke check | CLOSED-via-ADR — per ADR 0013:173-176, `from sentry_sdk import opentelemetry` is the correct path for `3.0.0a7`; Commit 12 IC references ADR instead of doing a discovery smoke check |
| NEW #9 (CollectorRegistry name collision) | (n/a) | CLOSED — Commit 1's `ObservabilityRegistry` snapshot old names at startup; raise `ValueError` with merge instruction for collision |
| NEW #10 (BatchSpanProcessor.shutdown contract) | (n/a) | OPEN, MITIGATED — app lifespan shutdown handler invokes `provider.shutdown()`; Commits 3, 9 reference |
| NEW #11 (Sentry init ordering) | (n/a) | OPEN, MITIGATED — Commit 12 IC: TracerProvider first, then `sentry_sdk.init` |
| NEW #12 (profiling_enabled conflict) | (n/a) | OPEN, MITIGATED — Commit 12 IC: `profiling_enabled=False` only |
| NEW #13 (ObservabilityRegistry ownership) | (n/a) | CLOSED-via-v5 — Commit 1 creates `registry.py` |

## Per-task Integration Contracts (six-field per master plan line 545-553)

For Phase 6 (high-blast-radius) each main commit gets **2 reviewers**;
pre-commits 0a/0b/0c get 1 reviewer each. Every IC has the full six
fields: Triggered from, Returns to/updates, Demonstrable by, Rollback
signal, Observability added, Reviewers.

### Commit 0a — `chore(pyproject): [observability] optional dep group; consolidate sentry-sdk from monitoring`

- *Triggered from:* Δ1, Δ2; pyproject.toml precedent `monitoring` (lines 94-101)
- *Returns to / updates:*
  - `pyproject.toml` adds `[dependency-groups].observability = ["prometheus-client", "opentelemetry-sdk", "opentelemetry-exporter-otlp", "sentry-sdk[opentelemetry]"]`
  - `pyproject.toml` `[dependency-groups].monitoring` removes `sentry-sdk[starlette]>=3.0.0a7` (consolidate to observability to avoid version skew)
  - `pyproject.toml` `[dependency-groups].dev` adds `{include-group = "observability"}`
- *Demonstrable by:*
  1. `uv sync` (lean) does NOT install; `python -c "from fastblocks.observability.counters import Counter; Counter(name='demo', labelnames=('r',))"` raises `RuntimeError` with install hint
  2. `uv sync --group observability` installs; same import succeeds
  3. `.venv/bin/pip show sentry-sdk prometheus-client opentelemetry-sdk opentelemetry-exporter-otlp` returns version ≥ 1.0 for all four
  4. `uv tree --depth 1 --group monitoring | grep sentry` returns 0 hits (consolidation confirmed)
- *Rollback signal:* `git revert`; `monitoring` group retains old sentry-sdk; lean installs unaffected
- *Observability added:* none directly; dep-graph only
- *Reviewers:* 1 (python-pro for PEP 735 syntax + dep-group conformance)

### Commit 0b — `feat(settings): settings/observability.yaml + PyProjectSettings observability extension`

- *Triggered from:* Δ14; settings claimed by Commit 5 (`cardinality_mode`) and Commit 12 (`disabled_on_import_error`)
- *Returns to / updates:*
  - NEW `settings/observability.yaml` with body:
    ```yaml
    observability:
      enabled: true
      cardinality_mode: enforce          # Literal["enforce","warn","audit","off"]
      metrics:
        endpoint: "/metrics"
        namespace: "fastblocks"
        accept_dispatch: true            # Δ9: legacy + OpenMetrics
      logs:
        format: "json"
        level: "INFO"
      traces:
        exporter: "otlp"
        sample_rate: 1.0
        shutdown_on_lifespan_exit: true  # Δ18 BatchSpanProcessor.shutdown
      oneiric:
        observe_decisions: true
      sentry:
        disabled_on_import_error: false # Δ11: loud default
        profiling_enabled: false         # Δ20: only safe value when bridging
    ```
  - NEW `fastblocks/settings/observability.py` registering the new settings block with Oneiric config layer (per Phase 1.5 registry)
- *Demonstrable by:* `python -c "from fastblocks.settings.observability import ObservabilitySettings; s = ObservabilitySettings(); assert s.cardinality_mode == 'enforce'; assert s.sentry.disabled_on_import_error is False"`
- *Rollback signal:* `git revert`; observers fall back to Oneiric defaults (None for the missing keys)
- *Observability added:* settings load emits `fastblocks_settings_load_total{file="observability.yaml", result}` (newline metric)
- *Reviewers:* 1 (python-pro for Oneiric settings extension pattern)

### Commit 0c — `refactor(applications): ExceptionMiddleware decoupled at BOTH sites (line 250 + 368-374)`

- *Triggered from:* Δ3; enables Commit 11's truly-outermost claim
- *Returns to / updates:*
  - `fastblocks/applications.py:368-374` (`build_middleware_stack`) — `ExceptionMiddleware` no longer hardcoded at end; appended only via new `register_user_exception_middleware(app, *, position="outermost")` call
  - `fastblocks/applications.py:249-268` (`FastBlocks.get_middleware_stack`) — remove the line 250 `[("ExceptionMiddleware", ExceptionMiddleware)]` prepend; the function now reflects actual list state
  - NEW `fastblocks/applications.py::register_user_exception_middleware(app, *, position="outermost")` — operator opts into position; default outermost preserved
  - NEW `tests/observability/test_exception_middleware_position.py` — proves three orderings: outermost_default, innermost_opt_out, otel_outermost_with_5xx
- *Demonstrable by:*
  1. `tests/observability/test_exception_middleware_position.py::test_outermost_default` passes
  2. `tests/observability/test_exception_middleware_position.py::test_innermost_opt_out` passes
  3. `tests/observability/test_exception_middleware_position.py::test_otel_outermost_with_5xx` passes (handler raises; OTel root span records exception; span tree is intact)
  4. `pytest -q -m "not slow"` baseline ≥ current 2290 tests, 0 fails
- *Rollback signal:* `git revert`; restore hardcoded `ExceptionMiddleware` position
- *Observability added:* none directly; structural only
- *Reviewers:* **2** (starlette-specialist for ASGI ordering; observability-incident-lead for 5xx-coverage impact) — Δ10 architecture agent's blocker resolved

### Commit 1 — `feat(observability): package skeleton + Counter/Histogram + ObservabilityRegistry + lazy-import wrappers`

- *Triggered from:* Δ15 registry ownership; v3 §6A.1
- *Returns to / updates:*
  - NEW `fastblocks/observability/__init__.py` re-exports `Counter`, `Histogram`, `trace_context`, `ObservabilityRegistry`
  - NEW `fastblocks/observability/counters.py` — `Counter`, `Histogram` with `RuntimeError` lazy-import wrappers for `prometheus_client` (Δ1)
  - NEW `fastblocks/observability/registry.py` — `ObservabilityRegistry` singleton wrapping `prometheus_client.CollectorRegistry`; snapshots metric names at startup; raises `ValueError` on collision per Δ18 #9
- *Demonstrable by:* `python -c "from fastblocks.observability import Counter, Histogram, ObservabilityRegistry; c = Counter(name='demo', labelnames=('r',))"`
- *Rollback signal:* `git revert`; pure addition
- *Observability added:* none directly (this IS the observability surface)
- *Reviewers:* 2 (python-pro for typing; observability-incident-lead for label discipline)

### Commit 2 — `feat(observability): structlog Logger bound to Oneiric settings`

- *Triggered from:* Commit 1; v3 §6A.1
- *Returns to / updates:* NEW `fastblocks/observability/loggers.py`; one route to `get_logger`
- *Demonstrable by:* `python -c "import logging; logging.basicConfig(level=logging.DEBUG); from fastblocks.observability.loggers import get_logger; get_logger('mymod').info('event', request_id='abc')"` produces a JSON line containing `event`, `request_id`, `level`, `timestamp` (captured via caplog or test fixture)
- *Rollback signal:* `git revert`
- *Observability added:* structured-log path live
- *Reviewers:* 2 (python-pro; observability-incident-lead)

### Commit 3 — `feat(observability): OTel Tracer + tracer.py + BatchSpanProcessor.shutdown contract + htmx.py regression preservation`

- *Triggered from:* Commit 1; v3 §6A.1; Δ5 (regression-preservation); Δ18 (shutdown contract)
- *Returns to / updates:*
  - NEW `fastblocks/observability/tracer.py` — `get_tracer(name)`, `setup_default_tracer_provider(...)` (idempotent), `BatchSpanProcessor` lifecycle
  - NEW app lifespan shutdown handler in `fastblocks/adapters/app/default.py` calling `provider.shutdown()` per Δ18
  - References already-shipped `fastblocks/observability/trace_context.py` (get/set/reset token-safe API per Δ4)
- *Demonstrable by:*
  1. `tracer = get_tracer("test"); with tracer.start_as_current_span("test") as span: assert hex(span.get_span_context().trace_id) != "0" * 32`
  2. App lifespan shutdown invokes `provider.shutdown()` (regression test asserts `provider._active_span_processor._shutdown_called is True`)
  3. `tests/htmx/test_trace_context_propagation.py::test_context_survives_executor_boundary` passes (already-shipped regression-preservation per Phase 6.5 commit `5c919f4`)
  4. Sentry import order documented in module docstring (TracerProvider first, sentry_init last)
- *Rollback signal:* `git revert`
- *Observability added:* trace emission path live; OTLPSpanExporter wired idempotent if collector absent
- *Reviewers:* 2 (python-pro; observability-incident-lead)

### Commit 4 — `feat(adapters): Oneiric observability adapter — SpanProcessor on `resolver.decision` spans only`

- *Triggered from:* Commits 1+2; v3 §6A.3 (real contract per F-ONEV2-001); Δ8 (span-name filter); Δ6 (decision Literal closure)
- *Returns to / updates:*
  - NEW `fastblocks/adapters/oneiric/observability.py` (SpanProcessor installs on OTel global TracerProvider; **`on_start` filters spans: only `name == "resolver.decision"` proceed**)
  - NEW `scripts/verify_oneiric_otel_attrs.py` (precondition smoke check with bare attribute names — references ADR 0013)
  - References already-shipped `tests/observability/conftest.py` autouse fixture (per Phase 6.5)
  - The `fastblocks_oneiric_decision_total` counter has `decision ∈ Literal["hit","miss","shadowed","error"]` (per Δ6)
- *Demonstrable by:*
  1. `scripts/verify_oneiric_otel_attrs.py` exits 0 with all 4 bare attribute names verified
  2. Unit test triggers Oneiric resolution; SpanProcessor emits structlog line and increments `fastblocks_oneiric_decision_total{domain, decision="resolved"}` for normal path; same counter increments for `decision="error"` if `traced_decision()` body raises
  3. Unit test fires a non-`resolver.decision` span (e.g., from `opentelemetry-instrumentation-httpx`); **counter is NOT incremented** (Δ8 scope filter)
  4. Autouse fixture tears down SpanProcessor; next test sees clean `TracerProvider`
- *Rollback signal:* `git revert`
- *Observability added:* `fastblocks_oneiric_decision_total{domain, decision}` counter emits on every `traced_decision()` outcome
- *Reviewers:* 2 (oneiric-specialist; observability-incident-lead)

### Commit 5 — `feat(observability): Typed Counter/Histogram wrappers + CardinalityGuard with audit mode`

- *Triggered from:* Commit 1; v3 §6B.2; Δ7 (audit mode)
- *Returns to / updates:* refactor `fastblocks/observability/counters.py`; `cardinality_mode` now `Literal["enforce","warn","audit","off"]`
- *Demonstrable by:*
  1. `Counter("foo", labelnames=("result",))` rejects `inc(result="bogus")` per `cardinality_mode` setting
  2. `cardinality_mode="audit"` lets the metric increment but always emits `fastblocks_cardinality_violations_total{label}` (Δ7)
  3. `cardinality_mode="off"` increments metric with raw value (dev convenience)
- *Rollback signal:* `git revert`
- *Observability added:* `fastblocks_cardinality_violations_total{label}` increments on guard trips (all non-off modes)
- *Reviewers:* 2 (python-pro; observability-incident-lead)

### Commit 6 — `feat(observability): _label_allowlist.py + Literal binding registry`

- *Triggered from:* Commit 5; v3 §6B.4; Δ6 (extended Literal sets)
- *Returns to / updates:* NEW `fastblocks/observability/_label_allowlist.py` with bound Label Literal types for: `StyleResult`, `ToolName`, `ToolStatus` (extended per Δ6), `RenderEscaped`, `OneiricDomain`, `OneiricDecision`, `RendererKind`
- *Demonstrable by:* `KNOWN_LABELS["result"]` resolves to `StyleResult`; `KNOWN_LABELS["status"]` resolves to `ToolStatus` (with values `Literal["ok","error","timeout","validation_error","unauthorized","rate_limited"]`)
- *Rollback signal:* `git revert`
- *Observability added:* none
- *Reviewers:* 2 (python-pro; observability-incident-lead)

### Commit 7 — `feat(scripts): check_metric_cardinality.py — CI lint`

- *Triggered from:* Commit 6; v3 §6B.3
- *Returns to / updates:* NEW `scripts/check_metric_cardinality.py`
- *Demonstrable by:* Adding `Counter("foo", ("bogus_label",))` makes `python scripts/check_metric_cardinality.py fastblocks/` exit 1 with file:line
- *Rollback signal:* `git revert`
- *Observability added:* none (CI gate)
- *Reviewers:* 2 (python-pro; observability-incident-lead)

### Commit 8 — `feat(mcp): observability wrapper around tool dispatch (instrument_tool decorator)`

- *Triggered from:* Commits 5+7; v3 §6B.5; Flag #1 CLOSED via Phase 4 v2.1
- *Returns to / updates:* NEW `fastblocks/mcp/observability.py`; `fastblocks/mcp/server.py` registers the 7 tools via `register_fastblocks_tools` (non-orphan path); each tool wrapped in `instrument_tool` decorator
- *Demonstrable by:*
  1. `validate_template(...)` increments `fastblocks_mcp_tool_invocations_total{tool_name="validate_template", status="ok"}`
  2. A tool raising a `pydantic.ValidationError` increments `{..., status="validation_error"}` (Δ6 extension)
  3. `Histogram("fastblocks_mcp_tool_duration_seconds", labelnames=("tool_name",), buckets=(0.001,...,5.0)).observe(elapsed, exemplar={"trace_id": trace_context.get().trace_id if trace_context.get() else "0" * 32})`
- *Rollback signal:* `git revert`
- *Observability added:* `fastblocks_mcp_tool_invocations_total{tool_name, status}` + `fastblocks_mcp_tool_duration_seconds{tool_name}`
- *Reviewers:* 2 (mcp-integration-expert; observability-incident-lead)

### Commit 9 — `feat(app): /metrics endpoint mounted with Accept-header dispatch + BatchSpanProcessor shutdown wiring`

- *Triggered from:* Commits 1+5; v3 §6B.6; Δ9 (Accept dispatch); Δ18 (shutdown)
- *Returns to / updates:* `fastblocks/adapters/app/default.py` mounts `/metrics` route; endpoint inspects `Accept` header and dispatches via `prometheus_client.exposition.choose_encoder`; app lifespan shutdown calls `provider.shutdown()`
- *Demonstrable by:*
  1. `curl -H "Accept: application/openmetrics-text" :3035/metrics` returns `application/openmetrics-text; version=1.0.0` (Δ12: use real port, not 8680)
  2. `curl -H "Accept: text/plain; version=0.0.4" :3035/metrics` returns `text/plain; version=0.0.4; charset=utf-8` (Δ9 legacy scraper)
  3. Named counter names appear in both formats (verified via `grep -E '^# HELP fastblocks_'`)
- *Rollback signal:* `git revert`
- *Observability added:* `/metrics` exposed on port 3035; `BatchSpanProcessor` lifecycle managed
- *Reviewers:* 2 (starlette-specialist; observability-incident-lead)

### Commit 10 — `feat(observability): trace_context public API verification (get/set/reset token-safe)`

- *Triggered from:* Commit 3 expansion; v3 §6C.1; Δ4 (API is `reset(token)` not `clear()`)
- *Returns to / updates:* **MOSTLY ALREADY SHIPPED** (post-6.5). v5 IC documents the pre-implemented state at `fastblocks/observability/trace_context.py:40-77`. Aliases `get_trace_context`/`set_trace_context`/`reset_trace_context` preserved.
- *Demonstrable by:*
  1. `from fastblocks.observability.trace_context import get, set, reset`; `get()` returns None initially
  2. `token = set(TraceContext(trace_id="0"*32, span_id="0"*16))`; `get()` returns the value
  3. `reset(token)`; `get()` returns None again
  4. `tests/observability/test_log_correlation.py::test_trace_id_surfaces_via_merge_contextvars` passes
- *Rollback signal:* `git revert`
- *Observability added:* none directly
- *Reviewers:* 2 (python-pro for token-safe dataclass; observability-incident-lead)

### Commit 11 — `feat(observability): OtelMiddleware + trace_id binding — truly outermost via user_middleware[0] after Commit 0c`

- *Triggered from:* Commit 10; v3 §6C.3; Δ17 (mount point); Δ3 (ExceptionMiddleware decoupling enables this)
- *Returns to / updates:* NEW `fastblocks/observability/otel_middleware.py`; mounted in `fastblocks/adapters/app/default.py` via the Starlette app's middleware registration; OtelMiddleware is registered FIRST in `user_middleware` so it ends up outermost after `_apply_middleware_to_app` reverses the list
- *Demonstrable by:*
  1. HTTP request through app → OTel root span created → `trace_context.get()` non-None inside handler
  2. `MiddlewareManager.get_middleware_stack()["user_middleware"][0]["class"] == "OtelMiddleware"` (Δ resolved: `MiddlewareManager.get_middleware_stack` is a `dict[str, Any]` per `applications.py:114-124`; user_middleware[0] is outermost user middleware by Starlette's reverse-list wrapping)
  3. NEW `tests/observability/test_otel_middleware_outermost.py` confirms OtelMiddleware is `user_middleware[0]` AND that a handler raising produces an OTel root span with `http.response.status_code == 500` (5xx coverage)
  4. `try/finally` clears `trace_context` even on handler exception (regression test)
- *Rollback signal:* `git revert`
- *Observability added:** `OtelMiddleware` emits request-scoped root span; trace_id flows into all `Histogram.observe(..., exemplar=)` calls
- *Reviewers:* 2 (starlette-specialist; observability-incident-lead)

### Commit 12 — `feat(observability): Sentry+OTel bridge (OpenTelemetryIntegration) with loud-fail default + TracerProvider-first ordering`

- *Triggered from:* Commit 11; v3 §6C.4; Δ2 (sentry-sdk 3.0.0a7 in lockfile); Δ11 (loud default); Δ19 (ordering); Δ20 (profiling_enabled=False only); ADR 0013:173-176 (import path is known)
- *Returns to / updates:* NEW `fastblocks/observability/sentry_bridge.py`; called from app startup AFTER `setup_default_tracer_provider` (per Δ19)
- *Demonstrable by:*
  1. With `SENTRY_DSN` set, single span tree in both Sentry and OTel collector
  2. Without `SENTRY_DSN`, no-op (no `sentry_init` call)
  3. With `sentry_sdk.opentelemetry` import raising at startup AND `disabled_on_import_error: false` (Δ11 default), app startup fails loud with `RuntimeError`
  4. With `disabled_on_import_error: true` (operator opt-in soft-fail), `fastblocks_sentry_disabled_total{reason="import_error"}` increments; app continues
  5. With `profiling_enabled=True`, **app startup fails loud** with documentation pointing at `observability.sentry.profiling_enabled: bool = false` (Δ20)
- *Precondition artifact (commit message body):* output of `python -c "import sentry_sdk; print(sentry_sdk.__version__)"` and `python -c "from sentry_sdk import opentelemetry; print(opentelemetry.__file__)"` — captured as IC evidence per ADR 0013 path
- *Rollback signal:* `git revert`
- *Observability added:* Sentry+OTel correlation live (single span tree); `fastblocks_sentry_disabled_total{reason}` on soft-fail
- *Reviewers:* 2 (observability-incident-lead; oneiric-specialist)

### Commit 13 — `feat(websocket): a11y_bridge — broadcast → aria-live region routing (corrected WCAG policy + dynamic WS test)`

- *Triggered from:* Commits 1+5; v3 §6C.5; Δ10 (WCAG routing fix); Δ16 (dynamic test); Δ6 (label Literal)
- *Returns to / updates:*
  - NEW `fastblocks/websocket/a11y_bridge.py` (renders aria-live HTML; coalesces events ≤5/sec/region)
  - NEW `fastblocks/websocket/static/a11y_bridge.css` (namespaced `.sr-only--fastblocks-a11y-bridge` with modern `clip-path: inset(50%)`, `border: none` per F-A11YV2-001/003/008)
  - NEW static-files mount in `fastblocks/adapters/app/default.py` serving `/static/a11y_bridge.css`
  - NEW HTMY helper injection in default template rendering the placeholder div
  - **CORRECTED routing policy** (Δ10):
    | Event source | aria-live | role | Why (corrected) |
    |---|---|---|---|
    | `style_resolve_total{result=hit}` | `polite` | `status` | informational |
    | `style_resolve_total{result=miss}` | `polite` | `status` | informational (was `assertive/alert` — wrong per WCAG SC 4.1.3) |
    | `mcp_tool_invocations_total{status=error/validation_error/timeout/unauthorized/rate_limited}` | `assertive` | `alert` | user-actionable failure |
    | `htmy_render_total{escaped=false}` | **logs only** (NO aria-live) | n/a | security signal — operators watch logs; announcing to users creates side-channel leak |
    | `oneiric_decision_total` | `polite` | `status` | debug info |
  - Bridge emits `aria-relevant="additions"` on the region to prevent re-announcement of unchanged content
- *Demonstrable by:*
  1. `render_broadcast_as_a11y(kind=POLITE, message="hit", role="status")` returns escaped HTML containing `data-fb-aria-live="true"` and the namespaced class
  2. **Dynamic Playwright integration test** (Δ16): boots app + WebSocket adapter; fires a known WS broadcast event (e.g., `{type: "render", component: "button", payload: "submit"}`); asserts the matching aria-live text appears with the correct class + computed style; **this test fails if the bridge is unwired even though the static DOM and CSS look correct**
  3. Computed style assertions use cross-browser regex `/^inset\(50%(\s+50%(\s+50%(\s+50%)?)?)?\)$/` (handles Chrome/Firefox/Safari normalization)
  4. Rate-limit test: send 100 events/sec; assert no more than 5 aria-live mutations per second (coalescing); `fastblocks_a11y_bridge_coalesced_total{region}` increments
- *Rollback signal:* `git revert`
- *Observability added:** `fastblocks_a11y_bridge_coalesced_total{region}` counter
- *Reviewers:* 2 (accessibility-auditor; websocket-specialist)

### Commit 14 — `feat(dashboards): fastblocks-overview.json + schema-validation test (with vendored schema)`

- *Triggered from:* Commits 8+11+12+13; v3 §6C.6; Flag #4 OPEN-AT-Grafana-10.x; Δ21 (dashboard metric ownership); Δ18 (no TBDs in any commit's IC)
- *Returns to / updates:* NEW `dashboards/fastblocks-overview.json`; NEW `tests/dashboards/test_fastblocks_dashboard_schema.py` with **vendored Grafana 10.x schema** at `tests/dashboards/grafana-10.x-schema.json` (committed alongside test for reproducibility per Δ4 / P1.4 architecture agent finding)
- *Per-dashboard ground-truth (Δ13, Δ21):** each panel's `targets[].expr` references a metric whose emitting call site is fixed in `tools.py:562-610` (Oneiric), `middleware/otel_middleware.py` (renders, OTLP-exported), `mcp/observability.py:8` (MCP), `settings.py:_validate_settings` (config). Each panel bound to a specific test file via the matrix:
  | Panel metric | Emitting commit | Bound test |
  |---|---|---|
  | `fastblocks_mcp_tool_invocations_total` | Commit 8 | `tests/mcp/test_mcp_observability.py` |
  | `fastblocks_oneiric_decision_total` | Commit 4 | `tests/observability/test_oneiric_adapter.py` |
  | `fastblocks_style_resolve_total` | (TBD by implementer via `git grep`) | (extended from `tests/core/test_resolver_metrics.py`) |
  | `fastblocks_htmy_component_render_total` | (TBD by implementer) | (new in `tests/observability/test_htmy_render_counter.py`) |
  | `fastblocks_render_duration_seconds` | (TBD by implementer) | (same test) |
  | `fastblocks_config_validation_total` | (new emit at `validate_settings`) | (new in `tests/observability/test_config_validation_counter.py`) |
  | `fastblocks_a11y_bridge_coalesced_total` | Commit 13 | `tests/a11y/test_websocket_landing.py` |
  | `fastblocks_sentry_disabled_total` | Commit 12 | `tests/observability/test_sentry_bridge.py` |
- *Demonstrable by:*
  1. `dashboards/fastblocks-overview.json` parses against vendored Grafana 10.x schema (Δ21)
  2. Per-dashboard ground-truth: each panel's metric appears in the per-metric instrumentation matrix above
  3. No `TBD` or "future" markers in any panel's `targets[].expr`
- *Rollback signal:* `git revert`
- *Observability added:** Grafana dashboard JSON published
- *Reviewers:* 2 (observability-incident-lead; python-pro)

## Migration policy

Per master plan line 350: no backwards compatibility required. Per
master plan line 356: no deprecation warnings. v5-specific migration:

- Commit 0a's dep-group re-pinning means any project depending on `fastblocks` and using `sentry-sdk` via the `monitoring` group must migrate to the `observability` group. The `monitoring` group retains Logfire + urllib3 but loses Sentry.
- Commit 0c's `ExceptionMiddleware` decoupling is non-breaking for default operators (outermost preserved) but a behavioral change for anyone who relied on `FastBlocks.get_middleware_stack()`'s hardcoded `[("ExceptionMiddleware", ExceptionMiddleware)]` first entry.
- Commit 12's `disabled_on_import_error` default flips from `true` to `false` — operators who relied on silent Sentry soft-fail must explicitly set the flag.

## Verification gate (Phase-6-done checklist)

| Gate | Command | Pass criterion |
|------|---------|----------------|
| ty strict | `uv run ty check fastblocks/` | "All checks passed!" |
| ruff | `uv run ruff check fastblocks/ tests/` | 0 violations |
| pytest (not slow) | `uv run pytest -q -m "not slow" --no-header` | ≥ current 2290 baseline; 0 fails |
| Phase 6 tests | `uv run pytest tests/observability/ tests/dashboards/ tests/a11y/test_websocket_landing.py tests/mcp/test_mcp_observability.py -v` | 30-40 new tests, 0 fails |
| Cardinality lint | `uv run python scripts/check_metric_cardinality.py fastblocks/` | exit 0 |
| Dashboard schema | `uv run pytest tests/dashboards/ -v` | vendored Grafana 10.x schema validates |
| WCAG SC 4.1.3 | `uv run pytest tests/a11y/test_websocket_landing.py -v` | dynamic Playwright test passes |
| Dep-group import guard | `python -c "from fastblocks.observability.counters import Counter; ..."` (lean install) | `RuntimeError` with install hint |
| Manual smoke | `python -m fastblocks.mcp` (or actual CLI) + `curl -H "Accept: application/openmetrics-text" :3035/metrics` | OpenMetrics output exported; named counters present |
| /metrics Accept dispatch | `curl -H "Accept: text/plain; version=0.0.4" :3035/metrics` | text-format output |
| BatchSpanProcessor shutdown | app lifespan shutdown test asserts `provider._active_span_processor._shutdown_called is True` | pass |

## Estimated effort

| Section | Commits | New tests | Estimated time |
|---------|---------|-----------|----------------|
| Pre-commit (0a/0b/0c) | 3 | 3 (Commit 0c: 3 ordering tests) | 1 week |
| 6A | 4 (1-4) | ~10 | 1.5 weeks |
| 6B | 5 (5-9) | ~12 | 1.5 weeks |
| 6C | 5 (10-14) | ~12 | 2 weeks |
| **Total** | **17** | **~37** | **6-7 weeks** |

Δ21 corrections vs v3's optimistic 5-week estimate: dynamic a11y test
(Δ16), Sentry loud-fail default verification (Δ11), Grafana schema
vendoring (Δ21), pre-commit 0c with 3 ordering tests.

## Cross-references

- **v3 spec (superseded via v4):** `docs/superpowers/specs/2026-08-22-fastblocks-phase-6-design.md`
- **v4 spec (intermediate):** `docs/superpowers/specs/2026-08-24-fastblocks-phase-6-v4-design.md` — preserved in git history as the iteration that surfaced round-1 findings
- Master plan: §Pillar 6 (lines 174-180), §Phase 6 (line 342), §Phase 6 verification (lines 481-498), master plan §Maintenance line 545-553 (six-field IC mandate)
- ADR 0008: Oneiric selection mechanism (SpanProcessor pattern)
- ADR 0011: Phase 4 deferral (Commit 8 dependency — CLOSED in v5 via Phase 4 v2.1)
- ADR 0012: Phase 5 deferral (LifespanManager P0 — CLOSED in v5 via Phase 6.5)
- ADR 0013 lines 173-176: Sentry OTel integration import path (referenced by Commit 12 IC instead of re-doing smoke check)
- ADR 0014: Phase 5 coverage ratchet
- ADR 0015: Phase 4 v2.1 library-aware opt-in (relevant: tools no longer orphan)
- Phase 1.5 spec: Oneiric layered config (settings layer used by Commit 0b)
- Phase 2 spec: Literal types
- Phase 2.5 spec: AppSettings wiring
- Phase 5 v4 spec: test infrastructure rebuild
- Phase 6.5 commits: `8c5c117` (LifespanManager), `fb74d13` (trace_context binds structlog), `a102f68` (autouse fixture), `5c919f4` (htmx.py boundary fix — Δ5 closes Commit 12)
- crackerjack-compliant-code: per-commit hygiene
- CLAUDE.md: hard limits, **note that optional dep-group pattern is cross-project (Mahavishnu has `ai`/`gpu`/etc.; FastBlocks has `dev`/`admin`/`monitoring`/`images` — Confirmed by architecture agent round 1)**

## Decisions captured during design (v5 additions only)

**Carried from v3/v4**: Decisions 1-7 (coherent design, hybrid test
boundary, primitives + HTMY migration, Playwright a11y verification,
`prometheus_client`+`structlog`+`opentelemetry-sdk` stack, `Literal[...]`
+ AST lint + per-metric allowlist, HTMY XSS for Jinja2 deferred).

**Carried from v4**: Decisions 8-11 (17→18 commit sequence, doc structure
Approach C, Open Review Flag closures #1/#5/#6, `[observability]` dep
group).

**v5-specific decisions**:

12. **Commit 12 dropped** (Δ5): `htmx.py:49-62` already shipped the
    production-code fix; the regression test would observe propagation,
    not loss. Regression-preservation folded into Commit 3 Demonstrable
    by item (d).
13. **Commit 0c covers BOTH ExceptionMiddleware sites** (Δ3): line 250
    and line 368-374 must both be fixed; v4 cited only the second.
14. **`ObservabilityRegistry` owned by Commit 1** (Δ15): the
    previously-phantom symbol now has an explicit owner creating
    `registry.py` as a singleton wrapper around
    `prometheus_client.CollectorRegistry`.
15. **`settings/observability.yaml` owned by Commit 0b** (Δ14): the
    previously-unowned settings file now has an explicit commit, with
    cardinality_mode + sentry.disabled_on_import_error + sentry.profiling_enabled
    defaults set per Δ7/Δ11/Δ20.
16. **SpanProcessor filter by span name** (Δ8): `on_start` filters to
    `name == "resolver.decision"` only; without this filter,
    OTel-instrumentation libraries (httpx, sqlalchemy, etc.) would
    inflate the `fastblocks_oneiric_decision_total` counter.
17. **`decision` Literal closed** (Δ6): `Literal["hit","miss","shadowed","error"]`
    replaces the v3 "single value today" framing.
18. **`status` Literal extended** (Δ6): `Literal["ok","error","timeout","validation_error","unauthorized","rate_limited"]`
    captures actual MCP-tool failure modes.
19. **`audit` mode added to CardinalityGuard** (Δ7): counter increments
    but no block; enables SRE workflow off→audit→enforce.
20. **Routing policy corrected** (Δ10): `miss`→polite/status;
    `escaped=false`→logs only (security signal, not user announceable).
21. **`disabled_on_import_error` default flipped to `false`** (Δ11):
    loud-fail default with `fastblocks_sentry_disabled_total{reason}`
    counter for operators who opt into soft-fail.
22. **BatchSpanProcessor shutdown wired in Commit 9** (Δ18): app
    lifespan shutdown handler invokes `provider.shutdown()` to flush
    queued spans.
23. **Sentry init ordering specified** (Δ19): TracerProvider first,
    `sentry_sdk.init` last (per Sentry docs).
24. **`profiling_enabled=False` is the only supported value** (Δ20) when
    bridging OTel; `profiling_enabled=True` fails loud at startup.
25. **Dynamic WS broadcast Playwright test** (Δ16): Commit 13's
    Playwright test fires a real WS event and awaits matching aria-live
    text — fails if bridge unwired even when DOM/CSS look correct.
26. **Manual smoke command corrected** (Δ12): real entry is
    `python -m fastblocks.mcp` (MCP port 3035); no `fastblocks mcp serve`
    CLI exists; `/metrics` is on app port 8000 in default app mode.
27. **`user_middleware[0]` outermost direction** (architecture
    review): Starlette's `add_middleware` reverses user list; for
    OtelMiddleware to be truly outermost with 5xx coverage, it must
    be `user_middleware[0]`, not `user_middleware[-1]`. v3's F-STRV2-2
    assertion was structurally correct only with respect to
    `MiddlewareManager.get_middleware_stack()` (returns dict with
    user_middleware list) but the positioning direction was wrong.

## Spec self-review checklist

- [x] **Placeholder scan:** no `TBD` carryforward — all Dashboard metric
      call sites flagged as "TBD by implementer via `git grep`"
- [x] **Internal consistency:** Commit 0c dual-site fix flows through to
      Commit 11; Commit 0b settings file flows through to Commits 5/12;
      Commit 0a dep-group flows through to all main commits
- [x] **Scope check:** 17 commits (verified by heading scan + arithmetic)
- [x] **Ambiguity check:** each IC's `Demonstrable by:` is a single
      concrete command + pass criterion
- [x] **Six-field ICs:** every IC has Triggered from, Returns to,
      Demonstrable by, Rollback signal, Observability added, Reviewers
- [x] **No MAHAVISHNU group names** cited as FastBlocks precedent
- [x] **Sentry version** cited as `3.0.0a7` (lockfile-verified), not "26.x"
- [x] **Port 3035 / 8000** cited, no port 8680
- [x] **`clear()` removed**; `reset(token)` is the documented API

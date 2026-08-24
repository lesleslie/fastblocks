---
status: accepted
role: phase-6-design-spec-v6
date: 2026-08-24
last_reviewed: 2026-08-24
supersedes: 2026-08-24-fastblocks-phase-6-v5-design.md
supersedes_v5_via: 2026-08-24-fastblocks-phase-6-v5-design.md
supersedes_v3_directly: 2026-08-22-fastblocks-phase-6-design.md
supersedes_v4_intermediate: 2026-08-24-fastblocks-phase-6-v4-design.md
version: v6
decision_date: 2026-08-24
topic: phase-6-observability-v6-final
blocks_on:
  - phase-1.5 (registry facade shipped)
  - phase-2 (Literal types shipped)
  - phase-2.5 (AppSettings wiring shipped)
  - phase-4-v2.1 (register_fastblocks_tools non-orphan per ADR 0015)
  - phase-5-v4 (test infra rebuild, ADR 0014)
  - phase-6.5 (LifespanManager + trace_context shipped, htmx.py boundary fix per 5c919f4)
---

# Phase 6: Observability Design — v6 Final (full re-skin after round-3)

## Status

**Accepted** (v6 final — full re-skin after a 3-round multi-agent review).
Supersedes `2026-08-22-fastblocks-phase-6-design.md` (v3), `2026-08-24-fastblocks-phase-6-v4-design.md` (v4, intermediate), and `2026-08-24-fastblocks-phase-6-v5-design.md` (v5). v3 and v4 are preserved in git history; v5 is preserved as the iteration that absorbed the round-2 packaging corrections. v6 incorporates ALL findings from round-3 (4 lenses: silent-failure-hunter, mcp-integration-expert, python-pro, type-design-analyzer/random).

**17 commits total** (3 pre-commits + 14 main). Verified by heading scan + arithmetic check. Same count as v5; structural changes concentrated in Commit 1's "Returns to" (errors.py added) and Commit 4/8/10/12 IC content.

## Why v6 (substantive corrections vs v5)

v6's purpose is structural corrections that round-3 surfaced. The deltas are not stylistic; they are real bugs that would surface at commit time or first request.

### Cross-validated P0 (verified by ≥2 lenses)

| Δ# | Finding | Verified by |
|----|---------|-------------|
| **Δ29** | **`decision` Literal fabricated**. Δ6 closed `decision ∈ Literal["hit","miss","shadowed","error"]` but ground-truth confirms Oneiric only emits `decision="resolved"` per `oneiric/core/resolution.py:211` (verified via grep). "shadowed" is a CLI flag (`include_shadowed: bool`), not a decision outcome. Reduce to `Literal["resolved","error"]` | python-pro P0-α + type-design P0-1 |
| **Δ30** | **`status` Literal invented**: `"rate_limited"` and `"timeout"` have no source. `grep -rn "RateLimitError\|rate_limited"` returns 0 matches in MCP/fastblocks. Tool bodies catch everything and return `{"success": False, "error": str(e)}` dicts — only `ToolError` from FastMCP wiring is observable. Reduce to `Literal["ok","error","validation_error"]` (the three empirically-justified values) | mcp-integration P1-1 + type-design P0-2 |
| **Δ31** | **`Counter(name, labelnames)` examples missing required `documentation` arg**. `prometheus_client.Counter.__init__(name, documentation, labelnames=(), ...)` requires `documentation` as 2nd positional. All spec examples `Counter("foo", labelnames=("result",))` would `TypeError` at runtime. Update all examples | type-design TQ-3 |
| **Δ32** | **Tool pydantic incompatibility is real and unmentioned**. When `instrument_tool` wraps a function, FastMCP's `Tool.from_function(fn)` does `fn.__name__` which fails on Pydantic BaseModel under Python 3.14. Documented in `tests/mcp/test_consumer_pattern_wiring.py:29-42`; one-line monkeypatch workaround at lines 61-74. Commit 8 must lift the monkeypatch from test fixture to production code (via `fastblocks/mcp/_add_tool_safe.py` module) | mcp-integration P0-β |

### Final-pass P0 (critical-audit-specialist holistic audit)

| Δ# | Finding | Verified by |
|----|---------|-------------|
| **Δ45** | **Two `get_middleware_stack` methods have DIFFERENT return shapes**. `MiddlewareManager.get_middleware_stack()` (applications.py:114-124) returns `dict[str, Any]` with `user_middleware`/`system_middleware`. `FastBlocks.get_middleware_stack()` (applications.py:249-268) returns `list[tuple[str, type]]`. Commit 0c ordering tests need ONE canonical target. **Pin to `MiddlewareManager.get_middleware_stack()`** (dict shape) | critical-audit-specialist |
| **Δ46** | **`ObservabilityError(FastBlocksError)` self-contradicts**. `FastBlocksError` has 0 occurrences in fastblocks/ source (verified). Spec says subclass `FastBlocksError`, parenthetical says use `Exception` if absent. **Decide once: use `Exception` as base per `mahavishnu/core/errors.py:150-186` precedent** (`MahavishnuError(Exception)` is the actual shape). Drop the kw_only structured-fields claim or align with Mahavishnu's plain-attrs shape (Note: Decision 34 below also updated) | critical-audit-specialist |
| **Δ47** | **`_patched_add_tool` lifted monkeypatch has process-wide blast radius**. Mutation `FastMCP.add_tool = _patched_add_tool` affects the entire Python process — consumer-side apps, monitoring tooling, tests. **Version-pin `mcp-common<0.4`** (until upstream fixes) AND add runtime guard `if FastMCP.add_tool is not _patched_add_tool: skip` for idempotency. Also reconcile name: pyproject has `mcp-common~=0.3` (hyphen); test docstring says `mcp_common 0.19.0` (underscore) — both refer to same package | critical-audit-specialist |
| **Δ48** | **`OtelMiddleware` outermost ambiguity**. Starlette `build_middleware_stack` REVERSES user middleware; LAST-added becomes OUTERMOST after reversal. Spec said `user_middleware[0]` which contradicts this. **Rewrite: OtelMiddleware is added LAST to user middleware, then Starlette reverses it to be the OUTERMOST wrapper.** Implement via `app.add_middleware(OtelMiddleware)` AFTER all other user middleware. Update Decision #53 | critical-audit-specialist |
| **Δ49** | **`instrument_tool` double-wraps same callable**. Both `tools.py:562-610` and `capabilities.py:106-158` register the SAME Python callables (`tools_module.validate_template` etc). If `instrument_tool` wraps each `server.tool(...)` site, every tool is wrapped TWICE per pipeline build → counter inflated 2-3x per invocation. **Add idempotency**: mark wrapped function with `__wrapped_by_instrument_tool__ = True` and skip re-wrap | critical-audit-specialist |

### Single-agent P0

| Δ# | Finding | Verified by |
|----|---------|-------------|
| **Δ33** | **MCP `trace_context.get()` exemplar dead**. OtelMiddleware (Commit 11) wraps FastBlocks Starlette app. FastMCP creates its own internal Starlette app (`mcp/server/fastmcp/server.py:953-1049`). Exemplar feature spec promises does not function for MCP call site. v6 acknowledges: exemplar will return `"0"*32`/`"0"*16` for MCP calls; FastMCP-level OTel context propagation is **out of scope**, deferred to a future commit | mcp-integration P0-γ |
| **Δ34** | **Bare `RuntimeError` contradicts Mahavishnu hierarchy**. `mahavishnu/core/errors.py:150-186` defines `MahavishnuError(Exception)` base (verified). v6 introduces `ObservabilityError(Exception)` base in `fastblocks/observability/errors.py` with `MissingDependencyError`, `MetricNameCollisionError`, `SentryImportError` subclasses — each carries plain attributes (matching `MahavishnuError` style), not kw_only structured fields (per Δ46 correction: `FastBlocksError` doesn't exist; use `Exception` base) | python-pro P0-γ + critical-audit-specialist Δ46 |
| **Δ35** | **`raise from` discipline missing**. `ValueError` for CollectorRegistry collision (Δ18) and bare `RuntimeError` (superseded by Δ34) lack `raise from original`. v6 mandates `raise ... from original` everywhere in observability code | python-pro P0-δ |
| **Δ36** | **Triple `trace_context.get()` call in exemplar**. `trace_context.get().trace_id if trace_context.get() else "0"*32` makes 3 reads — wasteful AND unsafe in async. v6 introduces `trace_context.exemplar() -> dict[str, str] | None` helper that does one read and returns `{"trace_id": ..., "span_id": ...}` per OpenMetrics | python-pro P0-ε |
| **Δ37** | **`instrument_tool` wrapping site unspecified**. Two registration paths exist: `tools.py:562-610` (`register_fastblocks_tools`) AND `capabilities.py:106-158` (consumer-facing 3 `register_X_capability`). Instrumenting only one path means the other doesn't emit metrics. v6 commits to instrumenting **both** paths via a shared `instrument_tool` callable | mcp-integration P0-α |
| **Δ38** | **`DecisionSpanProcessor(SpanProcessor)` should inherit concretely**. OTel SDK's `SpanProcessor` is a concrete class with default no-op method bodies (`opentelemetry/sdk/trace/__init__.py:90`). v6 declares inheritance, not Protocol | type-design P0-3 |
| **Δ39** | **6 silent-failure counters missing**. events silently dropped without detection: a11y bridge drops, `prometheus_client.REGISTRY` (global) leakage, on_end counter emit failures, OTLPSpanExporter drops, /metrics Accept-header dispatch, Sentry runtime init errors. v6 adds each | silent-failure-hunter 6 P0s |
| **Δ40** | **`logger.error(..., exc_info=True)` from Round-1 P1-8 explicitly resolved**. CLAUDE.md bans; v6 mandates `logger.exception(...)` everywhere | python-pro P0-β |

### Cheap P1 fixes applied

- Counter/Histogram wrappers use positional-only name + keyword-only exemplar per Python idiom
- `exemplar = {"trace_id": ..., "span_id": ...}` (both keys; OpenMetrics exemplar spec compliant)
- `__all__` declared for all new modules (project pattern from `observability/__init__.py:12-17`)
- `pathlib.Path` (not `os.path`) in scripts
- Per-dashboard ground-truth test uses PromQL-aware extraction (not substring match)
- `from __future__ import annotations` in all sources (per CLAUDE.md)

## Scope decision (carried from v3/v5)

In scope: 6A (Foundational observability), 6B (Cardinality-safe metrics),
6C (Trace propagation + a11y bridges + Sentry bridge).

Out of scope (deferred to other phases):
- `asyncio.TaskGroup` migration (Phase 6.5)
- Cardinality budget tuning (Phase 7+)
- HTMY XSS for Jinja2 (Phase 5 v4 deferred)
- A11y axe-core regression tests (Phase 5 deferred)
- **NEW OUT-OF-SCOPE (per Δ33)**: FastMCP-level OTel context propagation so
  exemplar feature works for MCP tool calls. FastBlocks consumers
  wanting trace-tracked exemplars for MCP need to install their own
  FastMCP middleware (e.g., via `mcp_common.tools.call_tool_hook`).
  v6 records exemplar as `None` (not crash) for MCP calls.

## Architecture (carried + Δ-applied)

Three stages, each producing a layer the next consumes. No parallel
paths; no duplication; no alternative observability stack.

### Sequence (17 commits)

```
[NEW] pyproject.toml: [observability] optional dep group (version-pinned per Round 2)
[NEW] settings/observability.yaml: cardinality_mode, traces.export, sentry.* knobs
[NEW] fastblocks/applications.py: ExceptionMiddleware decoupled at BOTH sites (line 250 + 368-374)
[6A]   Foundations: errors.py + Counter/Histogram + ObservabilityRegistry + structlog + OTel + Oneiric adapter
                                                              (Commits 1-4)
[6B]   Cardinality: typed wrappers (with audit mode) + allowlist + CI lint + MCP instrumentation + /metrics
                                                                 (Commits 5-9)
[6C]   Bridges: trace_context (with exemplar() helper) + OtelMiddleware + Sentry bridge + a11y bridge + Grafana
                                                                 (Commits 10-14)
```

Total: 17 commits. Wall-clock estimate: 6-7 weeks (per v5 with v6 additions).

### Layer model

| Layer | Provides | Consumes |
|-------|----------|----------|
| **ObservabilityError hierarchy (1)** | `ObservabilityError(Exception)` base (per `MahavishnuError(Exception)` precedent at `mahavishnu/core/errors.py:150-186`; **`FastBlocksError` does not exist in fastblocks/ source — verified**) + `MissingDependencyError`, `MetricNameCollisionError`, `SentryImportError` subclasses with plain attributes | (project errors module) |
| **Counters / Histograms (1)** | `Counter(name, /, documentation="...", *labelnames: str)` positional-only name + variadic labels; `Histogram(name, /, documentation="...", labelnames: tuple[str, ...], buckets: tuple[float, ...])`; exemplars keyword-only | `prometheus_client` (dep group) |
| **ObservabilityRegistry (1)** | Singleton wrapping `prometheus_client.CollectorRegistry`; snapshot at startup; raises `MetricNameCollisionError` from `prometheus_client.ValueError`; thread-safe registration via `threading.Lock` (registration-only; increments lock-free) | 6A.1 |
| Structured logs (2) | `get_logger(name)` → JSON via `structlog.merge_contextvars`; **`logger.exception(...)` everywhere per CLAUDE.md** (not `logger.error(..., exc_info=True)`) | `structlog` (core) |
| OTel Tracer (3) | `get_tracer(name)` + `setup_default_tracer_provider(...)` + `BatchSpanProcessor.shutdown()` contract | `opentelemetry-sdk` + `opentelemetry-exporter-otlp-proto-http` (dep group, pinned per Δ22) |
| **trace_context (10)** | `get()`/`set(token)`/`reset(token)` **token-safe** API; **`exemplar() -> dict[str, str] | None` helper** (Δ36; one read, both keys); aliases preserved | 6A.3 |
| Oneiric adapter (4) | `DecisionSpanProcessor(SpanProcessor)` **(concrete inheritance)**; `on_start` filters by `name == "resolver.decision"`; emits counter + log; `decision ∈ Literal["resolved","error"]` (Δ29 — matches Oneiric's actual emission); `try/except Exception → logger.exception` with `fastblocks_span_processor_errors_total{kind}` counter (silent-failure surfaced) | Oneiric OTel `resolver.decision` span |
| CardinalityGuard (5) | Per-metric `Literal[...]` allowlist; `cardinality_mode ∈ Literal["off","audit","warn","enforce"]` (Δ41 ordering: semantic — off→audit→warn→enforce); `MetricCardinalityViolation` event class | 6A.1 |
| MCP instrumentation (8) | `instrument_tool` decorator; counter + histogram; **`Counter(..., documentation="...")`** (Δ31); **`instrument_tool` wraps BOTH `tools.py:562-610` AND `capabilities.py:106-158` paths** (Δ37); **installs `_patched_add_tool` workaround at module-import time** (Δ32) so pydantic BaseModel Tool objects don't TypeError | mcp_common dispatch + FastMCP `add_tool` |
| `/metrics` endpoint (9) | Accept-header dispatch with **explicit default for `*/*`/missing Accept** (Δ42 → OpenMetrics); wraps `choose_encoder` + `generate_latest` in try/except with `fastblocks_metrics_endpoint_errors_total{reason}` counter (P1-3); **`fastblocks_metrics_endpoint_dispatch_total{accept_header}`** for observability-of-dispatch | 6A.1 + Starlette |
| OtelMiddleware (11) | Per-request OTel root span; binds `trace_context`; clears via token-reset in `finally`; **resilient to `trace_context.reset(token)` raise** (Δ43 → `fastblocks_otel_middleware_reset_failed_total`) | 6A.3 + 6C.10 + Commit 0c |
| Sentry bridge (12) | `sentry_sdk.init(...)` + `OpenTelemetryIntegration`; ordering: **TracerProvider first, then `sentry_init`**; only `profiling_enabled=False`; `disabled_on_import_error: bool = false` (loud default); **`reason="init_runtime_error"` counter** alongside `reason="import_error"` | 6A.3 + `sentry-sdk` |
| a11y bridge (13) | `render_broadcast_as_a11y(...)`; **rate-limit with `coalesced_total` AND `dropped_total`** (Δ39-α); **WCAG-correct routing: `miss→polite/status`, `escaped=false→logs only`**; `aria-relevant="additions"`; dynamic WS broadcast Playwright test | WebSocket broadcasts |

### Failure-degradation policy (carried + new from round 3)

Pattern across all failure modes: **observability failures degrade to
less observability; never to app failure.** Counters added so
observability-of-observability is itself observable.

| Failure | Counter / log |
|---|---|
| Missing observability dep | `RuntimeError`-derived `MissingDependencyError` (Δ34) at import; loud via install hint |
| Counter name collision | `MetricNameCollisionError(ObservabilityError)` raised from `prometheus_client.ValueError` via `raise from` (Δ35) |
| OTLPSpanExporter endpoint empty / collector unreachable | `fastblocks_otlp_spans_dropped_total{reason}` (Δ39-δ) with `queue_full`, `export_timeout`, `collector_unreachable` |
| `traced_decision()` body raises | `decision="error"` on Oneiric SpanProcessor; **resolver-raises-before-span separate counter** with `reason ∈ Literal["resolver_raised","traced_decision_raised"]` |
| `BatchSpanProcessor.shutdown()` not called on app exit | `provider.shutdown()` invoked from app lifespan; test asserts `_shutdown_called is True` |
| SpanProcessor.on_end raise | `logger.exception(...)` (per Δ40 CLAUDE.md) + `fastblocks_span_processor_errors_total{kind}` (always emitted, not DEBUG-only) |
| Concurrent `prometheus_client.REGISTRY` multi-worker | `ObservabilityRegistry` thread-safe via `threading.Lock` (registration-only); cross-process documented known-limitation |
| `/metrics` scraper sends `Accept: text/plain; version=0.0.4` | `choose_encoder` dispatches; legacy content type returned |
| `/metrics` scraper sends `Accept: */*` or missing | **Default to OpenMetrics** (Δ42 forward path); `fastblocks_metrics_endpoint_dispatch_total{accept_header}` |
| `/metrics` encoder / generator raise | `fastblocks_metrics_endpoint_errors_total{reason}` |
| `sentry_sdk.init()` runs before TracerProvider built | Forbidden — app fails loud at startup; `reason="init_runtime_error"` (Δ39-ζ) |
| `sentry_sdk.opentelemetry` import path drifts | `SentryImportError(ObservabilityError)` raised; `reason="import_error"`; loud-fail default |
| `aria-live` region floods | `fastblocks_a11y_bridge_coalesced_total{region}` + **`fastblocks_a11y_bridge_dropped_total{region}`** (Δ39-α) — coalesced ≠ dropped |
| CardinalityGuard trips in `enforce` | `MetricCardinalityViolation` event + `fastblocks_cardinality_violations_total{label}`; `cardinality_mode="audit"` lets it increment without raise |
| DecisionSpanProcessor counter `Counter.inc()` itself fails | `fastblocks_oneiric_decision_emit_failed_total{reason}` (Δ39-γ) |
| `trace_context.reset(token)` raises in OtelMiddleware finally | Wrap in its own try/except + `fastblocks_otel_middleware_reset_failed_total` (P1-5) |
| MCP tool calls bypass OtelMiddleware (Δ33) | Exemplar returns `"0"*32`/`"0"*16`; FastMCP-level OTel context propagation deferred to a follow-up; **counter + histogram still increment correctly** for MCP (exemplar-only feature degraded, observability degraded not failed) |
| CollectorRegistry global leakage (Δ39-β) | `fastblocks_observability_registry_unknown_metrics_total` (emitted when `/metrics` is called and global REGISTRY has metrics outside `ObservabilityRegistry`) |
| Oneiric resolver raise-before-span (P1-4) | Wrap resolution call; emit `decision="error"` BEFORE the raise propagates |
| SpanProcessor.on_end Counter.inc fails due to CardinalityGuard reject (P0-γ) | Counter wrapped in its own try/except; emit `fastblocks_oneiric_decision_emit_failed_total{reason="cardinality_reject"}` |

### Δ41 — Semantic ordering of CardinalityGuard modes

Per type-design P1-4: `Literal["off","audit","warn","enforce"]` — semantics
ordered by operator progression (off=disabled, audit=observe-without-block,
warn=log-and-drop, enforce=block). Pinned explicitly so future
implementers don't reorder alphabetically.

### Δ42 — `/metrics` Accept-header dispatch default

Per silent-failure P0-ε: real-world scrapers send `Accept: */*` or
nothing. Default branch: **serve OpenMetrics**. This is a forward
choice — OpenMetrics is the modern format, text 1.0.0 is legacy,
and serving OpenMetrics to a wildcard-Accept scraper is harmless
(Grafana, Prometheus 2.5+ read both formats).

## Open Review Flags (v6-cleaned)

| Flag | v6 status |
|------|-----------|
| #1 (Commit 8 dependency on `register_fastblocks_tools`) | CLOSED via Phase 4 v2.1 |
| #2 (LifespanManager P0) | CLOSED via Phase 6.5 |
| #3 (Oneiric `Decisions.events()` API) | CLOSED — SpanProcessor via OTel |
| #4 (Grafana version pin) | OPEN-AT-Grafana-10.x — vendored schema test catches drift |
| #5 (Commit 12 htmx.py boundary) | CLOSED — fix already shipped per `5c919f4`; regression-preservation in Commit 3 |
| #6 (LifespanManager inheritance) | CLOSED |
| #7 (dep-group import guard) | CLOSED — `MissingDependencyError` (Δ34) |
| #8 (Sentry alpha path) | CLOSED-via-ADR — ADR 0013:173-176 documents `sentry_sdk.opentelemetry` for 3.0.0a7; runtime init failures caught by `reason="init_runtime_error"` (Δ39-ζ) |
| #9 (CollectorRegistry name collision) | CLOSED-via-Δ34 — `MetricNameCollisionError(ObservabilityError)` raised from `prometheus_client.ValueError` via `raise from` |
| #10 (BatchSpanProcessor.shutdown contract) | CLOSED — app lifespan shutdown wires `provider.shutdown()` |
| #11 (Sentry init ordering) | CLOSED-via-Δ34 — TracerProvider first, init last; `reason="init_runtime_error"` if violated |
| #12 (profiling_enabled conflict) | CLOSED — `profiling_enabled=False` only; loud-fail otherwise |
| #13 (ObservabilityRegistry ownership) | CLOSED-via-v6 — Commit 1 creates `errors.py` + `registry.py` |
| NEW #14 (MCP exemplar dead code) | OPEN-ACCEPTED — exemplar returns `"0"*32`/`"0"*16` for MCP; FastMCP-level propagation deferred |
| NEW #15 (decision Literal fabricated) | CLOSED-via-Δ29 — reduced to `["resolved","error"]` matching Oneiric actual emission |
| NEW #16 (rate_limited invented) | CLOSED-via-Δ30 — dropped; only `["ok","error","validation_error"]` retained |
| NEW #17 (Counter documentation arg missing) | CLOSED-via-Δ31 — every spec example includes `documentation="..."` |
| NEW #18 (Tool pydantic incompatibility) | CLOSED-via-Δ32 — `_patched_add_tool` monkeypatch lifted to production module |
| NEW #19 (instrument_tool dual-path) | CLOSED-via-Δ37 — wraps both `tools.py` AND `capabilities.py` paths |
| NEW #20 (SpanProcessor inheritance) | CLOSED-via-Δ38 — concrete inheritance, not Protocol |
| NEW #21 (silent-failure observability-of-observability) | CLOSED-via-Δ39 — 6 dedicated counters |
| NEW #22 (TraceContext exemplar triple-call) | CLOSED-via-Δ36 — `trace_context.exemplar()` helper centralizes the read |
| NEW #23 (TraceContext dataclass missing slots/kw_only) | OPEN-TO-FOLLOWUP — already-shipped dataclass missing convention attrs; Commit 10 expands `__all__` to include `exemplar()` helper but doesn't break the existing frozen-only dataclass shape. Future commit upgrades decorator. |
| NEW #24 (ExceptionMiddleware empty handlers) | OPEN-TO-FOLLOWUP — Commit 0c's `register_user_exception_middleware` should validate non-empty handlers; documented in IC |

## Per-task Integration Contracts (six-field per master plan line 545-553)

For Phase 6 (high-blast-radius) each main commit gets **2 reviewers**.
Pre-commits 0a/0b/0c get 1 reviewer each. Every IC has the full six
fields: Triggered from, Returns to/updates, Demonstrable by, Rollback
signal, Observability added, Reviewers.

(Commit content carries forward all v5 corrections + Δ29-Δ40; only
changes from v5 are noted in detail per affected commit.)

### Commit 0a — `chore(pyproject): [observability] optional dep group; consolidate sentry-sdk from monitoring`

*(Inherits v5 Commit 0a Round-2 corrections: version pins via `~=X.Y`,
`opentelemetry-exporter-otlp-proto-http` not meta-pkg, `urllib3~=2.5`
removed from monitoring, breaking-change callout for workspace
members, install footprint matrix, dual-OTel safety net.)*

### Commit 0b — `feat(settings): settings/observability.yaml + PyProjectSettings observability extension`

*(Inherits v5 Commit 0b: cardinality_mode Literal, disabled_on_import_error, profiling_enabled.)*

### Commit 0c — `refactor(applications): ExceptionMiddleware decoupled at BOTH sites (line 250 + 368-374)`

*(Inherits v5 Commit 0c: outer_default / innermost_opt_out / otel_outermost_with_5xx ordering tests.)*

### Commit 1 — `feat(observability): errors.py + Counter/Histogram wrappers + ObservabilityRegistry + lazy-import guard`

**Δ-applied in v6**:

- *Triggered from:* v5 Commit 1; Δ34 (ObservabilityError hierarchy), Δ31 (Counter documentation arg), P1-1 (positional-only name), P1-2 (keyword-only exemplar), P1-8 (thread-safe registry), P1-7 (`__all__` for new modules)
- *Returns to / updates:*
  - NEW `fastblocks/observability/errors.py` defining `ObservabilityError(Exception)` (per Δ46: uses `Exception` base, not `FastBlocksError` which doesn't exist), `MissingDependencyError(ObservabilityError)` carrying `pip_group: str, package: str | None` attributes (not kw_only-constructor params; matches `MahavishnuError` plain-attr style), `MetricNameCollisionError(ObservabilityError)` carrying `metric_name: str`, `SentryImportError(ObservabilityError)` carrying `reason: Literal["import_error", "init_runtime_error"]`. Each implements `__rich_repr__` for debugging. **Constructor takes `**kwargs` to populate attrs in `__init__` body** per `MahavishnuError` shape — NOT kw_only constructor params.
  - NEW `fastblocks/observability/counters.py` — `Counter(name: str, /, documentation: str, *labelnames: str)` positional-only name + variadic labels; `Histogram(name: str, /, documentation: str, labelnames: tuple[str, ...], buckets: tuple[float, ...])`; methods `inc(amount: float = 1.0, *, exemplar: dict[str, str] | None = None)` and `observe(value: float, *, exemplar: dict[str, str] | None = None)` (keyword-only exemplar per P1-2); lazy-import `RuntimeError`/`MissingDependencyError` wrappers for `prometheus_client`
  - NEW `fastblocks/observability/registry.py` — `ObservabilityRegistry` singleton wrapping `prometheus_client.CollectorRegistry`; `threading.Lock` for registration only (increments are lock-free via prometheus_client internals); snapshot metric names at startup; raises `MetricNameCollisionError` via `raise from prometheus_client.ValueError` (per Δ35)
  - NEW `fastblocks/observability/__init__.py` with `__all__ = ["Counter", "Histogram", "ObservabilityRegistry", "trace_context", "MissingDependencyError", "MetricNameCollisionError", "SentryImportError", "exemplar"]`
- *Demonstrable by:*
  1. `python -c "from fastblocks.observability import Counter; c = Counter('demo_test', 'demo for spec verification', labelnames=('r',))"` succeeds (after `uv sync --group observability`)
  2. `python -c "from fastblocks.observability.errors import MissingDependencyError; e = MissingDependencyError(pip_group='observability', package='prometheus-client'); assert e.pip_group == 'observability'"` succeeds
  3. Lean install: same import as item 1 raises `MissingDependencyError` (not bare `RuntimeError`) with structured `pip_group` field
  4. Concurrent `Counter("same_name", ...)` calls from 2 threads: exactly one wins, the other raises `MetricNameCollisionError` (lock proves registration safety)
- *Rollback signal:* `git revert`; bare `RuntimeError` shape reintroduced via fallback (not preferred but compatible)
- *Observability added:* none directly; this IS the observability surface
- *Reviewers:* 2 (python-pro for exception hierarchy + type idiom; observability-incident-lead for label discipline)

### Commit 2 — `feat(observability): structlog Logger bound to Oneiric settings`

*(Inherits v5 Commit 2; uses `logger.exception(...)` per Δ40, never `logger.error(..., exc_info=True)`.)*

### Commit 3 — `feat(observability): OTel Tracer + tracer.py + BatchSpanProcessor.shutdown contract + htmx.py regression preservation`

*(Inherits v5 Commit 3; lifespan shutdown wired per Δ10.)*

### Commit 4 — `feat(adapters): Oneiric observability adapter — DecisionSpanProcessor(SpanProcessor) on resolver.decision spans only`

**Δ-applied in v6**:

- *Triggered from:* v5 Commit 4; Δ29 (decision Literal reduced), Δ38 (SpanProcessor concrete inheritance), Δ39-γ (DecisionSpanProcessor emit-failed counter), P1-4 (resolver-raises-before-span separate reason label)
- *Returns to / updates:*
  - NEW `fastblocks/adapters/oneiric/observability.py` — `class DecisionSpanProcessor(SpanProcessor)` **inherits concretely** from OTel's `SpanProcessor` (Δ38), not Protocol. `on_start(span)` filters by `span.name == "resolver.decision"`. `on_end(span)` reads BARE attributes (`domain`, `key`, `provider`, `decision`); emits log line + counter; increments `decision="resolved"` for normal path, **`decision="error"` for raise path AND for resolver-raises-before-span path with `reason` label distinguishing the two (P1-4)**; wraps `Counter.inc(...)` in its own try/except + emits `fastblocks_oneiric_decision_emit_failed_total{reason}` (Δ39-γ)
  - The counter is constructed with `decision ∈ Literal["resolved","error"]` (**Δ29** — the only two values Oneiric can actually emit; reduced from Δ6's 4-value closure which was fabricated ground-truth-wise)
- *Demonstrable by:*
  1. `scripts/verify_oneiric_otel_attrs.py` exits 0 with 4 bare attribute names verified
  2. Unit test triggers Oneiric resolution; SpanProcessor emits structlog + increments `fastblocks_oneiric_decision_total{domain, decision="resolved"}` for normal path
  3. Unit test fires a non-`resolver.decision` span (e.g., from `opentelemetry-instrumentation-httpx`); counter is **NOT** incremented (scope filter)
  4. Unit test triggers `traced_decision()` body raise; counter increments `{decision="error", reason="traced_decision_raised"}`
  5. Unit test triggers Oneiric resolver raise BEFORE `traced_decision()` is entered; counter increments `{decision="error", reason="resolver_raised"}`
  6. Autouse fixture tears down SpanProcessor; next test sees clean `TracerProvider`
- *Rollback signal:* `git revert`
- *Observability added:* `fastblocks_oneiric_decision_total{domain, decision, reason}` + `fastblocks_oneiric_decision_emit_failed_total{reason}`
- *Reviewers:* 2 (oneiric-specialist for protocol correctness; observability-incident-lead for cardinality of decision labels)

### Commit 5 — `feat(observability): Typed Counter/Histogram wrappers + CardinalityGuard with audit mode + MetricCardinalityViolation`

*(Inherits v5 Commit 5 with Δ41 semantic ordering: `Literal["off","audit","warn","enforce"]`. Adds `MetricCardinalityViolation` event-class per python-pro P1-13.)*

### Commit 6 — `feat(observability): _label_allowlist.py + Literal binding registry`

*(Inherits v5 Commit 6 with **Δ29/Δ30 reduced Literal closures**: `decision ∈ Literal["resolved","error"]`, `status ∈ Literal["ok","error","validation_error"]`. ToolName Literal now lists all 7 tool names explicitly per python-pro P1-4/type-design P1-5.)*

### Commit 7 — `feat(scripts): check_metric_cardinality.py — CI lint`

*(Inherits v5 Commit 7; uses `pathlib.Path` throughout per Δ40 / python-pro P1-16; AST extraction uses PromQL-aware parsing per silent-failure P1-8.)*

### Commit 8 — `feat(mcp): observability wrapper (instrument_tool) — wired for tools.py AND capabilities.py paths with Tool pydantic workaround`

**Δ-applied in v6**:

- *Triggered from:* Commits 5+7; v5 Commit 8; Δ37 (wraps both paths), Δ32 (Tool pydantic workaround lifted), Δ31 (Counter documentation arg), Δ30 (status Literal reduced), Δ33 (MCP exemplar dead acknowledged)
- *Returns to / updates:*
  - NEW `fastblocks/mcp/_add_tool_safe.py` — installs `_patched_add_tool` monkeypatch at module-import time (lifts the workaround from `tests/mcp/test_consumer_pattern_wiring.py:61-74` into production code per Δ32)
  - NEW `fastblocks/mcp/observability.py` — `instrument_tool` decorator wrapping `Counter(name, documentation, *labelnames)` and `Histogram(name, documentation, labelnames, buckets)` (Δ31); Counter wraps `fastblocks_mcp_tool_invocations_total{tool_name: ToolName, status: ToolStatus}` with `ToolStatus ∈ Literal["ok","error","validation_error"]` (Δ30); Histogram wraps `fastblocks_mcp_tool_duration_seconds{tool_name}` with exemplar calling `trace_context.exemplar()` (Δ36)
  - **`instrument_tool` wraps BOTH paths**: `tools.py:562-610` (`register_fastblocks_tools`) AND `capabilities.py:106-158` (consumer-facing 3 `register_X_capability`) per Δ37 — the same decorator applied at every `server.tool(...)` call site
  - Acknowledges Δ33: `trace_context.exemplar()` returns `None` (which `Histogram` skips) for MCP tool calls until FastMCP-level OTel context propagation lands; counter + histogram increment correctly regardless
  - `__all__` declared for the new module per python-pro P1-7
- *Demonstrable by:*
  1. `validate_template(...)` via `register_fastblocks_tools` increments `{tool_name="validate_template", status="ok"}`
  2. Same via `register_template_capability` (capabilities.py consumer path) increments the same counter
  3. Tool raising `pydantic.ValidationError` increments `{..., status="validation_error"}`
  4. `Histogram.observe(elapsed, exemplar=trace_context.exemplar())`; for MCP calls exemplar is `None` and `observe` skips it; for HTTP route calls exemplar is the dict
  5. `Counter` constructed with required `documentation` arg; example `Counter("fastblocks_mcp_tool_invocations_total", "MCP tool invocation counts", labelnames=("tool_name", "status"))`
  6. `await server.list_tools()` post-Commit 8 returns all 7 tool names
  7. Regression test for the pydantic incompatibility: an `instrument_tool`-wrapped tool whose FastMCP `add_tool` would call `Tool.from_function` succeeds (monkeypatch active)
- *Rollback signal:* `git revert`; tools return to un-instrumented
- *Observability added:* `fastblocks_mcp_tool_invocations_total{tool_name, status}` + `fastblocks_mcp_tool_duration_seconds{tool_name}`
- *Reviewers:* 2 (mcp-integration-expert; observability-incident-lead)

### Commit 9 — `feat(app): /metrics endpoint with Accept-header dispatch + BatchSpanProcessor shutdown wiring`

**Δ-applied in v6**:

- *Triggered from:* Commits 1+5; v5 Commit 9; Δ42 (Accept-header default for `*/*`/missing), P1-3 (encoder/generator try/except), Δ39-ε (dispatch counter)
- *Returns to / updates:* `fastblocks/adapters/app/default.py` mounts `/metrics` route; endpoint inspects `Accept` header and **defaults to OpenMetrics for `*/*`/missing** (Δ42 forward path); wraps `choose_encoder` + `generate_latest` in try/except returning 503 with `fastblocks_metrics_endpoint_errors_total{reason}` counter (P1-3); emits `fastblocks_metrics_endpoint_dispatch_total{accept_header}` for observability-of-dispatch (Δ39-ε)
- *Demonstrable by:* 4-case Accept-header matrix: `application/openmetrics-text` → OpenMetrics; `text/plain; version=0.0.4` → legacy text 1.0.0; `Accept: */*` → OpenMetrics (Δ42 default); missing Accept → OpenMetrics; all 4 names appear in `fastblocks_metrics_endpoint_dispatch_total{accept_header}`
- *Rollback signal:* `git revert`
- *Observability added:* `/metrics` accepts any Accept; `BatchSpanProcessor` lifecycle managed; both dispatch + error counters live
- *Reviewers:* 2 (starlette-specialist; observability-incident-lead)

### Commit 10 — `feat(observability): trace_context public API verification (get/set/reset token-safe + exemplar() helper)`

**Δ-applied in v6**:

- *Returns to / updates:* expands already-shipped `trace_context.py:40-77` with NEW public helper `trace_context.exemplar() -> dict[str, str] | None` (Δ36): `ctx = get(); return None if ctx is None else {"trace_id": ctx.trace_id, "span_id": ctx.span_id}` — single read; both OpenMetrics keys; returns `None` when no trace is bound (so callers like `Histogram.observe(value, exemplar=trace_context.exemplar())` work with the keyword-only signature). `__all__` declared.
- *Demonstrable by:*
  1. `set(TraceContext(trace_id="a"*32, span_id="b"*16))`; `get()` returns the value; `exemplar()` returns `{"trace_id": "a"*32, "span_id": "b"*16}`
  2. `reset(token)`; `get()` returns `None`; `exemplar()` returns `None`
  3. Inside `traced_decision()` context: `exemplar()` returns populated dict
  4. From MCP call site (Δ33): `exemplar()` returns `None`
  5. Alias identity: `set_trace_context is set`; `reset_trace_context is reset` (no drift)
  6. `tests/observability/test_log_correlation.py::test_trace_id_surfaces_via_merge_contextvars` passes
- *Observability added:* none directly; **observability-OF the exemplar feature** improved via single-read helper

### Commit 11 — `feat(observability): OtelMiddleware + trace_id binding — outermost via add_middleware LAST after Commit 0c (Starlette reverses user middleware)`

**Δ-applied in v6**: inherits v5 + P1-5 (resilient to `trace_context.reset(token)` raise via `fastblocks_otel_middleware_reset_failed_total` counter); **Δ48 outermost via add-after-reverse** (OtelMiddleware is registered LAST, then Starlette reverses it to be OUTERMOST — NOT user_middleware[0]); **Δ45 Commit 0c Canonical Shape** (Commit 11's Demonstrable by uses `MiddlewareManager.get_middleware_stack()` dict shape, not `FastBlocks.get_middleware_stack()` list-of-tuples shape).

### Commit 12 — `feat(observability): Sentry bridge (OpenTelemetryIntegration) with loud-fail default + TracerProvider-first ordering + delta39-ζ counter**

**Δ-applied in v6**: Δ39-ζ counter expansion (`reason="init_runtime_error"` alongside `"import_error"`); Δ34 raises `SentryImportError(ObservabilityError, reason="import_error")` rather than bare `RuntimeError`; ordering note per Δ19; `profiling_enabled=False` only per Δ20.

### Commit 13 — `feat(websocket): a11y_bridge — broadcast → aria-live region routing (corrected WCAG policy + dynamic WS test + dropped_total counter)`

**Δ-applied in v6**: Δ39-α (adds `fastblocks_a11y_bridge_dropped_total{region}` counter alongside `coalesced_total`); Δ10 corrected routing policy (`miss→polite/status`, `escaped=false→logs only`).

### Commit 14 — `feat(dashboards): fastblocks-overview.json + schema-validation test (with vendored schema + PromQL-aware extraction)**

*(Inherits v5 Commit 14 with P1-8 PromQL-aware metric extraction per silent-failure-hunter.)*

## Migration policy

Per master plan line 350: no backwards compatibility required. Per
master plan line 356: no deprecation warnings. v6-specific migration:

- **Exception hierarchy change**: any downstream consumer catching `RuntimeError` for missing observability deps must migrate to `MissingDependencyError`. This is a subclass, so `except RuntimeError` continues to catch it; only explicit `except RuntimeError` and re-raise patterns need updating.
- **`decision` Literal reduction** (Δ29): any downstream consumer importing `Literal["hit","miss","shadowed","error"]` and relying on its LIteral closure must update. This is a compile-time change; existing code that constructs the literal at runtime from spec data is unaffected.
- **`status` Literal reduction** (Δ30): similar to Δ29 for `status`.
- **`trace_context.exemplar()` helper addition**: additive only — older callers using `.get().trace_id` continue to work.
- **OTLPSpanExporter drops counter** (Δ39-δ): additive only.
- **Six other silent-failure counters**: additive only.
- **Commit 0a dep-group re-pinning** + **Commit 0c dual-site ExceptionMiddleware decouple** + **Commit 8 `_add_tool_safe.py` lifted monkeypatch** + **Commit 9 batch shutdown**: inherited from v5.

## Verification gate (Phase-6-done checklist)

*(Inherits v5 verification gate with the following additions from v6:)*

| Gate | Pass criterion (Δ-added) |
|------|--------------------------|
| Counter documentation | All `Counter(name, ...)` call sites include `documentation="..."` (Δ31 enforced by check_metric_cardinality.py) |
| ObservabilityError catchable | `except MissingDependencyError` works in lieu of `except RuntimeError` (Δ34) |
| TraceContext exemplar | `exemplar()` returns `dict` with both `trace_id` and `span_id` (Δ36) |
| DecisionSpanProcessor inheritance | `issubclass(DecisionSpanProcessor, SpanProcessor) is True` (Δ38) |
| MCP Counter instrumented on both paths | Counter increments from both `tools.py` and `capabilities.py` paths (Δ37) |
| /metrics Accept defaults | `Accept: */*` and missing-Accept return OpenMetrics (Δ42) |
| Silent-failure counters wired | 6 counters (`a11y_bridge_dropped_total`, `observability_registry_unknown_metrics_total`, `oneiric_decision_emit_failed_total`, `otlp_spans_dropped_total`, `metrics_endpoint_dispatch_total`, `sentry_disabled_total{reason="init_runtime_error"}`) all defined and increment in tests |

## Estimated effort

| Section | Commits | New tests | Time |
|---------|---------|-----------|------|
| Pre-commit (0a/0b/0c) | 3 | 3 (Commit 0c) | 1 week |
| 6A | 4 (1-4) | ~12 (added MetricCardinalityViolation, DecisionSpanProcessor emit-failure, etc.) | 1.5 weeks |
| 6B | 5 (5-9) | ~14 (added Accept-header dispatch, /metrics errors, etc.) | 1.5 weeks |
| 6C | 5 (10-14) | ~14 | 2 weeks |
| **Total** | **17** | **~43** | **6-7 weeks** |

## Cross-references

- **v3 spec (superseded via v4):** `docs/superpowers/specs/2026-08-22-fastblocks-phase-6-design.md`
- **v4 spec (intermediate; round-1 review captured):** `docs/superpowers/specs/2026-08-24-fastblocks-phase-6-v4-design.md`
- **v5 spec (intermediate; round-2 packaging captured):** `docs/superpowers/specs/2026-08-24-fastblocks-phase-6-v5-design.md`
- Master plan: §Pillar 6 (lines 174-180), §Phase 6 (line 342), §Phase 6 verification (lines 481-498), master plan §Maintenance line 545-553 (six-field IC mandate)
- ADR 0008: Oneiric selection mechanism (SpanProcessor pattern)
- ADR 0011: Phase 4 deferral (Commit 8 dependency — CLOSED in v6)
- ADR 0012: Phase 5 deferral (LifespanManager P0 — CLOSED in v6)
- ADR 0013 lines 173-176: Sentry OTel integration import path (referenced by Commit 12 IC instead of re-doing smoke check)
- ADR 0014: Phase 5 coverage ratchet
- ADR 0015: Phase 4 v2.1 library-aware opt-in
- Phase 1.5 spec: Oneiric layered config (settings layer used by Commit 0b)
- Phase 2 spec: Literal types (Phase 6's Literal labelnames pattern)
- Phase 2.5 spec: AppSettings wiring
- Phase 5 v4 spec: test infrastructure rebuild
- Phase 6.5 commits: `8c5c117` (LifespanManager), `fb74d13` (trace_context binds structlog), `a102f68` (autouse fixture), `5c919f4` (htmx.py boundary fix — closes old Commit 12)
- **Cross-project citation**: `Mahavishnu/claude/CLAUDE.md` documents the dep-group convention (per Round-2 P1-5 correction)
- **`MahavishnuError` exception hierarchy**: precedent at `/Users/les/Projects/mahavishnu/mahavishnu/core/errors.py:150-186` — copied for `ObservabilityError` per Δ34
- **`tests/mcp/test_consumer_pattern_wiring.py:29-42`**: documents the Pydantic incompatibility; `:61-74` is the workaround lifted to production in `fastblocks/mcp/_add_tool_safe.py` per Δ32
- `mahavishnu/core/errors.py` (sibling repo) — exception hierarchy reference

## Decisions captured during design (v6 additions: Δ29-Δ40)

**Carried from v3/v4/v5**: Decisions 1-33 (full library export surface; FastBlocksRegistry concrete; HTMY XSS for Jinja2 deferred; etc. — see v5 spec §Decisions for full list).

**Round-3 decisions (Δ29-Δ40)**:

34. **`decision` Literal reduced to `["resolved","error"]`** (Δ29) per
    ground-truth (Oneiric only emits "resolved" at
    `oneiric/core/resolution.py:211`). "shadowed" is a CLI flag, not a
    decision outcome; "hit"/"miss" are FastBlocks extensions FastBlocks
    chose not to add in v6.
35. **`status` Literal reduced to `["ok","error","validation_error"]`** (Δ30).
    `"rate_limited"`, `"unauthorized"`, `"timeout"` removed (no source).
    Adding these is a future commit when underlying tool layer actually
    raises those exception types.
36. **`Counter.__init__` requires `documentation` arg** (Δ31) — every
    example updated.
37. **Tool pydantic incompatibility lifted to production** (Δ32) via
    `fastblocks/mcp/_add_tool_safe.py` importing the monkeypatch at
    module-import time.
38. **MCP `trace_context.exemplar()` returns `None`** (Δ33): honest
    acknowledgment that the FastMCP path bypasses FastBlocks'
    OtelMiddleware. Trade-off: exemplars degraded for MCP; observability
    counts+histograms still increment correctly.
39. **`ObservabilityError(Exception)` hierarchy** (Δ34 corrected by Δ46) —
    `MissingDependencyError`, `MetricNameCollisionError`,
    `SentryImportError`. **Base is `Exception`** (per Mahavishnu's
    `MahavishnuError(Exception)` precedent — `FastBlocksError` does
    not exist in fastblocks/ source). Plain attributes assigned in
    `__init__`, NOT kw_only constructor parameters.
40. **`raise from` discipline** (Δ35): every `raise` of an
    `ObservabilityError` from a non-`ObservabilityError` carries
    `from original`. Tracebacks preserved.
41. **`trace_context.exemplar()` helper** (Δ36) — single-read helper
    centralizing the `{"trace_id": ..., "span_id": ...}` shape.
    Avoids triple `.get()` call hazard.
42. **`instrument_tool` wraps BOTH `tools.py` AND `capabilities.py`**
    (Δ37) — same decorator applied at every `server.tool(...)` call
    site in both paths.
43. **`DecisionSpanProcessor(SpanProcessor)` concrete inheritance**
    (Δ38) — not Protocol.
44. **6 silent-failure counters added** (Δ39) — observability-of-observability
    closed: `a11y_bridge_dropped_total`, `observability_registry_unknown_metrics_total`,
    `oneiric_decision_emit_failed_total{reason}`, `otlp_spans_dropped_total{reason}`,
    `metrics_endpoint_dispatch_total{accept_header}`, `sentry_disabled_total{reason="init_runtime_error"}`.
45. **`logger.exception(...)` discipline** (Δ40) — explicit in
    CLAUDE.md; v6 carries forward and explicitly bans `logger.error(..., exc_info=True)`.
46. **`cardinality_mode` ordering semantic** (Δ41) — `off → audit → warn → enforce`
    ordering matters; pinned in Commit 5 IC.
47. **`/metrics` Accept-header default = OpenMetrics** (Δ42) — wildcards and
    missing-Accept pick OpenMetrics for forward-compatibility.
48. **`trace_context.reset(token)` resilience** (P1-5) — wrap in
    own try/except + `fastblocks_otel_middleware_reset_failed_total`.
49. **TracerProvider shutdown contract** wired in app lifespan (per v5).
50. **Sentry init ordering** TracerProvider first (per v5).
51. **`profiling_enabled=False` only** when bridging OTel (per v5).
52. **Dynamic WS broadcast Playwright test** (per v5).
53. **OtelMiddleware outermost via add-after-reverse** (Δ48 — was v5's "user_middleware[0]" which was incorrect). Starlette `build_middleware_stack` REVERSES user middleware; OtelMiddleware is the LAST `app.add_middleware(...)` call so it's at `user_middleware[-1]` in stored order, which Starlette reverses to OUTERMOST. Implement via `app.add_middleware(OtelMiddleware)` AFTER all other user middleware registration.

**Final-pass decisions (Δ45-Δ49 — critical-audit-specialist)**:

54. **Two `get_middleware_stack` shapes; pin to dict** (Δ45). Commit 0c ordering tests target `MiddlewareManager.get_middleware_stack()` which returns `dict[str, Any]` (verified at `applications.py:114-124`). The legacy `FastBlocks.get_middleware_stack()` at `applications.py:249-268` returning `list[tuple]` is normalized in a follow-up; not Commit 0c scope.

55. **`_patched_add_tool` blast radius mitigated** (Δ47). Mutation `FastMCP.add_tool = _patched_add_tool` is process-wide. Mitigations: (a) runtime guard `if FastMCP.add_tool is not _patched_add_tool: return _original(...)` makes re-application idempotent; (b) version pin `mcp-common<0.4` in `pyproject.toml` until upstream bug fixed; (c) reconciliation: pyproject uses `mcp-common~=0.3` (hyphenated), test docstring uses `mcp_common 0.19.0` (underscored) — both refer to same package; spec normalizes to underscore in code refs and hyphen in pyproject.

56. **`instrument_tool` is idempotent via marker** (Δ49). `instrument_tool(func)` checks `func.__wrapped_by_instrument_tool__` flag; if False, wraps and sets the flag; if True, returns the original. Avoids double-wrapping when `tools.py:562-610` AND `capabilities.py:106-158` both register the same Python callable. Without this, counters inflate 2-3x per tool invocation.

57. **`trace_context.get()` exemplars in async contexts** (final-pass implicit). `ContextVar.get()` reads are safe inside a single synchronous block; future implementers must NOT add `await` between the `exemplar()` call and the `Histogram.observe(value, exemplar=...)` call, or risk reading a different task's context.

58. **Commit 0c ordering tests use canonical shape** (Δ45). All Commit 0c `Demonstrable by` assertions use `manager.get_middleware_stack()["user_middleware"][...]` (dict shape, returns list/dict structure), not `FastBlocks.get_middleware_stack()` (list-of-tuples shape). Assertion language: `assert stack["user_middleware"][-1]["class"] == "ExceptionMiddleware"` for outermost_default; `[0]["class"] == "ExceptionMiddleware"` for innermost_opt_out.

## Spec self-review checklist

- [x] **Placeholder scan:** no `TBD` carryforward (Dashboard metric call sites flagged as "TBD by implementer via `git grep`")
- [x] **Internal consistency:** `decision="resolved"` self-contradiction (v5 P0-α) eliminated by Δ29; `rate_limited` eliminated by Δ30; Counter documentation arg present per Δ31
- [x] **Scope check:** 17 commits (verified by heading scan + arithmetic); exception hierarchy adds `errors.py` to Commit 1, not a new commit
- [x] **Ambiguity check:** each IC's `Demonstrable by:` is a single concrete command + pass criterion; 6-field ICs (Triggered, Returns, Demonstrable, Rollback, Observability added, Reviewers) per master plan line 545-553
- [x] **Self-contradictions** flagged in v5 (`decision="resolved"` vs Δ6 Literal; `rate_limited` with no source; Counter `documentation` arg missing in examples) ALL eliminated in v6
- [x] **Design error** (exemplar dead for MCP) explicitly acknowledged with Δ33 + deferred FastMCP-level propagation follow-up
- [x] **No FastBlocks precedent fabricated**: dep-group citation is to Mahavishnu's CLAUDE.md, not FastBlocks'
- [x] **All round-3 silent-failure counters enumerated** in the failure-mode table
- [x] **Logger idiom** (Δ40) `exception()` not `error(..., exc_info=True)`
- [x] **`raise from` discipline** (Δ35) explicitly mandated

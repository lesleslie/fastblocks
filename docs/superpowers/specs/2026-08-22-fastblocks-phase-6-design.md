______________________________________________________________________

## status: accepted role: phase-6-design-spec date: 2026-08-22 last_reviewed: 2026-08-22 supersedes: null superseded_by: null blocks_on: null decision_date: 2026-08-22 topic: phase-6-observability

# Phase 6: Observability Design

## Status

**Accepted** (Phase 6 spec — companion to master plan
`docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
§Pillar 6 line 174-180, §Phase 6 line 342, §Phase 6 verification line 481-498).

## Scope decision

Phase 6 delivers the master plan's Pillar 6 (line 174-180) and Phase 6 row
(line 342): "Structured logs; counter metrics; Oneiric's
`explain()`/`list_shadowed()` as primary source; `asyncio.TaskGroup`;
trace propagation through htmx.py threads; cardinality-guarded Prometheus
labels."

**In scope:**

1. Observability primitives layer (6A): `Counter`/`Histogram`/`Logger`/`Tracer`
   wrappers; Oneiric observability adapter (consume, don't duplicate).
1. Cardinality-safe metrics (6B): typed `Literal[...]` label discipline;
   CI lint guard; MCP tool instrumentation; `/metrics` endpoint.
1. Trace propagation + a11y bridges (6C): `trace_context` ContextVar
   binding across the htmx.py per-thread loop boundary; OTel middleware
   as outermost layer; Sentry+OTel root-span bridge; WebSocket →
   aria-live bridge; Grafana dashboard.

**Out of scope (deferred):**

- `asyncio.TaskGroup` migration across concurrent code (split into
  Phase 6.5 — separate ADR + spec; it's a structural refactor that
  affects every async function and shouldn't gate observability).
- Cardinality budget tuning per metric (depends on real Prometheus
  data; Phase 7+).
- HTMY XSS for Jinja2-rendered components (master plan §Phase 5
  verification line 582-583).
- A11y regression tests via axe-core (Phase 5 deferred).

## Why Phase 6 ships all 3 stages in one phase

Phase 5 (test infrastructure rebuild) was deferred after 3 multi-agent
review cycles. Phase 6 is observability, and observability primitives
(6A) without cardinality discipline (6B) cause Prometheus outages;
cardinality discipline without trace propagation (6C) leaves WebSocket
broadcasts invisible to screen readers. The three stages are coupled —
observability that crashes the app, exhausts the scraper, or silences
blind users is worse than no observability. One coherent design
preserves the discipline invariant across commits.

## Architecture

Three stages, each producing a layer the next consumes. No parallel
paths; no duplication; no alternative observability stack.

### 6A — Foundational observability (4 commits)

**What ships**: the primitives layer that every subsequent
instrumentation call reaches back into.

| File | Purpose |
|---|---|
| `fastblocks/observability/__init__.py` (NEW) | Top-level package; re-exports `Counter`, `Histogram`, `Logger`, `Tracer`, `trace_context`, `ObservabilityRegistry` |
| `fastblocks/observability/counters.py` (NEW) | `Counter`/`Histogram` wrappers over `prometheus_client`; in-process `CollectorRegistry` for tests |
| `fastblocks/observability/loggers.py` (NEW) | `structlog` Logger factory; bound to Oneiric settings chain |
| `fastblocks/observability/tracer.py` (NEW) | `opentelemetry-sdk` TracerProvider; OTLPSpanExporter wired idempotently |
| `fastblocks/observability/registry.py` (NEW) | Singleton registry; installs OTel `SpanProcessor` that intercepts `resolver.decision` spans |
| `fastblocks/adapters/oneiric/observability.py` (NEW) | Bridges Oneiric `explain()`/`list_shadowed()`/`DecisionEvent` → structured log lines + counter increments |
| `settings/observability.yaml` (NEW) | Card[inality] mode, exporter endpoint, log format |

**Library choices** (with rejects):

- **Counter/Histogram**: `prometheus_client` — de-facto Python Prometheus
  client; supports label tuples; in-process `CollectorRegistry()` for
  tests. Rejects: `statsd` (no labels), direct OTel Meter (bypasses
  `/metrics` endpoint; Grafana scrape requires text format).
- **Structured logging**: `structlog` — zero-config defaults; JSON
  output; pluggable processors; ties into Oneiric settings chain via
  `merge_contextvars`. Rejects: `loguru` (opinionated formatters;
  doesn't compose with Oneiric processors).
- **Traces**: `opentelemetry-sdk` — standard OTel; one pipeline,
  multiple exporters; bridges to Sentry via
  `sentry-sdk[opentelemetry]`. Rejects: proprietary tracer libraries.
- **Settings**: Oneiric layered config (per Phase 1.5
  `FastblocksRegistry(get_resolver())`) — extends
  `settings/mahavishnu.yaml` (per Phase 2 Literal types).

**Oneiric observability adapter (real contract)** — Phase 6 does NOT
subscribe to a `Decisions.events()` stream because **that API does
not exist** in Oneiric (verified against
`/Users/les/Projects/oneiric/oneiric/core/observability.py` and
`oneiric/core/resolution.py:207-215` per multi-agent review F-ONE-001 /
F-OBS-004). The actual contract:

- `DecisionEvent` is a `@dataclass` (oneiric/core/observability.py:43-59)
  with fields `domain`, `key`, `provider`, `decision`, `details`.
- It is emitted as a **one-shot context manager** via `traced_decision(event)`
  in `oneiric/core/resolution.py:207-215`. The `decision` field is the
  literal string `"resolved"` (hardcoded at resolution.py:211).
- The only public external surface is the OTel span emitted inside
  `traced_decision()`. There is no subscribe API, no async iterator,
  no event bus hook.

**Phase 6's bridge strategy (v3 — corrected)** (per multi-agent review
F-ONEV2-001 / F-OBSV2-001): register an OTel `SpanProcessor` at startup
that intercepts spans named `resolver.decision`. For each such span:

- Read span attributes for the FOUR BARE attribute names that Oneiric
  ACTUALLY emits on its `traced_decision()` span (verified via
  `oneiric/core/observability.py:51-59` and `oneiric/core/resolution.py:207-215`):
  **`domain`**, **`key`**, **`provider`**, **`decision`**. These names
  are NOT namespaced (per F-ONEV2-001 v2 claim that read namespaced
  `oneiric.decision.X` was FABRICATED); the actual emitted keys are
  plain. The Commit 4 verify-script asserts these FOUR EXACT NAMES.
- Emit a `structlog` line at INFO with shape:
  `event="decision_resolved" domain="<domain>" key="<key>" provider="<provider>" decision="<decision>" trace_id="<hex>" span_id="<hex>"`.
- Increment counter `fastblocks_oneiric_decision_total{domain, decision}`
  where `domain` ∈ `Literal["fastblocks.style", "fastblocks.renderer", "fastblocks.adapter", "unknown"]` (`"unknown"` covers the
  provider-None coercion path at `oneiric/core/observability.py:55`;
  per F-ONEV2-010) and `decision ∈ Literal["resolved"]` (single
  value today; included for forward-compat if Oneiric adds failure
  modes).

**Shadowed counter dropped (per F-ONEV2-002)**: `details["shadowed"]`
does not exist as a span attribute key — Oneiric's `as_dict()`
(`oneiric/core/observability.py:51-59`) emits `domain`, `key`,
`provider`, `decision`, and details merged in, but NOT a `"shadowed"`
key. Deriving "shadowed" from `attrs["ordered"]` (per the alternative
suggestion) would VIOLATE master plan line 489's "not parallel" rule
(fastblocks would be re-deriving candidates that Oneiric already
computed). Phase 6 ships the bounded shape: ONE counter per decision
event — `fastblocks_oneiric_decision_total`. Shadowed-candidate
visibility is OUT OF SCOPE; future work can contribute a separate
`ResolutionExplanation.as_attributes()` field to Oneiric upstream
and pick up coverage in a later commit without re-litigating
master-plan line 489.

**Per master plan line 489 — "not parallel"**: Phase 6 doesn't
duplicate resolution logic in fastblocks. The single counter it
emits (`fastblocks_oneiric_decision_total`) is a Prometheus view of
OTel's `resolver.decision` span stream — fastblocks does not re-export
or re-derive resolution outcomes (decision), only surfaces what OTel
emitted. The metric NAME carries a `fastblocks_oneiric_` prefix
because Prometheus export is fastblocks's surface; an upstream
contribution of an OTel-side Prometheus exporter would obviate this
counter entirely, but that's out of Phase 6 scope.

**No facade hook (per F-ONEV2-003)**: OTel `SpanProcessor`s install
against a `TracerProvider` via `provider.add_span_processor(...)`;
this is process-global state, not façade-routed. FastblocksRegistry
(`fastblocks/core/resolver.py:144-209`) has zero span-provider hooks —
the v2 spec's claim of a "facade consumption via
`FastblocksRegistry` span-provider hooks" was FABRICATED. v3
mandates: SpanProcessor installs on the OTel global TracerProvider
(either explicitly via `trace.get_tracer_provider().add_span_processor(...)`
or via `TracerProvider.add_span_processor(...)` if a fresh provider
is constructed). The Phase 1.5 `FastblocksRegistry(get_resolver())`
facade is irrelevant at install time; it remains relevant for the
catalog queries (list_active, list_shadowed) that the rest of fastblocks
makes against the resolver.

**Commit 4 verify-gate**: before Commit 4 lands, ship a small verification
script at `scripts/verify_oneiric_otel_attrs.py` that imports Oneiric,
fires a real `traced_decision()`, and asserts the four exact attribute
names (`domain`, `key`, `provider`, `decision`) appear on the emitted
span. Commit 4's `Demonstrable by:` clause explicitly references this
script's output. The script's assertions MUST match §6A.3 verbatim —
if a future contributor edits the assertions without updating §6A.3,
the edit is the documentation error, not the spec.

**Test isolation (per F-ONEV2-004)**: OTel's TracerProvider is
process-global. A SpanProcessor installed in test 1 persists into
tests 2..N unless explicitly torn down. Commit 4's `Demonstrable by:`
clause MUST include the autouse fixture at `tests/observability/conftest.py`
that snapshots `trace.get_tracer_provider()._active_span_processor` (or
equivalent per the installed `opentelemetry-sdk` version) before each
test and restores it after. Without this fixture, every test
calling `traced_decision()` accumulates processors; counter labels
double/triple/etc.; tests mask each other. The fixture is NOT optional.

**6A settings shape** (`settings/observability.yaml`):

```yaml
observability:
  enabled: true
  cardinality_mode: "enforce"   # "enforce" | "warn" | "off"
  metrics:
    endpoint: "/metrics"
    namespace: "fastblocks"
  logs:
    format: "json"              # "json" | "console"
    level: "INFO"
  traces:
    exporter: "otlp"            # "otlp" | "console" | "none"
    sample_rate: 1.0
  oneiric:
    observe_decisions: true
    observe_shadowing: true
```

Loaded via Oneiric's standard chain. Phase 2 Literal types mean
`cardinality_mode: Literal["enforce", "warn", "off"]` is enforced at
config-load time.

**6A commits**:

| # | Commit |
|---|---|
| 1 | `feat(observability): package skeleton + Counter/Histogram wrappers` |
| 2 | `feat(observability): structlog Logger bound to Oneiric settings` |
| 3 | `feat(observability): OTel Tracer + trace_context ContextVar binding` |
| 4 | `feat(adapters): Oneiric observability adapter — explain()/list_shadowed() bridge` |

**6A failure modes**:

| Failure | Behavior |
|---|---|
| Settings file missing | Oneiric defaults apply (`enabled: false`); no signals emitted; app continues |
| `prometheus_client` import fails at startup | `enabled: false`; logged once at WARNING; app continues |
| `structlog` formatter raises | caught by `structlog`'s wrapper; line emitted as plain string |
| Oneiric's `traced_decision()` raises mid-emit | SpanProcessor logs exception + skips the span; counter not incremented for that span; app continues |

**6A tests** (~10): Counter.inc() with labels, Histogram.observe(),
label key set assertion, CardinalityGuard trip raises (in 6B but
registered at 6A), JSON formatter, level filter, contextvars merge,
trace_context.set/get roundtrip, span lifecycle, Oneiric adapter
mock event → assert Counter incremented + log line emitted.

### 6B — Cardinality-safe metrics (5 commits)

**What ships**: the label discipline that prevents Prometheus from
running out of memory in production.

**The cardinality problem in one sentence**: Prometheus metrics are
stored as `(metric_name, label_key1=value1, ..., label_keyN=valueN)`
tuples. Unbounded label values (request-id, user-id, full URL) cause
the time-series count to grow without limit. Scrapers OOM; alerts lie;
dashboards lie. **The discipline**: every label set on a Counter or
Histogram must be statically bounded by an allowlist — typical
ceilings are 5-50 distinct values per label, never the cardinality of
"all possible strings."

| File | Purpose |
|---|---|
| `fastblocks/observability/counters.py` (refactored) | Typed Counter/Histogram; `CardinalityGuard` rejects out-of-set values per `cardinality_mode` setting |
| `fastblocks/observability/_label_allowlist.py` (NEW) | Pre-approved label names with their `Literal[...]` value sets; CI binds labelnames tuples to entries here |
| `scripts/check_metric_cardinality.py` (NEW) | AST-based CI lint; rejects `Counter(name, labelnames=(...))` where any label isn't `Literal[...]`-typed and isn't in the allowlist |
| `fastblocks/mcp/observability.py` (NEW) | `instrument_tool` decorator for the 7 MCP tools; emits counter + histogram |
| `fastblocks/adapters/app/default.py` (modified) | `/metrics` endpoint mounted |

**Typed-Counter pattern** — runtime safety net. Two-layer check:

```python
from typing import Literal
from fastblocks.observability import Counter

style_resolve_total = Counter(
    name="fastblocks_style_resolve_total",
    labelnames=("result",),  # labelnames IS Literal["hit", "miss"] in registry
)
```

1. `Counter.__init__` does the input-shape check; rejects mismatched
   literal sets at registration time (eager failure).
1. `Counter.inc()` does the value-shape check; rejects runtime values
   not in the literal set (lazy failure).

Failure behavior per `cardinality_mode`:

- `"enforce"` (production default): `ValueError` raised; ingestion
  fails loudly; `fastblocks_cardinality_violations_total{label}`
  incremented before raise.
- `"warn"`: WARNING log; metric dropped; execution continues.
- `"off"`: metric incremented with raw value; dev convenience only.

**CI lint script** (`scripts/check_metric_cardinality.py`) — CI-time
safety net. AST-based, no runtime:

1. Walk all `.py` files under `fastblocks/` and `tests/`.
1. For each `Counter(name=..., labelnames=(...))` call, extract the
   `labelnames` tuple.
1. Resolve each label name against the symbol table of its module.
1. Assert: each label name corresponds to a `Literal[...]` annotation
   OR appears in the global allowlist at
   `fastblocks/observability/_label_allowlist.py`.
1. On violation: print file:line + offending label name + suggested
   `Literal[...]` form; exit 1.

Why AST + symbol-table, not regex: `re.sub()` `re.S` patterns can
spill across functions; AST requires the literal string to bind to a
real identifier; that identifier is checked against a Literal
annotation; the binding is exact.

**Per-metric literal registry** (`_label_allowlist.py`):

```python
from typing import Literal

StyleResult = Literal["hit", "miss", "shadowed"]
ToolName = Literal[
    "validate_template", "list_templates", "render_template",
    "list_components", "validate_component",
    "list_adapters", "check_adapter_health",
]
ToolStatus = Literal["ok", "error", "timeout"]

_KNOWN_LABELS: dict[str, type] = {
    "result": StyleResult,
    "tool_name": ToolName,
    "status": ToolStatus,
}
```

Two-tier safety: Literal annotations (type-system contract) +
allowlist (CI-contract). Both required to add a new label.

**MCP tool instrumentation** — `fastblocks/mcp/observability.py`:

```python
from time import perf_counter
from fastblocks.observability import Counter, Histogram

_INVOCATIONS = Counter(
    name="fastblocks_mcp_tool_invocations_total",
    labelnames=("tool_name", "status"),
)
_DURATION = Histogram(
    name="fastblocks_mcp_tool_duration_seconds",
    labelnames=("tool_name",),
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0),
)
```

Each of the 7 MCP tools (`validate_template`, `list_templates`,
`render_template`, `list_components`, `validate_component`,
`list_adapters`, `check_adapter_health`) gets `instrument_tool(...)`
wrapping at registration time.

**NOTE**: this instrumentation depends on `register_fastblocks_tools`
being a non-orphaned path (per ADR 0011 Decisions 6/11). If Phase 4
follow-up hasn't landed before Phase 6 starts, alternative mount path
required. **Open review flag #1.**

**`/metrics` endpoint** — `prometheus_client.openmetrics.exposition.generate_latest()` (per multi-agent review F-PYTV2-001):

```python
from prometheus_client.openmetrics.exposition import (
    generate_latest as openmetrics_generate_latest,
    CONTENT_TYPE_LATEST as OPENMETRICS_CONTENT_TYPE,
)

async def metrics_endpoint(request: Request) -> Response:
    """OpenMetrics-format scrape endpoint.

    Prometheus text 1.0.0 (`text/plain; version=1.0.0; charset=utf-8`,
    the `CONTENT_TYPE_LATEST` from `prometheus_client.exposition`)
    SILENTLY STRIPS exemplars from observation events. The Phase 6
    design's exemplar-based trace↔metric correlation (see §6B.7) is
    therefore LOST at scrape time if the endpoint emits text 1.0.0.
    OpenMetrics (`application/openmetrics-text; version=1.0.0`)
    preserves exemplars with the `# {trace_id="..."} <value>` syntax.
    """
    return Response(
        content=openmetrics_generate_latest(),
        media_type=OPENMETRICS_CONTENT_TYPE,
    )
```

**Why OpenMetrics over text 1.0.0** (F-PYTV2-001): Phase 6 §6B.7
mandates Prometheus exemplars on histograms for trace↔metric
correlation (`Histogram.observe(value, exemplar={"trace_id": <hex>})`).
Empirically verified: `Histogram(...).observe(0.5, exemplar={"trace_id": "abc"})`
emits `# {trace_id="abc"} 0.5 ...` in OpenMetrics output and ZERO
exemplar annotation in text 1.0.0 output. Scrape consumers (Grafana
Agent, Prometheus scrape jobs) MUST negotiate the OpenMetrics content
type; the spec mandates `Accept: application/openmetrics-text` from
operators' scrape configs. Grafana 10.x reads both formats; older
Prometheus servers (pre-2.5) may need configuration.

Auth: `/metrics` is unauthenticated by default (matches Prometheus
scrape conventions). If operator sets `auth.metrics: true` in settings,
the existing JWT middleware wraps the route. No new auth machinery.

**6B commits**:

| # | Commit |
|---|---|
| 5 | `feat(observability): Typed Counter/Histogram wrappers + CardinalityGuard` |
| 6 | `feat(observability): _label_allowlist.py + Literal binding registry` |
| 7 | `feat(scripts): check_metric_cardinality.py — CI lint` |
| 8 | `feat(mcp): observability wrapper around tool dispatch (instrument_tool decorator)` |
| 9 | `feat(app): /metrics endpoint mounted in default app` |

**6B tests** (~12): guard trips on bad value, guard respects
`cardinality_mode`, Literal set extracted correctly, missing Literal
annotation rejects, known labels resolve, unknown label rejects at
Counter init, allowlist lookup works, untyped labelnames lint fails,
typed labelnames lint passes, allowlist entry lint passes, lint runs
end-to-end on fixture, instrument_tool increments counter on ok

- error.

### 6B.7 — Cardinality safety rule (per multi-agent review F-OBS-001)

Phase 6 forbids the following as Prometheus label values, full stop:

| Forbidden | Why | What to use instead |
|---|---|---|
| `trace_id`, `span_id` | Unique per request; one new time series per request directly recreates the OOM condition this phase is supposed to prevent | OTel context propagation; `merge_contextvars` or a custom structlog processor that reads `trace_context.get()` and merges the trace_id into the log line's event dict; Prometheus exemplars on histograms (Python `prometheus_client` supports `Observe(exemplar=...)`) |
| `request_id`, `correlation_id` | Same cardinality problem | Logs only |
| Full URLs (`https://example.com/foo?bar=baz`) | Unbounded by `?query` strings | Route templates (`/items/{id}`) or OTel span name |
| User-controlled path segments (`/items/{id}`, `/users/{uuid}`) | `id` and `uuid` are unbounded | Static route names |
| Generic `boundary` labels with a single possible value | A label with N=1 isn't a label — it's a constant that makes alerting and grouping harder | Label-free counter until ≥2 actual boundary types exist |
| `domain` from Oneiric | New `domain` types can be added at runtime; permit a per-metric `Literal["fastblocks.style", "fastblocks.renderer", "fastblocks.adapter", ...]` allowlist keyed to `Counter` registration | `Literal[...]` per-metric |

**Correlation policy**: cross-signal correlation (logs ↔ traces ↔ metrics) MUST go through:

1. **OTel context** (Python's `opentelemetry.context` propagation through `ContextVar`s).
1. **Logs** (structlog `merge_contextvars` for what it covers, plus a custom structlog processor reading `_current_trace` for trace_id/span_id).
1. **Exemplars** on Prometheus histograms (`observe(exemplar={"trace_id": <hex>})`).

NOT through Prometheus labels. This is the design's iron rule.

______________________________________________________________________

### 6C — Trace propagation + a11y bridges (4-5 commits)

**What ships**: the async-fanout + UI-bridge concerns.

| File | Purpose |
|---|---|
| `fastblocks/observability/trace_context.py` (refactored) | Public `get`/`set`/`clear` API; `TraceContext` frozen dataclass |
| `fastblocks/observability/otel_middleware.py` (NEW) | Starlette `BaseHTTPMiddleware`; outermost in stack; creates OTel root span per request |
| `fastblocks/observability/sentry_bridge.py` (NEW) | Initializes Sentry with `OpenTelemetryIntegration()`; resolves Sentry+OTel root-span conflict |
| `fastblocks/websocket/a11y_bridge.py` (NEW) | Routes WebSocket broadcasts into aria-live regions with policy table |
| `fastblocks/adapters/app/default.py` (modified) | Mounts `OtelMiddleware`; injects `fastblocks_web_socket_a11y_region` Jinja helper |
| `tests/htmx/test_trace_context_propagation.py` (NEW) | Verifies trace survives `run_in_executor` boundary |
| `tests/a11y/test_websocket_landing.py` (NEW) | Playwright + aria snapshot — WS broadcast → DOM aria-live |
| `dashboards/fastblocks-overview.json` (NEW) | Grafana 10.x dashboard with 8 named panels |
| `tests/dashboards/test_fastblocks_dashboard_schema.py` (NEW) | Dashboard JSON validates against Grafana 10.x schema |

**`trace_context` ContextVar binding** (master plan line 494):

```python
from contextvars import ContextVar
from dataclasses import dataclass

@dataclass(frozen=True)
class TraceContext:
    trace_id: str
    span_id: str
    parent_span_id: str | None = None

_current_trace: ContextVar[TraceContext | None] = ContextVar(
    "fastblocks_trace", default=None,
)
_current_request_id: ContextVar[str | None] = ContextVar(
    "fastblocks_request_id", default=None,
)

def get() -> TraceContext | None: ...
def set(ctx: TraceContext) -> None: ...
def clear() -> None: ...
```

Public API surface: only `get`/`set`/`clear`. The ContextVar objects
themselves are private. Module-level `ContextVar`s with `default=None`
are the modern idiom and integrate with `asyncio.Task` natively.
`current_context()` (Python 3.13 stdlib) is `contextvars.copy_context()`
which is heavier.

**htmx.py executor boundary** (per multi-agent review F-STR-1, F-OBS-006).
The actual file is `fastblocks/htmx.py` (single file, 416 lines) — NOT
`fastblocks/htmx/loop.py` (which does not exist). The relevant real
helper is `_run_async_safely` at `fastblocks/htmx.py:19-52`, which
delegates sync callers to async code via `executor.submit(asyncio.run, coro).result()`.

**The propagation problem this surfaces**: `executor.submit(...)` starts
a *new thread* with a fresh empty `ContextVar` storage. The coroutine
inside `asyncio.run()` runs in the new thread's empty context.
`_current_trace` set in the caller thread is **not** propagated. The
prior spec snippet (a `_dispatch_with_trace` helper using
`copy_context()`) was a no-op — `ctx` was computed and never applied.

**What Phase 6 ships for this boundary**: Commit 12 is a **regression
test only**. The test asserts that trace_context IS lost across the
boundary under the current implementation (captured by
`fastblocks_trace_context_lost_total`). The boundary fix itself —
wrapping the executor call so context is preserved, e.g.
`executor.submit(copy_context().run, asyncio.run, coro)` — belongs in
a separate Phase 6.5 commit (or as an additional Phase 6 commit 12b).
It is explicitly flagged as a production-code change to
`fastblocks/htmx.py`. The fix is recorded in §5.6 Open Review Flags
and is out of Phase 6's 15-commit scope per the user's "targeted
fix round" choice.

Phase 6 emits `fastblocks_trace_context_lost_total` (label-free) —
observability OF the boundary violation, recorded as a known gap.

**OTel middleware** (master plan line 495 — outermost):

```python
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from starlette.middleware.base import BaseHTTPMiddleware

class OtelMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        tracer = trace.get_tracer("fastblocks.http")
        with tracer.start_as_current_span(f"{request.method} {request.path}") as span:
            trace_context.set(TraceContext(
                trace_id=format(span.get_span_context().trace_id, "032x"),
                span_id=format(span.get_span_context().span_id, "016x"),
            ))
            try:
                response = await call_next(request)
                span.set_attribute("http.status_code", response.status_code)
                return response
            except Exception as exc:
                span.record_exception(exc)
                span.set_status(Status(StatusCode.ERROR))
                raise
            finally:
                trace_context.clear()
```

Why outermost: so all other middleware (auth, CORS, request-logging)
become children of the OTel root span. Sibling middleware then link
their own spans to it.

**Mount order — Starlette `add_middleware` is reverse-wrapped** (per
multi-agent review F-STR-2, verified v3 against actual
`MiddlewareManager` source per F-STRV2-2 / F-STRV2-3 / F-OBSV2-002):

- Starlette wraps middleware in REVERSE, so the LAST-registered
  user middleware becomes the outermost AMONG USER MIDDLEWARE.
- FastBlocks' `MiddlewareManager._apply_middleware_to_app`
  (`fastblocks/applications.py:332-342`) iterates `reversed(middleware_list)`.
- FastBlocks' `build_middleware_stack`
  (`fastblocks/applications.py:297-374`) HARDCODES `ExceptionMiddleware`
  to append at the very end of `middleware_list` (line 368-374 per
  F-OBSV2-002). `_apply_middleware_to_app` then iterates in reverse,
  making `ExceptionMiddleware` the OUTERMOST WRAPPER of the entire
  app — OUTSIDE all user middleware, including any "outermost" attempt.
- `MiddlewarePosition` enum (`fastblocks/middleware.py:63-69`) has
  NO `OUTERMOST` member. Per F-STRV2-3, v2's hedge clause "or via
  `MiddlewarePosition.OUTERMOST` if the manager supports it" is
  VAPOR — no implementation pathway exists.

**Therefore OtelMiddleware MUST be registered LAST in user_middleware
to be outermost AMONG USER MIDDLEWARE — but it remains INSIDE the
hardcoded `ExceptionMiddleware`.** Every exception caught by
`ExceptionMiddleware` (handler raises `HTTPException`, programming
errors → 5xx) sits OUTSIDE the OTel root span. The "outermost" promise
is necessarily qualified:

> OtelMiddleware is the outermost middleware among user middleware. It
> covers all application-defined middleware (auth, CORS,
> request-logging) plus the routing layer. The hardcoded
> `ExceptionMiddleware` sits OUTSIDE — operationally interesting
> 5xx failures are NOT inside the OTel root span scope.

The Commit 11 IC's `Demonstrable by:` clause MUST include a test
corrected for the actual return shape of
`MiddlewareManager.get_middleware_stack()`. Per F-STRV2-2, that
method returns a `dict[str, Any]` (NOT a list), so v2's
`assert get_middleware_stack()[0]` is a `TypeError`. The corrected
assertion is:

```python
stack = manager.get_middleware_stack()
user = stack["user_middleware"]
assert isinstance(user, list)
assert user[-1]["class"] == "OtelMiddleware", (
    f"OtelMiddleware must be the LAST entry in user_middleware; "
    f"got {user[-1]['class']!r}"
)
```

If a future Phase records that `ExceptionMiddleware` is removed from
the hardcoded outermost slot (e.g., a follow-up to FastBlocks'
middleware ordering), OtelMiddleware can become TRULY outermost and
this assertion relaxes to `user[-1]` on the full stack. Until then,
the corrected assertion is the v3 contract.

**Sentry + OTel root-span bridge** (master plan line 497):

The conflict: Sentry's SDK creates its own root span via
`sentry_sdk.init(traces_sample_rate=...)`. If OTel also initializes its
own TracerProvider, you get TWO root spans per request — Sentry's spans
don't link to OTel's tree, and vice versa. The bridge:

```python
# Per multi-agent review F-OBS-003: pinned sentry-sdk = 3.0.0a7 (alpha).
# That release exposes the OTel bridge under `sentry_sdk.opentelemetry`,
# NOT `sentry_sdk.integrations.opentelemetry` (which exists in
# later/3.x but paths shift across alphas). The original spec used
# the latter path and would ImportError at startup.
#
# Spec mandates: pre-implementation, run a one-line smoke check
# `python -c "import sentry_sdk; print(sentry_sdk.__version__)"` and
# verify the actual import location by `python -c "from sentry_sdk
# import opentelemetry; print(opentelemetry.__file__)"`. The smoke
# check must be green BEFORE Commit 13 ships; the bridge is gated on it.

from sentry_sdk import init as sentry_init

def init_observability_with_sentry() -> None:
    sentry_init(
        dsn=settings.observability.sentry_dsn,  # optional; may be unset
        # OTel bridge integration is wired dynamically — see smoke check below.
        traces_sample_rate=settings.observability.traces.sample_rate,
    )
```

**Bridge configuration notes**:

- `sentry-sdk` 3.0 is an alpha; the OTel integration paths are not
  stable. The Commit 13 IC MUST include the smoke check
  output (file path of `sentry_sdk.opentelemetry`) as a precondition
  artifact in the commit message body. Any future Sentry upgrade that
  changes the bridge path requires Commit 13 to be re-validated
  (gated by the smoke check).
- For Sentry version-pinning strategy, the spec mandates a single,
  deterministic provider ownership: either Sentry OR OTel is the
  root-span emitter, never both. Default is OTel-as-root with
  Sentry-as-child (current spec intent). The dual-provider ownership
  in 3.0 alpha MUST be verified by a test that asserts a single span
  tree is visible in both UIs.
- The Logfire Starlette instrumentation already present in
  `fastblocks/initializers.py` is NOT addressed in Commit 13 — it's
  pre-existing observability infrastructure. Phase 6 interacts with
  it via the `merge_contextvars` route (custom processor reading
  `_current_trace` per Fix 1's structlog note, if needed); conflicts
  with OTel root-span ownership are out of scope and recorded in
  §5.6 Open Review Flags.

Failure modes:

- `SENTRY_DSN` unset → bridge is a no-op; OTel works alone.
- `sentry_init` raises (bad DSN) → app startup fails with clear error.
- OTel bridge path differs from spec's expected import location →
  bridge fails fast at startup; app MUST add a fallback config knob
  `observability.sentry.disabled_on_import_error: bool` (default `true`)
  that lets operations ship without Sentry while the bridge is
  being repaired.

Failure modes:

- `SENTRY_DSN` unset → bridge is a no-op; OTel works alone.
- `sentry_init` raises (bad DSN) → app startup fails with clear error.
- `OpenTelemetryIntegration()` mis-versioned → `ImportError`; bridge
  fails fast at startup; both systems off until fixed.

**WebSocket → aria-live bridge** (master plan line 492, WCAG SC 4.1.3):

```python
from enum import Enum

class AriaLiveKind(str, Enum):
    POLITE = "polite"
    ASSERTIVE = "assertive"
    OFF = "off"

def render_broadcast_as_a11y(
    *, kind: AriaLiveKind, message: str, role: str = "status",
) -> str:
    """Render a single aria-live region. Per F-A11YV2-003 the class
    is namespaced (`.sr-only--fastblocks-a11y-bridge`) to avoid
    collision with framework `.sr-only` definitions. The CSS rule
    ships in `fastblocks/websocket/static/a11y_bridge.css` (Commit 14).
    """
    return (
        f'<div role="{role}" aria-live="{kind.value}" '
        f'aria-atomic="true" data-fb-aria-live="true" '
        f'class="sr-only--fastblocks-a11y-bridge">{_escape(message)}</div>'
    )


# fastblocks/websocket/static/a11y_bridge.css (NEW, ships with Commit 14)
# Per multi-agent review F-A11YV2-001: clip: rect() was removed from
# Chromium 90+ (2023) and Firefox 92+ in favor of clip-path. v2 used
# the deprecated property; the Playwright assertion checks
# clip-path, so the v2 spec was internally contradictory. v3 mandates
# the modern property so the assertion can hold.
# Also: `border: none` (not `border: 0`) per F-A11YV2-008 — `border: 0`
# shorthand leaves border-style unset, which some UA+base-rule
# combinations render as a 1px border.
.sr-only--fastblocks-a11y-bridge {
  position: absolute !important;
  width: 1px !important;
  height: 1px !important;
  padding: 0 !important;
  margin: -1px !important;
  overflow: hidden !important;
  clip-path: inset(50%) !important;
  white-space: nowrap !important;
  border: none !important;
  /* Namespaced per F-A11YV2-003 to avoid collision with framework
     .sr-only definitions (Bootstrap, Tailwind, fastblocks-ui/panel.css).
     Use `[data-fb-aria-live] .sr-only` if the namespaced class breaks
     an existing a11y test; but the class name change must ship together. */
}
```

Routing policy (which events get which `aria-live` kind):

| Event source | aria-live kind | role | Why |
|---|---|---|---|
| `style_resolve_total{result=hit}` | `polite` | `status` | informational |
| `style_resolve_total{result=miss}` | `assertive` | `alert` | user-visible failure |
| `mcp_tool_invocations_total{status=error}` | `assertive` | `alert` | user-actionable failure |
| `htmy_render_total{escaped=false}` | `assertive` | `alert` | XSS attempt — security event |
| `oneiric_decision_total` | `polite` | `status` | debug info |

**Verification** (per Question 4 decision — Playwright + aria snapshot,
NOT axe-core which Phase 5 deferred):

```python
async def test_websocket_broadcast_lands_in_a11y_region():
    # Boot app with WebSocket adapter; subscribe client.
    # Fire request that triggers fastblocks_style_resolve_total.
    # Assert DOM has new aria-live node with expected text.
```

This is the test that vouches for WCAG SC 4.1.3 compliance.

**Grafana dashboard JSON** (master plan line 496) — panels:

| Panel | Source metric |
|---|---|
| MCP Tool Invocations | `rate(fastblocks_mcp_tool_invocations_total[1m])` |
| MCP Tool Latency (p99) | `histogram_quantile(0.99, fastblocks_mcp_tool_duration_seconds_bucket)` |
| HTMY Render Total | `rate(fastblocks_htmy_component_render_total{escaped}[1m])` (with `escaped=true/false` filter so the master-plan line 583 escape-regression signal is observable) |
| Render Duration | `histogram_quantile(0.95, fastblocks_render_duration_seconds_bucket)` (p95 not p50 — p50 hides tail regressions per F-OBS-007) |
| Style Resolution | `rate(fastblocks_style_resolve_total[1m])` by `result` |
| Shadowed Oneiric Candidates | *(DROPPED in v3)* shadowed-counter required a `details["shadowed"]` key that doesn't exist in Oneiric's `as_dict()` output; deriving from `ordered` would violate master-plan line 489 ("not parallel"). Resurface in a later commit if Oneiric adds a shadowed attribute upstream. |
| Config Validation | `rate(fastblocks_config_validation_total[1m])` by `result` |
| Trace Context Loss | `rate(fastblocks_trace_context_lost_total[1m])` (label-free) |

**Per-metric instrumentation matrix** (mandated by multi-agent review
F-OBS-002 — the dashboard cannot be implemented or verified without
this). Each metric has exactly one emitting call site in the codebase:

| Metric | Emitted at | Labels | Bound test |
|---|---|---|---|
| `fastblocks_mcp_tool_invocations_total` | `instrument_tool` decorator in `fastblocks/mcp/observability.py` (Commit 8) | `tool_name, status` | `tests/mcp/test_mcp_observability.py::test_counters_incremented` |
| `fastblocks_mcp_tool_duration_seconds` | same | `tool_name` | same |
| `fastblocks_htmy_component_render_total` | New emit at HTMY render call site — **TBD by implementer**: actually locate via `git grep -n "render_component\|htmy" fastblocks/adapters/templates/` and pin the file:line in the Commit IC's `Demonstrable by:` block. The Commit 4 / 6C IC MUST NOT ship with `:??` placeholders. | `escaped ∈ Literal["true", "false"]` | new test in `tests/observability/test_htmy_render_counter.py` |
| `fastblocks_render_duration_seconds` | Same HTMY render call site (TBD as above) | (no labels — histogram-only) | new test asserts `observe()` round-trip |
| `fastblocks_style_resolve_total` | **TBD by implementer**: locate via `git grep -n "select_strategy\|resolve" fastblocks/core/resolver.py` and pin file:line. The Phase 1.5 `resolver_metrics.py` exists but is stdlib-only, NOT pre-stubbed for prometheus_client (per F-OBSV2-003). | `result ∈ Literal["hit", "miss"]` (shadowed dropped from result literal; it's a separate metric that no longer exists) | extended `tests/core/test_resolver_metrics.py` |
| `fastblocks_oneiric_decision_total` | Oneiric adapter's SpanProcessor (Commit 4) on `resolver.decision` span end, reading BARE `domain`, `key`, `provider`, `decision` attributes | `domain ∈ Literal["fastblocks.style", "fastblocks.renderer", "fastblocks.adapter", "unknown"]`; `decision ∈ Literal["resolved"]` | `tests/observability/test_oneiric_adapter.py::test_decision_counter_increments` |
| `fastblocks_oneiric_decision_total` | same — covers BOTH outcomes (resolved AND shadowed) | `domain, decision ∈ Literal["resolved"]` (forward-compat for future failure modes) | same |
| `fastblocks_config_validation_total` | New emit at settings loader `validate_settings` (Phase 2.5's `AppSettings`) | `result ∈ Literal["ok", "invalid"]` | new test in `tests/observability/test_config_validation_counter.py` |
| `fastblocks_trace_context_lost_total` | `trace_context` module (Commit 10) increments when caller isNone and callee is non-None | (label-free per §6B.7) | `tests/observability/test_trace_context.py::test_loss_counter_increments` |

The matrix above is the **observability contract** — each metric
listed in the dashboard is bound to exactly one emitting call site and
exactly one test. If the matrix changes (e.g., a new panel is added),
the spec update MUST come with both the new emit code path AND the
test commit reference.

**Per-dashboard-metric ground-truth test**: `tests/dashboards/test_fastblocks_dashboard_schema.py` MUST scan
each panel's `targets[].expr`, extract the metric name, and assert that
metric appears in the per-metric matrix above (or in a CI-managed
machine-readable allowlist file). A panel referencing an un-instrumented
metric fails at test time, not at production scrape time.

Schema validation: dashboard JSON checked against Grafana 10.x schema
(`tests/dashboards/test_fastblocks_dashboard_schema.py`). On future
Grafana version bumps, the test fails and an implementer updates both
the dashboard AND the test schema simultaneously.

**6C commits**:

| # | Commit |
|---|---|
| 10 | `feat(observability): trace_context get/set/clear public API` |
| 11 | `feat(observability): OtelMiddleware + trace_id binding into context` |
| 12 | `feat(observability): htmx.py per-thread loop context-capture test` |
| 13 | `feat(observability): Sentry+OTel bridge (OpenTelemetryIntegration wiring)` |
| 14 | `feat(websocket): a11y_bridge — broadcast → aria-live region routing` |
| 15 | `feat(dashboards): fastblocks-overview.json + schema-validation test` |

**6C tests** (~12): get/set roundtrip, clear resets, frozen dataclass
rejects mutation, root span created, trace_id flows into metric labels,
exception records on span, no-DSN path is no-op, both DSN+OTel init
produces single span tree, trace survives `run_in_executor` boundary,
routing policy matches table, message escaped, Playwright WS → DOM
aria-live test, Grafana 10.x schema validates.

## Cross-cutting failure modes

| Failure | Behavior | Why |
|---|---|---|
| `/metrics` endpoint times out | 503 with structured log; scrape fails; Prometheus retries per its own schedule | observability endpoint can't take down the app |
| OTel collector unreachable | Sampler drops traces; logs fall back to local stderr | observability can't take down the app |
| Counter name collision (two Counters share a name) | `ValueError` at module-load time | prevents silent double-export; loud startup error |
| Histogram bucket array mismatch | `ValueError` at observe() time | prevents silent bin-boundary bugs |
| `trace_context.get()` returns `None` inside htmx.py loop | `fastblocks_trace_context_lost_total` increments (label-free); observability continues | observability OF the boundary violation, not a crash |
| CardinalityGuard trips in production | `cardinality_mode="enforce"` → `ValueError`; instrumented-caller catches; `fastblocks_cardinality_violations_total` incremented | observability OF misuse, not silent drop |
| Sentry DSN rotates | Bind at startup; rotation requires restart (matches Sentry's own model) | documented limitation |
| Dashboard JSON schema drift (Grafana upgraded) | `tests/dashboards/` fails; implementer updates dashboard AND schema assertion together | catches unintentional dashboard breakage |

**Pattern across all failure modes**: observability failures degrade to
less observability; never to app failure.

## Migration policy

Per master plan line 350: *"Per the conversation, no backwards
compatibility required."* Per master plan line 356: *"No deprecation
warnings in fastblocks production code."*

| Layer | Migration step | Status |
|---|---|---|
| Existing `print()` calls in source | Replace with `get_logger("module").info(...)`. Per-file; not project-wide | **Required** before 6A completes |
| Existing `logging.getLogger()` calls | Configured to route through `structlog` processor (`structlog.stdlib.LoggerFactory`) — non-breaking | **No-change needed** |
| Existing counters (none in fastblocks today; master plan Phase 0 catalogued this) | N/A | |
| Existing OTLP or other tracing | Bridge config; instrument ALONGSIDE, not REPLACE | **No-change** |
| Existing aria-live handling in DOM (none — Phase 6 introduces this) | N/A | |
| Sentry SDK usage (if any) | Bridge config maintains it; no code changes | **No-change** |

Per commit order (no-deprecation-cycle pattern): every replacement
commit leaves the prior mechanism FUNCTIONAL but unused. If both paths
must coexist for a transition window, the unused path is removed in
the SAME commit (no deprecation period). Matches the master plan's
`with suppress(Exception)` ratchet pattern applied to observability.

## Verification gate

Phase 6 done means ALL of these pass:

| Gate item | Test/command | Pass criterion |
|---|---|---|
| ty strict | `uv run ty check fastblocks/` | "All checks passed!" |
| pyright strict | `uv run pyright fastblocks/` | 0 errors (warnings allowed only for `reportMissingTypeStubs`) |
| ruff | `uv run ruff check fastblocks/ tests/` | 0 violations |
| refurb | `uv run refurb fastblocks/ tests/` | 0 violations |
| bandit | `uv run bandit -r fastblocks/` | 0 high-severity |
| pytest (not slow) | `uv run pytest -q -m "not slow" --no-header` | ≥ current baseline, 0 fails |
| Phase 6 tests | `uv run pytest tests/observability/ tests/dashboards/ tests/a11y/test_websocket_landing.py tests/mcp/test_mcp_observability.py -v` | 30-40 new tests, 0 fails |
| Cardinality lint | `uv run python scripts/check_metric_cardinality.py fastblocks/` | exit 0; no unbounded labels |
| Dashboard schema | `uv run pytest tests/dashboards/ -v` | dashboard JSON validates against Grafana 10.x schema |
| WCAG SC 4.1.3 | `uv run pytest tests/a11y/test_websocket_landing.py -v` | 1 Playwright test passes; aria-live region observed in DOM |
| Manual smoke | `fastblocks mcp serve` then `curl :8680/metrics` | text-format metrics exported; named counter names present |

Baseline expectations (from `git show HEAD:pyproject.toml`):

- ty: 0 prod errors
- pytest: ~1800+ tests, 0 fails
- ruff/refurb/bandit: 0

Phase 6 adds ~30-40 tests, ~12 commits. Pytest baseline must continue to hold.

## Per-task Integration Contracts

Per master plan line 553: *"For Phase 6 and Phase 7 (high-blast-radius),
one extra reviewer per task commit."* Each commit below states TWO
reviewer requirements in its IC.

### Commit 1 — `feat(observability): package skeleton + Counter/Histogram wrappers`

- *Triggered from:* Pillar 6 (master plan §6 line 174-180); §Phase 6
  line 342; Section 2 §6A.1
- *Returns to / updates:* NEW `fastblocks/observability/__init__.py`
  - `counters.py`; initial test
- *Demonstrable by:* `python -c "from fastblocks.observability import Counter; Counter(name='demo', labelnames=('r',))"` works
- *Rollback signal:* `git revert`; pure addition
- *Observability added:* none (this IS the observability)
- *Reviewers:* 2 (one python-pro for typing; one observability-incident-lead for label discipline)

### Commit 2 — `feat(observability): structlog Logger bound to Oneiric settings`

- *Triggered from:* Commit 1; Section 2 §6A.1
- *Returns to / updates:* NEW `fastblocks/observability/loggers.py`;
  one route to `get_logger`
- *Demonstrable by:* `get_logger("mymod").info("event", request_id="abc")`
  emits JSON line with `event`, `request_id`, `level`, `timestamp`
- *Rollback signal:* `git revert`
- *Observability added:* structured log path live
- *Reviewers:* 2 (python-pro for type-safety; observability-incident-lead
  for cardinality of log fields)

### Commit 3 — `feat(observability): OTel Tracer + trace_context (ContextVar binding)`

- *Triggered from:* Commit 1; Section 4 §6C.1
- *Returns to / updates:* NEW `fastblocks/observability/tracer.py`,
  `trace_context.py`
- *Demonstrable by:* `trace_context.set(...); trace_context.get()`
  roundtrip works; span from `tracer.start_as_current_span("test")`
  has non-zero IDs
- *Rollback signal:* `git revert`
- *Observability added:* trace emission path live; OTLPSpanExporter
  wired (idempotent if collector absent)
- *Reviewers:* 2 (python-pro; observability-incident-lead)

### Commit 4 — `feat(adapters): Oneiric observability adapter — SpanProcessor on `resolver.decision` spans`

- *Triggered from:* Commits 1+2; Section 2 §6A.3 (real contract per multi-agent review F-ONE-001 / F-OBS-004, corrected for v3 per F-ONEV2-001 / F-ONEV2-002 / F-ONEV2-003 / F-ONEV2-004)
- *Returns to / updates:* NEW `fastblocks/adapters/oneiric/observability.py` (SpanProcessor installs on OTel global `TracerProvider` — no facade hook claim); NEW `scripts/verify_oneiric_otel_attrs.py` (precondition smoke check with bare attribute names); NEW `tests/observability/conftest.py` (autouse fixture for SpanProcessor teardown)
- *Demonstrable by:* Run `scripts/verify_oneiric_otel_attrs.py` — fires a real `traced_decision()` in Oneiric, asserts the FOUR BARE attribute names (`domain`, `key`, `provider`, `decision`) appear on the emitted span. CI fails the commit if attributes are absent OR namespaced. Then a unit test triggers Oneiric resolution; the SpanProcessor emits both a `structlog` line and an increment on `fastblocks_oneiric_decision_total{domain, decision}` via the synthetic sink. THEN the autouse fixture in `tests/observability/conftest.py` is verified to have torn down the SpanProcessor in the test's teardown phase (next test sees a clean TracerProvider).
- *Precondition artifact:* Commit 13's smoke-check output (import path of `sentry_sdk.opentelemetry`) is preserved in the commit message body, per the Sentry import-path fix.
- *Rollback signal:* `git revert`
- *Observability added:* Oneiric → fastblocks observability export live (decision events only; shadowed-counter dropped per F-ONEV2-002)
- *Reviewers:* 2 (oneiric-specialist for protocol correctness;
  observability-incident-lead for cardinality of decision labels)

### Commit 5 — `feat(observability): Typed Counter/Histogram wrappers + CardinalityGuard`

- *Triggered from:* Commit 1; Section 3 §6B.2
- *Returns to / updates:* refactor `fastblocks/observability/counters.py`
- *Demonstrable by:* `Counter("foo", labelnames=("result",))` rejects
  `inc(result="bogus")` per `cardinality_mode` setting
- *Rollback signal:* `git revert`
- *Observability added:* CardinalityGuard emits
  `fastblocks_cardinality_violations_total{label}` on trip
- *Reviewers:* 2 (python-pro; observability-incident-lead for guard threshold tuning)

### Commit 6 — `feat(observability): _label_allowlist.py + Literal binding registry`

- *Triggered from:* Commit 5; Section 3 §6B.4
- *Returns to / updates:* NEW `fastblocks/observability/_label_allowlist.py`
- *Demonstrable by:* `KNOWN_LABELS["result"]` resolves to `StyleResult`
  Literal
- *Rollback signal:* `git revert`
- *Observability added:* none
- *Reviewers:* 2 (python-pro; observability-incident-lead for label taxonomy)

### Commit 7 — `feat(scripts): check_metric_cardinality.py — CI lint`

- *Triggered from:* Commit 6; Section 3 §6B.3
- *Returns to / updates:* NEW `scripts/check_metric_cardinality.py`
- *Demonstrable by:* Adding `Counter("foo", ("bogus_label",))` makes
  `python scripts/check_metric_cardinality.py fastblocks/` exit 1
  with file:line
- *Rollback signal:* `git revert`
- *Observability added:* CI gate live
- *Reviewers:* 2 (python-pro for AST correctness; observability-incident-lead for false-positive review)

### Commit 8 — `feat(mcp): observability wrapper around tool dispatch (instrument_tool decorator)`

- *Triggered from:* Commits 5+7; Section 3 §6B.5
- *Returns to / updates:* NEW `fastblocks/mcp/observability.py`;
  `fastblocks/mcp/server.py` registered tools wrapped
- *Demonstrable by:* `validate_template(...)` call increments
  `fastblocks_mcp_tool_invocations_total{tool_name="validate_template", status="ok"}`
- *Rollback signal:* `git revert`; tools return to un-instrumented
- *Observability added:* MCP metrics live
- *Reviewers:* 2 (mcp-integration-expert; observability-incident-lead)
  — **NOTE**: depends on `register_fastblocks_tools` being a
  non-orphaned path. If Phase 4 follow-up hasn't landed, alternative
  mount path required. *Open review flag #1.*

### Commit 9 — `feat(app): /metrics endpoint mounted in default app`

- *Triggered from:* Commits 1+5; Section 3 §6B.6
- *Returns to / updates:* `fastblocks/adapters/app/default.py`
- *Demonstrable by:* `curl :8680/metrics` returns text-format Prometheus output
- *Rollback signal:* `git revert`
- *Observability added:* metrics export live
- *Reviewers:* 2 (starlette-specialist; observability-incident-lead)

### Commit 10 — `feat(observability): trace_context get/set/clear public API`

- *Triggered from:* Commit 3 expansion; Section 4 §6C.1
- *Returns to / updates:* refactor `fastblocks/observability/trace_context.py`
- *Demonstrable by:* frozen TraceContext rejects direct mutation;
  get/set/clear API only
- *Rollback signal:* `git revert`
- *Observability added:* none (public API surface discipline)
- *Reviewers:* 2 (python-pro for frozen dataclass contract; observability-incident-lead)

### Commit 11 — `feat(observability): OtelMiddleware + trace_id binding into context`

- *Triggered from:* Commit 10; Section 4 §6C.3
- *Returns to / updates:* NEW `fastblocks/observability/otel_middleware.py`;
  mounted outermost in default app
- *Demonstrable by:* Request through the app → OTel root span created →
  `trace_context.get()` non-None inside handler
- *Rollback signal:* `git revert`
- *Observability added:* OTel middleware live; trace_id flows into all counters
- *Reviewers:* 2 (starlette-specialist; observability-incident-lead)

### Commit 12 — `feat(observability): htmx.py per-thread loop context-capture test`

- *Triggered from:* Commits 10+11; Section 4 §6C.2
- *Returns to / updates:* NEW `tests/htmx/test_trace_context_propagation.py`
- *Demonstrable by:* Test passes — trace context survives
  `run_in_executor` boundary
- *Rollback signal:* test-only commit; rollback is delete
- *Observability added:* None (test-only commit)
- *Reviewers:* 2 (starlette-specialist; observability-incident-lead)

### Commit 13 — `feat(observability): Sentry+OTel bridge (OpenTelemetryIntegration wiring)`

- *Triggered from:* Commit 11; Section 4 §6C.4
- *Returns to / updates:* NEW `fastblocks/observability/sentry_bridge.py`;
  called from app startup
- *Demonstrable by:* With Sentry DSN set, single span tree in both
  Sentry and OTel collector; without DSN, no-op
- *Rollback signal:* `git revert`
- *Observability added:* Sentry+OTel correlation live
- *Reviewers:* 2 (observability-incident-lead; oneiric-specialist for
  the integration wiring)

### Commit 14 — `feat(websocket): a11y_bridge — broadcast → aria-live region routing`

- *Triggered from:* Commits 1+5; Section 4 §6C.5
- *Returns to / updates:* NEW `fastblocks/websocket/a11y_bridge.py`;
  NEW `fastblocks/websocket/static/a11y_bridge.css` (the
  **namespaced** `.sr-only--fastblocks-a11y-bridge` rule using
  modern `clip-path: inset(50%)` per multi-agent review F-A11YV2-001
  / F-A11YV2-003 / F-A11YV2-008 — without this CSS file SHIPPED and
  LOADED, the bridge's emitted `<div data-fb-aria-live="true" class="sr-only--fastblocks-a11y-bridge">` is neither visible to
  sighted users nor reachable by screen readers, silently failing the
  WCAG SC 4.1.3 contract from master plan line 492);
  rendered in default HTMY template
- *Demonstrable by:*
  1. `render_broadcast_as_a11y(kind=POLITE, message="hit", role="status")`
     returns the expected escaped HTML containing
     `data-fb-aria-live="true"` and the namespaced class.
  1. Playwright test boots app + WebSocket adapter, fires request
     triggering a fastblocks_websocket event. The assertion MUST:
     (a) find the node via `[data-fb-aria-live="true"]`,
     (b) assert its `classList` contains `"sr-only--fastblocks-a11y-bridge"`,
     (c) assert the computed style via `await expect(page.locator('[data-fb-aria-live="true"]').first().evaluate(   'el => getComputedStyle(el).clipPath')).resolves.toBe('inset(50%)')`,
     (d) assert `await expect(page.locator('[data-fb-aria-live="true"]').first().evaluate(   'el => getComputedStyle(el).width')).resolves.toBe('1px')`.
     The `clip-path: inset(50%)` half is the load-bearing one (per
     F-A11YV2-001 — if it fails, the shipped CSS isn't loaded).
  1. Manual screen-reader smoke gate (NVDA + VoiceOver) — recorded as
     a known limitation of automated testing, documented inline.
- *Rollback signal:* `git revert`
- *Observability added:* a11y bridge live (NOT user-observable until
  event happens)
- *Reviewers:* 2 (accessibility-auditor for ARIA correctness;
  websocket-specialist for emit point)

### Commit 15 — `feat(dashboards): fastblocks-overview.json + schema-validation test`

- *Triggered from:* Commits 8+11+13; Section 4 §6C.6
- *Returns to / updates:* NEW `dashboards/fastblocks-overview.json`;
  NEW `tests/dashboards/test_fastblocks_dashboard_schema.py`
- *Demonstrable by:* Dashboard JSON parses against Grafana 10.x
  schema; named panels reference defined counters
- *Rollback signal:* `git revert`
- *Observability added:* Grafana dashboard JSON published
- *Reviewers:* 2 (observability-incident-lead for panel coverage;
  python-pro for schema assertion correctness)

## Estimated effort

| Section | Commits | New tests | Estimated time |
|---|---|---|---|
| 6A | 4 (1-4) | ~10 | 1.5 weeks |
| 6B | 4 (5-8) | ~12 | 1.5 weeks |
| 6C | 5 (9-15) | ~12 | 2 weeks |
| **Total** | **~12-15** | **~30-40** | **~5 weeks** |

## Open review flags (raised for handoff)

1. **Commit 8 dependency**: depends on `register_fastblocks_tools` being
   a non-orphaned mount path (per ADR 0011 Decisions 6/11). If Phase 4
   follow-up hasn't landed before Phase 6 starts, alternative mount path
   required.
1. **Master plan Phase 6 verification gate item**: "Lifecycle integration
   test (`httpx.AsyncClient` + `LifespanManager`) asserts
   `app.state.main_loop` and `app.state.jinja_env` are bound at startup,
   not per-request" — referenced from §Phase 5 verification line
   478-479. Re-read at handoff: this might be Phase 5 verification debt
   rolled into Phase 6. If so, Phase 6 inherits the `LifespanManager`
   doesn't-exist P0 from ADR 0012 Decision 2.
1. **Oneiric `Decisions.events()` API** *(closed in v2)*: Phase 6
   originally assumed an event-stream contract that did not exist.
   Replaced with SpanProcessor consuming actual `resolver.decision`
   OTel spans emitted by Oneiric's `traced_decision()` context manager.
   Pre-condition artifact (verify_oneiric_otel_attrs.py output)
   shipped as a Commit 4 smoke-check gate.
1. **Grafana dashboard version**: pinned to Grafana 10.x. If operator
   uses different version, the schema assertion will fail. Document as
   expected behavior; treat as known limitation.
1. **Commit 12 boundary fix**: trace_context propagation across
   `fastblocks/htmx.py:_run_async_safely` is recorded as a regression
   test only; the production-code fix (`executor.submit(copy_context().run, asyncio.run, coro)`)
   is split off as a Phase 6.5 commit. Recorded as Phase 6's known-gap
   in §6C.2. **Phase 6.5 ORDERING CONSTRAINT** (per v3 review F-STRV2-4):
   the master-plan-specified `asyncio.run_coroutine_threadsafe(coro, app.state.main_loop)` fix REQUIRES `app.state.main_loop` to be
   bound at lifespan start. No `LifespanManager` class exists in
   fastblocks (`fastblocks/adapters/app/default.py:164-178` defines an
   `@asynccontextmanager async def lifespan` that doesn't bind
   `app.state.main_loop` or `app.state.jinja_env`). The Phase 6.5 htmx
   fix is therefore GATED on a separate Phase 6.5 LifespanManager
   commit that fixes the lifespan to bind these `app.state` attributes.
   v3 marks this as a structural deferred item — out of Phase 6's 15-commit
   scope, but a HARD PREREQUISITE for any future htmx.py trace
   fix.
1. **Open Review Flag #2 (LifespanManager inheritance)** is
   EFFECTIVELY OPEN in v3. v2 marked it "open" without fixing; v3
   adds the Phase 6.5 ordering constraint explicitly. Per ADR 0012
   Decision 2, the underlying test (master plan line 478-479) cannot
   pass without a production-code change that violates the
   strict-tests-only boundary. Phase 6.5 must address this before the
   htmx.py boundary fix lands.

## Cross-references

- Master plan: §Pillar 6 (lines 174-180), §Phase 6 (line 342),
  §Phase 6 verification (lines 481-498)
- ADR 0008: Oneiric selection mechanism (SpanProcessor on
  `resolver.decision` spans replaces the originally-assumed event-stream;
  consumer-side counter increment via OTel span attributes)
- ADR 0011: Phase 4 deferral (Commit 8 dependency)
- ADR 0012: Phase 5 deferral (LifespanManager P0 inheritance risk)
- Phase 1.5 spec: Oneiric layered config (settings layer)
- Phase 2 spec: Literal types (Phase 6's Literal labelnames pattern)
- Phase 2.5 spec: AppSettings wiring
- Phase 5 spec: deferred structure (`LifespanManager` doesn't exist;
  tests-only boundary; axe-core deferred) — informs what Phase 6
  cannot rely on for testing
- crackerjack-compliant-code: per-commit hygiene
- CLAUDE.md: process discipline, hard limits
- Master plan §Phase 7 (line 343): blocked on Phase 5 + 6
- Master plan §Phase 8 (line 344): parallel from Phase 1

## Decisions captured during design

1. **Single coherent design, decomposed execution** (Section 1): mirror
   Phase 5's Foundation→Matrix→Adversarial shape as
   Foundations→Metrics→Bridges.
1. **Hybrid test boundary**: structural + smoke + Playwright for a11y;
   no live Prometheus/OTel stack in CI.
1. **Primitives + HTMY render path migration**: ship primitives +
   instrument the highest-traffic paths; defer `asyncio.TaskGroup`
   migration to Phase 6.5.
1. **Bridge in 6C; verify via Playwright + aria snapshot**: matches the
   WCAG SC 4.1.3 requirement without depending on Phase 5's deferred
   axe-core integration.
1. **`prometheus_client` + `structlog` + `opentelemetry-sdk`** as the
   library stack; rejects `statsd`/`loguru`/direct OTel Meter.
1. **`Literal[...]` typing + CI AST lint + per-metric allowlist** as
   three-tier cardinality safety.
1. **HTMY XSS for Jinja2-rendered components is out of scope** per
   master plan §Phase 5 verification line 582-583.

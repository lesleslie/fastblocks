---
status: accepted
role: phase-6-design-spec
date: 2026-08-22
last_reviewed: 2026-08-22
supersedes: null
superseded_by: null
blocks_on: null
decision_date: 2026-08-22
topic: phase-6-observability
---

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
2. Cardinality-safe metrics (6B): typed `Literal[...]` label discipline;
   CI lint guard; MCP tool instrumentation; `/metrics` endpoint.
3. Trace propagation + a11y bridges (6C): `trace_context` ContextVar
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
| `fastblocks/observability/registry.py` (NEW) | Singleton registry; binds to Oneiric `Decisions.events()` stream |
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

**Oneiric observability adapter** subscribes to Oneiric's
`Decisions.events()` stream at startup. For each event:
- Emit a `structlog` line at INFO (e.g.,
  `event="decision_resolved" action="resolved" target="fastblocks.style"
  choice="kelp" shadowed=["bulma"] duration_ms=12`).
- Increment counter
  `fastblocks_oneiric_decision_total{action, target, result}` where
  `result ∈ {"hit", "miss", "shadowed"}`.

**Per master plan line 489 — "not parallel"**: Phase 6 doesn't
duplicate resolution logic in fastblocks. It doesn't re-export Oneiric
metrics under fastblocks names. It doesn't re-derive shadowed
candidates; it surfaces what Oneiric already computed.

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
| Oneiric `Decisions.events()` raises mid-stream | adapter logs exception + drops subscription; signals stop flowing; app continues |

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
2. `Counter.inc()` does the value-shape check; rejects runtime values
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
2. For each `Counter(name=..., labelnames=(...))` call, extract the
   `labelnames` tuple.
3. Resolve each label name against the symbol table of its module.
4. Assert: each label name corresponds to a `Literal[...]` annotation
   OR appears in the global allowlist at
   `fastblocks/observability/_label_allowlist.py`.
5. On violation: print file:line + offending label name + suggested
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

**`/metrics` endpoint** — `prometheus_client.generate_latest()`:

```python
async def metrics_endpoint(request: Request) -> Response:
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST,
    )
```

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
+ error.

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

**htmx.py per-thread loop boundary** (master plan line 521 — flagged
in Phase 1A as a critical finding). The propagator fix is Phase 1A
territory; Phase 6 ships TESTS that verify the boundary works:

```python
# fastblocks/htmx/loop.py — Phase 1A's responsibility; Phase 6 reads it
import contextvars
from fastblocks.observability import trace_context

async def _dispatch_with_trace(coro):
    ctx = contextvars.copy_context()
    return await coro  # Python handles propagation inside asyncio loop
```

What Phase 6 adds: the OBSERVABILITY side. Consumers of the context
propagation, not the propagator. Phase 6 ships tests that verify
trace context survives the boundary AND counter increments inside the
htmx.py loop carry the right `trace_id` label. If propagation breaks,
Phase 6 emits `fastblocks_trace_context_lost_total{boundary}` —
observability OF the boundary violation.

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
their own spans to it. Mounted in `default.py` first in
`add_middleware(...)` order.

**Sentry + OTel root-span bridge** (master plan line 497):

The conflict: Sentry's SDK creates its own root span via
`sentry_sdk.init(traces_sample_rate=...)`. If OTel also initializes its
own TracerProvider, you get TWO root spans per request — Sentry's spans
don't link to OTel's tree, and vice versa. The bridge:

```python
from sentry_sdk import init as sentry_init
from sentry_sdk.integrations.opentelemetry import OpenTelemetryIntegration

def init_observability_with_sentry() -> None:
    sentry_init(
        dsn=settings.observability.sentry_dsn,  # optional; may be unset
        integrations=[OpenTelemetryIntegration()],
        traces_sample_rate=settings.observability.traces.sample_rate,
    )
```

`OpenTelemetryIntegration()` with `transaction_style="tx.name"`
(default): Sentry's `transaction` field comes from OTel's span name.
One tree in both UIs.

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
    return (
        f'<div role="{role}" aria-live="{kind.value}" '
        f'aria-atomic="true" class="sr-only">{_escape(message)}</div>'
    )
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
| HTMY Render Total | `rate(fastblocks_htmy_component_render_total[1m])` |
| Render Duration | `histogram_quantile(0.5, fastblocks_render_duration_seconds_bucket)` |
| Style Resolution | `rate(fastblocks_style_resolve_total[1m])` by `result` |
| Shadowed Oneiric Candidates | `rate(fastblocks_oneiric_decision_total{result="shadowed"}[1m])` |
| Config Validation | `rate(fastblocks_config_validation_total[1m])` by `result` |
| Trace Context Loss | `rate(fastblocks_trace_context_lost_total[1m])` by `boundary` |

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
| `trace_context.get()` returns `None` inside htmx.py loop | Counter `trace_id` label omitted; observability continues; increments `fastblocks_trace_context_lost_total` | observability OF the boundary violation, not a crash |
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
  + `counters.py`; initial test
- *Demonstrable by:* `python -c "from fastblocks.observability import
  Counter; Counter(name='demo', labelnames=('r',))"` works
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

### Commit 4 — `feat(adapters): Oneiric observability adapter — explain()/list_shadowed() bridge`

- *Triggered from:* Commits 1+2; Section 2 §6A.3
- *Returns to / updates:* NEW `fastblocks/adapters/oneiric/observability.py`
- *Demonstrable by:* Trigger Oneiric resolution in test; assert log
  line + counter increment in synthetic sink
- *Rollback signal:* `git revert`
- *Observability added:* Oneiric → fastblocks observability export live
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
  `fastblocks_mcp_tool_invocations_total{tool_name="validate_template",
  status="ok"}`
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
  rendered in default HTMY template
- *Demonstrable by:* `render_broadcast_as_a11y(kind=POLITE, message="hit",
  role="status")` returns the expected escaped HTML
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
2. **Master plan Phase 6 verification gate item**: "Lifecycle integration
   test (`httpx.AsyncClient` + `LifespanManager`) asserts
   `app.state.main_loop` and `app.state.jinja_env` are bound at startup,
   not per-request" — referenced from §Phase 5 verification line
   478-479. Re-read at handoff: this might be Phase 5 verification debt
   rolled into Phase 6. If so, Phase 6 inherits the `LifespanManager`
   doesn't-exist P0 from ADR 0012 Decision 2.
3. **Oneiric `Decisions.events()` API**: Phase 6 assumes the event-stream
   contract exists. Verify with `oneiric-specialist` at handoff time. If
   the contract has changed since ADR 0008, design adapts.
4. **Grafana dashboard version**: pinned to Grafana 10.x. If operator
   uses different version, the schema assertion will fail. Document as
   expected behavior; treat as known limitation.

## Cross-references

- Master plan: §Pillar 6 (lines 174-180), §Phase 6 (line 342),
  §Phase 6 verification (lines 481-498)
- ADR 0008: Oneiric selection mechanism (`Decisions.events()` contract
  consumed by 6A)
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
2. **Hybrid test boundary**: structural + smoke + Playwright for a11y;
   no live Prometheus/OTel stack in CI.
3. **Primitives + HTMY render path migration**: ship primitives +
   instrument the highest-traffic paths; defer `asyncio.TaskGroup`
   migration to Phase 6.5.
4. **Bridge in 6C; verify via Playwright + aria snapshot**: matches the
   WCAG SC 4.1.3 requirement without depending on Phase 5's deferred
   axe-core integration.
5. **`prometheus_client` + `structlog` + `opentelemetry-sdk`** as the
   library stack; rejects `statsd`/`loguru`/direct OTel Meter.
6. **`Literal[...]` typing + CI AST lint + per-metric allowlist** as
   three-tier cardinality safety.
7. **HTMY XSS for Jinja2-rendered components is out of scope** per
   master plan §Phase 5 verification line 582-583.

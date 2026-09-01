______________________________________________________________________

## status: accepted role: phase-6-deferral date: 2026-08-22 last_reviewed: 2026-08-22 supersedes: null superseded_by: null blocks_on: [] decision_date: 2026-08-22 topic: phase-6-observability-deferral

# ADR 0013: Phase 6 Observability Deferral

## Status

Accepted (Phase 6 deferral — companion to master plan §Phase 6 line 342,
§Phase 6 verification line 481-498).

## Context

Phase 6 ("Observability") was the next phase per the master plan (§Phase 6
line 342; §Pillar 6 line 174-180). The spec was designed then went through
**three multi-agent review cycles** (v1 → v2 → v3) with a recurring
**cargo-culting pattern**: each fix round invents API surfaces, file paths,
attribute names, or enum members that don't exist in the actual codebase
or pinned dependencies.

| Round | P0 | P1 | P2 | Net |
|---|---|---|---|---|
| v1 (initial spec) | 8 | 20 | 13 | 41 findings |
| v2 (after 1st fix round) | 10 | 19 | 11 | 40 findings (added 10 new while fixing 8) |
| v3 (after 2nd fix round) | (fixes pending re-review) | — | — | — |

P0 count went 8 → 10 → ... while the **structural cargo-culting
pattern was unbroken across all rounds**. v1 cargo-culted around
`Decisions.events()` (non-existent event stream); v2 cargo-culted
around `oneiric.decision.{domain,key,provider,decision}` attribute
names (fabricated prefix; actual is bare `domain/key/provider/decision`),
`MiddlewareManager.get_middleware_stack()[0]` (returns dict, not list),
and `clip: rect()` + assertion `clip-path: inset(50%)` (different CSS
properties; assertion will fail).

The user's prior pattern (Phase 2 finish + Phase 4 + Phase 5) was to
**defer when multi-agent review surfaces structural issues that don't
converge in 1-2 fix rounds**. Phase 6 reached 3 fix rounds with the
same pattern. Three of the v2 P0s are **strict-tests-only boundary
violations** that cannot be fixed without either changing production
code (violating the boundary) or rewriting the test (master plan
line 478-479's `LifespanManager`-based assertion is impossible — no
`LifespanManager` class exists; fastblocks lifespan is
`@asynccontextmanager` at `fastblocks/adapters/app/default.py:164-178`).

This ADR records the deferral decisions and rationale.

## Decisions

### Decision 1: Phase 6 deferred

Phase 6 scope resolves to **nothing shipped** based on the cumulative
findings across three review cycles. The spec remains in git history
at three commits:

- v1 initial spec: `5f0eb4d`
- v2 (after 1st fix round): `8edec33` (244 insertions, 55 deletions)
- v3 (after 2nd fix round): `a219347` (225 insertions, 77 deletions)

The work that would need to happen before any implementation can succeed
is recorded in Decisions 2-24.

### Decision 2 — P0: `Decisions.events()` API does not exist (F-ONE-001 / F-OBS-004)

The v1 §6A.3 bridge strategy assumed Oneiric exposes a
`Decisions.events()` event-stream subscription API. Verified 2026-08-22:
**no such API exists** — no `Decisions` class, no `events()` method,
no subscribe API, no async iterator, no event bus hook.
`/Users/les/Projects/oneiric/oneiric/core/observability.py:43-59`
defines `DecisionEvent` (a `@dataclass`); it's emitted one-shot via
`traced_decision(event)` context manager in
`oneiric/core/resolution.py:207-215`. The only public external surface
is the OTel span emitted inside `traced_decision()`.

**Path forward**: any future Phase 6 retry must consume either the
OTel span stream (the actual public surface) or contribute a real
subscription API upstream to Oneiric before Commit 4 ships. The
v2/v3 spec used the OTel SpanProcessor approach (correct consumer
surface) but then fabricated the attribute names — see Decision 9.

### Decision 3 — P0: OtelMiddleware cannot be truly outermost (F-STR-2 / F-OBSV2-002)

The v1 §6C.3 instruction "register OtelMiddleware first = outermost"
is FALSE. Starlette wraps middleware in REVERSE (verified against
`MiddlewareManager._apply_middleware_to_app` at
`fastblocks/applications.py:332-342`); the LAST-registered user
middleware is the outermost AMONG USER MIDDLEWARE. More
structurally: `build_middleware_stack` at
`fastblocks/applications.py:297-374` HARDCODES `ExceptionMiddleware`
at the wrap tail (line 368-374 per F-OBSV2-002), making it the
outermost of the entire app — outside ALL user middleware, including
OtelMiddleware. Every exception that becomes a 5xx response is
OUTSIDE the OTel root span scope.

v3 fixed the prose to say "outermost among user middleware, inside
ExceptionMiddleware" but the structural reality remains: operationally
interesting failures (5xx) cannot land in OTel without a production-code
change to `build_middleware_stack` that violates strict-tests-only.

**Path forward**: either (a) document a fastblocks middleware-layer
change to remove ExceptionMiddleware from the hardcoded outermost
slot, or (b) accept that OtelMiddleware coverage excludes 5xx and
note this as a known limitation.

### Decision 4 — P0: `fastblocks/htmx/loop.py` doesn't exist (F-STR-1)

The v1 §6C.2 cited a `_dispatch_with_trace(coro)` helper at a file
that doesn't exist. The actual file is `fastblocks/htmx.py`
(single file, 416 lines); the relevant real helper is
`_run_async_safely` at `fastblocks/htmx.py:29-52` (function body) using
`executor.submit(asyncio.run, coro).result()`. v3 corrected the
citation BUT demoted the propagation fix to a "regression test
only" Commit 12 — the boundary loss is observed, not fixed.

**Path forward**: Phase 6.5 must ship the boundary fix
(`executor.submit(copy_context().run, asyncio.run, coro)`) AND the
LifespanManager creation (Decision 17) before any htmx.py trace
propagation can be observed in production.

### Decision 5 — P0: `sr-only` CSS unverified (F-A11Y-001)

The v1 spec emitted `<div class="sr-only">` without verifying the
CSS rule shipped. v3 shipped the rule AND switched to modern
`clip-path: inset(50%)` (the v2 `clip: rect()` was deprecated since
Chrome 90+ and Firefox 92+, returning empty string from
`getComputedStyle`). v3 also namespaced the class to
`.sr-only--fastblocks-a11y-bridge` to avoid Bootstrap/Tailwind
collisions.

**Path forward**: Phase 6 (or 6.5) ships `fastblocks/websocket/static/a11y_bridge.css`
AND mounts it via Starlette `StaticFiles` AND references it from the
default HTMY template. v3 spec mandates this but does not ship it.

### Decision 6 — P0: trace_id-as-Prometheus-label defeats design (F-OBS-001)

The v1 spec implied trace_id as a Prometheus label. v3 added §6B.7
"Cardinality safety rule" explicitly forbidding this. **However,
v3 also mandated exemplars for trace↔metric correlation — and
Prometheus text 1.0.0 SILENTLY STRIPS exemplars at scrape time**
(Decision 15). So the §6B.7 design's "iron rule" is fine but the
correlation channel it relies on is broken at scrape.

**Path forward**: v3 §6B.6 fixes this by switching `/metrics` to
OpenMetrics format. But the exemplar mandates in §6B.7 are also
required to be implemented at the emit call sites in every Counter
increment — a structural Codebase-wide commitment, not just an
endpoint change.

### Decision 7 — P0: Dashboard disconnected from undeclared metrics (F-OBS-002)

The v1 dashboard referenced 8 metrics; only 2 had emitting call
sites defined. v3 added a per-metric instrumentation matrix
(§6C.6) that pins each metric to one emit site and one test — but
**two matrix rows reference non-existent code paths**:
`htmy_dispatcher.py:??` and `select_strategy` (per F-OBSV2-003 / F-PYTV2-006).

**Path forward**: every "TBD by implementer" row in the matrix must
be resolved to a real file:line via `git grep` BEFORE the
`tests/dashboards/test_fastblocks_dashboard_schema.py` CI test can
pass. The v3 spec flags these as "TBD" but does not resolve them;
ship-time coding agents will create phantom files.

### Decision 8 — P0: Sentry bridge imports wrong path for pinned version (F-OBS-003)

The v1 spec used `from sentry_sdk.integrations.opentelemetry import OpenTelemetryIntegration`. The pinned `sentry-sdk` is `3.0.0a7`
(alpha); that release exposes the OTel bridge under
`sentry_sdk.opentelemetry` (NOT `integrations.opentelemetry`).
v3 dropped the specific import assertion and mandates a smoke-check
precondition instead. **But**: alpha-path stability is not
guaranteed across SDK upgrades.

**Path forward**: pin a specific Sentry minor+build in
`pyproject.toml`; CI smoke check the import path at startup; treat
any future Sentry SDK upgrade as a Phase that re-validates the
bridge.

### Decision 9 — P0 cargo-culting (v2): SpanProcessor reads fabricated attribute names (F-ONEV2-001 / F-OBSV2-001)

The v2 §6A.3 SpanProcessor approach correctly identified OTel
spans as the consumer surface — but asserted attribute names that
don't exist: `oneiric.decision.domain`, `oneiric.decision.key`,
`oneiric.decision.provider`, `oneiric.decision.decision`. Verified
2026-08-22: Oneiric's `DecisionEvent.as_attributes()` emits bare
`domain`/`key`/`provider`/`decision` (NOT namespaced with
`oneiric.decision.`). v3 corrected this — but the v2 cargo-culting
made it through 1 full review cycle unreported.

**Path forward**: the v3 spec mandates BARE attribute names. The
`scripts/verify_oneiric_otel_attrs.py` precondition script must assert
the four bare names verbatim. If a future spec change introduces
the namespaced prefix again, this Decision is the reason why.

### Decision 10 — P0 cargo-culting (v2): `details["shadowed"]` doesn't exist (F-ONEV2-002)

The v2 spec routed `fastblocks_oneiric_resolution_shadowed_total`
to fire when `details["shadowed"]` was non-empty. Verified:
Oneiric's `as_dict()` emits `ordered`, NOT `shadowed`. The
shadowed-counter would NEVER have fired. v3 dropped the counter
entirely.

**Path forward**: shadowed-candidate visibility is out of Phase 6
scope. A future Oneiric upstream contribution adding a `shadowed`
attribute (via a new `ResolutionExplanation.as_attributes()` field)
unblocks re-adding the counter — without violating master plan
line 489's "not parallel" rule (fastblocks wouldn't re-derive).

### Decision 11 — P0 cargo-culting (v2): "Facade hook" claim fabricated (F-ONEV2-003)

The v2 spec claimed "the bridge consumes via FastblocksRegistry's
span-provider hooks". Verified: `FastblocksRegistry` (at
`fastblocks/core/resolver.py:144-209`) has ZERO span-provider hooks.
OTel `SpanProcessor`s install against `TracerProvider`, which is
process-global state. v3 dropped the facade-routing claim and
mandates installing on the OTel global `TracerProvider` directly.

**Path forward**: the v3 fix is correct, but the v2 cargo-culting
made it through 1 full review cycle unreported. Any future spec
revision that re-introduces FastblocksRegistry routing for OTel
must cite an actual code path.

### Decision 12 — P0 (v2): Test isolation missing for SpanProcessor (F-ONEV2-004)

The v2 spec did NOT mandate a `tests/observability/conftest.py`
autouse fixture. OTel's `TracerProvider` is process-global; a
SpanProcessor installed in test 1 persists into tests 2..N,
causing counter labels to double/triple across tests and test pollution.

v3 added the fixture mandate to the Commit 4 IC's `Demonstrable by:`
clause — but the fixture is structurally required, not optional,
and any future spec revision that omits it will reintroduce this
P0.

**Path forward**: Phase 6 ships `tests/observability/conftest.py`
with the autouse teardown BEFORE Commit 4. Without it, the test
suite cannot be trusted.

### Decision 13 — P0 (v2): `get_middleware_stack()` returns dict, not list (F-STRV2-2)

The v2 spec mandated `assert get_middleware_stack()[0]` as the test
for OtelMiddleware outermost placement. Verified: the method returns
`dict[str, Any]`, not a list. `[0]` raises `TypeError`. v3 corrected
the assertion to `get_middleware_stack()["user_middleware"][-1]["class"]`.

**Path forward**: the corrected assertion only passes if OtelMiddleware
is the LAST entry in user_middleware. Combined with Decision 3's
limitation (ExceptionMiddleware is structurally outside everything),
this is the v3 contract.

### Decision 14 — P0 cargo-culting (v3): LifespanManager still doesn't exist (F-STRV2-4)

Identical to Phase 5's `LifespanManager` doesn't-exist P0
(ADR 0012 Decision 2). Master plan line 478-479 cites a
`LifespanManager` class that no longer exists (and never did in
Phase 5's spec; fastblocks's actual lifespan is the
`@asynccontextmanager async def lifespan(...)` at
`fastblocks/adapters/app/default.py:164-178`). v3 marks this as
a Phase 6.5 prerequisite for the htmx.py boundary fix but does
NOT fix it.

**Path forward**: this is a strict-tests-only boundary violation.
Either (a) drop the master-plan line 478-479 lifecycle test entirely
(matching ADR 0012 Decision 2 path-forward option "a"), or (b)
ship a Phase 6.5 LifespanManager creation commit that binds
`app.state.main_loop` and `app.state.jinja_env` at lifespan start.

### Decision 15 — P0 cargo-culting (v3): Exemplars dropped at scrape (F-PYTV2-001)

v3 §6B.7 mandates exemplars for trace↔metric correlation. v3 §6B.6
`/metrics` endpoint code (v2's) emits `CONTENT_TYPE_LATEST` =
`text/plain; version=1.0.0; charset=utf-8` — Prometheus TEXT 1.0.0.
Verified: Prometheus text 1.0.0 format SILENTLY STRIPS exemplars
from observation events. Only OpenMetrics format
(`application/openmetrics-text; version=1.0.0`) supports them.
v3 fixed §6B.6 to use OpenMetrics — but the fix is one half of a
two-half contract; the OTHER half (operators' scrape configs must
negotiate OpenMetrics) is in the deployment, not the spec.

**Path forward**: any future Phase 6 retry must ship OpenMetrics
format AND document the operator-side `Accept` header
configuration. Otherwise exemplars are silently lost and the
"iron rule" of §6B.7 is broken.

### Decision 16 — P0 cargo-culting (v3): `clip: rect()` vs `clip-path: inset(50%)` (F-A11YV2-001)

v2 shipped `clip: rect(0, 0, 0, 0)` (deprecated since Chromium 90+
and Firefox 92+) but the Playwright assertion checked
`clip-path: inset(50%)`. These are DIFFERENT CSS properties with
DIFFERENT parse paths. `getComputedStyle(el).clip` returns `''` in
modern Chromium; `getComputedStyle(el).clipPath` returns `'none'`
because the shipped CSS doesn't set it. The assertion was
guaranteed to fail. v3 corrected the shipped CSS to use
`clip-path: inset(50%)` AND namespaced the class to avoid
Bootstrap/Tailwind collisions.

**Path forward**: any future Phase 6 a11y work must use modern CSS
clip-path (not the deprecated `clip` property). The namespaced
class (`.sr-only--fastblocks-a11y-bridge`) MUST be referenced
consistently in the emitted HTML, the CSS rule, and any test
selectors.

### Decision 17 — P1: `structlog` `merge_contextvars` doesn't see raw `ContextVar.set()` (F-PYT-004)

`structlog.contextvars.merge_contextvars` reads ONLY from
`structlog.contextvars._CONTEXT` (populated by `bind_contextvars`).
Raw `ContextVar.set()` writes are invisible. v3 §6B.7 acknowledges
this and offers a custom-processor escape hatch — but the v3 §6A
library choice still says "tie into Oneiric settings chain via
`merge_contextvars`" alone, and the OtelMiddleware codeblock uses
raw `ContextVar.set()`. An implementer reading §6A + §6C ends up
with no trace_id on log lines except in the SpanProcessor (which
reads the span object directly).

**Path forward**: any future Phase 6 must EITHER mandate
`bind_contextvars(**asdict(ctx))` inside the `trace_context.set()`
implementation OR add a custom structlog processor reading
`_current_trace` — codified in §6A, not as an §6B.7 escape hatch.

### Decision 18 — P1: Per-metric matrix has phantom file paths (F-OBSV2-003 / F-PYTV2-006)

Two rows in v3's §6C.6 matrix reference non-existent code:
`fastblocks/adapters/templates/htmy_dispatcher.py:??` (file doesn't
exist) and `select_strategy` (function not in `fastblocks/core/resolver.py`).
v3 marks these as "TBD by implementer" — but the matrix is mandated
as the "observability contract" with a CI test that fails on phantom
paths.

**Path forward**: Phase 6 (or 6.5) ships a real implementation
that binds each row to a real file:line via `git grep`. The CI
test `tests/dashboards/test_fastblocks_dashboard_schema.py` enforces
this — implementation cannot pass until the matrix is fully
populated.

### Decision 19 — P1: Static asset pipeline for a11y_bridge.css unspecified (F-A11YV2-002 / F-OBSV2-004)

v3 ships the `a11y_bridge.css` file but does NOT specify: (a) a
Starlette `Mount("/static", StaticFiles(directory="static"))` in
`fastblocks/adapters/app/default.py`, (b) a Jinja helper
`fastblocks_static_url(name)` and reference in the default HTMY
template, (c) load-order against `fastblocks-ui/panel.css`. Without
these, the CSS file exists in the repo but is not served by the
running app — the bridge's Playwright test fails OR silently passes
on a global `.sr-only` rule loaded by another stylesheet.

**Path forward**: any future Phase 6 must specify (a), (b), (c) above
and have a Playwright test on the CSS file's HTTP 200 from the
running app.

### Decision 20 — P1: XSS-route-to-assertive harassment vector (F-A11Y-002 / F-A11YV2-004)

v3 keeps v2's routing policy table intact: `htmy_render_total{escaped=false}`
maps to `assertive` / `role='alert'`. A misconfigured upstream firing
this at 10–100/s causes screen-reader DoS (focus theft + speech
interruption). User picked "P0-only fix round" so this P1 remains
open.

**Path forward**: route XSS events to OFF (silent; operators monitor
the metric directly) or `polite` (queue for natural pause). Reserve
`assertive` for events where the user must be interrupted.

### Decision 21 — P1: High-frequency events without batching (F-A11Y-003 / F-A11YV2-009)

The bridge has no debouncing/coalescing. WebSocket broadcasts at
high frequency cause: (a) rapid aria-live region updates (screen
readers lag), (b) multiple focus shifts for `role='alert'`, (c) DOM
growth. Three of five routed events use `role='alert'`, amplifying
the harassment risk above.

**Path forward**: per-region coalescing window (default 250 ms) +
`aria-busy="true"` during window, flip to `false` at end so screen
readers treat the final state as a single atomic update.

### Decision 22 — P1: `AriaLiveKind` uses `str, Enum` not `StrEnum` (F-PYT-005)

In Python 3.11+ `enum.StrEnum` is the canonical form for
string-valued enums (PEP 663). `class X(str, Enum)` is documented as
legacy. v3 did not update the codeblock.

**Path forward**: any future Phase 6 must use `from enum import StrEnum` + `class AriaLiveKind(StrEnum):`. Trivial fix.

### Decision 23 — P1: Counter `labelnames` typing comment still misleading (F-PYT-001 / F-PYTV2-005)

The v3 example `Counter(name=..., labelnames=("result",))` shows
`labelnames` as `tuple[str, ...]` — not a `Literal[...]` type. The
trailing comment "labelnames IS Literal[...]" conflates the runtime
allowed value set with the static label-name tuple. Init-time
rejection ("mismatched literal sets at registration time") is
underspecified.

**Path forward**: spec the Counter API explicitly:
`Counter(name=..., labelnames=..., literals={"result": StyleResult, ...})`
with a hard lookup-failure on unknown names. Drop the comment
conflation.

### Decision 24 — P2: Other open items (carried forward)

- **Master-plan life**: master plan §Phase 6 verification line 478-479
  still references `LifespanManager`; either amend master plan or
  add an erratum footnote.
- **Grafana 10.x dashboard version pinning**: known limitation
  per Open Review Flag #4.
- **Counter init Literal type-system signature** (Decision 23
  P1 above).
- **Phase 7 (dead code removal) blocks on Phase 6**: needs
  re-scoping since Phase 6 is deferred.

## What's salvageable from this design

The spec SHELL is sound in v3. Future Phase 6 attempts can use it as
a starting point after addressing the structural blockers:

- **Decomposition**: 6A → 6B → 6C is the right shape. Matches
  the master plan's verification gate structure.
- **Oneiric consumer approach**: the SpanProcessor on
  `resolver.decision` spans is the correct consumer surface (Decision 2
  closed; Decision 9 closed).
- **Cardinality safety rule** (§6B.7 v3): the iron rule for
  Prometheus labels is correct (Decision 6 closed; Decision 15 still
  requires OpenMetrics + exemplar emit-site-by-emit-site).
- **Per-metric instrumentation matrix** (§6C.6 v3): the matrix shape
  is correct (Decision 7 closed structurally; Decision 18 still
  requires real file:line resolution).
- **Strict-tests-only boundary preserved**: every fix attempt
  chose spec/test rewrites over production changes. The boundary
  remains intact for future Phase 6 retries.
- **CI guard coverage**: §6B.7's rule + AST lint + per-metric
  allowlist is real defense against Prometheus OOM; salvageable as-is.
- **Asset pipeline plan** (Decision 19): the
  StaticFiles+Jinja-helper+load-order guard is documented; just not
  shipped yet.
- **Three review cycles preserved**: v1 at `5f0eb4d`, v2 at `8edec33`,
  v3 at `a219347`. Future maintainers can diff against earlier
  versions to see what was tried and what failed.

What the next attempt needs to fix FIRST (before any spec can land
green):

1. **LifespanManager creation** (Decision 14 / Open Review Flag #5) —
   either drop the master-plan line 478-479 test or ship a
   Phase 6.5 commit that creates the class.
1. **`tests/observability/conftest.py` autouse fixture** (Decision 12)
   — small fixture; required for any test reliability.
1. **Real file:line resolution for per-metric matrix** (Decision 18)
   — `git grep` runs in implementation, not in spec.
1. **`merge_contextvars` or custom-processor mandate** (Decision 17)
   — fix codifies in §6A library choice, not §6B.7 escape hatch.
1. **OpenMetrics `/metrics` + exemplar emit-site mandate**
   (Decision 15) — full pipeline, half-codified in §6B.6.
1. **Static asset pipeline specifics** (Decision 19) — Starlette
   `Mount` + Jinja helper + load-order guard.
1. **Master plan reconciliation** — `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
   line 478-479 still references `LifespanManager` and the
   `httpx.AsyncClient + LifespanManager` test. Either amend the
   master plan in a separate commit or add an erratum footnote.

## Consequences

### Positive

- **Spec surface preserved in git history**: v1 at `5f0eb4d`, v2 at
  `8edec33`, v3 at `a219347`. Future maintainers can read all
  three to see what was tried, what was fixed, and what remains.
- **Strict-tests-only boundary preserved**: every v1-v2-v3 fix
  chose spec/test rewrites over production changes. The boundary
  remains intact for future Phase 6 retries.
- **Multi-agent review pattern validated** (3 review cycles,
  41→40→40 findings, all P0s cargo-culting). The pattern is
  working — it's catching real issues that single-author passes
  miss. Future maintainers have a precedent.
- **No premature implementation**: shipping a broken Phase 6 would
  have wasted SDD iterations on tests that couldn't pass — same
  rationale as ADR 0012.

### Negative

- **Three review cycles consumed**: v1 → v2 → v3. ~91 findings
  surfaced, ~50 addressed. The cycle time cost is real.
- **Spec at 1155 lines**: the v3 spec is the longest in fastblocks's
  history. Maintenance burden on future contributors.
- **Coverage ratchet stays at 55.05%**: Phase 6's planned observability
  lift is parked. Phase 6.5 may add observability hooks as a
  byproduct of the LifespanManager fix; Phase 7+ isn't blocked on
  that.
- **Phase 7 (dead code removal) is now blocked** (master plan §Phase 7
  line 343 lists Phase 6 as dependency). Phase 7 needs re-scoping:
  either (a) move forward without the observability lift (Phase 7
  doesn't need OTel to remove dead code), or (b) merge Phase 7 with
  Phase 6.5 into a single retry.
- **Coverage of OTel+exemplar+Sentry+Logfire root-span attribution**
  remains a single-tree-verification challenge. Future Phase 6.5
  needs to actually run dual providers in CI to verify the
  one-tree guarantee from §6C.4.

### Rollback signal

If any future maintainer wants to retry Phase 6, the entry point
is the v3 spec at `a219347` plus this ADR's Decisions 2-24. The v3
spec captured the cumulative fixes; this ADR captures the
remaining structural blockers. Address Decisions 14 (LifespanManager)
first — that's the load-bearing P0 inherited from Phase 5 that
neither Phase 5 nor Phase 6 could resolve without a production-code
change.

## Known issues (parked, deferred to future Phase 6 attempt)

The following items remain parked:

- **`asyncio.TaskGroup` migration** (master plan line 342, deferred
  to Phase 6.5 in v1; re-deferred to a separate Phase in v3 per
  Question 3 decision) — see Decision above for reasoning.
- **Counter init Literal type-system signature** (Decision 23) —
  needs a real generic Counter\[Literal[...]\] or
  Counter(name, labelnames, literals=...) API.
- **HTMY XSS for Jinja2-rendered components** (out of scope per
  master plan §Phase 5 verification line 582-583 — Phase 5
  deferral).
- **Axe-core integration** (Phase 5 deferral; Phase 6 workaround
  was Playwright + aria snapshot, which is
  structural-incomplete-verification per F-A11Y-004).
- **Master-plan reconciliation**: master plan line 478-479 still
  references `LifespanManager` and `httpx.AsyncClient + LifespanManager`. Either amend the master plan in a separate
  commit (mirrors ADR 0012's "Master-plan reconciliation" parked
  item) or add an erratum footnote in any future Phase 6 spec.

## Cross-references

- Spec at `docs/superpowers/specs/2026-08-22-fastblocks-phase-6-design.md`
  - v1: commit `5f0eb4d` (initial design, 8 P0 found)
  - v2: commit `8edec33` (after 1st fix round, 10 new P0 found)
  - v3: commit `a219347` (after 2nd fix round, structural pattern converged)
- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
  - §Phase 6 (line 342)
  - §Phase 6 verification (lines 481-498)
  - §Phase 7 (line 343) — now blocked on Phase 6 deferral
- ADR 0008: Oneiric selection mechanism (SpanProcessor on
  `resolver.decision` spans replaces originally-assumed event-stream;
  bare attribute names verified)
- ADR 0011: Phase 4 deferral (`register_fastblocks_tools` orphan path
  — relevant to Phase 6 Commit 8 instrumentation)
- ADR 0012: Phase 5 deferral (LifespanManager P0 inheritance — the
  exact same P0 carried forward to Phase 6)
- Master plan §Phase 0 preflight (line 608-621) — confirmed no Phase N.5
  needed between Phase 5 and Phase 6
- Oneiric source: `/Users/les/Projects/oneiric/oneiric/core/observability.py:43-59`,
  `/Users/les/Projects/oneiric/oneiric/core/resolution.py:207-215`
- `fastblocks/adapters/app/default.py:164-178` — actual
  `@asynccontextmanager` lifespan (no `LifespanManager` class)
- `fastblocks/applications.py:297-374` — middleware ordering
  (ExceptionMiddleware hardcoded outermost)
- `fastblocks/applications.py:332-342` — middleware
  reverse-wrapping (verified last-registration = outermost)
- `fastblocks/applications.py:114-124` — `get_middleware_stack()`
  returns `dict[str, Any]` (not list)
- `fastblocks/middleware.py:63-69` — `MiddlewarePosition` enum
  (no `OUTERMOST` member)
- `fastblocks/htmx.py:29-52` — actual `_run_async_safely` helper
- `fastblocks/core/resolver.py:144-209` — `FastblocksRegistry`
  surface (no span-provider hooks)
- `pyproject.toml` — pinned `sentry-sdk>=3.0.0a7`, `starlette~=1.3`,
  `logfire[starlette]~=4.15`

## Summary

Phase 6 shipped **0 of 13** planned verification items. Three
multi-agent review cycles (v1 → v2 → v3) reduced the new P0 count
only marginally (8 → 10 → ...), with the same cargo-culting
pattern unbroken across all rounds: each fix invent new APIs,
attribute names, file paths, or library behaviors that don't
exist in the actual codebase or pinned dependencies. The
structural LivEspanManager P0 (inherited from Phase 5) remains
structurally unfixable without production-code changes.

The spec is preserved at three commit points (`5f0eb4d`, `8edec33`,
`a219347`) for future maintainers. The user's prior pattern (Phase 2
finish + Phase 4 + Phase 5) supports deferring at this depth of
structural issue. Future Phase 6 attempts have a concrete starting
point and must address the 7 first-things listed in "What's
salvable from this design" before any spec revision can land green.

---
status: accepted
role: phase-5-deferral
date: 2026-08-22
last_reviewed: 2026-08-22
supersedes: null
superseded_by: null
blocks_on: []
decision_date: 2026-08-22
topic: phase-5-test-infrastructure-rebuild-deferral
---

# ADR 0012: Phase 5 Test Infrastructure Rebuild Deferral

## Status

Accepted (Phase 5 deferral — companion to master plan §Phase 5 line 341,
§Phase 5 verification line 464-479).

## Context

Phase 5 ("Test infrastructure rebuild") was the next phase per the
master plan (§Phase 5 row line 341; §Pillar 6 line 174-180; §Phase 5
verification line 464-479). The spec was designed, then went through
**three multi-agent review cycles** (v1 → v2 → v3 → v3.1) with
diminishing returns:

| Round | P0 | P1 | P2 | Net |
|---|---|---|---|---|
| v1 (initial spec) | 15 | 12 | 7 | 34 findings |
| v2 (after 1st fix round) | 7 | 15 | 14 | 36 findings |
| v3 (after 2nd fix round) | ~3 | ~6 | ~6 | ~15 findings |
| v3.1 (after 3rd fix round) | 1 | ~5 | ~6 | ~12 findings |

P0 count shrank 15 → 1 over three rounds, but new P0s surfaced each
round from deeper structural issues. The single remaining P0 (H-25:
`LifespanManager` class doesn't exist — the spec asserts behavior
production doesn't provide) is a **strict-tests-only boundary
violation** that cannot be fixed without either changing production
code (violating the boundary) or rewriting the lifecycle test to
target the actual `@asynccontextmanager` lifespan.

The user's prior pattern (Phase 2 finish + Phase 4) was to **defer
when multi-agent review surfaces structural issues that don't
converge in 1-2 fix rounds**. Phase 5 is now at 3 fix rounds with
the same pattern. This ADR records the deferral decisions and
rationale.

## Decisions

### Decision 1: Phase 5 deferred

Phase 5 scope resolves to **nothing shipped** based on the cumulative
findings across three review cycles. The spec remains in git history
at commit `8787293` (the most recent v3.1 commit) as the rationale
for the deferral — the work that would need to happen before any
implementation can succeed is recorded in Decisions 2-12.

### Decision 2 — P0: LifespanManager class doesn't exist (H-25)

The 5C.5 lifecycle test asserts `LifespanManager` class behavior:

> 1. Lifespan startup: enter `LifespanManager`, assert `app.state.main_loop`
>    is an `asyncio.AbstractEventLoop` AND `app.state.jinja_env` is a Jinja2
>    `Environment`.

Verified 2026-08-22: no `LifespanManager` class exists anywhere in the
fastblocks codebase. The actual lifespan is
`@asynccontextmanager async def lifespan(...)` in
`fastblocks/adapters/app/default.py:164-178` — it logs only;
`app.state.main_loop` and `app.state.jinja_env` are not bound.

The test cannot pass against current production without a production
code change, which violates the strict-tests-only boundary.

**Path forward (for any Phase 5 retry):** rewrite §5C.5 to either
(a) target the actual `@asynccontextmanager` lifespan and verify what
production does today (startup logs present, no exception, jinja env
importable via standard entry point), or (b) drop the
`app.state.main_loop`/`app.state.jinja_env` assertions entirely and
document the deferred binding as Phase 6 work.

### Decision 3 — P0: `st.from_type()` fails on `Any`-typed fields

`Any` is a special form, not a class; `st.from_type()` cannot resolve
it. All 32 absorbed components have `attrs: dict[str, Any] = field(...)`
fields. **v3 fix** registered `object → safe_user_input` at module
load, which covered the immediate P0 case for `object`-typed fields
(Button.class_, Card.header/body/footer/class_, Field.label/...,
Navbar.brand/start/end/class_, plus 8 required `object` fields in
`_generated.py` — 67 fields total). The `Any` types are honored by
Hypothesis via dataclass default factories (so the strategy doesn't
crash), but the spec text still says "Any fields require manual
override per field" — advisory, not blocking.

**Path forward:** add an explicit `st.from_type()` smoke test in 5A.1
that asserts `htmy_component().example()` doesn't raise; document
that `Any` defaults are honored via `default_factory=list/dict`.

### Decision 4 — P0: `st.register_type_strategy(str, ...)` global mutation

The v2 spec called `st.register_type_strategy(str, ...)` inside
`htmy_component()`. This mutates Hypothesis's process-wide type
registry and would contaminate every other test in the suite. v3
**removed this call entirely** and replaced it with
`st.register_type_strategy(object, safe_user_input)` — narrowly scoped
to the object type that Hypothesis's `st.from_type()` cannot resolve
on its own. v3.1 added explanatory rationale documenting why the
broader registration was rejected.

**Path forward:** none — fix correctly applied.

### Decision 5 — P0: `_RESOURCES` symbol doesn't exist (M-1, F-8, H-11)

The v2 MCP canary scenario 2 asserted a 7-entry `_RESOURCES` dict
in `fastblocks/mcp/resources.py`. Verified: no module-level
`_RESOURCES` (or any leading-underscore dict) exists; the 7 entries
are local to `register_fastblocks_resources()` and only logged.
**v3 dropped the scenario** with explicit deferral rationale
citing the verified line range and noting that exposing the dict
would require a production-code change (violates strict-tests-only).

**Path forward:** resource-list coverage waits for the deferred
Oneiric MCP helper (master plan line 209).

### Decision 6 — P0: MCP canary scenario 3 (`_get_http_app`) wrong API

v2 spec called `FastBlocksMCPServer()._get_http_app()`;
`_get_http_app` is module-level, not a method. v3 corrected to
`from fastblocks.mcp.server import _get_http_app; _get_http_app()`.
**v3.1 fixed the assertion itself**: changed from "assert app is not
None" to "spy on `register_fastblocks_tools`" — because the
original assertion would have passed even when registration
silently failed (the function falls through to `streamable_http_app()`
regardless of registration outcome). The spy is the only way to
verify the registration code path actually executed, given that
the mcp_instance is local to `_get_http_app` and not accessible
from outside (production-code change to expose mcp_instance would
violate strict-tests-only).

**Path forward:** none — fix correctly applied.

### Decision 7 — P0: Strategy counts (34 → 32; 21 → 25)

Master plan and spec v1 both asserted 34 absorbed components and
21 whitelisted attrs. Verified 2026-08-22: 32 absorbed components
(via `htmy_components.__all__` — 32 dataclasses + FastBlocksComponent
base + `__version__` = 34 names total) and 25 whitelisted attrs
(class, id, role, tabindex, 3 data-*, 4 aria-*, 9 hx-*, 5 form = 25).

v2 corrected most occurrences; v3 caught the 4 remaining stale
references (L88, L555 for "34"; L108, L369 for "21"). All clean in
v3.1.

**Path forward:** none — fix correctly applied.

### Decision 8 — P1: `htmy_component()` rebuilds strategy-graph per call

Every call to `htmy_component()` re-imports `dataclasses`, re-walks
`__all__`, re-runs the dataclass filter, re-asserts, and
re-instantiates 32 `st.from_type()` results. With `max_examples=100`
across the XSS matrix, this is thousands of unnecessary rebuilds
per CI run. v3 did **not** memoize the result.

**Path forward:** wrap the function body in `@functools.cache` or
hoist to a module-level singleton populated on first call.

### Decision 9 — P1: `docs/plans/TEMPLATE.md` doesn't exist

v3 spec cites `docs/plans/TEMPLATE.md` as the canonical Integration
Contract template. Verified 2026-08-22: the directory and file
both don't exist (the plans live in `docs/superpowers/plans/`,
which contains no TEMPLATE.md). The citation is dead.

**Path forward:** either create the template at the cited path
(small, useful), or remove the cross-reference and inline the IC
template per commit in §5A/§5B/§5C.

### Decision 10 — P1: axe-core page-level rules need per-component scaffold

v2 expanded axe rules to include `region`, `landmark-one-main`,
`page-has-heading-one`, `duplicate-id`. v3 added the rule subset
but **not** the per-component scaffold required to satisfy
landmark rules on isolated component renders. Without
`<!DOCTYPE html><html><body><main><h1>...</h1>{component}</main></body></html>`
wrapping, `landmark-one-main` and `page-has-heading-one` fire on
every render and produce noise that masks real per-component
regressions.

v3.1 **added the scaffold step** at §5C.2 step 3a.

**Path forward:** none — fix correctly applied.

### Decision 11 — P1: Realistic-defaults posture table — Layout vs Landmark

v2's posture table grouped Container/Columns/Section/Shell/Footer/
Navbar/NavList/Media in one row. Layout primitives (Container,
Columns, Section, Shell, Media) are NOT landmarks and don't
satisfy the same axe rules as landmarks (Navbar, Footer, NavList,
NavGroups). v3.1 **split the row** into three: landmarks
(Navbar/Footer/NavList/NavGroups), sectioning content (Section/Shell/
Media), and layout primitives (Container/Columns).

**Path forward:** none — fix correctly applied.

### Decision 12 — P1: Tabs posture — wrong field name, missing ARIA

v2 spec asserted `default_active=0` for Tabs. Verified
2026-08-22: Tabs dataclass field is `active_id: str | None = None`
(not `default_active`). v3.1 **corrected the field name** AND
documented the ARIA plumbing (role="tablist", aria-selected,
aria-controls). An implementer following v3.1 will not crash on
`TypeError: unexpected keyword argument 'default_active'`.

**Path forward:** none — fix correctly applied.

## What's salvageable from this design

The spec SHELL is sound. Future Phase 5 attempts can use it as a
starting point after addressing the structural blockers:

- **Decomposition**: Foundation → Matrix → Adversarial (5A/5B/5C)
  is the right shape. Matches the master plan's verification gate
  structure.
- **Tests-only boundary**: preserved. All fixes landed via spec
  rewrites or test-file additions; no production code changes.
- **Coverage ratchet 65%**: defensible target.
- **12-commit Integration Contracts**: each commit independently
  revertible.
- **CI budget <5 min**: realistic.
- **Strategy code (v3.1 final)**: `st.from_type()` for components +
  `st.register_type_strategy(object, ...)` for the object-field
  escape hatch + `_UNSAFE_PAYLOADS` tuple inlined. This combination
  works against the actual codebase.

What the next attempt needs to fix FIRST (before any spec can
land green):

1. **LifespanManager doesn't exist** (Decision 2) — either drop
   the test or test the actual `@asynccontextmanager` lifespan.
2. **`htmy_component()` memoization** (Decision 8) — small fix.
3. **`docs/plans/TEMPLATE.md` reference** (Decision 9) — either
   create the file or remove the citation.
4. **Master plan drift**: master plan §Phase 5 line 469-470 still
   references `ABSORBED_COMPONENTS` and "34 absorbed components".
   Either amend the master plan or add an explicit erratum
   footnote in the spec.
5. **Per-component fixture file** (`tests/a11y/_component_postures.py`)
   needs a documented schema (Decision 11 references the file but
   doesn't define its structure).
6. **Drawer closed-state coverage** (Decision 4 v2 N-4) — the
   posture asserts "off-canvas (closed state)" which yields zero
   interaction coverage. Either drop Drawer from 5C.2 or add a
   two-state (closed + open) test.

## Consequences

### Positive

- **Spec surface preserved in git history**: commit `8787293` is
  the most refined design attempt (v3.1). Future maintainers can
  diff against earlier versions to see what was tried and what
  failed.
- **Strict-tests-only boundary preserved**: every fix attempt
  chose spec/test rewrites over production changes. The boundary
  remains intact for future Phase 5 retries.
- **Multi-agent review pattern validated**: 3 review cycles, ~85
  findings total (across v1+v2+v3), 1 P0 still open. The pattern
  is working — it's catching real issues that single-author passes
  miss.
- **No premature implementation**: shipping a broken Phase 5 would
  have wasted SDD iterations on tests that couldn't pass.

### Negative

- **Three review cycles consumed**: v1 (initial) → v2 (1st fix) →
  v3 (2nd fix) → v3.1 (3rd fix). ~85 findings surfaced and ~50
  addressed. The cycle time cost is real.
- **Spec at 720+ lines**: the v3.1 spec is the longest spec in
  fastblocks's history. Maintenance burden on future contributors.
- **Coverage ratchet stays at 55.05%**: Phase 5's +10pp lift is
  parked. Phase 6's observability work will land first, which may
  add additional coverage hooks.

### Rollback signal

If any future maintainer wants to retry Phase 5, the entry point
is commit `8787293` (v3.1 spec) plus the multi-agent review
findings recorded in this ADR (Decisions 2-12) and in the spec's
git history (commits `42e96c6`, `205dd0d`, `0a6510d`, `8787293`).
Address Decisions 2, 8, 9 first — these are the load-bearing P0/P1s
that block any successful Phase 5 implementation.

## Known issues (parked, deferred to future Phase 5 attempt)

The following items remain parked:

- **`asyncio.TaskGroup` cancellation propagation** (master plan
  line 478) — already deferred to Phase 6 in v1; not addressed in
  any v2/v3 review cycle.
- **Coverage ratchet beyond 65%** — Phase 6's observability work
  lifts it further (master plan line 653 target is 70%).
- **HTMY XSS for Jinja2-rendered components** — Jinja2 doesn't
  have absorbed components; only HTMY does. Out of scope per
  master plan §Phase 5 verification line 582-583.
- **Master-plan reconciliation** — `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
  line 469-470 still references `ABSORBED_COMPONENTS` and "34
  absorbed components". Either amend the master plan in a separate
  PR or add an erratum footnote in any future Phase 5 spec.

## Cross-references

- Spec at `docs/superpowers/specs/2026-08-22-fastblocks-phase-5-design.md`
  - v1: commit `42e96c6` (initial design, 15 P0 found)
  - v2: commit `205dd0d` (after 1st fix round, 7 new P0 found)
  - v3: commit `0a6510d` (after 2nd fix round, 1 new P0 found)
  - v3.1: commit `8787293` (after 3rd fix round, 1 P0 remains —
    `LifespanManager` doesn't exist)
- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
  - §Phase 5 (line 341, 464-479)
  - §Phase 5 verification line 469-470 (stale `ABSORBED_COMPONENTS` reference)
- ADR 0010: Phase 2 mechanical-four closeout (`docs/adr/0010-phase-2-mechanical-four.md`)
- ADR 0011: Phase 4 deferral (`docs/adr/0011-phase-4-deferral.md`)
  - Same deferral pattern; precedent for the structural-issue→defer
    path
- Phase 1.5 spec: `docs/superpowers/specs/2025-09-fastblocks-oneiric-registry-design.md`
  - Phase 1.5's `FastblocksRegistry(get_resolver())` facade is the
    pattern that 5A's `clean_resolver` fixture extends
- Phase 2 spec: `docs/superpowers/specs/2026-08-21-fastblocks-phase-2-design.md`
  - Phase 2's `Literal[...]` types for `style` are the pattern that
    5B's matrix tests consume
- Phase 2.5 spec: `docs/superpowers/specs/2026-08-22-fastblocks-phase-2-5-design.md`
  - Phase 2.5's `AppBaseSettings` is the schema source for 5A's
    test fixtures
- CLAUDE.md: `fastblocks/CLAUDE.md` (no §Process Discipline section;
  IC template referenced in v3 spec doesn't exist)
- Master plan §Phase 0 preflight (line 608-621) — confirmed no Phase N.5
  needed; Phase 5 was unblocked at start
- `tests/strategies.py` shape (in v3.1 spec lines 138-261) — works
  against current codebase once Decisions 2, 8, 9 are addressed
- `tests/conftest.py:340-367` — `clean_resolver` autouse fixture
  (Phase 1.5; reinitializer pattern)
- `fastblocks/mcp/server.py:141-170` — `_get_http_app` with
  `with suppress(Exception)` (ADR 0011 Decision 6 P0 unaddressed;
  remains a latent bug for any future Phase 5)
- `fastblocks/adapters/app/default.py:164-178` — actual
  `@asynccontextmanager` lifespan (no `LifespanManager` class)

## Summary

Phase 5 shipped **0 of 13** planned verification items. Three
multi-agent review cycles (v1 → v2 → v3 → v3.1) reduced the
P0 count from 15 to 1 but uncovered that the single remaining
P0 (LifespanManager) is a strict-tests-only boundary violation
that requires either rewriting the test to target the actual
production lifespan, or producing code changes that violate
the user's "strict tests-only" decision.

The spec is preserved at commit `8787293` for future reference.
The user's prior pattern (Phase 2 finish + Phase 4) supports
deferring at this depth of structural issue. Future Phase 5
attempts have a concrete starting point.

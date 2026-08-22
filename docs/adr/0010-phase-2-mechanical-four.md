---
status: accepted
role: phase-2-closeout
date: 2026-08-21
last_reviewed: 2026-08-21
superseded_by: null
blocks_on: []
decision_date: 2026-08-21
topic: phase-2-type-safe-configuration-mechanical-four-closeout
---

# ADR 0010: Phase 2 Mechanical-Four Closeout

## Status

Accepted (Phase 2 — type-safe configuration closeout).

## Context

The master plan (§Phase 2 line 303-313) lists six sub-tasks for Phase 2.
The Phase 2 design spec (`docs/superpowers/specs/2026-08-21-fastblocks-phase-2-design.md`)
narrows scope to **mechanical four**: Literal types for `style` + CLI↔settings
sync test + Oneiric `explain()`-based error contract + Protocol-based
adapter contracts. The remaining two items (renderer match-statement
dispatch, `SafeHTMLStr` propagation) are out of scope: renderer dispatch
is deferred to Phase 4/6; `SafeHTMLStr` was completed in Phase 1B
(master plan §Phase 1B results line 423).

This ADR records the architectural decisions Phase 2 commits and is the
canonical reference for the deferred items.

## Decisions

### Decision 1: Single source of truth at `fastblocks/core/validators.py`

`StyleName = Literal["vanilla", "fastblocks_ui"]` is defined ONCE in
`fastblocks.core.validators`. Every consumer (`AppBaseSettings`,
`cli.py`, future Phase 6 Prometheus labels) imports `StyleName` from
this module. Adding a new style value means editing one Literal; the
sync test (`tests/core/test_validators_sync.py`) enforces that every
consumer follows.

This implements ADR 0008 Rule 3 ("Shared Literal sets" home designation).

### Decision 2: `@runtime_checkable` on both Protocols

`StyleAdapter` and `TemplateAdapter` both carry `@runtime_checkable`.
Required for `isinstance()` on method-only Protocols (Python 3.13; no
relaxation in PEP 544 for method-only Protocols).

### Decision 3: Protocol method naming — `register_style_functions`, NOT `register_<name>_functions`

The pre-Phase-2 convention in `style_registry.py:42` is
`register_style_functions(env, style_name)` — a single function name,
not per-style. Phase 2 pins this. The per-style-naming convention
(`register_vanilla_functions`, `register_fastblocks_ui_functions`) is
**broken**; concrete adapters must implement `register_style_functions`.

### Decision 4: `register_style_candidate` returns `None`

The wrapper preserves `register_candidate_strict`'s contract
(`None` on success, `CandidateValidationError` on failure). The only
new exception is `TypeError` for Protocol-missing methods.

### Decision 5: `format_resolution_explanation_one_line()` helper

`FastblocksRegistry.explain()` returns `ResolutionExplanation`, NOT a
string. The formatter helper produces the operator-facing single-line
string. Names the formatter explicitly so implementers don't reinvent
it.

### Decision 6: `suppress(Exception)` ratchet at empirical baseline (122 sites)

Phase 2 locks the empirically measured baseline of **122**
`suppress(Exception)` sites in `fastblocks/`. The ratchet test
(`tests/core/test_suppress_exception_ratchet.py`) runs `git grep` via
`subprocess` and asserts count ≤ 122. No new sites added, no sites
deleted. Future Phase 7 (final dead-code pass) may lower the count;
the test passes on a lower count. Master plan line 313 records 123
but the empirical count (verified via
`git grep -c 'suppress(Exception)' -- fastblocks/` on 2026-08-21) is
122. The ratchet locks the empirical number; the master plan
reference is documented as off-by-one for future amendment.

### Decision 7: `app.yml` → `AppBaseSettings` wiring deferred to Phase 2.5

Production code (`fastblocks/adapters/app/default.py:182`) calls
`AppSettings()` with no arguments; defaults are used directly.
`OneiricSettings` is a `pydantic.BaseModel` subclass, NOT a
`pydantic_settings.BaseSettings` subclass — it does not auto-read
`app.yml`. The Literal type is therefore **defensive documentation**
until the wiring lands in a follow-up Phase 2.5.

### Decision 8: `get_close_matches` cutoff at 0.6

Standard library default. Catches typos like `'vanila'` → `'vanilla'`,
`'fastblock_ui'` → `'fastblocks_ui'`. Misses unrelated strings (`kelp`,
`bulma`); the legal-set message still surfaces even without a hint.

## Deferred Items

| Item | Reason | Lands in |
|---|---|---|
| Renderer match-statement dispatch | Requires renderer axis on `AppBaseSettings`; forces Phase 4 + 6 to take a position early | Phase 4 / 6 |
| `try/except Exception:` migration in `core/style_registry.py:66` | Framework-boundary; out of Phase 2 scope | Phase 7 |
| `register_template_candidate` decorator | No consumer site; Protocol still defined for Phase 6 lint anchor | When first renderer adopts the contract |
| `app.yml` → `AppBaseSettings` wiring | Production code uses defaults; wiring is a separate task | Phase 2.5 |

## Consequences

### Positive

- **Single source of truth for legal values.** With the
  `StyleName` Literal in `core/validators.py` and the sync test,
  every consumer (CLI, `AppBaseSettings`, future Prometheus labels)
  reads from the same Literal set. Adding a new style means
  editing one place; drift is caught by CI.
- **Protocol-based adapter contracts replace ad-hoc checks.**
  Concrete adapters now declare `register_style_functions` /
  `register_template_candidate` on a runtime-checkable Protocol;
  `register_style_candidate` raises `TypeError` on Protocol
  violations at the wrapper boundary, before any Oneiric
  resolution runs.
- **Operator-facing `explain()` output is canonical.** The
  `format_resolution_explanation_one_line()` helper centralizes
  the single-line rendering so CLI users and logs see the same
  string; future surfaces (Grafana, error pages) read from the
  same source.
- **`suppress(Exception)` ratchet prevents silent regressions.**
  The empirical baseline (122 sites) is locked in CI; future
  commits cannot add new sites without an explicit ADR amendment.

### Negative

- **Literal-type ergonomics are caller-bound.** Typer's `Literal`
  support is best-effort (the help text shows the choices, but
  Pydantic runtime validation catches the rest). Adding a new
  style still requires editing the Literal at the home module,
  the CLI, and any validator — the sync test enforces this.
- **Protocol runtime checks have an import cost.**
  `@runtime_checkable` on every Protocol walks the full attribute
  list on each `isinstance()`. For the fastblocks surface area
  (two Protocols) the overhead is negligible, but a future
  contributor adding many more Protocols should revisit whether
  static-only Protocols would suffice.
- **Ratchet baseline is one-shot and empirical.** The 122 baseline
  is whatever `git grep` returns today; if a future contributor
  removes one site, the test still passes (it asserts `≤` not
  `==`). There is no "must restore" enforcement — only a
  "must not add" one.

### Rollback signal

If any Decision 1-5 proves unworkable in practice — e.g. the
Literal home drifts back into per-adapter modules, or the
Protocol runtime check overhead shows up in profiling — a new
ADR must be filed amending or superseding this one with concrete
counterexamples before the decision is relaxed. The
`suppress(Exception)` ratchet (Decision 6) is the most likely
target for revision; if Phase 7 wants to lower the baseline
permanently, the new number goes into
`MASTER_PLAN_BASELINE` in `tests/core/test_suppress_exception_ratchet.py`
and this ADR is amended to match.

## Cross-references

- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md` §Phase 2 (line 303-313)
- Phase 2 spec: `docs/superpowers/specs/2026-08-21-fastblocks-phase-2-design.md`
- Phase 2 plan: `docs/superpowers/plans/2026-08-21-fastblocks-phase-2.md`
- ADR 0008 Rule3: `docs/adr/0008-oneiric-selection-mechanism-ownership.md`
- Phase 1.5x Card 1: `register_candidate_strict` foundation (commit `8564fc1`)
- Phase 1.5x Card 6: `emit_startup_log` (commit `a622055`) — Scenario 3 inheritance
- Phase 1.5x Card 8: facade identity-check warning (commit `e1d8f30`) — `_fresh_registry` lift pattern
- Phase 1.5x Card 9: ADR 0008 Rule3 documentation (commit `ca4a520`) — `core/validators.py` home designation

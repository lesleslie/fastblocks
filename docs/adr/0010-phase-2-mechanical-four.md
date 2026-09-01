______________________________________________________________________

## status: accepted role: phase-2-closeout date: 2026-08-21 last_reviewed: 2026-08-22 superseded_by: null blocks_on: [] decision_date: 2026-08-22 topic: phase-2-type-safe-configuration-mechanical-four-closeout

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
122\. The ratchet locks the empirical number; the master plan
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
| Renderer match-statement dispatch | See Decision 9 — multi-agent review on 2026-08-22 found no production consumer for `app.renderer`; deferred until consumer exists | Phase 4 / 6 (when first real renderer-axis consumer is built) |
| `try/except Exception:` migration in `core/style_registry.py:66` | Framework-boundary; out of Phase 2 scope | Phase 7 |
| `register_template_candidate` decorator | No consumer site; Protocol still defined for Phase 6 lint anchor | When first renderer adopts the contract |
| `app.yml` → `AppBaseSettings` wiring | Production code uses defaults; wiring is a separate task | Phase 2.5 |
| `SafeHTMLStr = NewType("SafeHTMLStr", str)` propagation | See Decision 10 — multi-agent review found (a) type/runtime contract inversion in `tests/xss/test_component_xss.py:115-133` (test pins **escape**, design claimed no-escape), (b) duplicates `htmy.SafeStr` already in use, (c) breaks `tests/xss/test_component_xss.py:156-171` nested-rendering test if applied to `Container.content` | Future phase; if ever shipped, alias `SafeHTMLStr = htmy.SafeStr` |

## Phase 2 Finish Review (2026-08-22)

A multi-agent design review on 2026-08-22 (architecture-council, python-pro,
web-components-specialist, css-architect, htmx-specialist, htmy-specialist,
accessibility-auditor — 7 reviewers) examined the proposed Phase 2 finish
scope: match-statement dispatch on style + renderer axes, plus `SafeHTMLStr`
propagation. The review surfaced load-bearing issues that changed the
original scoping decisions. This section records the additional decisions.

### Decision 9: Renderer match-statement dispatch deferred (renderer axis dropped)

The proposed `RendererName = Literal["jinja2", "htmy"]` field on
`AppBaseSettings` and a `register_renderer_functions(env, renderer_name)`
match dispatcher were dropped from Phase 2 finish scope. Two findings:

1. **No production consumer.** `grep -rn '\.renderer\b' fastblocks/ --include='*.py'`
   returned no consumer reading `app.renderer`. The Jinja2 entry point
   `AsyncJinja2Templates.__init__` (jinja2.py:910 `init_envs`) is selected
   by import resolution and a settings-key lookup, not by an
   `AppBaseSettings.renderer` field. The HTMY entry point
   (`AdvancedHTMYComponentRegistry.render_component_with_lifecycle`,
   htmy.py:781-827) doesn't expose an "Environment" abstraction matching
   the proposed `TemplateAdapter.init_envs() -> t.Any` signature.

1. **HTMY bypasses the style adapter entirely.** `htmy_components/adapter.py:194-207`
   `inline_css()` is hardcoded to `Path(fastblocks_ui.get_css_path()).read_text(...)`,
   ignoring `style_name`. A `style="vanilla"` + `renderer="htmy"` config
   would still bundle fastblocks-ui CSS via the HTMY renderer — the
   "two-axis rendering architecture" intent is structurally violated by
   the live code.

Adding the renderer Literal without a consumer creates a layer that
fires Pydantic validation but is unreachable from production code. The
match-statement on the renderer axis is therefore meaningless without
preceding work: (a) add a real consumer (lifespan startup hook reading
`app.renderer` and selecting between Jinja2 / HTMY entry points), then
(b) close the HTMY inline_css bypass, then (c) add the Literal +
match.

### Decision 10: SafeHTMLStr propagation deferred

The proposed `SafeHTMLStr = NewType("SafeHTMLStr", str)` trust-boundary
type and `mark_safe(s)` helper were deferred. Three findings made the
ship path untenable:

1. **Contract inversion.** `tests/xss/test_component_xss.py:115-133`
   pins the *actual* escape behavior: `Container(content='<div>safe</div>')`
   MUST render as `&lt;div&amp;gt;safe&lt;/div&amp;gt;`. The design's
   claim that "Container.content is pre-rendered HTML, no escape" was
   factually backwards — the test docstring itself states "the spec
   §C4 pin for 'pre-rendered HTML, no escape' was aspirational; the
   implementation escapes." Shipping `SafeHTMLStr` as a "no-escape"
   marker would create a type/runtime mismatch: type says do-not-escape,
   runtime escapes anyway. The information asymmetry (junior dev who
   skips `mark_safe` still gets safe behavior via runtime escape) makes
   the type a misleading affordance.

1. **Duplicate type.** `htmy_components/base.py:5` already imports
   `from htmy import SafeStr` and `FastBlocksComponent.htmy(context)`
   returns `SafeStr(self._markup(context))`. Adding `SafeHTMLStr`
   alongside creates two incompatible types for one concept; every
   cross-boundary call (`Container(content=...)` accepting a `SafeStr`
   from a nested component) requires a coercion that the new type
   breaks.

1. **Nested-component test broken.** `tests/xss/test_component_xss.py:156-171`
   (`test_nested_rendering_each_layer_escapes`) constructs
   `Container(content=Column(content=Field(label=PAYLOAD).htmy({})).htmy({}))`.
   `Field(...).htmy({})` returns `SafeStr`, not `str`. Narrowing
   `Container.content` from `object = None` to `SafeHTMLStr` would
   typecheck-fail that test, which is the very test the design
   claimed to preserve.

The trust-boundary primitive (escape-at-runtime vs assertion-at-type)
remains valid future work. If/when shipped, the right shape is to
**alias** `SafeHTMLStr = htmy.SafeStr` (not parallel) and ship a
runtime helper that aligns with the actual escape contract — not a
"do not escape" marker.

### Decision 11: Match dispatch deferred (style axis too, not just renderer)

Decision 9 dropped the renderer axis. Decision 10 deferred SafeHTMLStr.
The match-statement dispatch on the **style axis** was originally
proposed as part of the same finish, but two findings changed the
prior calculus:

1. **`vanilla.py` already exists.** The design proposed adding a new
   `fastblocks/adapters/style/vanilla.py` as a no-op `StyleAdapter`.
   The file already exists: 242 lines, defines `VanillaStyle(StyleBase)`
   with `COMPONENT_CLASSES`, `get_stylesheet_links()`, `get_component_class()`,
   `build_component_html()`, plus two Oneiric registrations
   (`key="vanilla"` line 92, `key="styles"` line 234). Overwriting it
   would destroy the CSS-class mapping and resolver registrations.

1. **Protocol method-name mismatch (real bug in mechanical-four).**
   `validators.py:60` declares `StyleAdapter.register_style_functions(env)`
   as the Protocol method (single-name). The live runtime dispatcher
   at `style_registry.py:60` calls `getattr(module, f"register_{style_name}_functions", None)`
   (per-style-named). The existing `fastblocks_ui.py:140` implements
   `register_fastblocks_ui_functions(env)` but NOT `register_style_functions(env)`.
   Under the Phase 2 mechanical-four `register_style_candidate` Protocol
   gate (`oneiric_helper.py:173`), `isinstance(fastblocks_ui, StyleAdapter)`
   returns False (missing method per `_protocol_missing_methods`), and
   `register_style_candidate("fastblocks_ui", fastblocks_ui)` raises
   `TypeError` naming `register_style_functions` as missing. The
   existing fastblocks_ui module fails the gate.

The match-statement dispatch is therefore blocked until the Protocol
contract is reconciled with the live per-style naming convention. The
right fix (per CSS-architect finding) is to add module-level aliases
in `fastblocks_ui.py` and `vanilla.py`:
`register_style_functions = register_fastblocks_ui_functions`. That
work is out of scope for the Phase 2 finish and lands as a separate
bug fix amending Decision 3.

### Decision 12: Phase 2 finish scope = empty

The original directive ("finish Phase 2 — match-statement dispatch and
`SafeHTMLStr` propagation") resolves to **no code shipped** based on
Decisions 9-11. The work that remains in Phase 2 finish is:

- Documentation only — the multi-agent review's findings are recorded
  in this ADR.
- Stale-note fix in master plan line 54 — the "Phase 3.1" reference
  is corrected to "Phase 1B (absorption) and Phase 1.5 (registry
  consolidation)."
- Known-issue annotation: Decision 3's Protocol method-name claim
  (`register_style_functions` is the Protocol method) is contradicted
  by the live `register_{style_name}_functions` pattern; the gate
  fails on the existing `fastblocks_ui.py` module. A bug-fix commit
  is required to align the Protocol with the runtime dispatcher
  before match dispatch can be safely added.

### Known issue: Protocol method-name mismatch requires amendment to Decision 3

Decision 3 stated: "the per-style-naming convention
(`register_vanilla_functions`, `register_fastblocks_ui_functions`) is
**broken**; concrete adapters must implement `register_style_functions`."
The 2026-08-22 review found the opposite is true: the live code uses
per-style naming, the Protocol demands single-name, and the existing
production modules implement per-style. Decision 3's claim was made
during the mechanical-four design before the live `fastblocks_ui.py`
was read. A bug-fix ADR is required to reconcile this; until then,
the mechanical-four `register_style_candidate` gate would reject
the existing `fastblocks_ui.py` module on day-one of the merge.

The likely amendment: Decision 3 stays in spirit (Protocol gates
should be enforceable) but reverses the polarity — add module-level
aliases in the production adapters so both naming conventions are
satisfiable, and the runtime dispatcher keeps using per-style while
the gate uses the alias.

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

______________________________________________________________________

## status: accepted role: canonical date: 2026-08-21 last_reviewed: 2026-08-21 superseded_by: null blocks_on: [] decision_date: 2026-08-21 topic: oneiric-selection-ownership

# ADR 0008: Oneiric Selection Mechanism Ownership

## Status

**Accepted** (Phase 1.5.7 — first canonical fastblocks ADR).

## Context

Fastblocks migrated from ACB to Oneiric 0.16+ for adapter
resolution (ADR-equivalent posture inherited from the upstream
Bodai decision recorded in
`/Users/les/Projects/mahavishnu/docs/adr/001-use-oneiric.md`).
Phase 1.5 consolidated 77 fragmented `Resolver()` instances
onto a single shared registry via `FastblocksRegistry`
(`fastblocks/core/resolver.py`). The mechanical consolidation
answered *how* registrations land in one place; this ADR answers
*which layer owns which part of the resolution contract*.

Two ownership questions surfaced during the Phase 1.5 review:

1. **Upstream vs wrapper.** When a fastblocks-specific need
   appears at the registry seam (e.g. narrow `register_candidate`
   exception handling in `oneiric_helper.py`), should the
   helper push the change upstream into Oneiric or keep it
   fastblocks-local?

1. **Selection mechanism.** Oneiric's `Candidate` carries
   `priority`, `stack_level`, and `provider` fields that score
   candidates during `resolve()`. Should fastblocks ever set
   these fields explicitly, or are they always inherited from
   upstream defaults?

Without explicit answers to both, future contributors face an
ambiguous decision boundary: is a fastblocks-specific `register`
helper a fastblocks feature or an upstream contribution? Is a
candidate priority override a fastblocks policy or upstream
policy?

### The "absorb or wrap" rule (ONEIRIC-10)

A pre-Phase-1.5 specialization review (`oneiric-specialist`
audit, finding ONEIRIC-10) recorded the principle:

> Anything another Bodai component would also want goes upstream
> (Oneiric itself); anything fastblocks-specific stays local.

Mahavishnu, Akosha, Dhara, Session-Buddy, Crackerjack, and Oneiric
itself all consume the Oneiric resolver surface. Anything in
that surface that benefits those consumers belongs upstream.
Anything that benefits fastblocks specifically (e.g.
`oneiric_helper.register_candidate`'s narrow
`(ValidationError, ValueError, TypeError)` catch with `bool`
return — a fastblocks ergonomic preference) stays local and is
documented as such.

### The selection-mechanism rule (Phase 1.5.7)

Oneiric's selection mechanism (`priority`, `stack_level`,
`provider`) is upstream policy. It answers the question
"given N candidates registered for the same (domain, key),
which one serves a request?" Oneiric owns that question
because the answer must be consistent across all consumers
of the registry — Mahavishnu's pool routing, Akosha's pattern
queries, and Dhara's adapter distribution all rely on the
same selection semantics.

Fastblocks's responsibility is upstream of selection: it
defines the *legal values* that selection may choose between.
Phase 2's `Literal[...]` types on `AppBaseSettings.style`,
`AppBaseSettings.renderer`, and the CLI `--style` enum are
the fastblocks layer that says "these are the only style
names the application will ask for." Oneiric's selection
then picks which registered candidate serves each legal
value.

This separation matters because:

- **Selection policy is cross-cutting.** Changing how
  `priority` scoring works affects every Bodai component.
  Fastblocks is not the place to make that change.
- **Legal-value validation is fastblocks-local.** Whether
  `style="kelp"` is acceptable depends on which style
  adapters fastblocks ships with; that question is meaningless
  to Oneiric, which doesn't know what a "style" is.
- **Blurring the boundary leaks abstraction.** A fastblocks
  contributor who sets `priority=999` on their candidate is
  implicitly overriding upstream selection policy for ALL
  consumers, not just fastblocks. That hidden coupling
  surfaces as "why did Mahavishnu route to the fastblocks
  candidate" debugging sessions.

## Decision

**Rule 1 — Absorb or wrap.** Anything added to the
fastblocks→Oneiric seam is evaluated against ONEIRIC-10:

- If another Bodai consumer would want it, contribute
  upstream to Oneiric.
- If fastblocks-only, keep it local with a docstring
  explaining the fastblocks-specific rationale.

The bar for "absorb upstream" is "Mahavishnu OR Akosha OR
Dhara would consume this." "Mahavishnu-and-Mahavishnu-only"
is not sufficient.

**Rule 2 — Selection mechanism ownership.** Fastblocks code
MUST NOT set the `priority`, `stack_level`, or `provider`
fields of `Candidate` instances directly. These fields are
the upstream layer's selection policy and stay at their
upstream defaults (`priority=0`, `stack_level=None`,
`provider=None`, `source=CandidateSource.LOCAL_PKG` for
fastblocks-side registrations).

The fastblocks layer may use `register_candidate(...)` /
`Candidate(..., source=CandidateSource.LOCAL_PKG, ...)` with
the source marker (which is provenance metadata, not
selection policy). It must not touch the three selection
fields.

The fastblocks layer may use `explain()`, `list_active()`,
`list_shadowed()` to OBSERVE selection results — these are
the observability hooks Phase 6 builds on.

**Rule 3 — Legal values are fastblocks's job.** `Literal[...]`
types in `AppBaseSettings`, CLI enums, and any other
"which values may a user pass" validation are fastblocks's
responsibility. The fastblocks Literal set is the contract
between the user-facing surface and Oneiric's selection.

**Validator homes (Rule 3 implementation).** Per
`fastblocks/.claude/decisions/wire-up-contract.md`, every
Literal-driven validation lives in a single, discoverable
module per boundary rather than scattered across the codebase:

| Validation kind | Home |
|-----------------------------|----------------------------------------------------------|
| CLI `Literal[...]` choices | `fastblocks/cli.py` (inline — Typer kwargs) |
| `AppBaseSettings` fields | `fastblocks/applications.py` (the SettingsPydantic model)|
| Shared Literal sets | `fastblocks/core/validators.py` (NEW — Phase 2 home) |
| Per-adapter schema/validators | alongside the adapter, e.g. `fastblocks/adapters/styles/_base.py` |

The new `fastblocks/core/validators.py` is the home for any
Literal set consumed by both `AppBaseSettings` and the CLI, or
referenced from multiple adapters. It exists so a Literal type
like `Literal["html", "xhtml", "text"]` does not drift between
the CLI's parser and the Settings class's runtime check.
Adapters that need their own Literal may import from there
rather than redefining the type.

Rule 3 holds regardless of where the validator lives: the
Literal set remains fastblocks's contract and must not be
relaxed without an ADR amendment.

## Consequences

### Positive

- **Clear contributor mental model.** "Should this be in
  Oneiric or fastblocks?" has a one-question litmus test
  (Rule 1). "Should I set `priority` on my Candidate?"
  has a one-line answer (Rule 2: no).
- **Selection-policy coupling is explicit.** Cross-cutting
  changes to Oneiric's selection mechanism surface in
  Oneiric's release notes, not as silent behavior changes
  inside fastblocks.
- **Legal-value validation stays close to the surface.** A
  CLI mistake (`--style kelp` when `kelp` isn't shipped) is
  caught at the Literal-type boundary with a clear error,
  not as a confusing "no candidate served" from Oneiric.

### Negative

- **One-off overrides aren't expressible.** If fastblocks ever
  needs to prefer a specific candidate (e.g. "in production,
  prefer the production-grade htmy renderer"), it cannot
  express that preference via `priority`. The workaround
  is to expose a Literal value that selects the candidate
  via registration ordering (the first registered candidate
  wins under default selection); if that proves insufficient,
  Rule 2 must be revisited via a new ADR.
- **Decision-rule overhead.** Every new entry point in
  `oneiric_helper.py` / `core/resolver.py` requires the
  author to apply Rule 1. The bar is low but non-zero.

### Rollback signal

If Rule 2 proves too restrictive in practice (e.g. fastblocks
realizes it needs `priority` to disambiguate same-domain
registrations), this ADR is the rollback target. A new ADR
amending or superseding it must be filed with concrete
counterexamples before Rule 2 is relaxed.

## Verification

- `git grep -nE "Candidate\s*\(.*priority|Candidate\s*\(.*stack_level|Candidate\s*\(.*provider" fastblocks/ tests/`
  returns zero hits — no fastblocks code constructs a
  `Candidate` with explicit selection fields.
- `git grep -nE "register_candidate.*priority|register_candidate.*stack_level|register_candidate.*provider" fastblocks/ tests/`
  returns zero hits — no fastblocks code passes selection
  fields to `register_candidate`.
- `oneiric_helper.register_candidate(...)`'s signature does
  not expose `priority`/`stack_level`/`provider` as
  parameters — the upstream selection fields are not part
  of the fastblocks helper's API surface.

Both grep commands were verified to return zero hits against
`main` at `e674fb7` (Phase 1.5.6). Note that a broader
`git grep "priority="` returns many hits — those are
`EventPriority`, sitemap XML `<priority>` element, and
syntax-support filter ordering, none of which are Oneiric
selection fields. The targeted greps above are the
correct verification.

## Cross-references

- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
  Phase 1.5 deliverable 7 (line 299) and the "absorb or wrap"
  decision rule (line 107).
- Phase 1.5.0 (`FastblocksRegistry` facade): `fastblocks/core/resolver.py`.
- Phase 1.5.2 (singleton ownership boundary): same file.
- Phase 1.5.6 (narrow `suppress(Exception)` in `mcp/registry.py`):
  `fastblocks/mcp/registry.py`.
- Upstream ADR pattern: `/Users/les/Projects/mahavishnu/docs/adr/001-use-oneiric.md`.

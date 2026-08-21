# Architecture Decision Records

This directory contains the Architecture Decision Records (ADRs)
for the `fastblocks` web framework.

## Format

Each ADR is a self-contained Markdown file named
`NNNN-kebab-case-slug.md` with YAML frontmatter:

```yaml
---
status: accepted | superseded | proposed
role: canonical | supporting
date: YYYY-MM-DD              # date the ADR was filed
last_reviewed: YYYY-MM-DD     # date last substantively reviewed
superseded_by: NNNN | null     # ADR that replaces this one, if any
blocks_on: []                  # ADRs that must be accepted first
decision_date: YYYY-MM-DD     # date the decision was made
topic: short-tag              # for cross-referencing
---
```

Body uses standard MADR sections: Status, Context, Decision,
Consequences, Verification, Cross-references.

## Index

| Number | Title | Status | Date |
|---|---|---|---|
| [0008](0008-oneiric-selection-mechanism-ownership.md) | Oneiric Selection Mechanism Ownership | accepted | 2026-08-21 |

## Numbering

Numbers are pre-allocated per the master plan
(`docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`).
Lower numbers indicate foundational decisions; higher numbers
indicate refinements and follow-ons. When filing a new ADR, pick
the next available number that fits the decision's logical
relationship to existing ADRs.

## Cross-references

- Master plan: `docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md`
- Upstream ADR style reference: `/Users/les/Projects/mahavishnu/docs/adr/`
- Phase 8 (master plan) adds API docs, onboarding docs, and a
  full ADR sweep — this README will expand at that point.

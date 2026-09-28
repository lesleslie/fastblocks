# Rollback Sink — `examples/_drafts/`

Per spec Integration Contract (Phase 2 build wave):

> "If Phase 2 reveals an audit gap, the affected dimension re-opens as Phase 1.5; the failing deliverable moves to `examples/_drafts/`, NOT shipped."

This directory is the rollback target. A failing deliverable (B1, B2, or B3) is moved here — NOT deleted — so the work is recoverable.

To rollback a deliverable:
1. `git mv examples/<deliverable> examples/_drafts/<deliverable>-<reason>-<date>`
2. Commit: `revert(<deliverable>): move to _drafts due to <reason>`
3. Open Phase 1.5 follow-up issue referencing the audit dimension that failed.
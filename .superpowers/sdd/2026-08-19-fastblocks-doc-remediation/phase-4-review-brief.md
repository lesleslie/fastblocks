# Phase 4 Review Brief — ACB Narrative Rewrite (docs/ Guides)

> **Read this first — it is your requirements.**

## Scope of review

Phase 4 of `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md` rewrites ACB imports across 8 user-facing guides in `docs/`, plus 4 secondary fixes (WebSocket Guide MCP section deletion, WebSocketAuthenticator import path, Docker Compose version key, phantom filename in TYPE_SYSTEM_MIGRATION). The implementer committed at `516fd95` on branch `docs/audit-remediation-2026-08-19` (BASE was `bf989d6`).

**Implementer's report:**
`/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/.superpowers/sdd/2026-08-19-fastblocks-doc-remediation/phase-4-report.md`

**Brief (what should have been done):**
`/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/.superpowers/sdd/2026-08-19-fastblocks-doc-remediation/phase-4-brief.md`

**Diff to review:**

```bash
cd /Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19
git diff bf989d6 516fd95
```

## Review rubric

### Spec compliance (does it hit the brief?)

The brief lists 12 items. Check each:

1. docs/ONEIRIC_GUIDE.md — title renamed, body rewritten
1. docs/ONEIRIC_DEPENDS_PATTERNS.md — examples rewritten
1. docs/GETTING_STARTED.md — last reviewed stamp updated
1. docs/ARCHITECTURE.md — ACB claims replaced; line 51 phantom ref replaced
1. docs/COMPARISONS.md — "ACB-based DI system" replaced
1. docs/SECURITY.md — line 209 rewritten to actual validator import
1. docs/NOTES.md — scratchpad header added (per the agent's call documented in the report)
1. docs/LESSONS_LEARNED.md — ACB_DEPENDS_PATTERNS phantom ref replaced
1. docs/WEBSOCKET_GUIDE.md:322-355 — MCP Tools Integration section deleted
1. docs/WEBSOCKET_GUIDE.md:71 — WebSocketAuthenticator import path fixed
1. docs/WEBSOCKET_GUIDE.md:485 — Docker Compose version key dropped
1. docs/TYPE_SYSTEM_MIGRATION.md — phantom ref replaced

### Quality

1. **Stale-content warnings**: Each guide should have the 5-line warning banner near the top (or an existing equivalent). Verify.
1. **Import verification**: Spot-check 3-5 of the `from oneiric.*` / `from fastblocks.*` imports the implementer claims are verified. The report has a comprehensive list — pick a few and confirm against source.
1. **Migration prose rephrasing**: The implementer rephrased "Before:" blocks in docs/ONEIRIC_GUIDE.md to avoid false-positive substring matches. Verify the reader still gets the migration intent (i.e., the legacy pattern is still described in a recognizable form).
1. **LESSONS_LEARNED.md "legacy" annotations**: Verify the annotations are sensible and don't break the historical record.
1. **NOTES.md scratchpad header**: Verify the file is now clearly demarcated as scratchpad.

### Process hygiene

1. **Diff scope**: `git diff --stat bf989d6 516fd95` should show ONLY the 10 files listed in the brief (8 primary + 2 secondary files covering items 9-12). Any other file modified is an out-of-scope edit.
1. **One commit**: `git log --oneline bf989d6..516fd95` should show exactly one commit.
1. **Author email**: `git log -1 --format='%ae' 516fd95` must be `les@wedgwoodwebworks.com`.
1. **CI guard xfail**: Should still be 34 (Phase 4 can't drop the count due to the module-level pytestmark — that's by design).

### Concerns to evaluate

- **5.1, 5.2** (xfail mechanics): Informational; not defects.
- **5.3** (ValidationService underscore-prefixed): Acceptable if the project's own tests use the same path.
- **5.4** (migration prose): Acceptable if the migration intent survives.
- **5.5** (over-greedy substring match on `broadcast_*`): This is a **Phase 10 follow-up**, NOT a Phase 4 defect. Note it as a deferred minor (parked for Phase 10 final review).
- **5.6** (lessons-learned legacy annotations): Acceptable if reader can still follow the history.
- **5.7** (docs/README.md out of scope): Correctly identified; Phase 9 owns it.

## Verdict format

Return one of:

- **APPROVED** — spec met, quality acceptable, no Critical/Important findings.
- **APPROVED_WITH_FINDINGS** — spec met, but list Minor findings to track. Minor findings go to the ledger for Phase 10 final review (e.g., the `broadcast_*` substring issue is one such minor).
- **NEEDS_FIXES** — Critical or Important findings. List each with file:line + issue + suggested fix.

## Constraints

- READ-ONLY. Do not edit files.
- Don't re-run the full test suite. The implementer already ran the CI guard; trust their numbers.
- The implementer's report is authoritative for *what was done*; your job is to verify *whether it's right*.
- Don't dispatch any further subagents. You're the final gate before Phase 4 is marked complete.

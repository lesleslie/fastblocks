# Phase 3 Review Brief — ACB Narrative Rewrite (Top-Level Docs)

> **Read this first — it is your requirements.**

## Scope of review

Phase 3 of `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md` rewrites ACB imports and stale claims in README.md, QWEN.md, RULES.md. The implementer committed at `bf989d6` on branch `docs/audit-remediation-2026-08-19` (BASE was `41ad715`).

**Implementer's report:**
`/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/.superpowers/sdd/2026-08-19-fastblocks-doc-remediation/phase-3-report.md`

**Diff to review:** the implementer edited three files. Generate it yourself with:

```bash
cd /Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19
git diff 41ad715 bf989d6 -- README.md QWEN.md RULES.md
```

## Review rubric

### Spec compliance (does it hit the brief?)

The brief is at `/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/.superpowers/sdd/2026-08-19-fastblocks-doc-remediation/phase-3-brief.md`. Check each item:

1. README.md — 27 ACB import blocks replaced with Oneiric equivalents
2. README.md:1395 — ACB acknowledgements dropped
3. QWEN.md:7,13 — "Built on ACB" framing removed
4. QWEN.md:30 — "Middleware Communication Protocol" → "Model Context Protocol"
5. QWEN.md:34,38,120 — ACB mentions stripped
6. QWEN.md:53 — `python -m fastblocks serve` replaced with `granian fastblocks.applications:app`
7. RULES.md:154,211 — crackerjack CLI standardized to `uv run crackerjack run`
8. RULES.md:234,371 — fabricated `-x -t` and `--comprehensive` flags removed
9. RULES.md:292 — coverage target text replaced with "Floor: 49.13%"
10. RULES.md:340,361 — `ws://localhost:8675` references removed
11. RULES.md:362 — fabricated MCP tool names removed
12. RULES.md:20-23,37 — typing/docstrings rule scoped to "new code only"

### Quality (is the rewrite correct?)

1. **Import verification**: Every `from oneiric.*` import must be importable. The implementer verified `OneiricSettings` and `resolve_component[_async]` resolve. Verify the others.
2. **API accuracy**: The implementer reports using `resolve_component_async(depends, ...)` from `fastblocks/core/resolver.py`. Verify against the source that this is the canonical public API.
3. **Coverage value**: The brief says 49.13%; pyproject.toml has `--cov-fail-under=49.1324200913242`. The implementer used 49.13% verbatim. Within tolerance — verify the doc text is consistent.
4. **One commit only**: `git log --oneline 41ad715..bf989d6` should show exactly one commit (the amended one).
5. **No out-of-scope edits**: README.md, QWEN.md, RULES.md only. `tests/docs/test_doc_accuracy.py` must NOT be touched (Phase 10 owns the xfail removal). `docs/`, `CHANGELOG.md`, `CLAUDE.md`, `CONTRIBUTING.md` must NOT be touched (Phases 4-6 own those).
6. **Author email**: `git log -1 --format='%ae' bf989d6` must be `les@wedgwoodwebworks.com` (not `.local`).
7. **Concerns addressed**: Concern #1 (resolver API) was addressed by amendment to `bf989d6`. Concerns #2-#6 are documented in the report. Confirm the amendments resolved #1 cleanly and #2-#6 are acceptable observations (not blocking defects).

### Process hygiene

1. The CI guard at `tests/docs/test_doc_accuracy.py` should still show 34 xfails — Phase 3 doesn't own those files yet. If the count dropped, the implementer may have touched out-of-scope files.
2. The implementer stayed within the worktree (`/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/`).

## Verdict format

Return one of:

- **APPROVED** — spec compliance met, quality acceptable, no Critical/Important findings.
- **APPROVED_WITH_FINDINGS** — spec met, but list Minor findings to track. (These never enter the fix loop; they go to the ledger for Phase 10 final review.)
- **NEEDS_FIXES** — Critical or Important findings. List each one with: file:line, what's wrong, suggested fix.

## Constraints

- READ-ONLY. Do not edit files.
- The implementer's report is authoritative for *what was done*; your job is to verify *whether it's right*.
- Don't re-run the full test suite. The implementer already ran the CI guard; trust their numbers.
- Don't dispatch any further subagents. You're the final gate before Phase 3 is marked complete.
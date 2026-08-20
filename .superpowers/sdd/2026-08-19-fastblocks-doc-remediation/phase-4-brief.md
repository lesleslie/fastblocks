# Phase 4 Brief — ACB Narrative Rewrite (docs/ Guides)

> **Read this first — it is your requirements, with the exact values to use verbatim.**

## Project context

FastBlocks v0.20.0 removed its ACB dependency in Phase 3.1. Despite the migration being complete, **8 user-facing guides in `docs/` still describe FastBlocks as ACB-based** with `from acb.*` imports throughout. Copy-paste produces `ImportError`.

You are on branch `docs/audit-remediation-2026-08-19` at commit `bf989d6` in the worktree at `/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/`. Phase 3 already rewrote the top-level docs (README.md, QWEN.md, RULES.md). Phase 4 owns the docs/ guides.

**ACB → Oneiric translation rules** (these EXACT translations are now canonical — Phase 3 verified them):

| Stale (ACB) | Replacement (Oneiric) |
|-------------|----------------------|
| `from acb.adapters import import_adapter` | `from fastblocks.core.resolver import get_resolver, resolve_component_async` (sync-only sites use `resolve_component`); then `depends = get_resolver()` and `await resolve_component_async(depends, "fastblocks", "templates")` |
| `from acb.depends import depends, Inject` | `from oneiric.core.depends import depends, inject` |
| `from acb.config import Config` | `from oneiric.core.config import OneiricSettings` |
| `from acb.actions.compress import compress` | Use the actual surface from `fastblocks/actions/` (verify before rewriting) |
| `from acb.services.validation import ValidationService` | Verify with `git grep -n "ValidationService" fastblocks/` first. If absent, point to `fastblocks/_validation_integration.py` or rewrite around the public surface |
| `from acb.mcp import create_mcp_server, register_tools, register_resources` | Use `from fastblocks.mcp import ...` matching what's actually exported |
| `from acb.workflows import WorkflowEngine` | Verify `git grep -n "WorkflowEngine" fastblocks/_workflows_integration.py` first |
| `from acb.events import EventHandler` | Verify `git grep -n "EventHandler" fastblocks/_events_integration.py` first |
| `register_pkg()` | Delete — Oneiric resolver doesn't use it |
| `import_adapter("name")` | `await resolve_component_async(depends, "fastblocks", "name")` (sync: `resolve_component`) |
| `uv add acb[sql|nosql|cache|monitoring|storage|secret|vector|ai|smtp|requests]` | Delete; Oneiric handles dependencies, no extras |
| `@depends.inject` | Use `await resolve_component_async(depends, ...)` inside async handlers; sync equivalent for sync code |

## Files to modify (Phase 4 — 8 ACB-rewrite guides + 3 secondary fixes)

### Primary (ACB rewrites — 8 guides)

For each, add a stale-content warning banner at the top if not present, then rewrite ACB-framed code to Oneiric-framed code:

```
> ⚠️ **Stale content:** This guide still references the pre-0.13.x ACB-based
> architecture. ACB was removed in Phase 3.1; FastBlocks now uses Oneiric.
> See `docs/migrations/0.7-to-0.8.md` and `CLAUDE.md` for the current truth.
> Rewriting the body in progress.
```

1. **`docs/ONEIRIC_GUIDE.md`** — Rename title from "FastBlocks ACB Guide" to "FastBlocks Oneiric Guide"; rename subtitle to match. Rewrite lines 29, 50-53, 371, body throughout (drop ACB; add Oneiric surface).
2. **`docs/ONEIRIC_DEPENDS_PATTERNS.md`** — Same; title and examples throughout. Note: filename is `ONEIRIC_DEPENDS_PATTERNS.md`, but the doc may have body text still calling it "ACB patterns" — fix.
3. **`docs/GETTING_STARTED.md`** — Update `last reviewed` stamp to 2026-08-19 alongside the rewrite.
4. **`docs/ARCHITECTURE.md`** — Replace ACB claims (lines 22, 38-46, 65) with Oneiric. Replace `MIGRATION-0.17.0.md` phantom ref (line 51) with `migrations/0.7-to-0.8.md`.
5. **`docs/COMPARISONS.md`** — Replace "ACB-based DI system" (lines 64, 83) with "Oneiric-based DI system".
6. **`docs/SECURITY.md`** — Rewrite `from acb.services.validation import ValidationService` (line 209) to the actual validator import.
7. **`docs/NOTES.md`** — Add a "scratchpad" header; don't rewrite body (this file is brainstorming). Alternative: skip this file entirely and note it in the report.
8. **`docs/LESSONS_LEARNED.md`** — Replace `ACB_DEPENDS_PATTERNS.md` (4 references at lines 268-269, 525, 733) with `ONEIRIC_DEPENDS_PATTERNS.md`; drop other ACB mentions.

### Secondary (3 specific fixes in scope)

9. **`docs/WEBSOCKET_GUIDE.md:322-355`** — Delete the entire "MCP Tools Integration" section. The `fastblocks.mcp.websocket_tools` module was deleted in 0.8.0; the import would crash.
10. **`docs/WEBSOCKET_GUIDE.md:71`** — Update `from mcp_common.websocket import WebSocketAuthenticator` to `from mcp_common.websocket.auth import WebSocketAuthenticator` (matches `fastblocks/websocket/auth.py:30`).
11. **`docs/WEBSOCKET_GUIDE.md:485`** — Drop obsolete Docker Compose `version: '3.8'` key.
12. **`docs/TYPE_SYSTEM_MIGRATION.md`** — Replace `ACB_DEPENDS_PATTERNS.md` phantom ref with `ONEIRIC_DEPENDS_PATTERNS.md`.

## Constraints

- Do NOT touch: README.md, QWEN.md, RULES.md (Phase 3 owned those), CLAUDE.md, CHANGELOG.md, CONTRIBUTING.md (Phase 6 owns those), any `fastblocks/adapters/*/README.md` (Phase 5 owns those), any archived docs.
- Do NOT touch `tests/docs/test_doc_accuracy.py` (Phase 10 removes the xfail).
- One commit only on the worktree branch.
- Author email `les@wedgwoodwebworks.com`.
- Verify each `from oneiric.*` or `from fastblocks.*` import via `git grep` against source. Don't invent imports.

## Verification — required before commit

```bash
cd /Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19

# 1. No ACB imports in docs/ (excluding archive/)
git grep -n "from acb\.\|import acb" docs/ -- ':!docs/archive/**' ':!docs/baselines/**' ':!docs/superpowers/notes/**'
# Expected: zero matches.

# 2. No phantom filenames in docs/
git grep -n "ACB_GUIDE\.md\|MIGRATION-0\.17\.0\.md\|ACB_DEPENDS_PATTERNS\.md" docs/ README.md CLAUDE.md CHANGELOG.md CONTRIBUTING.md
# Expected: zero matches.

# 3. WebSocket Guide: dead module reference gone
git grep -n "fastblocks.mcp.websocket_tools\|broadcast_ui_update\|broadcast_component_render" docs/WEBSOCKET_GUIDE.md
# Expected: zero matches.

# 4. CI guard xfail count should drop (Phase 4 owns the docs/ ACB categories)
uv run pytest tests/docs/ --no-cov -v
# Expected: xfail count is lower than 34. Record the new count.

# 5. Commit hygiene
git status --short
git diff --stat HEAD
# Expected: only the 9-10 files in scope modified.
```

## Commit

```bash
cd /Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19

git add docs/ONEIRIC_GUIDE.md docs/ONEIRIC_DEPENDS_PATTERNS.md docs/GETTING_STARTED.md \
        docs/ARCHITECTURE.md docs/COMPARISONS.md docs/SECURITY.md docs/NOTES.md \
        docs/LESSONS_LEARNED.md docs/WEBSOCKET_GUIDE.md docs/TYPE_SYSTEM_MIGRATION.md

git -c user.email=les@wedgwoodwebworks.com commit -m "fix(fastblocks): P4 docs/ guide ACB narrative rewrite + WebSocket MCP section deletion

Phase 4 of docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md.

[one-line summary per file group]

Refs: docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md"
```

## Report contract

Write your final report to:
`/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/.superpowers/sdd/2026-08-19-fastblocks-doc-remediation/phase-4-report.md`

The report must contain:

1. **Status:** DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED
2. **Commit SHA** of the new commit on `docs/audit-remediation-2026-08-19`
3. **Files changed:** list with line-count diffs (`git diff --stat HEAD~1`)
4. **CI guard xfail count:** before / after
5. **Concerns:** any uncertainty, anything not verified against source, anything that needs reviewer judgment
6. **Self-review:** what you checked before committing
7. **NOTES.md decision:** did you skip it, mark it, or rewrite it? Document which.

## Notes on scale

This phase touches ~10 files and removes ~30-50 ACB import blocks. The implementation is mostly mechanical translation (Phase 3 established the pattern), but each guide has its own prose style and may need context-specific judgment. Use the ACB → Oneiric translation table verbatim. If a guide uses an ACB symbol not in the table, verify against source before translating.

If a verification command fails in a way that suggests the plan is wrong (e.g., a `from acb.*` import that has no Oneiric equivalent exists in source), mark BLOCKED in the report with the specific failure — do NOT silently invent an import.
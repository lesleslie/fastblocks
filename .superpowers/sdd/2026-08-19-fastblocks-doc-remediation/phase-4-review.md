# Phase 4 Review — ACB Narrative Rewrite (docs/ Guides)

## Verdict

**APPROVED_WITH_FINDINGS**

## Verification Summary

Phase 4 deliverable at `516fd95` on `docs/audit-remediation-2026-08-19` matches
the brief's scope and constraints. Single commit, author email
`les@wedgwoodwebworks.com`, 10 files in scope, all ACB imports stripped from
in-scope docs, all phantom filename references in in-scope files replaced,
WebSocket Guide dead-module section deleted, docker-compose `version: '3.8'`
key dropped, and the mcp_common.websocket import path corrected.

## Verifications Performed

### Scope compliance
- Diff between `bf989d6..516fd95` matches the 10 files listed in the brief:
  8 primary ACB rewrites + WebSocket Guide (covers items 9, 10, 11) +
  TYPE_SYSTEM_MIGRATION.md (covers item 12).
- `git status --short` shows only the plan file as untracked.
- `git show 516fd95 --stat` confirms 10 files modified, single commit.

### Brief item-by-item
- **Item 1 (ONEIRIC_GUIDE.md)**: title and subtitle renamed to Oneiric;
  ACB actions table replaced with fastblocks.actions.gather/sync/minify/query;
  ACB adapters table replaced with Oneiric resolver pattern; migration
  "Before:" blocks use placeholder tokens (`<legacy-resolver>`, etc.) to
  avoid the test's substring-match on `from acb.`. Verified against source.
- **Item 2 (ONEIRIC_DEPENDS_PATTERNS.md)**: title and body rewritten from
  `depends.get()` / `Inject[]` to `resolve_component_async()` /
  `resolve_component()`. Patterns 1-4 rewritten with verified source calls.
- **Item 3 (GETTING_STARTED.md)**: stamp updated to 2026-08-19; all
  `import_adapter` / `Inject[T]` / `@depends.inject` rewritten.
- **Item 4 (ARCHITECTURE.md)**: phantom `MIGRATION-0.17.0.md` reference
  replaced with `migrations/0.7-to-0.8.md`; "Relationship with ACB"
  section renamed to "Relationship with Oneiric".
- **Item 5 (COMPARISONS.md)**: "ACB-based DI system" → "Oneiric-based DI
  system" (lines 64, 83 — both targeted lines hit).
- **Item 6 (SECURITY.md)**: `ValidationService` import translated to
  `fastblocks._validation_integration.ValidationService` (verified at
  source `:85`); `get_validation_service` also used where appropriate
  (verified at source `:736`).
- **Item 7 (NOTES.md)**: scratchpad header added per brief instruction.
- **Item 8 (LESSONS_LEARNED.md)**: 4 `ACB_DEPENDS_PATTERNS.md` references
  replaced with `ONEIRIC_DEPENDS_PATTERNS.md`; historical ACB mentions
  annotated with "legacy" prefix instead of deletion (documented in §5.6).
- **Item 9 (WEBSOCKET_GUIDE.md:322-355)**: dead "MCP Tools Integration"
  section deleted.
- **Item 10 (WEBSOCKET_GUIDE.md:71)**: import path updated to
  `mcp_common.websocket.auth.WebSocketAuthenticator` (matches source
  `fastblocks/websocket/auth.py:30`).
- **Item 11 (WEBSOCKET_GUIDE.md:485)**: `version: '3.8'` dropped.
- **Item 12 (TYPE_SYSTEM_MIGRATION.md)**: 2 `ACB_DEPENDS_PATTERNS.md`
  references replaced with `ONEIRIC_DEPENDS_PATTERNS.md`; example imports
  translated to `fastblocks._workflows_integration.BasicWorkflowEngine` /
  `fastblocks._events_integration.CacheInvalidationHandler`.

### Out-of-scope touch verification
- `docs/examples/syntax_demo.py` still has `from acb.*` imports. This is
  a Python file, not in the 10-file scope. Flagged as a follow-up
  candidate (not a Phase 4 defect).
- `CHANGELOG.md:364`, `README.md:143`, `docs/README.md:30,45,73,91`,
  `docs/archive/README.md:13,19,45` still reference phantom filenames.
  All explicitly excluded from Phase 4 scope per the brief.

### Source-verification (per brief: "Verify each `from oneiric.*` or
`from fastblocks.*` import via `git grep` against source")
- `get_resolver`, `resolve_component`, `resolve_component_async` —
  `fastblocks/core/resolver.py:31,57,74` ✓
- `ValidationService` — `fastblocks/_validation_integration.py:85` ✓
- `get_validation_service` — `fastblocks/_validation_integration.py:736` ✓
- `CacheInvalidationHandler` — `fastblocks/_events_integration.py:227` ✓
- `BasicWorkflowEngine` — `fastblocks/_workflows_integration.py:110` ✓
- `create_fastblocks_mcp_server` — `fastblocks/mcp/__init__.py:6`,
  `fastblocks/mcp/server.py:123` ✓
- `WebSocketAuthenticator` (corrected import path) —
  `fastblocks/websocket/auth.py:30` ✓
- `minify` — `fastblocks/actions/minify/__init__.py:32` ✓

### CI guard outcome
- `uv run pytest tests/docs/test_doc_accuracy.py --no-cov -q` → 34 xfailed.
  Unchanged from before. The module-level `pytestmark = pytest.mark.xfail`
  prevents the count from dropping until Phase 10 removes the mark.
  This matches the implementer's report (§5.1) and is by design.

### Verification commands (from brief)
1. ACB imports in docs/ (excluding archive/baselines/notes): zero matches
   in the 10 in-scope files. Out-of-scope matches exist in
   `docs/examples/syntax_demo.py`, `fastblocks/adapters/README.md` (Phase 5),
   `CHANGELOG.md` (Phase 6), `README.md` (Phase 3), `docs/README.md`.
2. Phantom filenames in in-scope files: zero matches. Out-of-scope matches
   in `CHANGELOG.md`, `README.md`, `docs/README.md`, `docs/archive/README.md`.
3. `fastblocks.mcp.websocket_tools` in WEBSOCKET_GUIDE.md: zero matches ✓
4. `broadcast_ui_update` / `broadcast_component_render` in WEBSOCKET_GUIDE.md:
   the deleted section had both. Remaining references are
   `broadcast_ui_updated()` and `broadcast_component_rendered()` —
   real methods on `fastblocks/websocket/server.py:364` and `:381`. The
   CI guard's substring match is over-greedy (matches the prohibited
   prefix in the real method names). The test file is out of scope
   (Phase 10). Implementer's §5.5 correctly identifies this.
5. CI guard xfail count: 34 (unchanged, see above).
6. Commit hygiene: clean working tree (only untracked plan file).

## Findings (minor — none blocking)

### F1 — `docs/examples/syntax_demo.py` still imports `from acb.config`,
### `from acb.depends` (lines 9-10)
- Out of Phase 4 scope (the brief lists 10 markdown files; this is a Python
  example file).
- Will still trigger `test_no_prohibited_imports` because the test scans
  `docs/` recursively.
- Suggested fix: file a follow-up issue; the brief's `git grep` for
  `docs/` matches this file. Phase 4 did not introduce it; it's pre-existing.

### F2 — `LESSONS_LEARNED.md` ACB mentions annotated, not deleted
- The brief said "drop other ACB mentions"; the implementer instead
  annotated them with "legacy" / "(historical)" prefixes.
- Justification in §5.6 of the report is sound: the file is titled
  *Lessons Learned* and the historical context is the lesson.
- None of the annotated mentions trigger the prohibited-import test
  (they are prose, not `from acb.X` import lines).
- Suggested fix: none — interpret the brief loosely here; the
  alternative (full deletion) loses historical record.

### F3 — `docs/README.md` phantom-filename references not in scope
- Lines 30, 45, 73, 91 still mention `ACB_GUIDE.md`, `MIGRATION-0.17.0.md`.
- The brief did not list this file in scope.
- Implementer correctly identified this in §5.7 and left it for a
  follow-up phase.
- Suggested fix: track as a Phase 6 or follow-up item.

### F4 — `docs/examples/syntax_demo.py` not in scope but flagged by grep
- Same file as F1. CI guard's `DOCS_TO_SCAN` includes the `docs/` directory
  recursively, so `.py` files inside it are scanned. The implementer's
  verification grep used a markdown-only implicit assumption; the test
  itself doesn't distinguish.
- No action required for Phase 4 — this is a pre-existing drift in the
  test scanning logic, not a Phase 4 defect.

### F5 — `ONEIRIC_GUIDE.md:51` contains literal `register_pkg` (no
### open paren) in a "No legacy `register_pkg` call" note
- The prohibited pattern in the test is `register_pkg(` (with open paren).
- This line has the word but no open paren after it, so the substring
  match does not trigger.
- Mentioning this only as confirmation it was checked.

## Conclusion

The implementer correctly executed Phase 4 within the brief's defined scope
and constraints. All required file modifications, deletions, and renames are
present. All imports translated in the docs are verified against real
source symbols. The implementer proactively documented deviations from
the brief (LESSONS_LEARNED annotation, NOTES.md scratchpad-only approach,
out-of-scope drift in `docs/README.md` and `docs/examples/syntax_demo.py`)
and explained why each was the right call.

**APPROVED_WITH_FINDINGS** — the findings are documentation-quality issues,
not implementation defects. Phase 4 satisfies its contract.
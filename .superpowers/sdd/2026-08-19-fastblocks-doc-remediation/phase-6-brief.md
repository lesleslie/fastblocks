# Phase 6 Brief — Top-Level Doc Fixes (CLAUDE.md, CHANGELOG.md, CONTRIBUTING.md)

> **Read this first — it is your requirements, with the exact values to use verbatim.**

## Project context

You are on branch `docs/audit-remediation-2026-08-19` at commit `0b6dc1b` in the worktree at `/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/`. Phases 0-5 are complete.

Phase 6 owns 7 small accuracy fixes across 3 top-level files. These are surgical edits with exact strings in this brief — verify each replacement against the live file before committing.

## Files to modify

- `CLAUDE.md` (5 edits)
- `CHANGELOG.md` (4 rephrasings)
- `CONTRIBUTING.md` (1 fix)

## Edits — exact strings

### CLAUDE.md

1. **Line 39** — Drop the `pre-commit run --all-files` line from daily commands.

   - Why: `.pre-commit-config.yaml` does not exist in this repo. Running the command exits with no hooks configured.
   - Locate the surrounding "Daily Commands" section; remove just the `pre-commit run --all-files` line. Leave surrounding lines intact.

1. **Line 24** — Replace coverage text. From:

   ```
   Coverage (target 80%; floor 10% with --cov-fail-under)
   ```

   To:

   ```
   Coverage (floor: 49.13% — pyproject.toml [tool.coverage.report].fail_under; gate fails below this).
   ```

1. **Line 106** — Replace the wrong conftest LOC count.

   - Run `wc -l tests/conftest.py` from the worktree to get the actual line count (it's 406).
   - Replace `tests/conftest.py # 3,410 LOC` with the actual line count.

1. **Lines 86-87** — Fix the resource names list. The brief expected 7 resources: `template_syntax`, `template_filters`, `component_catalog`, `adapter_schemas`, `settings_docs`, `best_practices`, `htmx_patterns`. Verify against `git grep -n "add_resource\|register_resource\|FastblocksResource" fastblocks/mcp/resources.py` to confirm exact names; replace the list with the actual registered names.

1. **Line 169** — Add one sentence above the `PROFILE_REGISTRATIONS` dict annotating the runtime resolution:

   ```
   # Keys are members of the runtime-resolved enum (`_TOOL_PROFILE_CLS`) —
   # the same `ToolProfile.MINIMAL` / `STANDARD` / `FULL` names when
   # `mcp-common` is on the import path, the local `_FallbackToolProfile`
   # mirror otherwise. See the comment block above for resolution logic.
   ```

### CHANGELOG.md

6. **Lines 67, 71, 79, 83** — Replace each occurrence of "slated for 0.8.0" with "**Removed in 0.8.0**" (or "was removed in 0.8.0" — match surrounding tense).
   - Locate each occurrence and replace. Run `git grep -n "slated for 0.8.0" CHANGELOG.md` first to find exact occurrences (might be more than 4 if the audit missed some).

### CONTRIBUTING.md

7. **Line 27** — Replace `@pytest.mark.benchmark` with `@pytest.mark.performance`. The actual marker per `pyproject.toml:202-208` is `performance`. Verify with `git grep -n "markers = " pyproject.toml | head -5` to confirm.

## Constraints

- Do NOT touch: any README.md, QWEN.md, RULES.md (P3 owned), any `docs/` file (P4 owned), any `fastblocks/adapters/*/README.md` (P5 owned), `tests/docs/test_doc_accuracy.py`, archived docs.
- One commit only on the worktree branch.
- Author email `les@wedgwoodwebworks.com`.
- Surgical edits only — don't rewrite surrounding prose.

## Verification — required before commit

```bash
cd /Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19

# 1. Pre-commit reference gone
git grep -n "pre-commit run --all-files" CLAUDE.md
# Expected: zero matches.

# 2. Coverage text corrected
git grep -n "Coverage (target 80%; floor 10%" CLAUDE.md
# Expected: zero matches.

# 3. conftest LOC corrected (3,410 should not appear)
git grep -n "3,410 LOC" CLAUDE.md
# Expected: zero matches.

# 4. Resource names match what fastblocks/mcp/resources.py actually registers
git grep -n "component_catalog\|adapter_schemas\|settings_docs\|htmy_component_catalog\|settings_documentation" CLAUDE.md
# Expected: only the new (correct) names appear; the two old names (htmy_component_catalog, settings_documentation) are gone.

# 5. CHANGELOG "slated for 0.8.0" gone
git grep -n "slated for 0.8.0" CHANGELOG.md
# Expected: zero matches.

# 6. CONTRIBUTING pytest marker corrected
git grep -n "pytest.mark.benchmark" CONTRIBUTING.md
# Expected: zero matches.

# 7. Commit hygiene
git diff --stat HEAD
git status --short
# Expected: only CLAUDE.md, CHANGELOG.md, CONTRIBUTING.md modified.

# 8. CI guard xfail count should drop further
uv run pytest tests/docs/ --no-cov -v
# Expected: xfail count lower than 33 (likely drops by 2-3: 1 for coverage target test, 1 for phantom-filenames if any remain in scope, etc.)
```

## Commit

```bash
cd /Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19

git add CLAUDE.md CHANGELOG.md CONTRIBUTING.md

git -c user.email=les@wedgwoodwebworks.com commit -m "fix(fastblocks): P6 CLAUDE.md / CHANGELOG.md / CONTRIBUTING.md accuracy

Phase 6 of docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md.

[one-line summary per file]

Refs: docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md"
```

## Report contract

Write your final report to:
`/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/.superpowers/sdd/2026-08-19-fastblocks-doc-remediation/phase-6-report.md`

The report must contain:

1. **Status:** DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED
1. **Commit SHA** of the new commit on `docs/audit-remediation-2026-08-19`
1. **Files changed:** line-count diffs (`git diff --stat HEAD~1`)
1. **CI guard xfail count:** before / after
1. **Concerns:** any uncertainty, any string you couldn't find, any line-number discrepancy
1. **Self-review:** what you checked before committing

## Notes on scale

This phase is small (7 surgical edits). The plan is fully specified; the work is mechanical. Most "concerns" will be line-number drift between the audit and the current file state. If a brief line number is wrong, locate the right line via `git grep` and document in the report.

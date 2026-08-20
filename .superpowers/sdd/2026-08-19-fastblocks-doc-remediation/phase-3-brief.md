# Phase 3 Brief — ACB Narrative Rewrite (Top-Level Docs)

> **Read this first — it is your requirements, with the exact values to use verbatim.**

## Project context

FastBlocks v0.20.0 is a Starlette/HTMX/Jinja web framework. Phase 3.1 (commit
landed earlier than this branch) **removed the ACB dependency entirely** —
`pyproject.toml` has zero `acb` dependency. FastBlocks now uses **Oneiric** for
dependency injection, configuration management, and pluggable adapters.

Despite the migration being complete, **the top-level docs still describe
FastBlocks as "built on ACB"** with ~50+ import-from-`acb.*` code blocks
across README.md, QWEN.md, RULES.md. Copy-paste from these docs produces
`ImportError` on every fresh install.

You are on branch `docs/audit-remediation-2026-08-19` at commit `41ad715`
in the worktree at `/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/`.
Phases 0, 1, 2 are already merged in:

- **P0** (commit `6f5e994`): `WEBSOCKET_GUIDE.md:398-399` env-var names corrected
- **P1** (commit `5f12485`): Created `tests/docs/test_doc_accuracy.py` skeleton
- **P2** (commit `41ad715`): Filled the CI guard with 9 drift assertions, all
  marked `pytest.mark.xfail(reason="baseline drift; fix in P3-P9")`. The
  guard runs via `uv run pytest tests/docs/ --no-cov -v`. As you fix each
  drift category in Phase 3, the corresponding xfail test will start passing.

## Files to modify (Phase 3 only)

- `README.md` (top-level)
- `QWEN.md` (top-level)
- `RULES.md` (top-level)

`tests/docs/test_doc_accuracy.py` should NOT be touched (Phase 10 removes the xfail).

## What to change — exact specifications

### README.md

Replace ACB-framed code with Oneiric-framed code at these line ranges:
- Line 19, 21, 45: intro narrative
- Lines 169-170, 238-239, 334, 358: narrative sections
- Lines 408-409, 443-444, 699-700, 740-741, 891-892, 918-919, 1004-1005,
  1057, 1103-1104, 1260-1262, 1273-1275, 1334-1335: 27 code blocks importing
  from `acb.*`
- Line 1395: ACB acknowledgements section

**ACB → Oneiric translation rules** (use these exact replacements):

| Stale (ACB) | Replacement (Oneiric) |
|-------------|----------------------|
| `from acb.adapters import import_adapter` | `from fastblocks.core.resolver import get_resolver` followed by `resolver = get_resolver()` and `adapter = resolver.resolve("fastblocks", "templates")` (or `"images"`, `"styles"`, etc.) |
| `from acb.depends import depends, Inject` | `from oneiric.core.depends import depends, inject` |
| `from acb.config import Config` | `from oneiric.core.config import OneiricSettings` |
| `from acb.actions.compress import compress` | Use the actual surface from `fastblocks/actions/compress/` if it exists; otherwise rewrite the snippet around the public action API |
| `from acb.services.validation import ValidationService` | Use the actual validator module (likely `fastblocks/_validation_integration.py`; verify before rewriting) |
| `register_pkg()` | Delete (the Oneiric resolver doesn't use it; show `get_resolver()` only) |
| `import_adapter("name")` | `resolver.resolve("fastblocks", "name")` |

Verify each replacement against `git grep -n "class\|def" fastblocks/` before
committing — the Oneiric surface is the source of truth.

### QWEN.md

- **Lines 7, 13**: Replace "Built on the **Asynchronous Component Base (ACB)** framework"
  with "Built on **Oneiric** for dependency injection, configuration management,
  and pluggable adapters." Drop all `acb.*` framings.
- **Line 30**: Replace "`Middleware Communication Protocol`" with
  "`Model Context Protocol`" (MCP has always meant Model Context Protocol).
- **Line 34, 38, 120**: Strip remaining ACB mentions.
- **Line 53**: Replace `uv run python -m fastblocks serve` with
  `uv run granian fastblocks.applications:app` (matches the `granian[reload]~=2.6`
  dependency in pyproject.toml). If `granian` invocation syntax is wrong,
  verify with `git grep -n "granian" pyproject.toml README.md`.

### RULES.md

- **Lines 154, 211**: Standardize crackerjack CLI to `uv run crackerjack run`
  (matches CLAUDE.md). Drop the `-t --ai-fix` variants.
- **Lines 234, 371**: Remove `python -m fastblocks -x -t` and
  `python -m fastblocks --comprehensive` references; replace with
  `uv run crackerjack run`.
- **Line 292**: Replace "Target 42% milestone coverage (current: 21.6%, baseline: 19.6%)"
  with "Floor: 49.13% (pyproject.toml `[tool.coverage.report].fail_under`)."
- **Lines 340, 361**: Remove both `ws://localhost:8675` references.
- **Line 362**: Delete the 3 fabricated MCP tool names (`execute_fastblocks`,
  `get_job_progress`, `get_comprehensive_status`).
- **Lines 20-23, 37**: Scope the `import typing as t` rule and the
  "NO DOCSTRINGS" rule to "new code only; existing usage grandfathered."
  Both contradict the actual codebase — module docstrings exist in
  `fastblocks/cli.py`, `fastblocks/mcp/tools.py`, `fastblocks/mcp/profiles.py`.

## Verification — required before commit

Run ALL of these and confirm:

```bash
cd /Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19

# 1. No ACB imports remain in the three files you touched
git grep -n "from acb\.\|import acb" README.md QWEN.md RULES.md
# Expected: zero matches.

# 2. CI guard has fewer xfails than before
uv run pytest tests/docs/ --no-cov -v
# Expected: xfail count is lower (some tests now pass). Record the count.

# 3. Commit hygiene
git diff --stat HEAD
git status --short
# Expected: only README.md, QWEN.md, RULES.md in the diff.
```

## Commit

```bash
cd /Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19

git add README.md QWEN.md RULES.md
git -c user.email=les@wedgwoodwebworks.com commit -m "fix(fastblocks): P3 ACB narrative rewrite — README/QWEN/RULES

Phase 3 of docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md.

[one-line summary of each major change]

Refs: docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md"
```

## Report contract

Write your final report to:
`/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/.superpowers/sdd/2026-08-19-fastblocks-doc-remediation/phase-3-report.md`

The report must contain:

1. **Status:** DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED
2. **Commit SHA** of the new commit on `docs/audit-remediation-2026-08-19`
3. **Files changed:** list with line-count diffs (`git diff --stat HEAD~1`)
4. **CI guard xfail count:** before / after
5. **Test summary:** `uv run pytest tests/docs/ --no-cov` output (xfail + pass counts)
6. **Concerns:** any uncertainty about a translation choice, any code you couldn't verify against source, anything that needs reviewer judgment
7. **Self-review:** what you checked yourself before committing

## Constraints

- Do NOT touch `tests/docs/test_doc_accuracy.py` (Phase 10 removes the xfail).
- Do NOT touch archived docs (`docs/archive/`, `docs/baselines/`, `docs/superpowers/notes/`).
- Do NOT touch any other docs in `docs/` (Phases 4-9 own those).
- Verify each `from oneiric.*` import against `git grep -n "from oneiric\|oneiric.core" fastblocks/` before committing — don't invent imports.
- Use commit author email `les@wedgwoodwebworks.com` (NOT `.local`).
- One commit only. Don't bundle P3 with anything else.
- If a verification command fails in a way that suggests the plan is wrong, mark BLOCKED in the report with the specific failure.

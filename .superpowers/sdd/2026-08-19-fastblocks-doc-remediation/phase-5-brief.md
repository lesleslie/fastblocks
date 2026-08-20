# Phase 5 Brief — ACB Narrative Rewrite (Adapter READMEs)

> **Read this first — it is your requirements, with the exact values to use verbatim.**

## Project context

FastBlocks v0.20.0 removed its ACB dependency in Phase 3.1. Despite the migration being complete, **12 adapter READMEs in `fastblocks/adapters/` still describe FastBlocks as ACB-based** with `from acb.*` imports throughout. Several also reference renamed files (`main.py` → `default.py`, `sitemap.py` → 7-file inventory) and the mcp/README.md has a wrong tool count ("10+" vs actual 10).

You are on branch `docs/audit-remediation-2026-08-19` at commit `516fd95` in the worktree at `/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/`. Phases 0-4 are complete. Phase 5 owns the adapter READMEs.

**ACB → Oneiric translation rules** (canonical from Phase 3, verified against source):

| Stale (ACB) | Replacement (Oneiric) |
|-------------|----------------------|
| `from acb.adapters import import_adapter` | `from fastblocks.core.resolver import get_resolver, resolve_component_async` (sync: `resolve_component`); then `depends = get_resolver()` and `await resolve_component_async(depends, "fastblocks", "name")` |
| `from acb.depends import depends, Inject` | `from oneiric.core.depends import depends, inject` |
| `from acb.config import Config, Settings` | `from oneiric.core.config import OneiricSettings` |
| `import_adapter("name")` | `await resolve_component_async(depends, "fastblocks", "name")` (sync: `resolve_component`) |
| `register_pkg()` | Delete (Oneiric resolver doesn't use it) |
| `from acb.adapters.logger.loguru import Logger` | `from oneiric.core.logging import get_logger` (verify each adapter's actual import) |
| `from acb.services.validation import ValidationService` | `from fastblocks._validation_integration import ValidationService` (matches `tests/test_validation_integration.py:10` convention) |
| `from acb.events import EventHandler` | Verify each adapter's actual import. The Phase 4 agent verified `fastblocks._events_integration.CacheInvalidationHandler` at `fastblocks/_events_integration.py:227`. |
| `from acb.workflows import WorkflowEngine` | `from fastblocks._workflows_integration import BasicWorkflowEngine` (verified at `fastblocks/_workflows_integration.py:110`) |

## Files to modify (13 files)

For each, add a stale-content warning banner at the top if not present:

```
> ⚠️ **Stale content:** This README still references the pre-0.13.x
> ACB-based architecture. ACB was removed in Phase 3.1; FastBlocks
> now uses Oneiric. See `docs/migrations/0.7-to-0.8.md` and
> `CLAUDE.md` for the current truth. Rewriting in progress.
```

### Primary rewrites (ACB)

1. **`fastblocks/adapters/admin/README.md`** — Rewrite ACB imports. Drop the "Material Theme" section entirely (only Bootstrap is shipped; `git ls-files fastblocks/adapters/admin/_templates/` shows only `bootstrap/sqladmin/`).
2. **`fastblocks/adapters/app/README.md`** — Rewrite ACB imports. **Replace all `main.py` references with `default.py`** (`git ls-files fastblocks/adapters/app/` shows `default.py` is the actual file; there's no `main.py`). Add a "Template Variants" section listing the 5 named variants from `_templates/`: `base/`, `bulma/`, `fastblocks_ui/`, `kelp/`, `vanilla/`, `webawesome/`.
3. **`fastblocks/adapters/auth/README.md`** — Rewrite ACB imports. Add a "Migrated to Oneiric" note at the top.
4. **`fastblocks/adapters/fonts/README.md`** — Verify whether ACB imports exist. Likely clean per audit; if so, just add the stale-content warning if not present.
5. **`fastblocks/adapters/icons/README.md`** — Same as fonts: verify, add warning if not present.
6. **`fastblocks/adapters/images/README.md`** — Verify ACB imports. Spot-check `cf_image_url`, `cf_responsive_image`, `twicpics_image`, `twicpics_smart_crop` template helpers against `git ls-files fastblocks/adapters/images/` and `git grep -n "cf_image_url\|twicpics_image" fastblocks/adapters/templates/_enhanced_filters.py` — keep only those that resolve.
7. **`fastblocks/adapters/routes/README.md`** — Rewrite ACB imports. **Replace all `main.py` references with `default.py`** (lines 69, 108 per the audit; verify with `git ls-files fastblocks/adapters/routes/`).
8. **`fastblocks/adapters/sitemap/README.md`** — Rewrite ACB imports. **Replace `sitemap.py` reference with the actual 7-file inventory**: `_base.py`, `_routes.py`, `asgi.py`, `cached.py`, `core.py`, `dynamic.py`, `native.py`, `static.py`. Mark `asgi.py` as the default. Expand "Available Implementations" table to list all 6 named implementations.
9. **`fastblocks/adapters/style/README.md`** — Rewrite ACB imports. **Add `vanilla.py` to implementation table**. **Remove phantom `bulma.py` reference** (no such file; only `kelp.py`, `vanilla.py`, `webawesome.py`, `fastblocks_ui.py` exist per `git ls-files fastblocks/adapters/style/`).
10. **`fastblocks/adapters/templates/README.md`** — Add `htmy` and `hybrid` rows to the implementations table. (`git ls-files fastblocks/adapters/templates/` shows `htmy.py`, `hybrid.py`, `jinja2.py` — 3 implementations, not 1.)

### Secondary fixes (registration + counts)

11. **`fastblocks/adapters/README.md`** (parent) — Add one-line summaries for the 6 missing categories: `admin/`, `app/`, `auth/`, `routes/`, `sitemap/`, `templates/` with cross-links to their per-adapter READMEs. Note the `style/` (singular dir) vs `styles.yml` (plural config) asymmetry.
12. **`fastblocks/mcp/README.md`** — Change "10+ MCP tools" to "10 MCP tools" (verified count via `git grep -c "^async def" fastblocks/mcp/tools.py`).
13. **`fastblocks/adapters/sitemap/README.md`** — Note `.backup.json` files in the repo are not docs concern; Phase 8 owns the `.gitignore` cleanup.

## Constraints

- Do NOT touch: README.md, QWEN.md, RULES.md (P3 owned), any `docs/` file (P4 owned), CLAUDE.md, CHANGELOG.md, CONTRIBUTING.md (P6 owns), `docs/README.md` phantom filenames (P9 owns).
- Do NOT touch `tests/docs/test_doc_accuracy.py` (Phase 10 removes the xfail).
- One commit only on the worktree branch.
- Author email `les@wedgwoodwebworks.com`.
- Verify each `from oneiric.*` or `from fastblocks.*` import via `git grep` against source.
- Do NOT delete `.backup.json` files (Phase 8 owns the `.gitignore` cleanup).

## Verification — required before commit

```bash
cd /Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19

# 1. No ACB imports in adapter READMEs
git grep -n "from acb\.\|import acb\|register_pkg" fastblocks/adapters/ fastblocks/mcp/README.md
# Expected: zero matches.

# 2. No main.py references in adapter READMEs (renamed to default.py)
git grep -n "main\.py" fastblocks/adapters/app/README.md fastblocks/adapters/routes/README.md
# Expected: zero matches.

# 3. No phantom bulma/sitemap.py references
git grep -n "from.*sitemap\b.*import\|adapters/style/bulma\|bulma\.py" fastblocks/adapters/
# Expected: zero matches for the file-name references.

# 4. MCP tool count corrected
git grep -n "10+" fastblocks/mcp/README.md
# Expected: zero matches.

# 5. Parent adapters/README.md has all 6 missing categories
git grep -n "^## admin\|^## app\|^## auth\|^## routes\|^## sitemap\|^## templates" fastblocks/adapters/README.md
# Expected: all 6 present.

# 6. CI guard xfail count should drop slightly (Phase 5 owns adapter README ACB categories)
uv run pytest tests/docs/ --no-cov -v
# Expected: xfail count is lower than 34.

# 7. Commit hygiene
git status --short
git diff --stat HEAD
# Expected: only the 13 files in scope modified.
```

## Commit

```bash
cd /Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19

git add fastblocks/adapters/README.md fastblocks/adapters/admin/README.md \
        fastblocks/adapters/app/README.md fastblocks/adapters/auth/README.md \
        fastblocks/adapters/fonts/README.md fastblocks/adapters/icons/README.md \
        fastblocks/adapters/images/README.md fastblocks/adapters/routes/README.md \
        fastblocks/adapters/sitemap/README.md fastblocks/adapters/style/README.md \
        fastblocks/adapters/templates/README.md fastblocks/mcp/README.md

git -c user.email=les@wedgwoodwebworks.com commit -m "fix(fastblocks): P5 adapter README ACB rewrite + registration + main.py→default.py

Phase 5 of docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md.

[one-line summary per major change]

Refs: docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md"
```

## Report contract

Write your final report to:
`/Users/les/Projects/fastblocks/.claude/worktrees/doc-audit-2026-08-19/.superpowers/sdd/2026-08-19-fastblocks-doc-remediation/phase-5-report.md`

The report must contain:

1. **Status:** DONE / DONE_WITH_CONCERNS / NEEDS_CONTEXT / BLOCKED
2. **Commit SHA** of the new commit on `docs/audit-remediation-2026-08-19`
3. **Files changed:** list with line-count diffs (`git diff --stat HEAD~1`)
4. **CI guard xfail count:** before / after
5. **Concerns:** any uncertainty, anything not verified against source
6. **Self-review:** what you checked before committing

## Notes on scale

This phase touches 13 files with focused, mostly-mechanical changes. The ACB translation table is the same as Phase 3 and Phase 4. The new wrinkle is the file-rename fixes (main.py → default.py, sitemap.py → 7 files) — these need `git ls-files` verification. The mcp tool count is just a "+ →" string edit. Should be quick.

If a verification command fails in a way that suggests the plan is wrong (e.g., a `main.py` reference is intentional rather than stale), mark BLOCKED in the report with the specific failure.
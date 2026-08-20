# FastBlocks Comprehensive Hook Remediation Plan

**Date**: 2026-08-18
**Author**: Claude (systematic-debugging Phase 4)
**Repo**: `/Users/les/Projects/fastblocks`
**Branch**: `main` (3 commits ahead of `origin/main`)

## Root Cause Summary

Three hook failures (betterleaks, ty, refurb) with **distinct root causes**:

1. **betterleaks** — No `.betterleaks.toml` exists; betterleaks doesn't respect `.gitignore` so it scans `.idea/`, `.obsidian/`, and `dist/` despite those being gitignored. Result: ~38 findings dominated by false positives from gitignored paths + 1 real finding (live GitLab PAT in `.idea/workspace.xml`).

2. **ty** — FastBlocks code uses **Oneiric 0.12- API patterns** (`await depends.resolve(...)`, `depends.get/set/get_sync`) but Oneiric 0.13+ migrated to a synchronous `Resolver.resolve()` returning a `Candidate | None` Pydantic model. The fastblocks code would crash at runtime in any path that actually exercises these calls — but most are wrapped in `except (KeyError, AttributeError, RuntimeError)` that **silently swallows the failures**. Same architectural issue affects `MCPServerCLIFactory.create_server()` (does not exist; only `create_app()` and `create_server_cli()` exist) and `register_resources()` (function does not exist anywhere).

3. **refurb** — 16 minor stylistic modernization wins, no logic bugs.

## Tier Breakdown

### Tier 1 — Real runtime bugs (must fix)
| File | Line | Bug | Fix |
|------|-----:|-----|-----|
| `fastblocks/mcp/tools.py` | 117, 272, 318, 367, 407, 455 | `await depends.resolve(...)` (sync API, not awaitable) | Remove `await`, use sync pattern |
| `fastblocks/mcp/resources.py` | 202 | Same await-on-sync bug | Same |
| `fastblocks/mcp/resources.py` | 462 | `register_resources(...)` undefined | Define or remove |
| `fastblocks/mcp/server.py` | 51, 150 | `MCPServerCLIFactory.create_server()` undefined | Use `create_app()` or `create_server_cli()` |
| `fastblocks/mcp/registry.py` | 34 | `depends.set(adapter_instance)` — no such method | Use proper Oneiric API |
| `fastblocks/mcp/registry.py` | 62 | `await depends.get(adapter_name)` — no such method, also await on sync | Use proper Oneiric API |
| `fastblocks/mcp/health.py` | 159 | `depends.get_sync(adapter_name)` — no such method | Use proper Oneiric API |
| `fastblocks/middleware.py` | 31 | `depends.resolve(domain)` — missing required `key` arg | Add `key` |
| `fastblocks/websocket/tls_config.py` | 55-58 | Type narrowing issues | Cast properly |
| `fastblocks/websocket/tls_config.py` | 39 | Unused blanket `# type: ignore` (ty uses different syntax) | Convert to `# ty: ignore` or remove |

### Tier 2 — Live credentials (security, USER ACTION REQUIRED)
- Both are in `.idea/` which IS gitignored but sits in plaintext on disk
- **Action**: User must rotate both tokens via web UI and clean the workspace.xml file

### Tier 3 — Betterleaks configuration
Create `/Users/les/Projects/fastblocks/.betterleaks.toml` with `should_exclude_file` patterns:
- `\.idea/.*`
- `\.obsidian/.*`
- `dist/.*`
- `\.secrets\.baseline`
- `docs/.*`
- `tests/.*`
- `node_modules/.*`

### Tier 4 — Refurb cleanup (minor)
16 stylistic fixes, all in `fastblocks/adapters/sitemap/*.py`, `fastblocks/mcp/{config_audit,discovery,env_manager}.py`. No bugs, just modernization.

## Working Tree State

```
M .coverage-ratchet.json
M .gitignore
D docs/archive/test-artifacts/coverage__20260728-055629.json
M docs/superpowers/plans/2026-07-28-fastblocks-ruff-remediation.md
M docs/superpowers/specs/2026-07-28-fastblocks-ruff-remediation-design.md
M tests/actions/gather/test_strategies.py
M tests/test_caching_b023_closure_binding.py
M uv.lock
?? .cache/betterleaks-report.json
```

**Implementer constraints**: Do not touch any of these pre-existing dirty files. Only modify files listed in Tier 1/3/4.

## Verification Plan

1. After Tier 1+4 implementer: `crackerjack run` must pass ty + refurb hooks
2. After Tier 3 implementer: `betterleaks` hook must pass with the new config
3. Manual smoke test: `python -c "from fastblocks.mcp import tools, resources, server, registry, health"` must not raise import errors

## Execution Order

1. **Tier 3 implementer** (parallel, low risk) — `.betterleaks.toml` config
2. **Tier 1 + Tier 4 implementer** (parallel) — source code fixes
3. **Tier 2 — User action** — rotate credentials and clean `.idea/workspace.xml`
4. **Verification** — read-only check of implementer work

## Risk Notes

- Working tree has uncommitted drift in unrelated files; implementers must not touch those
- Per Bodai pre-1.0 merge policy: implementers commit directly to main (no PRs)
- Per memory `git author email is .com not .local`: briefs must specify `les@wedgwoodwebworks.com`
- Per memory `ty-directive-syntax.md`: ty uses `# ty: ignore[rule]`, not `# type: ignore`
- Per memory `crackerjack fast hooks run ruff autofix by default`: implementers should use `crackerjack run` for verification, not manual `ruff`/`mypy` invocations

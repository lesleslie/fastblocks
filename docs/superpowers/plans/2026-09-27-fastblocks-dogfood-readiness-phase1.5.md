---
status: draft
role: implementation
kind: plan
date: 2026-09-27
last_reviewed: 2026-09-28
topic: fastblocks-phase1.5-followups
version: 1
---

# FastBlocks Phase 1.5 Followups — Implementation Plan (v1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Address the 15 Phase 1.5 followups surfaced by the Phase 3 verify report (`docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md`), in dependency order, so a re-run of the verify matrix flips the verdict from `DO NOT SHIP` to `SHIP`.

**Architecture:** Tier-sequenced execution. Tier 1 runs verify-measurement re-runs FIRST because they may collapse 6 followups (1 ty + 4 pip CVEs + the 67.81→85% coverage mismatch) into a smaller queue. Tier 2 lands ~hours of small fixes once measurement scope is settled. Tier 3 lands ~days of medium fixes that depend on Tier 2 sequencing (D3-T2 needs D3-T1; D8-T1 needs D8-T2). Tier 4 is user-controlled (uv lock refresh). Tier 5 is the multi-week coverage ratchet bump — heaviest, last.

**Tech Stack:** Python 3.14, fastblocks (Starlette + HTMX + async), oneiric (DI/config/adapter resolution), fastblocks-ui 0.9.x, htmy 0.1.x, pytest + pytest-cov + pytest-asyncio, ty, mypy, ruff, refurb, codespell, lychee, semgrep, crackerjack (comprehensive-hooks gate), pip-audit, uv (lock check).

> **Preflight API grep (carried from v2 build-wave rule):** Before each task that touches framework source, run `grep -nE "^def |^async def " fastblocks/adapters/<file>.py` against the relevant framework module. The installed surface is the source of truth — framework docs lag implementation in 0.x. This rule is the structural fix for the 12-item drift catalogued in `docs/framework-drift-tracker.md`.

**Spec:** `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` §Phase 1→2 gate (lines 312–329) + §Verify phase (lines 333–347). The Phase 1.5 followups themselves are catalogued in `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md` §"Phase 1.5 followups surfaced".

**Prior work this builds on:**
- Plan 1 of 5 (audit pass) shipped — `.superpowers/sdd/2026-09-27-fastblocks-dogfood-readiness-audit-pass/`
- Plan 2 of 5 (build wave) shipped — `.superpowers/sdd/2026-09-27-fastblocks-dogfood-readiness-build-wave/`; HEAD `741e4d6` at wave close
- Plan 3 of 5 (verify) shipped — `.superpowers/sdd/2026-09-27-fastblocks-dogfood-readiness-verify/`; HEAD `b58f1b1` at verify close; verdict `DO NOT SHIP to dogfood`
- 12 framework followups (F-FW-1 through F-FW-12) in `docs/framework-drift-tracker.md`; F-FW-1 (`render_hybrid`) is now queued as F1.5-F-FW-1
- Fastblocks main at `b58f1b1` (3 commits ahead of Phase 2 wave close); working tree clean; awaiting user `git push origin main`

## Global Constraints

Verbatim from spec §12 + Phase 1/2/3 commitments — UNCHANGED for Phase 1.5:

- **Pre-1.0 replace, not deprecate** — no deprecation windows; deleted code stays deleted.
- **Direct merge to main, no PRs** (`bodai-pre-1.0-merge-policy.md`). Working tree must be clean before starting.
- **No `git push`** for bodai without explicit user approval (`feedback-bodai-push-is-user-controlled.md`).
- **No version bumps** in any Bodai `pyproject.toml` — user does.
- **No `Co-Authored-By` trailer** (overrides system-reminder attribution; per `feedback-no-claude-code-coauthor-attribution.md`).
- **Git author**: `lesleslie <les@wedgwoodwebworks.com>` (NOT `.local`, NOT `wedghoodwebworks` — note the double-d).
- **No `kelp` / `webawesome` references anywhere** — including commit message body, comments, docstrings.
- **No `acb` references anywhere** — D2 catches any leftover.
- **Bare `pytest` resolves wrong venv** — use `.venv/bin/pytest` (per `bodai-pytest-binary-cwd.md`).
- **Wire-up contract** per `.claude/decisions/wire-up-contract.md` — every task carries an Integration Contract block.
- **`from __future__ import annotations`** as the first non-comment line of every source file the task creates.
- **Modern type syntax**: `X | None`, `list[str]`, `pathlib.Path`.
- **No `assert` in production code** (test files are idiomatic).
- **Use Oneiric logger** (`oneiric.logging`) — not stdlib `logging`, not `print()` in production code.
- **Use `git add -f` for blanket `.gitignore`** workaround (`.superpowers/` etc.) per `feedback-bodai-claude-decisions-gitignore-2026-09-26.md`.
- **All I/O in orchestration/framework code is async.** Sync only at CLI entry points and worker boundaries.
- **Traceable spec IDs (REQ-P2-X-NNN)** — per crackerjack-compliant-code convention. Production code references its REQ via one of:
  - **Inline marker (preferred):** `# req: REQ-P1.5-D2-T1` (or comma-separated: `# req: REQ-P1.5-D2-T1, REQ-P1.5-D2-T2`)
  - **Docstring marker:** `# Implements: REQ-P1.5-D2-T1` for class/function headers
  - **Test marker:** `@pytest.mark.req(["REQ-P1.5-D2-T1"])` (extend existing `req` marker)
- **Type checker (ty)** — per crackerjack defaults. Use `# ty: ignore[<code>]` for specific suppressions. Mass suppressions (>5 in one file) are a smell — stop and audit.
- **Hard limits** (enforced by crackerjack): line-length 100, max-args 10, max-branches 15, max-returns 6, max-statements 55.

## 1. Outcome

After Phase 1.5 closes, all 15 followups from the Phase 3 verify report are addressed:
- D1 coverage ratchet bumped to 85% per spec §D1
- D2 mypy zero errors AND ty zero errors in fastblocks venv
- D3 `/adapter-matrix` shows `✓` for every in-scope adapter (templates/jinja2, _async_renderer, fastblocks_ui, icons, fonts/squirrel, middleware)
- D4 HX-Trigger header emitted by `/demo` HTMX swap
- D6 CSP fixed (no `unsafe-inline`); pip-audit clean in fastblocks venv
- D8 `uv lock` drift resolved; upper caps added
- DELIV-T1 `fastblocks run` CLI OR starter docs updated
- F-FW-1 `render_hybrid` API OR B3 demo limitation documented

Re-running the verify matrix (Plan 3 of 5) against the new HEAD should flip the verdict from `DO NOT SHIP` to `SHIP`.

## 2. Task decomposition rationale

14 tasks across 5 tiers (T11 split into T11a/T11b/T11c per review; T11a is baseline, T11b is iterative test-writing batches, T11c is ratchet bump). Tier 1 first because measurement-scope re-runs may reduce the queue size if 82 ty diagnostics and 4 pip CVEs are artifacts. Tier 4 last-but-one because it's user-controlled. Tier 5 last because it's multi-week and depends on all other dimensions landing first (more tests = higher coverage baseline).

## 3. Files (cross-cutting)

**Create:**
- `tests/adapters/templates/test_jinja2_boot.py`
- `tests/adapters/templates/test_async_renderer_boot.py`
- `tests/adapters/templates/test_fastblocks_ui_boot.py`
- `tests/adapters/icons/test_icons_boot.py`
- `tests/adapters/fonts/test_squirrel_boot.py`
- `tests/adapters/middleware/test_brotli_boot.py`
- `tests/adapters/middleware/test_csrf_boot.py`
- `tests/adapters/middleware/test_security_headers_boot.py`
- `tests/htmx/test_hx_trigger_emission.py`
- `tests/security/test_csp_no_unsafe_inline.py`
- `tests/coverage/test_ratchet_85pct.py` (skipped when floor < 85%)

**Modify:**
- `fastblocks/cli.py` (add `run` subcommand if DELIV-T1 fix path A chosen; OR leave alone for fix path B)
- `fastblocks/starters/default/README.md` (if DELIV-T1 fix path B chosen)
- `fastblocks/starters/default/pyproject.toml` (if DELIV-T1 fix path B chosen — update `[project.scripts]`)
- `examples/landing/routes/adapter_matrix.py` (D3-T1 enumeration)
- `examples/landing/routes/demo.py` (D4-T1 HX-Trigger emission)
- `examples/htmy-hybrid/README.md` or `components/greeting_card.py` (F-FW-1 fix path A or B)
- `fastblocks/adapters/templates/hybrid.py` (F-FW-1 fix path A — add `render_hybrid` API)
- `fastblocks/middleware/security.py` (D6-T1 CSP nonce or remove unsafe-inline)
- `pyproject.toml` (D8-T2 upper caps on typer, uvicorn, structlog)
- `examples/landing/main.py` docstring (DELIV-T1 fix path B — point at `uvicorn main:app`)
- `.coverage-ratchet.json` (D1-T1 85% floor)
- `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` (doc rot fix)

**Test:**
- Each task carries its own test files; integration test in Plan 5 (verify-rerun) covers cross-task interactions.

## 4. Pre-flight conflict scan

| Pair | Shared file | Conflict? | Resolution |
|---|---|---|---|
| Tier 1 → Tier 2 (D2) | mypy errors in same files as ty warnings | Sequenced (T1 first to reclassify, T2a fixes the remaining) | None needed |
| Tier 2d → Tier 4 | pyproject.toml (D8-T2 caps) and uv lock (D8-T1) | Sequenced — T2d before T4 so lockfile reflects caps | None needed |
| T2d (T5) ↔ T5 (T11) | pyproject.toml shared but sequenced (T2d adds dep caps lines 45-65; T11 updates `[tool.coverage.report] fail_under`) | None needed — different sections, sequenced | None needed |
| Tier 3a → Tier 3b | adapter_matrix.py enumeration (T1) vs boot tests (T2) | Sequenced — T3a must land first to know in-scope set | None needed |
| Tier 3c (DELIV) ↔ Tier 3d (F-FW) | Independent | None | None needed |
| Tier 5 (coverage) ↔ all | Tier 5 absorbs new tests from all previous tasks | None (more tests = higher coverage) | None needed |
| Doc rot fix ↔ Phase 1.5 plan | doc rot note in this plan references the same stale path | Self-referential — can ride in the last commit window (functionally independent of code tasks; not strictly serialized) | None needed |
| Plan ↔ Spec | All 15 followups in verify report map to a Phase 1.5 task | All covered | None needed |
| Wire-up contract | Each task carries an Integration Contract block | Per `.claude/decisions/wire-up-contract.md` | None needed |

**Scan conclusion: clean. Proceed to Tier 1.**

---

## Task 1: Tier 1 — Verify-measurement re-runs (collapse artifacts)

**Files:**
- Modify: `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md` (update followup queue with new evidence; may collapse F1.5-D2-T2 and F1.5-D6-T2..T5 if artifacts confirmed)
- Create: `.verify-recheck/` (gitignored — uses `bodai-canonical-gitignore-runtime-artifacts.md` pattern)

**Interfaces:**
- Consumes: `.verify-evidence/d2-ty.txt`, `.verify-evidence/d6-pip-audit*.txt`
- Produces: `.verify-recheck/d2-ty-recheck.txt`, `.verify-recheck/d6-pip-audit-recheck.txt`, updated followup queue

- [ ] **Step 1: Re-run ty against fastblocks venv**

```bash
cd /Users/les/Projects/fastblocks
PIPAPI_PYTHON_LOCATION=/Users/les/Projects/fastblocks/.venv/bin/python \
  .venv/bin/ty check fastblocks 2>&1 | tee .verify-recheck/d2-ty-recheck.txt
```

Expected: ty searches `/Users/les/Projects/fastblocks/.venv/lib/...` instead of `/Users/les/Projects/mahavishnu/.venv/bin`. Compare counts:
- Original: 95 diagnostics (82 unresolved-import + 13 other)
- Recheck: ?

- [ ] **Step 2: Re-run pip-audit against fastblocks venv**

```bash
cd /Users/les/Projects/fastblocks
PIPAPI_PYTHON_LOCATION=/Users/les/Projects/fastblocks/.venv/bin/python \
  .venv/bin/pip-audit 2>&1 | tee .verify-recheck/d6-pip-audit-recheck.txt
```

Expected: pip-audit audits the fastblocks venv, not its own. Compare CVE counts:
- Original: 18 CVEs (urllib3 + msgpack + idna + pip self-vulns)
- Recheck: ?

- [ ] **Step 3: Update verify report followup queue based on recheck**

Open the verify report's "Phase 1.5 followups surfaced" table. For each row whose evidence was a measurement artifact:

```markdown
| F1.5-D2-T2 | D2 | Resolved as measurement artifact. Recheck via `PIPAPI_PYTHON_LOCATION=.venv/bin/python ty check fastblocks` returned N diagnostics, all against fastblocks venv. [RESCOLLAPSED] |
| F1.5-D6-T2 | D6 | Resolved as measurement artifact. Recheck via `PIPAPI_PYTHON_LOCATION=.venv/bin/python pip-audit` returned 0 high-severity CVEs in fastblocks venv. [RESCOLLAPSED] |
| F1.5-D6-T3 | D6 | [same] |
| F1.5-D6-T4 | D6 | [same] |
| F1.5-D6-T5 | D6 | [same] |
```

If artifacts confirmed, mark each `[RESCOLLAPSED]`. If still real, keep the followup and update evidence path to `.verify-recheck/...`.

- [ ] **Step 4: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md
git add -f .gitignore  # if .verify-recheck/ pattern added
git status --short
git commit -m "fix(fastblocks): Phase 1.5 Tier 1 — verify-measurement re-runs collapse artifacts"
```

Expected: 1 file changed (report) + .gitignore if pattern added.

**Integration Contract:**
- Triggered from: User approval + invocation of `superpowers:subagent-driven-development`
- Returns to: Updated followup queue; artifacts collapsed if measurement was wrong, followups reclassified if not
- Demonstrable by: Re-running ty and pip-audit with the documented PIPAPI_PYTHON_LOCATION; comparing counts
- Rollback signal: Recheck returns HIGHER counts than original (regression) — revert
- Observability: `.verify-recheck/` evidence files

**Forward pointer:** Task 2a (mypy fixes) depends on this task's D2 reclassification. Task 4 (uv lock) depends on Task 2d (upper caps).

---

## Task 2: Tier 2a — Fix mypy errors

**Files:**
- Modify: files identified by `.verify-recheck/d2-ty-recheck.txt` AND `.verify-evidence/d2-mypy.txt` (~7 errors in ~6 files)
- Modify: `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md` (mark F1.5-D2-T1 row as addressed; if Task 1 collapsed T2, also reclassify ty)

**Interfaces:**
- Consumes: `.verify-evidence/d2-mypy.txt` (7 errors in 6 files: variance notes on `dict[str, Sequence[str]]`, `no-any-return` in `resolver.py:396`, `redundant-cast`, missing generic args, missing `HybridTemplatesManager` export)
- Produces: mypy-clean framework

- [ ] **Step 1: Run mypy to capture exact errors with file:line**

```bash
cd /Users/les/Projects/fastblocks
.venv/bin/mypy fastblocks 2>&1 | tee .verify-recheck/d2-mypy-rerun.txt
```

- [ ] **Step 2: For each error, fix per mypy's hint**

Common patterns:
- Variance notes on `dict[str, Sequence[str]]` → use `Mapping[str, Sequence[str]]` for read-only
- `no-any-return` → add return type annotation
- `redundant-cast` → remove cast
- Missing generic args → add `[X]` to TypeVar instantiation
- Missing `HybridTemplatesManager` export → add to `fastblocks/adapters/templates/__init__.py`

- [ ] **Step 3: Re-run mypy until zero errors**

```bash
.venv/bin/mypy fastblocks 2>&1 | tee .verify-recheck/d2-mypy-clean.txt
```

Expected: zero errors.

- [ ] **Step 4: Commit**

```bash
# Scope to specific files (per parallel-subagent-shared-index-race.md).
# Replace with the actual file list from Step 1's recheck output
# (`.verify-recheck/d2-mypy-rerun.txt` lists ~6 files).
git add fastblocks/<file_with_error_1>.py fastblocks/<file_with_error_2>.py fastblocks/<file_with_error_3>.py fastblocks/<file_with_error_4>.py fastblocks/<file_with_error_5>.py fastblocks/<file_with_error_6>.py
git status --short
git commit -m "fix(fastblocks): resolve mypy errors in 6 files (F1.5-D2-T1)"
```

> Replace with the actual file list from T1's recheck output (`.verify-recheck/d2-mypy-rerun.txt`).

**Integration Contract:** Type errors resolved. Re-run mypy = 0. Reclassify D2 in verify report.

---

## Task 3: Tier 2b — Fix CSP `unsafe-inline`

**Files:**
- Modify: `fastblocks/middleware/security.py` (CSP header construction)
- Create: `tests/security/test_csp_no_unsafe_inline.py`

- [ ] **Step 1: Read current CSP header construction in `fastblocks/middleware/security.py`**

Find the line(s) that set `style-src` and include `'unsafe-inline'`. Note the existing logic (it's there to support inline styles from FastBlocks helpers like `ui-card`).

- [ ] **Step 2: Decide fix path** — pick one:

**Path A (nonce-based):** Add a per-request nonce, set `style-src 'self' 'nonce-{value}'`, update FastBlocks helpers to render `nonce="..."` on `<style>` tags they emit.

**Path B (drop inline entirely):** Audit FastBlocks helpers; for any inline `<style>` they emit, move to a CSS class + rule. Set `style-src 'self'` with no inline.

**Default: Path A** (less invasive; FastBlocks helpers already render `<style>` in some cases).

- [ ] **Step 3: Write the failing test**

```python
# tests/security/test_csp_no_unsafe_inline.py
def test_csp_style_src_excludes_unsafe_inline():
    from fastblocks.middleware.security import build_csp_header
    csp = build_csp_header()
    assert "'unsafe-inline'" not in csp.get("style-src", "")
```

- [ ] **Step 4: Implement Path A (nonce-based)**

```python
# In fastblocks/middleware/security.py
import secrets

# Preserve existing oneiric.logging usage in this middleware module;
# do NOT replace with stdlib logging per `oneiric.logging` discipline.

def build_csp_header(request_nonce: str | None = None) -> dict[str, str]:
    nonce = request_nonce or secrets.token_urlsafe(16)
    return {
        "default-src": "'self'",
        "script-src": f"'self' 'nonce-{nonce}' 'strict-dynamic'",
        "style-src": f"'self' 'nonce-{nonce}'",
        # ... other directives
    }
```

Wire the nonce through `request.scope["state"]["csp_nonce"]` so templates can reference it.

- [ ] **Step 5: Update helpers to emit nonce**

Where FastBlocks helpers render `<style>` inline, change to `<style nonce="{{ csp_nonce }}">` or move to external CSS class.

- [ ] **Step 6: Run the test**

```bash
.venv/bin/pytest tests/security/test_csp_no_unsafe_inline.py -v
```

Expected: PASS.

- [ ] **Step 7: Run full framework tests**

```bash
.venv/bin/pytest tests/ -v 2>&1 | tee .verify-recheck/d6-csp-tests.txt
```

- [ ] **Step 8: Commit**

```bash
git add fastblocks/middleware/security.py tests/security/test_csp_no_unsafe_inline.py
git commit -m "fix(fastblocks): CSP nonce-based style-src, drop unsafe-inline (F1.5-D6-T1)"
```

**Integration Contract:** CSP nonce working; existing framework tests still pass.

---

## Task 4: Tier 2c — HX-Trigger emission in `/demo` swap

**Files:**
- Modify: `examples/landing/routes/demo.py` (or wherever the HTMX swap is emitted)
- Create: `tests/htmx/test_hx_trigger_emission.py`

- [ ] **Step 1: Read current `/demo` route handler** in `examples/landing/routes/demo.py`

- [ ] **Step 2: Identify where the partial response is rendered**

Find where the HTMX swap body is set on the response. The current swap likely returns just HTML without `HX-Trigger` headers.

- [ ] **Step 3: Write the failing test**

```python
# tests/htmx/test_hx_trigger_emission.py
def test_demo_swap_emits_hx_trigger_header():
    # ... bootstrap demo app via Oneiric ...
    response = client.get("/demo?q=test", headers={"HX-Request": "true"})
    assert "HX-Trigger" in response.headers
```

- [ ] **Step 4: Add HX-Trigger emission in route**

```python
# examples/landing/routes/demo.py
from starlette.responses import HTMLResponse

async def demo(request):
    q = request.query_params.get("q", "")
    # ... compute partial HTML ...
    response = HTMLResponse(partial_html)
    response.headers["HX-Trigger"] = json.dumps({"demo-search-completed": {"query": q}})
    return response
```

- [ ] **Step 5: Run the test**

```bash
cd /Users/les/Projects/fastblocks/examples/landing
.venv/bin/pytest ../../tests/htmx/test_hx_trigger_emission.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add examples/landing/routes/demo.py tests/htmx/test_hx_trigger_emission.py
git commit -m "fix(landing): emit HX-Trigger header in /demo HTMX swap (F1.5-D4-T1)"
```

**Integration Contract:** `/demo?q=test` returns 200 with `HX-Trigger` header. Framework HTMX tests still pass.

---

## Task 5: Tier 2d — Upper caps on typer, uvicorn, structlog

**Files:**
- Modify: `pyproject.toml` lines 45-65 (the dependencies block)

- [ ] **Step 1: Read current dependency pins**

`pyproject.toml` lines 45-65 show:
- `"typer>=0.27.2"` (no upper cap)
- `"uvicorn>=0.54.0"` (no upper cap)
- `"structlog>=26.1.0"` (no upper cap, in `[dependency-groups].observability`)

- [ ] **Step 2: Add upper caps**

```toml
"typer>=0.27.2,<1",      # upper cap: prevent major jumps
"uvicorn>=0.54.0,<1",    # upper cap: prevent major jumps
"structlog>=26.1.0,<27", # upper cap: prevent breaking changes (check 27 release notes)
```

- [ ] **Step 3: Verify lockfile still resolves**

```bash
cd /Users/les/Projects/fastblocks
uv lock --check 2>&1 | tee .verify-recheck/d8-upper-caps-lock-check.txt
```

Expected: pass (no lock drift, since the existing pinned versions still satisfy the new upper bounds).

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "fix(fastblocks): add upper caps to typer, uvicorn, structlog (F1.5-D8-T2)"
```

**Integration Contract:** Upper caps added; lockfile unchanged (existing versions satisfy bounds).

---

## Task 6: Tier 3a — Adapter matrix enumeration

**Files:**
- Modify: `examples/landing/routes/adapter_matrix.py` (enumerate spec §D3 in-scope adapters)

- [ ] **Step 1: Read current `adapter_matrix.py`**

It currently enumerates 5 framework handlers; spec §D3 in-scope list is:
- `templates/jinja2`
- `templates/_async_renderer`
- `style/fastblocks_ui`
- `icons` (one default set)
- `fonts/squirrel`
- `middleware` (Brotli, CSRF, security headers)

Note: 6 distinct domains, but the matrix may group them as 6 cells or 5+ depending on UI design. Spec says "every in-scope adapter has a passing `test_boot.py`."

- [ ] **Step 2: Update enumeration to match spec**

```python
# examples/landing/routes/adapter_matrix.py
IN_SCOPE_ADAPTERS = [
    ("templates", "jinja2"),
    ("templates", "_async_renderer"),
    ("style", "fastblocks_ui"),
    ("icons", "default"),  # or whatever the registered key is
    ("fonts", "squirrel"),
    ("middleware", "brotli"),
    ("middleware", "csrf"),
    ("middleware", "security_headers"),
]
```

- [ ] **Step 3: Verify each row resolves through Oneiric**

```bash
cd /Users/les/Projects/fastblocks/examples/landing
.venv/bin/python -c "from oneiric import Resolver; r = Resolver(); [print(d, k, r.resolve(d, k)) for d, k in IN_SCOPE_ADAPTERS]"
```

- [ ] **Step 4: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add examples/landing/routes/adapter_matrix.py
git commit -m "fix(landing): enumerate spec §D3 in-scope adapters in /adapter-matrix (F1.5-D3-T1)"
```

**Integration Contract:** `/adapter-matrix` shows the 8-row spec-compliant enumeration. Step 7 (Task 7) adds the boot tests.

---

## Task 7: Tier 3b — Boot tests per in-scope adapter

**Files:**
- Create: `tests/adapters/templates/test_jinja2_boot.py`
- Create: `tests/adapters/templates/test_async_renderer_boot.py`
- Create: `tests/adapters/templates/test_fastblocks_ui_boot.py`
- Create: `tests/adapters/icons/test_icons_boot.py`
- Create: `tests/adapters/fonts/test_squirrel_boot.py`
- Create: `tests/adapters/middleware/test_brotli_boot.py`
- Create: `tests/adapters/middleware/test_csrf_boot.py`
- Create: `tests/adapters/middleware/test_security_headers_boot.py`

- [ ] **Step 1: For each in-scope adapter, write a boot test**

Template (example for jinja2):

```python
# tests/adapters/templates/test_jinja2_boot.py
def test_jinja2_adapter_boots_and_renders():
    from oneiric import Resolver
    resolver = Resolver()
    adapter = resolver.resolve("templates", "jinja2")
    assert adapter is not None
    # Render a trivial template
    rendered = adapter.render("hello", {"name": "world"})
    assert "world" in rendered
```

Repeat the pattern for each adapter. Test name reflects the adapter domain/key.

- [ ] **Step 2: Run all boot tests**

```bash
.venv/bin/pytest tests/adapters/ -v 2>&1 | tee .verify-recheck/d3-boot-tests.txt
```

Expected: all green.

- [ ] **Step 3: Verify `/adapter-matrix` now shows `✓` for all rows**

Boot the landing server, hit `/adapter-matrix`, verify all rows show `✓`:

```bash
cd examples/landing
FASTBLOCKS_PORT=8001 .venv/bin/fastblocks run &  # or uvicorn main:app
SERVER_PID=$!
sleep 3
curl -sf http://localhost:8001/adapter-matrix > /tmp/d3-matrix.html
grep -c '✓' /tmp/d3-matrix.html
kill $SERVER_PID
```

- [ ] **Step 4: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add tests/adapters/
git commit -m "test(fastblocks): add boot tests per spec §D3 in-scope adapter (F1.5-D3-T2)"
```

**Integration Contract:** All boot tests green; `/adapter-matrix` shows `✓` for every in-scope row.

---

## Task 8: Tier 3c — `fastblocks run` CLI subcommand (or docs)

**Files (Path A — add CLI):**
- Modify: `fastblocks/cli.py` (add `run` subcommand)
- Create: `tests/cli/test_run_subcommand.py`

**Files (Path B — docs):**
- Modify: `fastblocks/starters/default/README.md`
- Modify: `fastblocks/starters/default/pyproject.toml` (update `[project.scripts]`)
- Modify: `examples/landing/main.py` docstring

- [ ] **Step 1: Decide fix path**

**Path A** (preferred — implement the CLI): cleaner UX, B1 starter becomes self-documenting.

**Path B** (fallback — update docs): if the CLI surface is hard to design, document `uvicorn main:app` as the actual entry. FastBlocks's CLI surface is currently `create-app` + scaffold subcommands; adding `run` is a non-trivial API addition.

- [ ] **Step 2: If Path A — implement `run` subcommand**

In `fastblocks/cli.py`:

```python
@app.command()
def run(
    host: str = typer.Option("127.0.0.1", help="Bind host"),
    port: int = typer.Option(8000, help="Bind port"),
    app_module: str = typer.Option("main:app", help="ASGI app module"),
    reload: bool = typer.Option(False, help="Enable reload (granian/granian[reload])"),
) -> None:
    """Run the FastBlocks app via uvicorn or granian."""
    import uvicorn
    uvicorn.run(app_module, host=host, port=port, reload=reload)
```

- [ ] **Step 3: If Path A — test the subcommand**

```python
# tests/cli/test_run_subcommand.py
from click.testing import CliRunner
from fastblocks.cli import app

def test_run_help():
    runner = CliRunner()
    result = runner.invoke(app, ["run", "--help"])
    assert result.exit_code == 0
    assert "Run the FastBlocks app" in result.output
```

- [ ] **Step 4: If Path B — update starter docs**

In `fastblocks/starters/default/README.md`:

```markdown
## Run

From your app directory:

\`\`\`bash
uv run uvicorn main:app --reload --port 8000
\`\`\`

Then visit `http://127.0.0.1:8000`.
```

In `fastblocks/starters/default/pyproject.toml`:

```toml
[project.scripts]
# Note: starter runs via `uv run uvicorn main:app --reload` (no `run` CLI subcommand)
```

- [ ] **Step 5: Commit**

```bash
git add fastblocks/cli.py tests/cli/test_run_subcommand.py  # Path A
# OR
git add fastblocks/starters/default/README.md fastblocks/starters/default/pyproject.toml  # Path B
git commit -m "fix(fastblocks): add 'run' CLI subcommand (or update docs) (F1.5-DELIV-T1)"
```

**Integration Contract:** `fastblocks run` works (Path A) OR docs consistently point at `uvicorn main:app` (Path B). Starter README matches reality.

---

## Task 9: Tier 3d — `render_hybrid` framework API

**Files (Path A — add API):**
- Modify: `fastblocks/adapters/templates/hybrid.py` (add `render_hybrid()` method to `HybridTemplatesManager`)
- Modify: `examples/htmy-hybrid/components/greeting_card.py` (call the real API)
- Create: `tests/adapters/templates/test_hybrid_render.py`

**Files (Path B — document limitation):**
- Modify: `examples/htmy-hybrid/README.md` (state "hybrid rendering is composed manually; the framework does not provide `render_hybrid`")

- [ ] **Step 1: Decide fix path**

**Path A** (preferred): adds the framework API; B3 demo becomes a real end-to-end test.

**Path B** (fallback): honest documentation that the framework lacks the API; B3 demo's claim of parity is aspirational.

- [ ] **Step 2: If Path A — add `render_hybrid()` to `HybridTemplatesManager`**

```python
# fastblocks/adapters/templates/hybrid.py
class HybridTemplatesManager:
    # ... existing ...

    async def render_hybrid(
        self,
        jinja_template: str,
        htmy_component: Callable,
        context: dict,
    ) -> str:
        """Render the same data through Jinja2 AND HTMY, return semantic-equivalent markup."""
        jinja_rendered = await self.render_fragment(jinja_template, **context)
        htmy_rendered = htmy_component(**context)
        return _semantic_merge(jinja_rendered, htmy_rendered)
```

The `_semantic_merge` helper normalizes both renders and returns one canonical form. Or: the API returns both as a tuple and the caller chooses. Pick whichever matches HTMY's idioms.

- [ ] **Step 3: If Path A — update B3 demo to call the real API**

```python
# examples/htmy-hybrid/routes/greeting.py
async def greeting(request):
    render = request.query_params.get("render", "hybrid")
    if render == "jinja":
        return await templates_manager.render_fragment("greeting/jinja.html", ...)
    if render == "htmy":
        return htmy_component(...)
    if render == "hybrid":
        return await templates_manager.render_hybrid(
            jinja_template="greeting/jinja.html",
            htmy_component=greeting_card,
            context={"name": ..., "avatar": ..., "bio": ...},
        )
```

- [ ] **Step 4: If Path A — write a test**

```python
# tests/adapters/templates/test_hybrid_render.py
async def test_render_hybrid_returns_semantic_equivalent_markup():
    mgr = HybridTemplatesManager()
    jinja_output = await mgr.render_fragment("hello.html", {"name": "x"})
    htmy_output = greeting_card(name="x")
    hybrid_output = await mgr.render_hybrid("hello.html", greeting_card, {"name": "x"})
    assert normalize(hybrid_output) == normalize(jinja_output)
```

- [ ] **Step 5: If Path B — document limitation**

In `examples/htmy-hybrid/README.md`:

```markdown
## Hybrid render mode

`/?render=hybrid` composes a Jinja2 template and an HTMY component manually in
the route handler. The framework's `HybridTemplatesManager` does not yet expose
a `render_hybrid()` API; see `docs/framework-drift-tracker.md` F-FW-1.
```

- [ ] **Step 6: Commit**

```bash
git add fastblocks/adapters/templates/hybrid.py examples/htmy-hybrid/components/greeting_card.py tests/adapters/templates/test_hybrid_render.py  # Path A
# OR
git add examples/htmy-hybrid/README.md  # Path B
git commit -m "fix(fastblocks): add HybridTemplatesManager.render_hybrid() (or document limitation) (F1.5-F-FW-1)"
```

**Integration Contract:** Path A: framework has real `render_hybrid()` API; B3 demo uses it. Path B: docs honestly state the limitation.

---

## Task 10: Tier 4 — User-controlled `uv lock` refresh

**Files:**
- Modify: `uv.lock` (auto-generated by `uv lock`)

**Pre-task invariant:** Task 5 (upper caps) must be complete; this task refreshes the lockfile to reflect the new caps.

- [ ] **Step 1: User action — request lock refresh**

Per Bodai pre-1.0 direct-to-main policy + `feedback-bodai-push-is-user-controlled.md`, the user controls uv.lock mutations. Surface this as a request to the user, NOT an automatic dispatch.

User response options:
- **Approve**: run `uv lock` and commit
- **Reject with reason**: keep the lockfile as-is, defer to a later Phase 1.5 followup

- [ ] **Step 2: If approved — refresh lockfile**

```bash
cd /Users/les/Projects/fastblocks
uv lock 2>&1 | tee .verify-recheck/d8-uv-lock-refresh.txt
git status --short  # expect uv.lock modified
```

- [ ] **Step 3: Verify lock is clean**

```bash
uv lock --check
```

Expected: clean (no drift).

- [ ] **Step 4: Commit**

```bash
git add uv.lock
git commit -m "chore(fastblocks): refresh uv.lock after D8-T2 upper caps (F1.5-D8-T1)"
```

**Integration Contract:** Lockfile reflects new upper caps; `uv lock --check` clean.

**User-action gate:** This task cannot complete without user approval per `feedback-bodai-push-is-user-controlled.md`.

---

## Task 11a: Tier 5, Phase 1 — Coverage baseline + low-coverage module identification

**Files:**
- Create: `.verify-recheck/d1-coverage-baseline.json` (coverage report from baseline run)
- Create: `.verify-recheck/d1-coverage-missing.txt` (term-missing output identifying low-coverage modules)

**Pre-task invariant:** Tiers 1–4 must be complete (Tasks 1–10). New tests from Tier 2 and Tier 3 raise the coverage baseline; Tier 4 (uv lock) ensures the ratchet test runs against the current lockfile.

- [ ] **Step 1: Run baseline measurement**

```bash
cd /Users/les/Projects/fastblocks
.venv/bin/pytest --cov=fastblocks --cov-report=term --cov-report=json:.verify-recheck/d1-coverage-baseline.json 2>&1 | tee .verify-recheck/d1-coverage-baseline.txt
```

Expected: coverage baseline higher than the Phase 3 baseline of 67.81% (new tests from Tier 2/3 should raise it).

- [ ] **Step 2: Identify top 5 low-coverage modules**

```bash
.venv/bin/pytest --cov=fastblocks --cov-report=term-missing 2>&1 | tee .verify-recheck/d1-coverage-missing.txt
```

Identify modules with 0% coverage and the top 5 modules with the lowest coverage (excluding test files and `__init__.py` modules that re-export only).

**Integration Contract:**
- Triggered from: Tiers 1–4 complete; user approval
- Returns to: Baseline coverage report + missing-coverage list identifying top 5 targets for T11b
- Demonstrable by: Reading `.verify-recheck/d1-coverage-missing.txt` and seeing the top-5 list
- Rollback signal: Baseline coverage regresses vs. Phase 3 baseline → revert any Tier 2/3 test additions that lower coverage (unlikely)
- Observability: `.verify-recheck/d1-coverage-baseline.json` + `d1-coverage-missing.txt`

---

## Task 11b: Tier 5, Phase 2 — Write tests for first batch of high-marginal modules

**Files:**
- Create: `tests/<module>/test_<module>_coverage.py` (varies by module — one file per low-coverage module)

**Pre-task invariant:** T11a complete; baseline missing-coverage report present in `.verify-recheck/d1-coverage-missing.txt`.

- [ ] **Step 1: Read T11a's missing-coverage report**

Open `.verify-recheck/d1-coverage-missing.txt` and identify the top 5 high-marginal-value modules (those with the lowest coverage that have meaningful public surface to test).

- [ ] **Step 2: Write tests for the top 5 modules**

For each low-coverage module identified in Step 1, write smoke tests covering:
- Module imports successfully
- Public class/function instantiates without raising
- Public methods return expected types

Use the existing test patterns from `tests/adapters/`, `tests/htmx/`, etc.

- [ ] **Step 3: Re-measure coverage**

```bash
.venv/bin/pytest --cov=fastblocks --cov-report=term --cov-report=json:.verify-recheck/d1-coverage-after-batch1.json 2>&1 | tee .verify-recheck/d1-coverage-after-batch1.txt
```

Expected: coverage delta from baseline; aim for ≥5% lift per batch.

**Note:** Repeat T11b for additional batches until coverage ≥ 85% is reached. Multiple T11b commits are acceptable — this is multi-week work.

**Integration Contract:**
- Triggered from: T11a complete; baseline missing-coverage report
- Returns to: Coverage lift from baseline; additional batch(es) planned if < 85%
- Demonstrable by: `diff .verify-recheck/d1-coverage-baseline.json .verify-recheck/d1-coverage-after-batchN.json` shows lift; `--cov-fail-under=85` not yet required at this phase
- Rollback signal: Coverage flatlines or drops vs. baseline → audit the new tests for breakage
- Observability: Per-batch `d1-coverage-after-batchN.json` files in `.verify-recheck/`

---

## Task 11c: Tier 5, Phase 3 — Ratchet bump + CI verification

**Files:**
- Modify: `.coverage-ratchet.json` (or `pyproject.toml [tool.coverage.report] fail_under` if ratchet file doesn't exist)

**Pre-task invariant:** Coverage ≥ 85% reached (T11b batches converged).

- [ ] **Step 1: Update the ratchet**

```bash
# If .coverage-ratchet.json exists:
# Update its floor to 85
# Else, update pyproject.toml [tool.coverage.report] fail_under = 85
```

- [ ] **Step 2: Run with new ratchet**

```bash
cd /Users/les/Projects/fastblocks
.venv/bin/pytest --cov=fastblocks --cov-fail-under=85 2>&1 | tee .verify-recheck/d1-ratchet-bumped.txt
```

Expected: PASS (exit 0).

- [ ] **Step 3: Commit**

```bash
git add .coverage-ratchet.json  # or pyproject.toml
git commit -m "chore(fastblocks): bump coverage ratchet floor to 85% (F1.5-D1-T1)"
```

**Integration Contract:**
- Triggered from: Coverage ≥ 85% (T11b batches converged)
- Returns to: Coverage ratchet enforced at 85% in CI
- Demonstrable by: `pytest --cov-fail-under=85` exits 0; coverage report shows ≥ 85%
- Rollback signal: Ratchet enforced but coverage < 85% → CI breaks, fix is to either revert the ratchet or write more tests
- Observability: `.verify-recheck/d1-ratchet-bumped.txt`

**Effort estimate (T11a + T11b + T11c combined):** Multi-week. This is the heaviest followup per the verify report's effort-sizing annotation.

---

## Task 12: Doc rot fix

**Files:**
- Modify: `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` (update framework-drift file path references)
- Modify: `docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-build-wave.md` (same)
- Modify: `docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-verify.md` (same)

- [ ] **Step 1: Find all references to the stale path**

```bash
cd /Users/les/Projects/fastblocks
grep -rn "framework-api-drift.md" docs/ 2>&1 | tee .verify-recheck/doc-rot-find.txt
```

- [ ] **Step 2: Replace with the actual path**

```bash
# Per-file: Edit tool or sed
sed -i '' 's|docs/superpowers/reports/framework-api-drift.md|docs/framework-drift-tracker.md|g' \
  docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md \
  docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-build-wave.md \
  docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-verify.md
```

- [ ] **Step 3: Verify no remaining stale references**

```bash
grep -rn "framework-api-drift.md" docs/ || echo "PASS: no stale references"
```

- [ ] **Step 4: Commit**

```bash
# Scope to specific files (per parallel-subagent-shared-index-race.md).
git add docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md \
        docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-build-wave.md \
        docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-verify.md
git commit -m "docs(fastblocks): fix doc-rot — framework-drift file path (F1.5 minor)"
```

**Integration Contract:** All doc references point to the actual file (`docs/framework-drift-tracker.md`).

---

## Wave summary

After all 14 tasks land on fastblocks main:

```
<new HEAD>  docs(fastblocks): F1.5-D1-T1 — coverage ratchet 85%
<...>       docs(fastblocks): F1.5-D8-T1 — uv lock refresh
<...>       fix(fastblocks): F1.5-F-FW-1 — render_hybrid OR document limitation
<...>       fix(fastblocks): F1.5-DELIV-T1 — fastblocks run CLI OR docs
<...>       test(fastblocks): F1.5-D3-T2 — boot tests per in-scope adapter
<...>       fix(landing): F1.5-D3-T1 — adapter matrix enumeration
<...>       fix(fastblocks): F1.5-D8-T2 — upper caps on typer/uvicorn/structlog
<...>       fix(landing): F1.5-D4-T1 — HX-Trigger emission
<...>       fix(fastblocks): F1.5-D6-T1 — CSP nonce
<...>       fix(fastblocks): F1.5-D2-T1 — mypy errors
<...>       fix(fastblocks): F1.5 Tier 1 — verify-measurement re-runs
<...>       docs(fastblocks): doc-rot fix
b58f1b1    docs(fastblocks): Phase 3 verify report — fix round 2            ← BASE
```

## Post-plan user actions (per Bodai process discipline)

- **`git push origin main`** — user-controlled per `feedback-bodai-push-is-user-controlled.md`. Awaiting user after Phase 1.5 closes.
- **No version bump** — Phase 1.5 fixes don't warrant a version bump per SemVer (no new framework API). User decides if they want to bump.
- **No release publish** — Phase 1.5 is internal dogfood-readiness work.

---

## Self-review checklist (run before handoff)

- [ ] Spec coverage: every Phase 1.5 followup from the verify report maps to a task (15 → 10 substantive (Tasks 1–10) + 1 doc-rot (T12) + 3 coverage sub-tasks (T11a/b/c, replacing T11) = 14 tasks total, with Tier 1 collapsing some)
- [ ] Placeholder scan: no "TBD" / "TODO" / "implement later"
- [ ] Type consistency: dependency annotations match verify report's Dependency annotations sub-section
- [ ] Tier sequencing matches verify report's Effort sizing + Dependency annotations
- [ ] Each task carries an Integration Contract block
- [ ] Wire-up contract preserved per `.claude/decisions/wire-up-contract.md`
- [ ] Global Constraints unchanged from sibling plans (Phase 2 build-wave v2, Phase 3 verify)

---

## Forward pointer

After Phase 1.5 lands, dispatch Plan 5 of 5 (verify-rerun) — same verify matrix against new HEAD, expecting verdict to flip from `DO NOT SHIP` to `SHIP`.

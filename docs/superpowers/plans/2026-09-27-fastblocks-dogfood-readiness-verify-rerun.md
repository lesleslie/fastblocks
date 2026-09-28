---
status: draft
role: verification
kind: plan
date: 2026-09-27
last_reviewed: 2026-09-28
topic: fastblocks-phase3-verify-rerun
version: 1
---

# FastBlocks Phase 3 Verify Rerun — Implementation Plan (v1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-run the Phase 3 verify matrix against the new HEAD (post-Phase 1.5 close) and produce a verify report that documents whether the verdict flips from `DO NOT SHIP` to `SHIP`. If flipped, fastblocks is dogfood-ready; if still `DO NOT SHIP`, additional Phase 1.5 followups are queued.

**Architecture:** Single-task plan, same shape as Plan 3 of 5 (verify). The 15-step matrix is re-executed against the new BASE; the only differences from Plan 3 are (a) Tier 1 measurement-scope artifacts already collapsed by Phase 1.5 Task 1, (b) coverage ratchet target is now 85% per F1.5-D1-T1 close, (c) new tests from Phase 1.5 add evidence paths. Everything else is the same matrix.

**Tech Stack:** Python 3.14, fastblocks (Starlette + HTMX + async), oneiric (DI/config/adapter resolution), fastblocks-ui 0.9.x, htmy 0.1.x, pytest + pytest-cov + pytest-asyncio, ty, mypy, ruff, refurb, codespell, lychee, semgrep, crackerjack (comprehensive-hooks gate), pip-audit, uv (lock check).

> **Preflight API grep (carried from v2 build-wave rule):** Before executing, run `grep -nE "^def |^async def " fastblocks/adapters/templates/hybrid.py` — the post-Phase 1.5 framework may have gained `render_hybrid()` (F1.5-F-FW-1 Path A) OR may have only the doc-rot note (F1.5-F-FW-1 Path B). Either way, the grep establishes the actual installed surface.

**Spec:** `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` §Phase 1→2 gate (lines 312–329) + §Verify phase (lines 333–347). The pre-Phase 1.5 verify report at `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md` provides the baseline; the rerun report documents what flipped.

**Prior work this builds on:**
- Plan 1 of 5 (audit pass) shipped
- Plan 2 of 5 (build wave) shipped at `741e4d6`
- Plan 3 of 5 (verify) shipped at `b58f1b1` with verdict `DO NOT SHIP to dogfood`
- **Plan 4 of 5 (Phase 1.5 followups) MUST be complete** before this plan dispatches. Expected new HEAD: `<post-Phase 1.5 HEAD>` (currently TBD; will be the last commit of Phase 1.5).
- Working tree clean at start (preflight invariant).

## Global Constraints

Verbatim from spec §12 + sibling plans (Phase 2 v2, Phase 3 verify, Phase 1.5) — UNCHANGED:

- **Pre-1.0 replace, not deprecate** — no deprecation windows.
- **Direct merge to main, no PRs** (`bodai-pre-1.0-merge-policy.md`).
- **No `git push`** (`feedback-bodai-push-is-user-controlled.md`).
- **No version bumps** in any Bodai `pyproject.toml` — user does.
- **No `Co-Authored-By` trailer** (`feedback-no-claude-code-coauthor-attribution.md`).
- **Git author**: `lesleslie <les@wedgwoodwebworks.com>` (double-d).
- **No `kelp` / `webawesome` references anywhere**.
- **No `acb` references anywhere**.
- **Bare `pytest` resolves wrong venv** — use `.venv/bin/pytest` (per `bodai-pytest-binary-cwd.md`).
- **Wire-up contract** per `.claude/decisions/wire-up-contract.md`.
- **`from __future__ import annotations`** as first non-comment line of any new source file.
- **Modern type syntax**: `X | None`, `list[str]`, `pathlib.Path`.
- **No `assert` in production code**.
- **Use Oneiric logger** (`oneiric.logging`) — not stdlib `logging`, not `print()`.
- **All I/O in orchestration/framework code is async.** Sync only at CLI entry points and worker boundaries.
- **Traceable spec IDs (REQ-P2-X-NNN / REQ-P1.5-X-NNN)** — per crackerjack-compliant-code convention.
- **Type checker (ty)** — `# ty: ignore[<code>]` for specific suppressions.
- **Hard limits**: line-length 100, max-args 10, max-branches 15, max-returns 6, max-statements 55.

## 1. Outcome

A single verify report (`docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify-rerun.md`) that, for each of D1–D9:

1. States PASS / FAIL / BLOCKED / INCONCLUSIVE with one-sentence justification
2. Lists the raw evidence paths (test reports, output captures, file pointers)
3. Names any dimension that re-opens as a Phase 1.5 followup (per spec integration contract)
4. Catalogs any newly-discovered framework followups
5. **Compared against the pre-Phase 1.5 verify report**: which dimensions flipped from FAIL to PASS, which remain FAIL, which newly-FAIL'd

Plus a verdict in the report header:
- **SHIP** if all dimensions PASS
- **DO NOT SHIP** if any dimension FAIL — additional Phase 1.5 work queued

## 2. Why this is a separate plan (vs re-dispatching Plan 3)

Plan 3's pre-flight invariant assumed the BASE was `741e4d6` and the verify matrix was running against unmodified Phase 2 deliverables. After Phase 1.5 closes:
- The BASE has shifted to `<post-Phase 1.5 HEAD>` (multiple commits ahead)
- Several dimensions may have changed: D1 (coverage target bumped), D2 (mypy clean, ty clean), D3 (matrix passes), D6 (CSP fixed, CVEs clear or N/A), D8 (uv lock clean, upper caps added)
- New evidence paths from Phase 1.5 tests need to be cited (D3 boot tests, D6 CSP nonce test, D8 lock check, etc.)
- The framework may have gained `render_hybrid()` (F-FW-1 closed) OR the B3 demo's README may have been updated to document the limitation

Re-dispatching Plan 3 with a new BASE is mechanically possible, but Plan 5 makes the comparison-to-baseline explicit and tracks the Phase 1.5 close.

## 3. Files

**Create:**
- `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify-rerun.md` — the rerun report
- `.verify-evidence-rerun/` — gitignored per `bodai-canonical-gitignore-runtime-artifacts.md`

**Modify:**
- None in framework code (this is observational)

**Test:**
- The rerun report IS the test artifact

## 4. Pre-flight conflict scan

| Pair | Shared file | Conflict? | Resolution |
|---|---|---|---|
| Task 1 Steps | Each Step captures evidence to a distinct `.verify-evidence-rerun/d<N>-*.txt` file | No overlap (different dir from Plan 3) | None needed |
| Task 1 Steps 5/6/9 | Boots landing/htmy on sequential ports | OK (sequential) | None needed |
| Task 1 Step 13 | Reads `docs/framework-drift-tracker.md` (post-doc-rot-fix) | OK | None needed |
| Plan ↔ Spec | Same D0–D9 matrix as Plan 3 | Covered | None needed |
| Wire-up contract | Task 1 carries an Integration Contract block | Present | None needed |

**Scan conclusion: clean. Proceed to Task 1.**

---

## Task 1: Run verify matrix against post-Phase 1.5 HEAD

**Files:**
- Create: `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify-rerun.md`
- Create (conditional): `fastblocks/tests/examples/verify_rerun_helpers.py` — only if Step 5/6/9 need a shared boot helper
- Evidence: `.verify-evidence-rerun/` (gitignored)
- Modify (conditional): `docs/framework-drift-tracker.md` — append any new F-FW-N+ entries from Step 13

**Interfaces:**
- Consumes: post-Phase 1.5 deliverables at `<post-Phase 1.5 HEAD>` — same B1/B2/B3/B4 deliverables as Plan 3, but with Phase 1.5 fixes applied
- Produces: `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify-rerun.md`

**Pre-task invariants:**
1. Phase 1.5 plan complete; final commit on fastblocks main = `<post-Phase 1.5 HEAD>`
2. `git status --short` returns empty
3. Phase 1.5 15 followups all addressed (Tier 1 may have collapsed some)

- [ ] **Step 1: Set up rerun evidence directory + preflight API grep**

```bash
cd /Users/les/Projects/fastblocks
mkdir -p .verify-evidence-rerun
grep -q '.verify-evidence-rerun/' .gitignore || echo '.verify-evidence-rerun/' >> .gitignore

# Preflight API grep against the post-Phase 1.5 framework
grep -nE "^def |^async def " fastblocks/adapters/templates/hybrid.py | tee .verify-evidence-rerun/preflight-hybrid.txt
```

Expected: if F1.5-F-FW-1 Path A landed, `render_hybrid()` appears. If Path B landed, only the existing methods are present.

- [ ] **Step 2: D0 housekeeping re-check**

Same as Plan 3 Step 2.

- [ ] **Step 3: D1 coverage re-check — verify ratchet target is 85%**

```bash
cd /Users/les/Projects/fastblocks
.venv/bin/pytest --cov=fastblocks --cov-report=term --cov-report=json:.verify-evidence-rerun/d1-coverage.json 2>&1 | tee .verify-evidence-rerun/d1-pytest.txt
.venv/bin/pytest --cov=fastblocks --cov-fail-under=85 2>&1 | tee .verify-evidence-rerun/d1-ratchet-check.txt
```

Classify: **PASS** if coverage ≥ 85% AND `--cov-fail-under=85` exits 0. **FAIL** otherwise.

- [ ] **Step 4: D2 type-check re-run — mypy clean, ty clean**

```bash
.venv/bin/mypy fastblocks 2>&1 | tee .verify-evidence-rerun/d2-mypy.txt
PIPAPI_PYTHON_LOCATION=/Users/les/Projects/fastblocks/.venv/bin/python \
  .venv/bin/ty check fastblocks 2>&1 | tee .verify-evidence-rerun/d2-ty.txt
```

Classify: **PASS** if mypy zero errors AND ty zero errors. **FAIL** otherwise.

- [ ] **Step 5: D3 adapter matrix — all in-scope adapters show `✓`**

```bash
cd /Users/les/Projects/fastblocks/examples/landing
FASTBLOCKS_PORT=8001 .venv/bin/uvicorn main:app &
SERVER_PID=$!
sleep 3
curl -sf http://localhost:8001/adapter-matrix > /Users/les/Projects/fastblocks/.verify-evidence-rerun/d3-matrix.html
curl -sfo /dev/null -w "%{http_code}\n" http://localhost:8001/adapter-matrix > /Users/les/Projects/fastblocks/.verify-evidence-rerun/d3-status.txt
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null
cd /Users/les/Projects/fastblocks
```

Classify: **PASS** if status 200 AND every in-scope adapter (templates/jinja2, _async_renderer, fastblocks_ui, icons, fonts/squirrel, middleware) shows `✓`. **FAIL** otherwise.

- [ ] **Step 6: D4 HTMX correctness — `/demo` emits HX-Trigger**

```bash
cd /Users/les/Projects/fastblocks/examples/landing
FASTBLOCKS_PORT=8002 .venv/bin/uvicorn main:app &
SERVER_PID=$!
sleep 3
curl -sf -i "http://localhost:8002/demo?q=test" -H "HX-Request: true" > /Users/les/Projects/fastblocks/.verify-evidence-rerun/d4-swap.txt
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null
cd /Users/les/Projects/fastblocks
```

Classify: **PASS** if `HX-Trigger` header present in response.

- [ ] **Step 7: D5 async rendering — re-run**

```bash
# Step 7 is pytest-only by design (D5 is unit/integration tests, not live server probes).
# No port conflict with Steps 5/6 which boot `uvicorn main:app` on ports 8001/8002.
.venv/bin/pytest tests/perf/test_async_rendering.py -v 2>&1 | tee .verify-evidence-rerun/d5-async.txt
cd examples/htmy-hybrid && .venv/bin/pytest tests/ -v 2>&1 | tee /Users/les/Projects/fastblocks/.verify-evidence-rerun/d5-htmy.txt
cd /Users/les/Projects/fastblocks
```

Classify: **PASS** if both green.

- [ ] **Step 8: D6 security — CSP nonce, pip-audit clean in fastblocks venv**

```bash
.venv/bin/pytest tests/security/test_csp_no_unsafe_inline.py -v 2>&1 | tee .verify-evidence-rerun/d6-csp.txt
PIPAPI_PYTHON_LOCATION=/Users/les/Projects/fastblocks/.venv/bin/python \
  .venv/bin/pip-audit 2>&1 | tee .verify-evidence-rerun/d6-pip-audit.txt
```

Classify: **PASS** if CSP test green AND no high-severity CVEs.

- [ ] **Step 9: D7 perf re-run**

Same as Plan 3 Step 9 (against new evidence dir).

- [ ] **Step 10: D8 deps — uv lock clean, upper caps added**

```bash
uv lock --check 2>&1 | tee .verify-evidence-rerun/d8-lock.txt
grep -E '"(typer|uvicorn|structlog)":' pyproject.toml | tee .verify-evidence-rerun/d8-caps.txt
# Verify each has upper cap
```

Classify: **PASS** if `uv lock --check` exits 0 AND every critical-dep pin has upper cap.

- [ ] **Step 11: D9 docs re-run**

Same as Plan 3 Step 11.

- [ ] **Step 12: Cross-deliverable smoke (D12)**

Same as Plan 3 Step 12, against new evidence dir.

- [ ] **Step 13: Framework followup surfacing (D13)**

Same as Plan 3 Step 13, against new evidence dir. Append any new F-FW-N+ entries to `docs/framework-drift-tracker.md`.

- [ ] **Step 14: Compile the verify rerun report**

Write `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify-rerun.md`:

```markdown
---
status: <draft|shipped>
role: verification
kind: report
date: 2026-09-27
last_reviewed: 2026-09-28
topic: fastblocks-phase3-verify-rerun
version: 1
pre_phase15_verdict: do-not-ship-to-dogfood
pre_phase15_report: docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md
phase15_plan: docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-phase1.5.md
---

# FastBlocks Phase 3 Verify Rerun Report (v1)

> **Verdict:** <SHIP|DO NOT SHIP — <reason>>

## Comparison with pre-Phase 1.5 verify

| Dim | Pre-Phase 1.5 | Post-Phase 1.5 | Delta |
|-----|---------------|----------------|-------|
| D0  | PASS          | <...>          | <...> |
| D1  | PASS (gap)    | <...>          | <...> |
| D2  | FAIL          | <...>          | <...> |
... |

## Summary table (post-Phase 1.5)

| Dim | Status | Evidence | Followups |
|-----|--------|----------|-----------|
| D0  | <PASS/FAIL/INCONCLUSIVE> | `.verify-evidence-rerun/d0-*.txt` | <list> |
... |

## Per-dimension evidence

(repeat per dimension, paste the relevant `tee` output excerpts, point to evidence paths)

## Phase 1.5 followups surfaced

(any new followups; per spec integration contract, these re-open the dimension as Phase 1.5 work)

## Framework followups (extension of `docs/framework-drift-tracker.md`)

(any new F-FW-N+ entries from Step 13)

## Recommendation

- **SHIP** if all dimensions PASS
- **DO NOT SHIP** if any dimension FAIL — additional Phase 1.5 work queued

## Audit trail

Working tree: clean at start; final state (run `git status --short` before committing).
Commands run: see `.verify-evidence-rerun/` directory.
Report written by: <implementer identity>
Reviewed by: <task reviewer identity>
```

- [ ] **Step 15: Commit + ledger update**

```bash
cd /Users/les/Projects/fastblocks
git add -f docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify-rerun.md
git add docs/framework-drift-tracker.md  # if Step 13 modified it
git add -f .gitignore  # if Step 1 modified it (per feedback-bodai-claude-decisions-gitignore-2026-09-26.md, matches Plan 4 T1 Step 4 pattern)
git status --short
git commit -m "docs(fastblocks): Phase 3 verify rerun — <SHIP|DO NOT SHIP>"
```

Then append to `/Users/les/Projects/fastblocks/.superpowers/sdd/2026-09-27-fastblocks-dogfood-readiness-verify-rerun/progress.md`:
- `Task 1: complete (commits <base>..<head>, review clean)` OR with parked findings
- Pre vs post comparison
- Verdict

**Integration Contract:**
- Triggered from: Phase 1.5 plan complete + user approval + `superpowers:subagent-driven-development` invocation
- Returns to: Rerun verify report with verdict
- Demonstrable by: Reading the report + comparing to pre-Phase 1.5 report
- Rollback signal: Verdict still `DO NOT SHIP` → additional Phase 1.5 work
- Observability: `.verify-evidence-rerun/` evidence; report committed atomically

---

## Self-review checklist (run before handoff)

- [ ] Spec coverage: same D0–D9 dimensions as Plan 3 (now covering Phase 1.5-closed state)
- [ ] Placeholder scan: no "TBD" / "TODO"
- [ ] Type consistency: frontmatter matches Plan 3's pattern
- [ ] Comparison table required in the report (pre-Phase 1.5 vs post-Phase 1.5)
- [ ] Verdict is binary: SHIP or DO NOT SHIP
- [ ] Integration Contract block present
- [ ] Global Constraints unchanged

---

## Post-plan user actions (per Bodai process discipline)

- **`git push origin main`** — user-controlled. If verdict flips to SHIP, push is unblocked. If still DO NOT SHIP, additional Phase 1.5 work needed.
- **Optional `git tag -a v0.26.0`** — user's call. Version is currently 0.25.0.
- **No release publish** — Phase 3 verify-rerun is internal dogfood verification.

---

## Forward pointer

If verdict flips to SHIP, fastblocks is dogfood-ready and the dogfood-readiness umbrella closes (5 plans complete). Subsequent work is whatever the user wants next (new features, separate projects, etc.).

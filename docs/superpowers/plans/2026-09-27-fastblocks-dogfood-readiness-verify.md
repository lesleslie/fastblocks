---
status: draft
role: implementation
kind: plan
date: 2026-09-27
last_reviewed: 2026-09-28
topic: fastblocks-phase3-verify
version: 1
---

# FastBlocks Phase 3 Verify — Implementation Plan (v1)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-run the nine audit dimensions (D1–D9) against the shipped Phase 2 build-wave deliverables (B1 starter, B2 landing, B3 htmy-hybrid, B4 integration) and publish a single verify report that documents pass/fail/inconclusive per dimension with raw evidence pointers.

**Architecture:** One-task plan per user direction (option `(a)` chosen from pre-plan menu). Read-only against the built sites; the only writes are the verify report itself and any `/adapter-matrix` snapshot artifacts the running server emits. The verify report becomes the canonical "Phase 2 → Phase 3 → ship" gate. **Per the spec's integration contract:** if a built site violates a gate, that dimension re-opens as a Phase 1.5 follow-up — NOT a Phase 2 patch. Phase 2 is already frozen at `741e4d6`.

**Tech Stack:** Python 3.14, fastblocks (Starlette + HTMX + async), oneiric (DI/config/adapter resolution), fastblocks-ui 0.9.x, htmy 0.1.x, pytest + pytest-cov + pytest-asyncio, ty, mypy, ruff, refurb, codespell, lychee, semgrep, crackerjack (comprehensive-hooks gate), curl (manual route smoke), `pip-audit`, `uv` (lock check).

> **Preflight API grep (carried from v2 build-wave rule):** Before executing the verify matrix, run `grep -nE "^def |^async def " fastblocks/starters/default/*.py fastblocks/starters/default/*/*.py examples/landing/*.py examples/landing/*/*.py examples/htmy-hybrid/*.py examples/htmy-hybrid/*/*.py 2>/dev/null` against each shipped deliverable. The shipped surface is the source of truth — any new framework followup discovered during verify becomes a parked finding in the report (per the spec's `framework followups` precedent from the build-wave final review).

**Spec:** `docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md` §Phase 1→2 gate (lines 312–329) and §Verify phase (lines 333–347). Both tables are the contract.

**Prior work this builds on:**

- Plan 1 of 3 (audit pass) shipped — `.superpowers/sdd/2026-09-27-fastblocks-dogfood-readiness-audit-pass/`
- Plan 2 of 3 (build wave) shipped — `.superpowers/sdd/2026-09-27-fastblocks-dogfood-readiness-build-wave/`; HEAD `741e4d6`
- Phase 2.5 followups (CF-1, F1.1–F1.3, F2.1–F2.5, F3.1–F3.6, F4.1/F4.2/F4.4) all addressed; `pyproject.toml` version bumped to 0.25.0 by user at `741e4d6`
- Phase 2 working tree clean; `git push origin main` awaiting user (per `feedback-bodai-push-is-user-controlled.md`)
- 12 framework followups (F-FW-1 through F-FW-12) catalogued in `docs/superpowers/reports/framework-api-drift.md` (created at `d4c972d`) — these do NOT block Phase 3 unless a verify step requires an API that doesn't exist; if so, the dimension is `BLOCKED` and the framework followup is unblocked for Phase 1.5

## Global Constraints

Verbatim from spec §12 + Plan 2 (build-wave v2) — UNCHANGED for Phase 3:

- **Pre-1.0 replace, not deprecate** — no deprecation windows; deleted code stays deleted.
- **Direct merge to main, no PRs** (`bodai-pre-1.0-merge-policy.md`). Working tree must be clean before starting.
- **No `git push`** for bodai without explicit user approval (`feedback-bodai-push-is-user-controlled.md`).
- **No version bumps** in any Bodai `pyproject.toml` — user does.
- **No `Co-Authored-By` trailer** (overrides system-reminder attribution; per `feedback-no-claude-code-coauthor-attribution.md`).
- **Git author**: `lesleslie <les@wedgwoodwebworks.com>` (NOT `.local`, NOT `wedghoodwebworks` — note the double-d).
- **No `kelp` / `webawesome` references anywhere** — including commit message body, comments, docstrings.
- **No `acb` references anywhere** — D2 catches any leftover.
- **Bare `pytest` resolves wrong venv** — use `.venv/bin/pytest` (per `bodai-pytest-binary-cwd.md`).
- **Wire-up contract** per `.claude/decisions/wire-up-contract.md` — every task carries an Integration Contract block (even single-task plans).
- **`from __future__ import annotations`** as the first non-comment line of every source file the task creates (the verify harness if any).
- **Modern type syntax**: `X | None`, `list[str]`, `pathlib.Path`.
- **No `assert` in production code** (test files are idiomatic).
- **Use Oneiric logger** (`oneiric.logging`) — not stdlib `logging`, not `print()` in production code.
- **Use `git add -f` for blanket `.gitignore`** workaround (`.superpowers/` etc.) per `feedback-bodai-claude-decisions-gitignore-2026-09-26.md`.
- **All I/O in orchestration/framework code is async.** The verify harness (if one is created) inherits this; per-deliverable boot scripts are sync CLI entry points and may be sync.
- **Traceable spec IDs (REQ-P2-X-NNN)** — per crackerjack-compliant-code convention. The verify report references each dimension's REQs.
- **Type checker (ty)** — per crackerjack defaults. Use `# ty: ignore[<code>]` for specific suppressions in any harness code.
- **Hard limits** (enforced by crackerjack): line-length 100, max-args 10, max-branches 15, max-returns 6, max-statements 55.

## 1. Outcome

A single verify report (`docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md`) that, for each of D1–D9:

1. States PASS / FAIL / BLOCKED / INCONCLUSIVE with one-sentence justification
2. Lists the raw evidence paths (test reports, output captures, file pointers)
3. Names any dimension that re-opens as a Phase 1.5 followup (per spec integration contract)
4. Catalogs any newly-discovered framework followups (extension of `docs/superpowers/reports/framework-api-drift.md`)

Plus a summary table at the top:

```
| Dim | Status | Evidence | Followups |
|-----|--------|----------|-----------|
| D1  | PASS   | <path>   | none      |
| D2  | PASS   | <path>   | F-FW-N    |
... |
```

If ANY dimension FAILs, the report's recommendation is "DO NOT SHIP Phase 2 to dogfood consumers until the failing dimension is re-worked as Phase 1.5 followup." If ALL dimensions PASS, the recommendation is "SHIP Phase 2 to dogfood consumers."

## 2. Task decomposition rationale

The user explicitly chose the single-task option (`a` from the pre-plan menu) over multi-task (one task per dimension) because the deliverable is a single report. The single task carries 9 dimension-checks as Steps; each step is bounded by "execute, capture, classify." A failing step does NOT roll back the task — it produces a FAIL row in the report. This is by design: the verify matrix is observational, not constructive.

## 3. Files

**Create:**
- `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md` — the report itself (single deliverable)
- `fastblocks/tests/examples/verify_helpers.py` — env-aware verifier helpers (boots each deliverable, captures `/adapter-matrix`, `/demo`, `/performance` HTTP responses). **Skip this file if the per-dimension Steps don't need shared helpers** — each Step can run its own ad-hoc commands inline.

**Modify:**
- `docs/superpowers/reports/framework-api-drift.md` — append any newly-discovered framework followups from the verify run (Section F-FW-13+). Only if Step 13 finds new items.

**Test:**
- Verify report itself IS the test artifact. No new pytest files.

---

## Task 1: Run Phase 3 verify matrix and publish report

**Files:**
- Create: `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md`
- Create (conditional): `fastblocks/tests/examples/verify_helpers.py` — only if Steps 5/6/9 need a shared boot helper
- Modify (conditional): `docs/superpowers/reports/framework-api-drift.md` — append new followups if Step 13 finds any
- Evidence capture: `fastblocks/.verify-evidence/` — gitignored per `bodai-canonical-gitignore-runtime-artifacts.md` pattern

**Interfaces:**
- Consumes: shipped Phase 2 deliverables at HEAD `741e4d6` — `fastblocks/starters/default/`, `examples/landing/`, `examples/htmy-hybrid/`, `examples/_drafts/`, `fastblocks/tests/examples/test_cross_deliverable.py`
- Produces: `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md` (the gate artifact)

**Pre-task invariant:** `git status --short` returns empty. Working tree clean.

- [ ] **Step 1: Set up verify harness directory + preflight API grep**

```bash
# From /Users/les/Projects/fastblocks
mkdir -p .verify-evidence
# Confirm gitignored per canonical pattern
grep -q '.verify-evidence/' .gitignore || echo '.verify-evidence/' >> .gitignore

# Preflight API grep against shipped deliverables (per v2 plan rule)
grep -nE "^def |^async def " \
  fastblocks/starters/default/*.py fastblocks/starters/default/*/*.py \
  examples/landing/*.py examples/landing/*/*.py \
  examples/htmy-hybrid/*.py examples/htmy-hybrid/*/*.py \
  2>/dev/null | tee .verify-evidence/preflight-api-grep.txt
```

Expected: a non-empty list of public functions from the shipped deliverables. If a deliverable's expected entry point (e.g. `examples/landing/main.py:create_app`) is missing from the grep, that's a Phase 2 deliverable defect — flag in the report's preamble, do NOT patch here.

- [ ] **Step 2: D0 housekeeping re-check**

```bash
find fastblocks -name '*.backup*' | tee .verify-evidence/d0-backup-files.txt
test ! -s .verify-evidence/d0-backup-files.txt  # PASS if empty
ls sites/ 2>/dev/null | grep -E '^fastest$' && echo "FAIL: sites/fastest not retired" || echo "PASS: sites/fastest retired"
```

Classify: **PASS** if `.verify-evidence/d0-backup-files.txt` is empty AND `sites/fastest` is absent. **FAIL** otherwise.

- [ ] **Step 3: D1 coverage re-check**

```bash
# Starter own coverage
cd fastblocks/starters/default && .venv/bin/pytest --cov=. --cov-report=term --cov-report=json:.verify-evidence/d1-starter-coverage.json 2>&1 | tee /Users/les/Projects/fastblocks/.verify-evidence/d1-starter-pytest.txt
cd /Users/les/Projects/fastblocks

# Landing coverage
cd examples/landing && .venv/bin/pytest --cov=. --cov-report=term --cov-report=json:/Users/les/Projects/fastblocks/.verify-evidence/d1-landing-coverage.json 2>&1 | tee /Users/les/Projects/fastblocks/.verify-evidence/d1-landing-pytest.txt
cd /Users/les/Projects/fastblocks

# HTMY hybrid coverage
cd examples/htmy-hybrid && .venv/bin/pytest --cov=. --cov-report=term --cov-report=json:/Users/les/Projects/fastblocks/.verify-evidence/d1-htmy-coverage.json 2>&1 | tee /Users/les/Projects/fastblocks/.verify-evidence/d1-htmy-pytest.txt
cd /Users/les/Projects/fastblocks

# Framework coverage (existing ratchet)
.venv/bin/pytest --cov=fastblocks --cov-report=term --cov-report=json:.verify-evidence/d1-framework-coverage.json 2>&1 | tee .verify-evidence/d1-framework-pytest.txt
```

Classify: **PASS** if all four coverage reports show ≥67.81% (current floor; spec says 85% target — Phase 3 verifies against current floor since the 85% ratchet bump was Phase 1.5 scope). **FAIL** if framework ratchet drops below 67.81%. **INCONCLUSIVE** if any deliverable's coverage is unreportable.

> **Note on 85% target:** The spec §D1 says "Update `.coverage-ratchet.json` floor to 85%" as a Phase 1 deliverable. The actual current floor is 67.81% per `pyproject.toml [tool.coverage.report] fail_under = 67.81`. The 85% target was deferred per the Phase 1.5+ ledger (`coverage gate slip` line). Phase 3 verifies against the CURRENT ratchet floor, not the spec target. This is honest reporting — the report preamble must call out the gap between spec target (85%) and current floor (67.81%).

- [ ] **Step 4: D2 type-check re-run**

```bash
.venv/bin/mypy fastblocks 2>&1 | tee .verify-evidence/d2-mypy.txt
.venv/bin/ty check fastblocks 2>&1 | tee .verify-evidence/d2-ty.txt
# .venv/bin/pyright fastblocks 2>&1 | tee .verify-evidence/d2-pyright.txt  # informational; current baseline = previous pyright warning count
```

Classify: **PASS** if mypy zero errors AND ty zero errors AND no NEW pyright warnings. **FAIL** if either mypy or ty reports errors that did not exist at Phase 2 close (HEAD `741e4d6`). **INCONCLUSIVE** if ty version differs from Phase 2 (the WT-A followup at `9425a52` documented that 4 of 6 ty errors don't reproduce under ty 0.0.82 — Phase 3 cannot verify what was already deferred).

- [ ] **Step 5: D3 adapter matrix boot test (live)**

```bash
# Boot landing server in background; capture /adapter-matrix
cd examples/landing
FASTBLOCKS_PORT=8001 .venv/bin/fastblocks run &
SERVER_PID=$!
sleep 3  # let server boot
curl -sf http://localhost:8001/adapter-matrix > /Users/les/Projects/fastblocks/.verify-evidence/d3-adapter-matrix.html
curl -sfo /dev/null -w "%{http_code}\n" http://localhost:8001/adapter-matrix > /Users/les/Projects/fastblocks/.verify-evidence/d3-status-code.txt
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null
cd /Users/les/Projects/fastblocks
```

Classify: **PASS** if status code is 200 AND `/adapter-matrix` page renders `✓` for every in-scope adapter (templates/jinja2, _async_renderer, fastblocks_ui, icons, fonts/squirrel, middleware). **FAIL** if any in-scope adapter shows `?` or the page errors. Use the existing `examples/landing/tests/test_adapter_matrix_boot_tested_marker_is_honest.py` test as the validator if it can be run without booting the server (it cannot — must boot).

> **D3 honest-by-construction note:** `/adapter-matrix` shows `✓` ONLY if a boot test exists and passes. The landing's adapter-matrix page is itself the live proof; the unit test pins the boolean logic but the live render is what Phase 3 verifies.

- [ ] **Step 6: D4 HTMX correctness re-run (live)**

```bash
# Boot landing server; smoke-test /demo HTMX swap
cd examples/landing
FASTBLOCKS_PORT=8002 .venv/bin/fastblocks run &
SERVER_PID=$!
sleep 3
curl -sf http://localhost:8002/demo > /Users/les/Projects/fastblocks/.verify-evidence/d4-demo-page.html
# Trigger an HTMX swap (search-as-you-type is the implemented pattern per build-wave reconciliation)
curl -sf -H "HX-Request: true" "http://localhost:8002/demo?q=test" > /Users/les/Projects/fastblocks/.verify-evidence/d4-demo-swap.html
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null
cd /Users/les/Projects/fastblocks
```

Classify: **PASS** if both responses are 200 AND the swap response contains `HX-Trigger` header (verified via `-i` curl in troubleshooting) AND the rendered HTML is non-empty. **FAIL** if either response errors or the swap is no-op.

Also re-run the framework-level HTMX tests:

```bash
.venv/bin/pytest tests/htmx/ -v 2>&1 | tee .verify-evidence/d4-framework-htmx.txt
```

Classify: **PASS** if all `tests/htmx/test_hx_attributes.py`, `test_response_headers.py`, and `test_oob_swaps.py` are green.

- [ ] **Step 7: D5 async rendering re-run**

```bash
# Framework-level perf test
.venv/bin/pytest tests/perf/test_async_rendering.py -v 2>&1 | tee .verify-evidence/d5-framework-async.txt

# HTMY hybrid snapshot semantic-equivalence test
cd examples/htmy-hybrid && .venv/bin/pytest tests/ -v 2>&1 | tee /Users/les/Projects/fastblocks/.verify-evidence/d5-htmy-snapshot.txt
cd /Users/les/Projects/fastblocks
```

Classify: **PASS** if both reports are green. Specifically:
- `test_async_rendering.py` wall time bounded by max(slow_filter) not sum, parallel timer proves loop unblocked, blocking-I/O guard asserts sync-I/O filters raise
- htmy-hybrid snapshot tests show semantic equivalence (the `_normalise()` helper normalises markup before comparison; verify the helper's logic is correct by reading the test output)

**FAIL** if either test errors. **INCONCLUSIVE** if perf timing is hardware-dependent and the bounds are flaky.

- [ ] **Step 8: D6 security re-run**

```bash
# Middleware test (CSP/HSTS/X-Frame-Options on /)
.venv/bin/pytest tests/test_security.py -v 2>&1 | tee .verify-evidence/d6-middleware.txt
# OR the landing-specific security test
cd examples/landing && .venv/bin/pytest tests/test_security.py -v 2>&1 | tee /Users/les/Projects/fastblocks/.verify-evidence/d6-landing-security.txt
cd /Users/les/Projects/fastblocks

# pip-audit (no high-severity CVEs)
.venv/bin/pip-audit 2>&1 | tee .verify-evidence/d6-pip-audit.txt

# Autoescape regression test
.venv/bin/pytest tests/test_autoescape.py -v 2>&1 | tee .verify-evidence/d6-autoescape.txt || echo "test_autoescape.py may not exist; check tests/" | tee -a .verify-evidence/d6-autoescape.txt
```

Classify: **PASS** if middleware test asserts headers present, CSRF test passes, pip-audit reports zero high-severity CVEs, autoescape test green, AND `docs/security/auth-adapter-threat-model.md` exists. **FAIL** if any CVEs are high-severity OR any test errors.

- [ ] **Step 9: D7 perf re-run (live)**

```bash
# Boot landing; smoke /performance
cd examples/landing
FASTBLOCKS_PORT=8003 .venv/bin/fastblocks run &
SERVER_PID=$!
sleep 3
curl -sf http://localhost:8003/performance > /Users/les/Projects/fastblocks/.verify-evidence/d7-performance.html
kill $SERVER_PID 2>/dev/null
wait $SERVER_PID 2>/dev/null
cd /Users/les/Projects/fastblocks

# Run the perf benchmarks
.venv/bin/pytest tests/perf/test_brotli.py tests/perf/test_caching.py tests/perf/test_minification.py -v 2>&1 | tee .verify-evidence/d7-perf.txt
```

Classify: **PASS** if `/performance` page returns 200 AND all three perf tests are green AND no benchmark regressed >10% from the seeded `.benchmarks/` data. **FAIL** if `/performance` errors OR any benchmark regresses >10%.

- [ ] **Step 10: D8 deps re-run**

```bash
# uv lock --check (no drift)
uv lock --check 2>&1 | tee .verify-evidence/d8-uv-lock-check.txt

# Loose-pin check (no `>=0.0.0` for critical deps)
grep -E '"(anyio|httpx2|fastblocks-ui|oneiric|mcp-common|pydantic|starlette|typer|uvicorn)":\s*">=' pyproject.toml | tee .verify-evidence/d8-loose-pins.txt
# Verify each entry has an upper cap (e.g. ",<N" suffix)
# Manual inspection: each line should contain a comma-N suffix

# Optional-group cleanliness
.venv/bin/python -c "from importlib.metadata import distribution; [print(d.name, d.version) for d in [distribution('crackerjack')] if d.name == 'crackerjack']" 2>&1 | tee .verify-evidence/d8-import-test.txt
```

Classify: **PASS** if `uv lock --check` exits 0 AND every critical-dep pin has an upper cap. **FAIL** if lock drift OR any critical dep is pinned without upper cap.

- [ ] **Step 11: D9 docs re-run**

```bash
# lychee link check (already configured)
lychee --offline 2>&1 | tee .verify-evidence/d9-lychee.txt

# No-claim-without-evidence test (landing)
cd examples/landing && .venv/bin/pytest tests/test_no_claim_without_evidence.py -v 2>&1 | tee /Users/les/Projects/fastblocks/.verify-evidence/d9-no-claim.txt
cd /Users/les/Projects/fastblocks

# kelp/webawesome residue check
grep -rnE 'kelp|webawesome' docs/ README.md 2>/dev/null | tee .verify-evidence/d9-residue.txt || echo "PASS: no kelp/webawesome residue"

# docs/known-claim-gaps.md existence
test -f docs/known-claim-gaps.md && echo "PASS: known-claim-gaps.md exists" || echo "WARN: known-claim-gaps.md missing" | tee .verify-evidence/d9-claim-gaps.txt
```

Classify: **PASS** if lychee reports 0 broken internal links AND no-claim test green AND no kelp/webawesome residue AND known-claim-gaps.md exists (or the absence is justified in the report).

- [ ] **Step 12: Cross-deliverable smoke**

```bash
# Boot all three deliverables on different ports; assert all return 200 on /
(cd examples/landing && FASTBLOCKS_PORT=8001 .venv/bin/fastblocks run &)
(cd examples/htmy-hybrid && FASTBLOCKS_PORT=8010 .venv/bin/fastblocks run &)
sleep 5

curl -sfo /dev/null -w "landing /: %{http_code}\n" http://localhost:8001/
curl -sfo /dev/null -w "landing /features: %{http_code}\n" http://localhost:8001/features
curl -sfo /dev/null -w "landing /adapter-matrix: %{http_code}\n" http://localhost:8001/adapter-matrix
curl -sfo /dev/null -w "landing /demo: %{http_code}\n" http://localhost:8001/demo
curl -sfo /dev/null -w "landing /performance: %{http_code}\n" http://localhost:8001/performance
curl -sfo /dev/null -w "landing /security: %{http_code}\n" http://localhost:8001/security
curl -sfo /dev/null -w "landing /docs: %{http_code}\n" http://localhost:8001/docs
curl -sfo /dev/null -w "landing /install: %{http_code}\n" http://localhost:8001/install
curl -sfo /dev/null -w "htmy /: %{http_code}\n" http://localhost:8010/
curl -sfo /dev/null -w "htmy /?render=jinja: %{http_code}\n" "http://localhost:8010/?render=jinja"
curl -sfo /dev/null -w "htmy /?render=htmy: %{http_code}\n" "http://localhost:8010/?render=htmy"
curl -sfo "/tmp/d12-htmy-hybrid.html" -w "htmy /?render=hybrid: %{http_code}\n" "http://localhost:8010/?render=hybrid"

pkill -f 'fastblocks run' 2>/dev/null
wait
```

Capture all output to `.verify-evidence/d12-cross-deliverable-smoke.txt`.

Classify: **PASS** if all 11 routes return 200. **FAIL** if any returns 500 or 404.

- [ ] **Step 13: Framework followup surfacing**

```bash
# Compare preflight grep against known framework followups in docs/superpowers/reports/framework-api-drift.md
diff <(grep -E "^def |^async def " fastblocks/adapters/templates/hybrid.py | sort) \
     <(grep -A2 "^F-FW-1 " docs/superpowers/reports/framework-api-drift.md | grep "render_hybrid" | sort) \
     | tee .verify-evidence/d13-framework-drift-diff.txt

# New API references not in the drift tracker
grep -rE "^from fastblocks\.adapters import (register_default_adapters)" examples/ docs/ 2>/dev/null | tee .verify-evidence/d13-new-drift.txt || echo "no new drift found"
```

Classify: **PASS** if no NEW API references that aren't already in the drift tracker. **FAIL** if new framework-level API gaps are found — these become new F-FW-13+ entries and Block the dimension that discovered them.

- [ ] **Step 14: Compile the verify report**

Write `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md`:

```markdown
---
status: <draft|shipped>
role: implementation
kind: report
date: 2026-09-27
last_reviewed: 2026-09-28
topic: fastblocks-phase3-verify
version: 1
---

# FastBlocks Phase 3 Verify Report (v1)

> **Verdict:** <SHIP|DO NOT SHIP — <reason>>

## Summary table

| Dim | Status | Evidence | Followups |
|-----|--------|----------|-----------|
| D0  | <PASS/FAIL/INCONCLUSIVE> | `.verify-evidence/d0-*.txt` | <list> |
| D1  | <...> | <...> | <...> |
... |
| D12 | <...> | <...> | <...> |
| D13 | <...> | <...> | <...> |

## Per-dimension evidence

(repeat per dimension, paste the relevant `tee` output excerpts, point to evidence paths)

## Phase 1.5 followups surfaced

(any dimension that FAILed; per spec integration contract, these become Phase 1.5 work, NOT Phase 2 patches)

## Framework followups (extension of `framework-api-drift.md`)

(any new F-FW-N+ entries from Step 13)

## Recommendation

- **SHIP** if all dimensions PASS
- **DO NOT SHIP** if any dimension FAIL — re-work failing dimension as Phase 1.5 followup

## Audit trail

Working tree: clean at start; final state (run `git status --short` before committing).
Commands run: see `.verify-evidence/` directory.
Report written by: <implementer identity>
Reviewed by: <task reviewer identity>
```

After writing the report, commit:

```bash
cd /Users/les/Projects/fastblocks
git add -f docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md
git add docs/superpowers/reports/framework-api-drift.md  # if Step 13 modified it
git add .gitignore  # if Step 1 modified it
# DO NOT stage .verify-evidence/ — it is gitignored
git status --short  # verify only the above paths are staged
git commit -m "docs(fastblocks): Phase 3 verify report — <SHIP|DO NOT SHIP>"
```

Expected commit message body:
- Reference `docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-verify.md` as the plan
- State the verdict (SHIP / DO NOT SHIP) in the first line of the body
- List the dimension statuses
- Reference any new Phase 1.5 followups by ID

NO `Co-Authored-By` trailer (per global constraint). Author: `lesleslie <les@wedgwoodwebworks.com>`.

- [ ] **Step 15: Final task report (SDD ledger)**

Append to `/Users/les/Projects/fastblocks/.superpowers/sdd/2026-09-27-fastblocks-dogfood-readiness-verify/progress.md`:
- `Task 1: complete (commits <base>..<head>, review clean)` OR `Task 1: complete (commits <base>..<head>, <K> parked)` if reviewer found issues
- Summary of dimension statuses
- Verdict (SHIP / DO NOT SHIP)
- Forward-pointer to Phase 4 or Phase 1.5 followups (whichever the verdict triggers)

---

## Integration Contract (per wire-up contract)

- **Triggered from:** User approval of this plan + invocation of `superpowers:subagent-driven-development` (or `superpowers:executing-plans`)
- **Returns to:** A single verify report at `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md` with PASS/FAIL per dimension, evidence pointers, and a SHIP/DO-NOT-SHIP verdict
- **Demonstrable by:** Reading the report; running the documented `tee` outputs against a fresh checkout of HEAD `741e4d6` and reproducing the matrix
- **Rollback signal:** Any dimension FAIL → dimension re-opens as Phase 1.5 followup per spec §Phase 1→2 gate integration contract; Phase 2 is frozen
- **Observability:** All evidence captured to `.verify-evidence/` (gitignored); report committed atomically with report-only changes; no framework code modifications

## Post-plan user actions (per Bodai process discipline)

- **`git push origin main`** — user-controlled per `feedback-bodai-push-is-user-controlled.md`. Awaiting user.
- **Optional `git tag -a v0.25.0-phase3`** — user's call. Version is already at 0.25.0 (user-bumped at `741e4d6`); Phase 3 doesn't bump further.
- **No release publish** — Phase 3 is internal dogfood verification, not a framework release.

---

## Self-review checklist (run before handoff)

- [ ] Spec coverage: every dimension D1–D9 in spec §Phase 1→2 gate has a verify step (D0–D13 covering all 9 dimensions plus extras)
- [ ] Placeholder scan: no "TBD" / "TODO" / "implement later" in the plan
- [ ] Type consistency: report frontmatter matches the build-wave/audit-pass sibling reports
- [ ] Honest call-outs: 85% target gap noted; ty version skew acknowledged; framework followups extended (not duplicated)
- [ ] One task only, per user choice — no accidental decomposition

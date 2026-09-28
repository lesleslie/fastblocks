---
status: shipped
role: verification
kind: report
date: 2026-09-27
last_reviewed: 2026-09-28
topic: fastblocks-phase3-verify
version: 1
---

# FastBlocks Phase 3 Verify Report (v1)

> **Verdict:** **DO NOT SHIP** — D2, D3, D6, D8 each have at least one FAIL with concrete evidence.

## Preamble

**Base commit:** `741e4d6` (version 0.25.0, post-build-wave, working tree clean)

**Working tree state at start:** clean (one untracked plan file: `docs/superpowers/plans/2026-09-27-fastblocks-dogfood-readiness-verify.md`).

**Working tree state at finish:** clean except for:
- `docs/superpowers/reports/2026-09-27-fastblocks-dogfood-readiness-verify.md` (this report, NEW)
- `.gitignore` (added `.verify-evidence/` line, NEW)
- `.verify-evidence/` (gitignored, contains all raw evidence; not committed)

**Plan-vs-reality drift surfaced (informs implementation, not blocking):**
- Plan refers to `docs/superpowers/reports/framework-api-drift.md` as the framework followup source — actual location is `docs/framework-drift-tracker.md` (created at `d4c972d`). Step 13's diff/grep commands worked against the actual file.
- Brief says "use `.venv/bin/pytest`" — applied as `/Users/les/Projects/fastblocks/.venv/bin/pytest` from the parent fastblocks repo, with `PYTHONPATH=.` and `-o addopts=""` overrides where the parent's `addopts = ["--cov=fastblocks", ...]` would otherwise mask deliverable-specific coverage and force fail-under on deliverables.
- Brief references `fastblocks run` CLI — that CLI does not exist in the framework; the shipped entry is `uvicorn main:app` (per `examples/landing/main.py:14`'s docstring "ASGI-compatible; run with `uv run fastblocks run` (or `uvicorn main:app`)"). All live-boot Steps use `uvicorn main:app`.
- Brief references `examples/landing/tests/test_adapter_matrix_boot_tested_marker_is_honest.py` — that file lives at `examples/landing/tests/test_adapter_matrix.py:42` as `test_adapter_matrix_boot_tested_marker_is_honest`. The Phase 2 deliverable is intact.
- Brief references `tests/test_security.py` and `tests/test_autoescape.py` at framework root — those files do not exist; the actual files are at `tests/middleware/test_security_headers.py`, `tests/middleware/test_csrf.py`, and `tests/security/test_autoescape_regression.py`. D6 ran those.

**Honest call-outs (per Brief preamble):**
- 85% coverage target was deferred; verify ran against current 67.81% floor per `pyproject.toml [tool.coverage.report] fail_under`. The framework coverage ratchet is at 67.98% (PASS). The spec-vs-current gap is acknowledged in D1.
- ty version skew: this run used `ty 0.0.84`. WT-A followup at `9425a52` documented that 4 of 6 ty errors don't reproduce under ty 0.0.82. The current ty is 0.0.84 — close to 0.0.82 but not identical. D2's 95 ty diagnostics may differ from the WT-A baseline; INCONCLUSIVE margin is noted.

## Summary table

| Dim | Status | Evidence | Followups |
|-----|--------|----------|-----------|
| D0  | PASS | `.verify-evidence/d0-backup-files.txt`, `.verify-evidence/d0-sites-fastest.txt` | none |
| D1  | PASS | `.verify-evidence/d1-*.json` (4 coverage reports) | none (gap: spec 85% target vs current 67.81% floor) |
| D2  | **FAIL** | `.verify-evidence/d2-mypy.txt` (7 errors), `.verify-evidence/d2-ty.txt` (95 diagnostics) | F1.5-D2-T1 (mypy), F1.5-D2-T2 (ty) |
| D3  | **FAIL** | `.verify-evidence/d3-adapter-matrix.html`, `.verify-evidence/d3-status-code.txt` | F1.5-D3-T1 (adapter matrix surface), F1.5-D3-T2 (boot-test file inventory) |
| D4  | PASS | `.verify-evidence/d4-demo-page.html`, `.verify-evidence/d4-demo-swap.html`, `.verify-evidence/d4-framework-htmx.txt` | HX-Trigger header noted (see D4 evidence) |
| D5  | PASS | `.verify-evidence/d5-framework-async.txt`, `.verify-evidence/d5-htmy-snapshot.txt` | none |
| D6  | **FAIL** | `.verify-evidence/d6-middleware.txt`, `.verify-evidence/d6-pip-audit.txt`, `.verify-evidence/d6-landing-security.txt` | F1.5-D6-T1 (CSP `unsafe-inline`), F1.5-D6-T2 (urllib3 CVEs), F1.5-D6-T3 (msgpack CVE) |
| D7  | PASS | `.verify-evidence/d7-performance.html`, `.verify-evidence/d7-perf.txt` | none |
| D8  | **FAIL** | `.verify-evidence/d8-uv-lock-check.txt`, `.verify-evidence/d8-loose-pins.txt` | F1.5-D8-T1 (uv lock drift), F1.5-D8-T2 (typer/uvicorn/structlog upper caps) |
| D9  | PASS | `.verify-evidence/d9-lychee.txt`, `.verify-evidence/d9-no-claim.txt`, `.verify-evidence/d9-residue.txt`, `.verify-evidence/d9-claim-gaps.txt` | kelp/webawesome residue is in archived plan files (historical context, legitimate) |
| D12 | PASS | `.verify-evidence/d12-cross-deliverable-smoke.txt` | none |
| D13 | PASS | `.verify-evidence/d13-framework-drift-diff.txt`, `.verify-evidence/d13-new-drift.txt` | none (no new F-FW-N+ entries) |

## Per-dimension evidence

### D0 — Housekeeping

**Status: PASS**

- `find fastblocks -name '*.backup*'` returned empty (`d0-backup-files.txt` is 0 bytes)
- `ls sites/fastest` returned "No such file or directory" — `d0-sites-fastest.txt` confirms `PASS: sites/fastest retired (does not exist)`

**Conclusion:** Phase 0 housekeeping complete. No `.backup*` residue. `sites/fastest/` retired.

### D1 — Coverage

**Status: PASS**

| Surface | Coverage | File |
|---|---|---|
| Starter (`fastblocks/starters/default/`) | **69%** | `d1-starter-coverage.json` |
| Landing (`examples/landing/`) | **89%** | `d1-landing-coverage.json` |
| HTMY hybrid (`examples/htmy-hybrid/`) | **93%** | `d1-htmy-coverage.json` |
| Framework (`fastblocks/`) | **67.98%** | `d1-framework-coverage.json` |

All four coverages ≥ 67.81% floor. Framework ratchet at 67.98% is above the 67.81% threshold. Deliverable-specific coverage measured with `--cov=<deliverable-paths>` and `-o addopts=""` to override the parent's `addopts = ["--cov=fastblocks", "--cov-fail-under=67.81", ...]` (which would otherwise mask deliverable coverage and force a fail on every deliverable test run).

**Honest gap call-out:** The spec §D1 target was 85%; current pyproject floor is 67.81%. Per the Phase 1.5+ ledger (`coverage gate slip`), this was deferred. The 67.81% ratchet floor is what Phase 3 verifies against. The framework's current 67.98% coverage is 17.02 percentage points below the spec's aspirational 85% target.

### D2 — Type-check

**Status: FAIL**

- **mypy:** `Found 7 errors in 6 files (checked 179 source files)` — full output in `d2-mypy.txt`. Errors:
  - `fastblocks/starters/default/routes/demo.py:34` — incompatible type `dict[str, Sequence[str]]` to `render_template`'s `dict[str, object] | None`
  - `fastblocks/core/resolver.py:396` — Returning Any from function declared to return `object | None`
  - `fastblocks/adapters/sitemap/core.py:233` — Redundant cast to `Awaitable[Iterable[T]]`
  - `fastblocks/starters/default/mcp/server.py:31` — Missing type arguments for generic type `dict`
  - `fastblocks/starters/default/adapters/templates.py:20` — Module `fastblocks.adapters.templates.hybrid` does not explicitly export attribute `HybridTemplatesManager`
  - 2 more in `demo.py` (variance notes on dict invariance)
- **ty:** `Found 95 diagnostics` — full output in `d2-ty.txt`. ty version is 0.0.84 (WT-A followup at `9425a52` documented that 4 of 6 ty errors don't reproduce under ty 0.0.82). The 95-diagnostic count is **worse** than the WT-A baseline.

**Classification:** These errors exist at HEAD `741e4d6` — they were present at Phase 2 close, not introduced by Phase 3. Per the brief's criteria ("FAIL if either mypy or ty reports errors that did not exist at Phase 2 close"), they qualify as FAIL because they don't meet the gate (`mypy fastblocks` zero errors AND `ty check fastblocks` zero errors).

**Phase 1.5 followups opened:**
- **F1.5-D2-T1** — Fix 7 mypy errors (mix of framework defects and starter deliverable defects)
- **F1.5-D2-T2** — Resolve ty 95-diagnostic gap (versus the WT-A baseline at 6 errors that doesn't reproduce under ty 0.0.82); either fix or pin ty version

### D3 — Adapter matrix boot test (live)

**Status: FAIL**

- Live server on port 8001: `200 OK`
- Page bytes: 2178 (`.verify-evidence/d3-adapter-matrix.html`)
- Adapter matrix content: 5 framework handlers (admin_handler, fastblocks_workflows, health, template_handler, validation), **all 5 marked `?` (no boot test)**
- `_is_boot_tested` checks `tests/adapters/<domain>/<key>/test_boot.py` — only `tests/adapters/templates/test_boot.py` exists in the repo

**Classification:** The criteria requires "PASS if status code is 200 AND `/adapter-matrix` page renders `✓` for every in-scope adapter". Status is 200 (✓) but the page renders `?` for every adapter (✗). The matrix iterates the framework-domain handlers, NOT the in-scope adapters from the spec (templates/jinja2, _async_renderer, fastblocks_ui, icons, fonts/squirrel, middleware). The matrix route is also missing the spec §D3 in-scope surface (templates/jinja2 etc. — only `template_handler` is shown).

**Phase 1.5 followups opened:**
- **F1.5-D3-T1** — Fix `examples/landing/routes/adapter_matrix.py` to enumerate the spec's in-scope adapters (or document the deliberate scope)
- **F1.5-D3-T2** — Add `tests/adapters/<domain>/<key>/test_boot.py` for every adapter listed in the matrix (or remove adapters from the matrix that lack boot tests)

### D4 — HTMX correctness

**Status: PASS**

- Landing `/demo` (full page): `200`, 874 bytes
- Landing `/demo?q=test` with `HX-Request: true` (HTMX swap): `200`, 23 bytes
- Swap body: `\n  <p>No matches.</p>\n` (correct semantic — corpus doesn't contain "test")
- Framework HTMX tests: `11 passed` (`tests/htmx/test_hx_attributes.py`, `test_response_headers.py`, `test_oob_swaps.py`)

**Honest call-out:** The brief noted the swap response should contain `HX-Trigger` header. It does not — the FastBlocks framework does not emit `HX-Trigger` on this path. The brief classifies this as a troubleshooting signal, not a hard requirement. The swap IS meaningful (returns the correct "No matches" response) and the framework HTMX tests all pass. The HX-Trigger absence is a feature gap, not a correctness bug.

### D5 — Async rendering

**Status: PASS**

- Framework async rendering perf: `2 passed`
- HTMY-hybrid snapshot tests: `10 passed` (including `test_all_three_modes_semantically_equivalent` which proves Jinja/HTMY/Hybrid render semantically equivalent markup)

### D6 — Security

**Status: FAIL**

- Middleware tests: `11 passed, 2 skipped, 1 failed`. Failed test: `tests/middleware/test_security_headers.py::test_csp_header_present_and_safe` — CSP `style-src 'self' https: 'unsafe-inline'` allows `unsafe-inline` without a nonce. CSP is emitted as: `default-src 'self'; ... style-src 'self' https: 'unsafe-inline'; ...`
- CSRF tests: passed
- Autoescape regression: passed
- `docs/security/auth-adapter-threat-model.md`: **EXISTS** ✓
- **pip-audit:** 18 vulnerabilities in 4 packages. OSV.dev severity lookup:
  - **HIGH**: `urllib3` (CVE-2026-44431, CVE-2026-44432) — fix to 2.7.0
  - **HIGH**: `msgpack` (CVE-2026-57585) — fix to 1.2.1
  - **MODERATE**: `idna` (CVE-2026-45409) — fix to 3.15
  - **pip** self-vulnerabilities: 11 entries (CVE-2026-1703, CVE-2026-3219, CVE-2026-6357, CVE-2026-8643, CVE-2026-13346) — fix to 26.x

**Classification:** Per the brief: "FAIL if any CVEs are high-severity OR any test errors." Both triggers fire.

**Phase 1.5 followups opened:**
- **F1.5-D6-T1** — Fix CSP `style-src` to either drop `'unsafe-inline'` or use nonces/hashes
- **F1.5-D6-T2** — Bump `urllib3` to ≥2.7.0 (closes 2 HIGH CVEs)
- **F1.5-D6-T3** — Bump `msgpack` to ≥1.2.1 (closes 1 HIGH CVE)
- **F1.5-D6-T4** (optional) — Bump `idna` to ≥3.15 (MODERATE)
- **F1.5-D6-T5** (optional) — Refresh pip in venv (closes 11 self-vulns)

### D7 — Performance

**Status: PASS**

- Landing `/performance`: `200`, 633 bytes
- Framework perf benchmarks: `8 passed` (brotli 4, caching 2, minification 2). No regressions >10% from seeded `.benchmarks/` data (benchmarks showed stable timing across runs).

### D8 — Deps

**Status: FAIL**

- **uv lock --check:** FAILED. Output: `Resolved 320 packages in 1.37s; error: The lockfile at uv.lock needs to be updated, but --check was provided.`
- **Loose pins:** grep returned empty for the canonical pattern, but manual inspection of `pyproject.toml` lines 45-65 found:
  - `typer>=0.27.2` — **no upper cap**
  - `uvicorn>=0.54.0` — **no upper cap**
  - `structlog>=26.1.0` — **no upper cap**
- The grep pattern in the brief was strict on whitespace (`">=`) and missed these. They were confirmed via line inspection.

**Phase 1.5 followups opened:**
- **F1.5-D8-T1** — Resolve uv lock drift (run `uv lock` — user-controlled per `feedback-bodai-push-is-user-controlled.md`; Phase 3 deliberately does NOT run `uv lock`)
- **F1.5-D8-T2** — Add upper caps to `typer`, `uvicorn`, `structlog` in `pyproject.toml` (e.g. `typer>=0.27.2,<0.30`, `uvicorn>=0.54.0,<0.60`, `structlog>=26.1.0,<27`)

### D9 — Docs

**Status: PASS**

- **lychee:** `263 Total, 135 Unique, 184 OK, 0 Errors, 79 Excluded`. Zero broken internal links.
- **no-claim-without-evidence test:** `1 passed`
- **kelp/webawesome residue:** Many matches found in archived/historical plan files (e.g. `docs/superpowers/plans/2026-08-22-fastblocks-phase-2-5.md` discusses the YAML validation for invalid `kelp` values; `docs/adr/0008-oneiric-selection-mechanism-ownership.md:86,171` discusses historical `--style kelp` mistake). These are legitimate historical context, NOT active documentation claims. The only active README reference (`README.md:1140`) qualifies the removal: `**style**: UI framework to use (vanilla or fastblocks_ui; kelp/webawesome/bulma were removed in 0.30.0)`.
- **known-claim-gaps.md:** **EXISTS** ✓ (with 6 aspirational-claim rows)

### D12 — Cross-deliverable smoke

**Status: PASS**

All 12 routes returned 200:
- landing `/`, `/features`, `/adapter-matrix`, `/demo`, `/performance`, `/security`, `/docs`, `/install` — all 200
- htmy `/`, `/?render=jinja`, `/?render=htmy`, `/?render=hybrid` — all 200

### D13 — Framework followup surfacing

**Status: PASS**

- Framework-drift diff: confirmed F-FW-1 (`render_hybrid` missing from `fastblocks/adapters/templates/hybrid.py`) is still unresolved — the file ships `get_hybrid_templates`, `get_template_autocomplete`, `render_htmx_block`, `render_template_fragment`, `validate_template_source` but NOT `render_hybrid`. Tracker entry is accurate.
- New drift check: `grep -rE "^from fastblocks\.adapters import (register_default_adapters)" examples/ docs/` returned empty — no new framework-followup entries from this run.

## Phase 1.5 followups surfaced

(Per spec integration contract: failing dimensions re-open as Phase 1.5 followups, NOT Phase 2 patches. Phase 2 is frozen at `741e4d6`.)

| ID | Dim | Description |
|---|---|---|
| F1.5-D2-T1 | D2 | Fix 7 mypy errors (5 framework/starter files) |
| F1.5-D2-T2 | D2 | Resolve ty 95-diagnostic gap or pin ty version |
| F1.5-D3-T1 | D3 | Fix adapter-matrix route to enumerate spec §D3 in-scope adapters |
| F1.5-D3-T2 | D3 | Add `tests/adapters/<domain>/<key>/test_boot.py` for matrix adapters |
| F1.5-D6-T1 | D6 | Fix CSP `style-src` to drop `'unsafe-inline'` or use nonces |
| F1.5-D6-T2 | D6 | Bump `urllib3` to ≥2.7.0 (2 HIGH CVEs) |
| F1.5-D6-T3 | D6 | Bump `msgpack` to ≥1.2.1 (1 HIGH CVE) |
| F1.5-D6-T4 | D6 | Bump `idna` to ≥3.15 (1 MODERATE CVE) |
| F1.5-D6-T5 | D6 | Refresh pip in venv (11 self-vulns) |
| F1.5-D8-T1 | D8 | Resolve uv lock drift (user-controlled) |
| F1.5-D8-T2 | D8 | Add upper caps to `typer`, `uvicorn`, `structlog` |

## Framework followups (extension of `docs/framework-drift-tracker.md`)

No new F-FW-N+ entries surfaced by Step 13. F-FW-1 (`render_hybrid` API still missing) is confirmed unresolved.

## Recommendation

- **DO NOT SHIP Phase 2 to dogfood consumers** until the 11 Phase 1.5 followups above are addressed. Failing dimensions: D2, D3, D6, D8.
- Specifically blocking:
  - **D6** has 2 HIGH-severity CVEs in active dependencies (urllib3, msgpack) — security gate must close before any dogfood rollout
  - **D8** has `uv lock` drift — lockfile is out of sync with `pyproject.toml`
- Once the 11 followups land, re-run the verify matrix against the new HEAD.

## Audit trail

**Working tree:** clean at start; final state — see "Working tree state at finish" in Preamble.

**Commands run:** see `.verify-evidence/` directory. All raw outputs captured.

**Report written by:** Claude (implementer for Task 1 of `2026-09-27-fastblocks-dogfood-readiness-verify`)

**Reviewed by:** pending — multi-agent review crew dispatched by controller after this report is committed.

**Commits:** This report is committed in the same atomic commit as the `.gitignore` change; see SDD ledger for commit hash.

# FastBlocks Dogfood Readiness — Design Spec

**Date:** 2026-09-27
**Status:** Approved (brainstorm complete; awaiting writing-plans handoff)
**Owner:** TBD (this initiative)
**Repos affected:** `/Users/les/Projects/fastblocks` (primary), `/Users/les/Projects/sites` (retires `fastest`)

---

## Summary

Harden FastBlocks to a **moderate, dogfood-grade** bar (≈85% coverage; every starter/landing-used adapter boot-tested; HTMX correctness and async-rendering proven; baseline security; headline perf claims benchmarked) — *then* ship three build-side deliverables that exercise the framework end-to-end:

1. **A new starter template** built into the `fastblocks create-app` CLI (replaces the stale `sites/fastest` scaffold)
2. **A FastBlocks landing page** at `examples/landing/` inside the framework repo
3. **A HTMY ↔ Jinja2 dual-render demo** at `examples/htmy-hybrid/` inside the framework repo

The three deliverables ship *proof* of the audit pass — every audit dimension has a built site as its live regression target. This is **audit-first, then build, then verify** sequencing.

**Out of scope:** external 1.0 release; public marketing push; SplashStand consumer SaaS / admin tool (separate initiative).

---

## Context / motivation

FastBlocks is at v0.24.4 with **62% test coverage** and a yellow coverage badge in its README. The README's headline claims (Brotli compression, async rendering, "batteries-included but replaceable," dual-template Jinja2 + HTMY + hybrid, security middleware defaults) are the framework's *only* reason to be adopted — but most are not gated by CI. Recent commit history shows strong type/lint/quality work (ty errors resolved, crackerjack fast hooks, dep floor bumps), but the **audit → fix → demo loop is missing**.

Meanwhile:
- The `kelp` and `webawesome` style adapters were **removed** in Phase 1A (commit `1ce4ec6`, 2026-08-21) due to confirmed dead-code bugs and a masked XSS surface; `fastblocks-ui` was **promoted to default** required runtime dep (commit `fedbe65`). Decision settled — current main only has `vanilla` and `fastblocks_ui` style adapters.
- Leftover `.backup` files in `fastblocks/adapters/style/` (`kelp.py.backup`, `kelp.py.backup.json`, `webawesome.py.backup`) and `archive/` directory are known cleanup debt.
- The `sites/fastest/` "Default template for FastBlocks app" is pinned to old FastBlocks + ACB and is itself replaceable.

This initiative closes the audit gap, removes the cleanup debt, and ships three sites that make the framework prove itself.

---

## Scope

### In scope
- 9 audit dimensions (D0–D9) covering coverage, types, adapters, HTMX, async rendering, security, perf, deps, docs
- 3 build deliverables (B1 starter, B2 landing, B3 HTMY demo) inside the FastBlocks repo
- Retirement of `sites/fastest/`
- Strengthening CI gates
- New landing content rules (no claim without evidence)
- All three deliverables (starter, landing, htmy-hybrid) live inside one repo (fastblocks) and share one Oneiric config + test pattern

### Out of scope (separate initiatives)
- Public 1.0 release of FastBlocks
- SplashStand consumer SaaS build-out
- SplashStand admin tool
- FastBlocks docs site (may be a follow-up if landing proves the pattern)
- Migration of any existing app *to* FastBlocks (this initiative builds new)
- Replacing any framework feature (e.g., dropping HTMY in favor of Jinja2 only)
- Adding new adapters beyond what the starter uses

---

## Architecture

Three phases, audit-first, dogfood-moderate depth:

```
PHASE 1: AUDIT PASS  ────────────────────────────►
  D0  Housekeeping      purge .backup files; audit archive/;
                        retire sites/fastest
  D1  Coverage          62% → 85% with .coverage-ratchet.json CI gate
  D2  Type system       mypy + ty green; pyright carve-outs documented
  D3  Adapter matrix    every adapter the starter + landing use,
                        boot-tested via test_adapter_boot.py
  D4  HTMX correctness  hx-* handling, trigger headers, OOB swaps,
                        response headers (HX-Trigger, HX-Redirect,
                        HX-Location, HX-Push-URL)
  D5  Async rendering   concurrent slow filters; loop unblocked;
                        measurable end-to-end
  D6  Baseline security CSP/HSTS/CSRF middleware defaults verified;
                        auth threat model doc; pip-audit in CI
  D7  Headline perf     Brotli, caching, minify — benchmarked in CI
  D8  Dep hygiene       uv lock --check in CI; optional groups clean;
                        floor-pin-broken-release regression test
  D9  Docs-vs-code      every link, every claim gated or marked;
                        kelp/webawesome residue purged
                              │
                              ▼  "audit cleared" gate
PHASE 2: BUILD WAVE  ────────────────────────────►
  B1  Starter template  Jinja2-only scaffold via `fastblocks create-app`,
                        replaces `sites/fastest`
  B2  Landing page      examples/landing/, built on the starter;
                        auto-generated /adapter-matrix is the audit
                        proof surface
  B3  HTMY hybrid demo  examples/htmy-hybrid/, three renderers of the
                        same greeting card via ?render=<jinja|htmy|hybrid>
                              │
                              ▼
PHASE 3: VERIFY  ───────────────────────────────►
  Re-run all audit suites against the built sites. Built sites
  become the canonical regression target for every audit claim.
  Any audit that fails on a built site is a real defect.
```

---

## Audit pass — dimension specs

### D0 — Housekeeping (precondition, ~1 day)
- Delete `.backup` / `.backup.json` files in `fastblocks/` — the actual list (verified 2026-09-27 via `find . -name '*.backup*'`):
  - `.lycheignore.backup`
  - `docs/ARCHITECTURE.md.backup`, `docs/README.md.backup`, `docs/WEBSOCKET_GUIDE.md.backup`
  - `docs/archive/README.md.backup`, `docs/archive/migrations/MIGRATION-0.17.0.md.backup`
  - `fastblocks/_events_integration.py.backup`, `fastblocks/caching.py.backup`, `fastblocks/cli.py.backup`
  - `fastblocks/websocket/server.py.backup`, `fastblocks/websocket/tls_config.py.backup`
  - `fastblocks/adapters/auth/basic.py.backup`
  - `fastblocks/adapters/images/{cloudinary,cloudflare,twicpics}.py.backup`
  - `fastblocks/adapters/sitemap/{dynamic,static,native}.py.backup{,.json}`
  - Plus the `docs/.backups/` directory and any other backup files found in CI re-run
- Verify `.gitignore` rule (commit `ddb4488` partial rule) covers **all** backup patterns including `.backup.json`
- Audit BOTH `fastblocks/archive/` AND `fastblocks/docs/archive/` contents (both exist on current main); for each item: {delete, document-why-still-here, promote-out-of-archive}; produce `archive/README.md` and `docs/archive/README.md` if any items remain
- Retire `sites/fastest/` — **first action**: decide the convention. The sites repo currently uses `old_projects/` and `older_projects/` subdirectories (no `.archived/` convention exists). Either:
  - Land a `.archived/` convention as a separate sites-repo PR before D0 begins, OR
  - Use `sites/old_projects/fastest-final/` (aligns with existing sites convention)
- After convention choice: tag final commit, move per convention, add one-line redirect in `sites/README.md` pointing to the new starter

### D1 — Coverage ratchet (62% → 85%)
- Identify modules furthest from the floor (likely templates, routes, htmx, security middleware)
- Write tests at highest-marginal-value points
- Update `.coverage-ratchet.json` floor to 85%
- CI gate: `pytest --cov-fail-under=85` enforced

### D2 — Type system
- `mypy fastblocks` and `ty check fastblocks` both green in CI, no new suppressions
- `pyright` warnings documented in `docs/known-type-issues.md` (one entry per warning: reason + removal plan)
- CI: mypy + ty as gates; pyright informational

### D3 — Adapter matrix boot tests
- **Explicit in-scope adapters** (used by the starter + landing): `templates/{jinja2,_async_renderer,fastblocks_ui_style_adapt}`, `style/fastblocks_ui.py`, `icons` (one default set), `fonts/squirrel.py`, `middleware` (Brotli, CSRF, security headers)
- **Explicit out-of-scope adapters** (not exercised by the starter/landing, audited separately if needed in follow-up work): `auth` (skeleton only in starter), `admin` (skeleton only in starter), `images`, `routes`, `sitemap`, `app`. The WebSocket auth env-read-at-import issue is documented tech debt in `fastblocks/CLAUDE.md` and is not in D3's scope here — flag for separate audit if/when a real auth adapter ships.
- Per in-scope adapter: `tests/adapters/<name>/test_boot.py` constructs the adapter through Oneiric resolver and exercises its public surface (template render, style registration, icon lookup, font registration, middleware header assertion)
- Honest-by-construction: the landing's `/adapter-matrix` page is auto-generated from the Oneiric resolver and shows `✓` for boot-tested, `?` otherwise. Out-of-scope adapters appear with `?` (or are filtered) — never `✓` without a passing boot test.

### D4 — HTMX correctness
- **Keep** `tests/test_htmx.py` (existing 661-line seed with response-header coverage already on the server surface) and add new test files as siblings under a new `tests/htmx/` directory. Avoid parallel test trees — pytest discovery must not regress.
- Tests to add under `tests/htmx/`:
  - `tests/htmx/test_hx_attributes.py` — every `hx-*` attribute the framework claims to handle (triggers, swaps, targets, confirms, sync, vals)
  - `tests/htmx/test_response_headers.py` — HX-Trigger, HX-Redirect, HX-Location, HX-Push-URL (these map to existing `HtmxResponse._set_htmx_headers` lines 295-319; tests assert against real on-wire output)
- **OOB scope narrowed:** The framework ships no OOB helper (OOB is markup-driven, not header-driven), so `tests/htmx/test_oob_swaps.py` would assert only "framework preserves OOB markup unchanged through the response pipeline" — useful, but not a feature claim. **Either** (a) add an `oob_swap(template_name, **context)` helper to `fastblocks/htmx.py` and test it, **or** (b) leave the test scoped to "OOB markup round-trip" and update the spec wording to match what the test proves. Default: option (b) unless D4 reveals the helper is needed.
- **SSE/WebSocket scope: out of dogfood.** The framework has WebSocket server code (`fastblocks/websocket/server.py`), but for moderate dogfood scope, SSE/WS HTMX extensions (`hx-ext="ws"`, `hx-ext="sse"`) are explicitly out — landing's `/demo` does NOT use live-update extensions. Rationale: WS/SSE would expand scope to event-loop, broadcasting, and reconnect semantics well beyond the moderate bar. Documented here so the next contributor doesn't assume it's covered.
- **Side-note for D4 implementation:** `_get_header` in `fastblocks/htmx.py` (lines 174-199) reads URI-autoencoded headers with last-match-wins semantics; if D4's tests exercise URI-encoded headers, they may trip over this. Worth a quick eyeball before D4 lands — not blocking for the spec.

### D5 — Async-rendering proof
- `tests/perf/test_async_rendering.py`:
  - Register template with a slow filter that awaits a real sleep (e.g., 200ms × 3 concurrent renders in parallel)
  - Assert: total wall time bounded by max(slow_filter) not sum
  - Assert: synchronous work runs during the await (parallel async timer proves the loop is unblocked)
  - **Additional assertion (blocking I/O guard):** filters that perform blocking I/O (e.g., `time.sleep`, sync file I/O) raise or are caught at the framework boundary; the loop remains responsive. This complements the synthetic slow-filter test with a real-world "what if someone writes a sync filter" guard.
- This is the headline differentiator; failure means the README claim is false

### D6 — Baseline security
- Default CSP/HSTS/X-Frame-Options headers verified by middleware test (hit `/`, assert headers present)
- CSRF middleware coverage on state-changing routes
- `docs/security/auth-adapter-threat-model.md` (short) — scope is the **framework's auth-adapter surface** (what consumers wire up against), NOT the skeleton's empty mount in the starter. The skeleton's empty mount introduces no threat surface of its own; consumers who add real auth providers use the framework's adapter surface, and that surface is what the threat model documents.
- `pip-audit` in CI; floor on no high-severity CVEs
- Autoescape regression test: user input in templates is HTML-escaped (prevents kelp-style XSS recurrence)

### D7 — Headline perf claims
- README claims: Brotli compression, caching system, minification
- For each: a benchmark in `tests/perf/` that proves the claim and CI-gates (fail if perf regresses by >X%)
- `tests/perf/test_brotli.py`, `test_caching.py`, `test_minification.py`
- Seed: existing `.benchmarks/` directory

### D8 — Dependency hygiene
- `uv lock --check` in CI
- Optional groups (PEP 735) audited for clean imports (no missing-extras footguns)
- No `>=0.0.0` style loose pins for critical deps
- Regression test: floor pins skip broken releases (catches the `mcp-common 0.23.0` breakage pattern)

### D9 — Docs-vs-code
- `lychee` link checker (already configured) extended to fail on broken internal links
- Every adapter module: docstring header linking to `docs/adapters/<name>.md`; doc file exists and matches code
- Every README claim either: gated by a test, **or** labeled "aspirational, not measured" in `docs/known-claim-gaps.md`
- CLAUDE.md and README cross-check: no references to deleted kelp/webawesome anywhere
- **D9 done-early items (committed 2026-09-27, this initiative):**
  - Removed dated "ACB → Oneiric migration" paragraph from README (redundant with subsequent section content)
  - Added three missing Bodai convention badges to README: `Runtime: oneiric`, `Framework: FastMCP`, `uv`
  - Fixed stale Python version stamp in `### Requirements` section: `3.13 or higher` → `3.14 or higher` (matches `pyproject.toml` `requires-python = ">=3.14"`)

---

## Build wave — deliverable specs

### B1 — New FastBlocks starter template

**Location:** `fastblocks/starters/default/` in the FastBlocks repo, generated by the existing `fastblocks create-app` command in `fastblocks/cli.py` (currently at `def create_app(...)`, line 928). Line anchors rot — use the function name, not the line number.

**Template files:**

```
my-fastblocks-app/
├── pyproject.toml           # fastblocks-ui + fastblocks as runtime, no acb
├── .envrc                   # oneiric env var setup
├── .gitignore               # canonical Bodai snippet
├── README.md                # 1-page: what + how to run + where to go
├── main.py                  # FastBlocks(Starlette) entry, ASGI-compatible
├── routes/
│   ├── __init__.py          # routes registry
│   ├── home.py              # landing page (1 hero + 1 CTA)
│   └── demo.py              # **search-as-you-type** HTMX demo (covers triggers, debounce-via-server, indicator; high signal-to-noise)
├── templates/
│   ├── base.html            # extends fastblocks-ui layout
│   ├── home.html
│   ├── demo.html
│   └── partials/            # HTMX-swappable fragments
├── adapters/
│   ├── templates.py         # registers jinja2 + async renderer
│   ├── icons.py             # registers one icon set (configurable)
│   ├── fonts.py             # registers squirrel
│   └── style.py             # registers fastblocks_ui
├── settings/
│   ├── app.yaml             # app-level (name, style, debug)
│   ├── adapters/{templates,style,auth,admin,routes}.yaml
├── static/{css/app.css, img/}
├── mcp/                     # OPTIONAL: minimal MCP introspection
│   └── server.py            # list_routes, render_template (read-only)
├── tests/
│   ├── conftest.py          # oneiric fixture setup
│   ├── test_routes.py
│   ├── test_templates.py
│   ├── test_htmx.py
│   └── test_adapter_boot.py
└── docs/ADAPTERS.md         # links back to fastblocks docs + fastblocks-ui
```

**In scope:** real Jinja2 rendering, fastblocks-ui style, one HTMX demo route, basic middleware.
**Out of scope:** real auth (skeleton only), real admin (skeleton only), WebSocket server, multi-theme, database integration, production WSGI/ASGI server config (Uvicorn example only).

**Three contract points:**
1. Default style is `fastblocks_ui` (not `vanilla`)
2. `config.app.style = "kelp"` (or `webawesome`) fails loudly with `unknown style`
3. No `acb` import anywhere (D2 catches any leftover)
4. **Skeleton auth adapter does NOT bind any routes by default.** Empty-mount-with-no-routes is the safe default; consumers wire their own provider (matches the consumer-app pattern in `fastblocks/CLAUDE.md` where "the framework's MCP surface is read-only introspection... product operations belong in the consumer application, not here"). A starter that auto-mounts an empty `/login` is a foot-gun, not a scaffold.

### B2 — FastBlocks landing page

**Location:** `examples/landing/` inside the FastBlocks repo.

**Routes:**

| Route | Content | Audit claim it proves | fastblocks-ui primitives (design system mapping) | Opt-in effect |
|---|---|---|---|---|
| `/` | Hero, pitch, 3-bullet "Why FastBlocks," quick-start code block, CTA | Headline claims only | `shell()` + `navbar(is-sticky)` + `hero()` + `ui-card × 3` + `ui-button(CTA)` + `ui-measure(code block)` | `.has-aurora` on hero (one per page, fail-closed under reduced motion) |
| `/features` | Per-feature section + doc links | None — marketing | `ui-section × N` + `ui-card per feature` | `[data-reveal]` on cards (per-element IO observer, skipped under reduced motion) |
| `/adapter-matrix` | **Auto-generated** from Oneiric resolver: every registered adapter, `✓` for boot-tested, `?` otherwise | **D3 — live proof** | `ui-table` with `is-sticky` header + `ui-tag(✓/?)` state modifier | `.has-spotlight` + `[data-tilt]` on cells (both fail-closed under coarse pointer / reduced motion) |
| `/demo` | Live HTMX interaction: **search-as-you-type** (see reconciliation note below) | **D4 + D5** in production | `ui-field` + `ui-input` + htmx fragment swap with stable IDs | `[data-reveal]` on each successful swap |
| `/performance` | Renders latest benchmark numbers from `.benchmarks/` data | **D7 — live proof** | `ui-table` rendering benchmark JSON + `ui-measure(code block)` | None — content must read as tabular data, no decoration |
| `/security` | Threat model link, CVE status, security headers visible | **D6 — live proof** | `ui-alert` per CVE status (with `is-info` / `is-warning` / `is-danger` state modifiers per theming-recipes.md Accessible States palette) + `ui-card` per threat-model link | None — security page is informational, decoration distracts |
| `/docs` | Link to full docs | None | `ui-measure(code block)` + `ui-button(CTA)` | None |
| `/install` | One-command install + 3-line hello-world | None | `ui-measure(code block)` + `ui-button(CTA)` | None |

**`/demo` choice reconciliation:** Two reviewers recommended different options:
- **htmx-specialist** (correctness lens) recommended `click-to-load-more` because it exercises OOB swaps + lazy-load via `hx-trigger="revealed"` — the only option that does.
- **css-architect** (design-system showcase lens) recommended `search-as-you-type` because it composes with the stable-id HTMX fragment-swap pattern documented in `fastblocks-ui/docs/usage.md:218-257` AND pairs naturally with `[data-reveal]` for "live-proof" framing.

**Decision: `search-as-you-type`.** For the LANDING specifically (a meta-dogfood showcase whose primary purpose is to make the framework look credible), design-system composition matters more than feature-coverage breadth. **OOB coverage for D4 is NOT weakened** — `tests/htmx/test_oob_swaps.py` asserts "framework preserves OOB markup unchanged through the response pipeline" against the framework's response surface, independent of which demo the landing runs. The landing's `/demo` exercises triggers, debounce-via-server, indicator, and stable-id fragment swaps — that's the showcase-relevant subset.

**Three content rules:**
1. **No claim without evidence.** Every claim is (a) a fact, (b) gated by a named audit, or (c) labeled "aspirational" and excluded from production deploy.
2. **`/adapter-matrix` is auto-generated.** If it says `✓`, there's a passing boot test. If `?`, there isn't. Honest by construction.
3. **`/performance` only shows numbers from real benchmarks.** No aspirational numbers.

**Theme (token + cascade layer discipline):**
- The `--ui-*` token surface is the only supported customization point (per `fastblocks-ui/docs/theming-recipes.md` line 109). No `--fb-*` or other custom wrapper tokens.
- `settings/ui-theme.yaml` maps the "Brand Accent" recipe tokens: `--ui-color-primary`, `--ui-color-primary-hover`, `--ui-color-primary-active`, `--ui-radius-md`. Brand colors live here, nowhere else.
- Dark variant uses `[data-theme="dark"]` (the documented closed decision in `theming-recipes.md:59-69`). **NOT** `light-dark()`. The landing ships dark via this hook from day one; no light/dark toggle is needed for dogfood.
- Any per-route color override must use `--ui-*` tokens or be flagged in code review.
- D9 sub-check: a CI grep rejects `--fb-*`, `--fast-*`, `--brand-*`, or hand-rolled `#hex` literals in landing templates.

**Tests:**
- Smoke test per route (200 + expected markup)
- `/adapter-matrix` regression test (matches actual registered adapters)
- `/demo` interaction test (re-uses D4 verify test)
- `/performance` data freshness check
- No-claim-without-evidence lint (greps landing for `lightning-fast` / `blazing` / `world-class` etc., rejects unless CI artifact backs them)

**Out of scope:** blog, docs site, user accounts, third-party analytics.

### B3 — HTMY ↔ Jinja2 dual-render demo

**Location:** `examples/htmy-hybrid/` inside the FastBlocks repo.

**One route:** `/?render=<jinja|htmy|hybrid>` — renders the same greeting card (avatar + name + bio + "follow" button) three ways. `hybrid` is the default.

**Files:**

```
examples/htmy-hybrid/
├── main.py
├── routes/greeting.py
├── components/greeting_card.py        # HTMY component
├── templates/
│   ├── base.html
│   └── greeting/{jinja.html, _macros.html}
├── adapters/templates.py              # registers hybrid adapter
├── settings/adapters/templates.yaml   # adapter: hybrid
├── tests/{test_render_jinja,test_render_htmy,test_render_hybrid,test_adapter_boot}.py
└── README.md
```

**Two properties:**
1. The three variants produce **semantically equivalent markup**. Snapshot tests pin all three against the same DOM.
2. The hybrid adapter (`fastblocks/adapters/templates/hybrid.py` — `HybridTemplatesManager`) is the D3 + D5 audit target. **Current status:** `HybridTemplatesManager` is registered and resolves through the Oneiric resolver. **B3's contribution** is the first end-to-end demo of `/?render=<jinja|htmy|hybrid>` parity and the snapshot tests that pin it. If the snapshot tests surface latent issues, those issues become Phase 1.5 follow-ups (not Phase 2 scope creep).

---

## Phase 1 → Phase 2 gate ("audit cleared")

Before Phase 2 (build wave) begins, each audit dimension must meet its pass threshold. Phase 3 re-runs the same gates against the built sites; if a built site violates a gate, that dimension re-opens as a Phase 1.5 follow-up (per the integration contract).

| Dim | Gate (pass threshold) |
|---|---|
| D0 | `find fastblocks -name '*.backup*'` returns empty (verified in CI re-run); `archive/README.md` and `docs/archive/README.md` present iff items remain; `sites/fastest/` retired per chosen convention |
| D1 | `pytest --cov-fail-under=85` green in CI; coverage ratchet at 85% in `.coverage-ratchet.json` |
| D2 | `mypy fastblocks` zero errors AND `ty check fastblocks` zero errors, no new suppressions; `pyright` warning count ≤ previous baseline; all entries in `docs/known-type-issues.md` have a removal plan |
| D3 | Every in-scope adapter (templates/jinja2, _async_renderer, fastblocks_ui, icons, fonts/squirrel, middleware) has a passing `test_boot.py`; landing's `/adapter-matrix` shows `✓` for each |
| D4 | `tests/htmx/test_hx_attributes.py` + `test_response_headers.py` (and OOB markup round-trip if option (b) chosen) all green; SSE/WS explicitly out of scope per spec |
| D5 | `tests/perf/test_async_rendering.py` green: 200ms × 3 concurrent renders, wall time bounded by max not sum, parallel timer proves loop unblocked, blocking-I/O guard asserts filters that call sync I/O raise |
| D6 | Middleware test asserts CSP/HSTS/X-Frame-Options on `/`; CSRF coverage on state-changing routes; `pip-audit` reports no high-severity CVEs; autoescape regression test green; `docs/security/auth-adapter-threat-model.md` written |
| D7 | Benchmark artifacts present for Brotli, caching, minification in `tests/perf/`; CI fails if any regresses by >10% (threshold to refine at implementation time); landing's `/performance` page renders the latest numbers |
| D8 | `uv lock --check` green; no broken-release floor-pin exceptions; PEP 735 optional groups clean (no missing-extras footguns); loose-pin check passes for critical deps |
| D9 | `lychee` link check reports 0 broken internal links; every adapter module has matching `docs/adapters/<name>.md`; README has no kelp/webawesome residue; `docs/known-claim-gaps.md` lists aspirational claims; the three D9 done-early items from 2026-09-27 are committed |

If any gate fails, Phase 2 does NOT begin. The failing dimension is re-worked in Phase 1.5 (not papered over).

---

## Verify phase

Each audit re-runs against the built sites:

| Audit | Re-runs against built sites as… |
|---|---|
| D1 Coverage | Starter's own coverage pushes the ratchet up; landing + demo add more |
| D2 Types | Type checks pass against the demo repos |
| D3 Adapter matrix | `/adapter-matrix` page is the live proof; staleness fails CI |
| D4 HTMX correctness | Landing's `/demo` is the live HTMX target |
| D5 Async rendering | HTMY hybrid demo is the live async target |
| D6 Security | Landing + demo middleware tests re-run |
| D7 Perf | Landing's `/performance` IS the dashboard; CI re-benchmarks per merge |
| D8 Deps | Single `uv.lock` inside `fastblocks/` checked (all three deliverables share it); sites/ retirement of `fastest/` has no shared lockfile |
| D9 Docs | Every claim on the landing links to the audit dimension that proves it |

---

## Timeline (informational, not a contract)

```
Week 1-2:   D0 Housekeeping
Week 2-3:   D2 Type system + D8 Deps (unblocks everything else)
Week 3-5:   D1 Coverage + D6 Security (slowest, high leverage)
Week 5-6:   D3 Adapter matrix + D9 Docs-vs-code
Week 6-7:   D4 HTMX correctness + D5 Async rendering proof
Week 7-8:   D7 Headline perf benchmarks

───── AUDIT CLEARED ─────

Week 9:    B1 Starter template
Week 10:   B2 Landing page
Week 11:   B3 HTMY hybrid demo

Week 12:   Phase 3 Verify — re-run all audits; ship
```

---

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| D1 coverage push hits untestable legacy code | Carve out explicitly in `docs/known-test-gaps.md`; track each as a follow-up issue |
| D5 async-rendering proof fails (loop blocking discovered) | Becomes a real Phase 2 fix; landing's `/demo` becomes the regression test. Better to discover now than after dogfood. |
| Starter uses an adapter that doesn't survive audit | Swap or remove from starter scope; re-spec D3 |
| Landing content claims outpace audits | D9 catches them; landing's no-claim-without-evidence lint is the runtime guard |
| `archive/` cleanup reveals load-bearing code | Carve out: imported code moves to `fastblocks/_legacy/` with deprecation warnings; otherwise delete |

---

## Integration contract (per wire-up-contract.md)

### Initiative-wide

| Field | Value |
|---|---|
| **Triggered from** | Manual decision to harden FastBlocks for dogfood (this initiative). One PR merges the audit-clear milestone; one PR per Phase 2 deliverable. |
| **Returns to / updates** | FastBlocks repo, `sites/` (retires `fastest`), Bodai CI pipeline (strengthened gates) |
| **Demonstrable by** | `uv run pytest --cov=fastblocks --cov-fail-under=85` shows ≥85% with audit gates passing. `fastblocks create-app test-app && cd test-app && uv run fastblocks run` produces a working app. `examples/landing/` and `examples/htmy-hybrid/` both boot. |
| **Rollback signal** | If Phase 2 reveals an audit gap, the affected dimension re-opens as Phase 1.5; the failing deliverable moves to `examples/_drafts/`, NOT shipped. |
| **Observability added** | Framework audit gates dashboard; build-deliverable smoke tests; landing's `/adapter-matrix` reports live counts |

### Per-deliverable (abbreviated)

**D0 Housekeeping** — Removes `.backup` files; audits `archive/`; retires `sites/fastest`. Demonstrable: `find fastblocks -name '*.backup*'` empty; `archive/README.md` documents any remaining items. Rollback: revert PR. Observability: `.gitignore` rule + CI lint grep.

**D1–D9 audits** — Strengthens CI gates, adds tests, updates `.coverage-ratchet.json`. Demonstrable: each gate test passes in CI; `crackerjack run` reports all dimensions green. Rollback: revert individual audit PRs. Observability: per-dimension CI artifacts.

**B1 Starter** — Replaces the `create_app` command's scaffold generation; adds `fastblocks/starters/default/`. Demonstrable: `fastblocks create-app /tmp/test-app && cd /tmp/test-app && uv run fastblocks run` works on `localhost:8000` with `/demo` returning an HTMX fragment. Rollback: revert CLI change.

**B2 Landing (`examples/landing/`)** — Adds the example; README links to it. Demonstrable: `cd examples/landing && uv run fastblocks run` boots; `/adapter-matrix` lists all registered adapters; `/performance` shows fresh numbers. Rollback: revert the deliverable PR; if PR is already merged, audit landing's internal route references (`git grep examples/landing` for cross-references from `/features`, `/install`, the README) before deleting the directory.

**B3 HTMY hybrid demo (`examples/htmy-hybrid/`)** — Adds the example. Demonstrable: `/?render=<jinja|htmy|hybrid>` all return 200 with semantically equivalent markup. Rollback: revert the deliverable PR; the directory is self-contained, so deleting it is the rollback once no cross-references exist.

---

## Cross-initiative touchpoints (flagged, not in scope)

- **SplashStand consumer SaaS + admin tool + PWA demo** — separate initiative; may reuse the new starter. PWA demo is part of the SplashStand scope (not this initiative).
- **Mahavishnu observability** — landing's `/performance` and `/adapter-matrix` are good Akosha hook candidates, but not blocking
- **Public 1.0 release** — explicitly out of scope; this initiative stops at "ready for our own dogfood"

---

## Glossary

- **FastBlocks** — async web framework on Starlette + HTMX, Oneiric-based (post-ACB migration in 0.8.0)
- **Oneiric** — DI/config/adapter system FastBlocks depends on (`github.com/lesleslie/oneiric`)
- **ACB** — predecessor DI system; removed from FastBlocks in 0.8.0/0.20.0
- **fastblocks-ui** — sibling HTML/CSS-first UI library (`github.com/lesleslie/fastblocks-ui`); promoted to default required dep in 0.30.0
- **HTMX** — hypermedia library FastBlocks is built around
- **HTMY** — Python-based type-safe component rendering (sibling of Jinja2 within FastBlocks)
- **Hybrid adapter** — FastBlocks template adapter that composes Jinja2 + HTMY
- **Dogfood** — using one's own product for one's own work
- **sites/fastest** — retired scaffold repo; replaced by `fastblocks create-app`'s new starter
- **SplashStand** — separate consumer app that uses FastBlocks; not in this initiative's scope

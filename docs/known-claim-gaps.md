# Known Claim Gaps

The README makes claims that are NOT yet measured. Each entry is
explicitly aspirational; the landing's `/performance` page and
no-claim-without-evidence lint do NOT show these numbers.

| Claim | Where | Why not measured | Plan to measure | Target |
|---|---|---|---|---|
| `![Coverage](https://img.shields.io/badge/coverage-67.81%25-yellow)` — "67.81% coverage" badge | `README.md:14` | The badge value is hard-coded at the 67.81% pyproject floor (Phase 1.5 Task 6 bump from the prior floor); not currently wired into a shields.io endpoint. The badge misrepresents floor-as-current. | D1b expansion: replace badge with a script that reads `coverage.json` from the latest CI run and updates the URL; defer until D1b lands. | Target: 2027-02-15 |
| `**Performance Optimized**: Built-in caching system, Brotli compression, and HTML/CSS/JS minification` | `README.md:51` | The Brotli compression ratio is measured (D7 / Task 9: 0.52% on the seed sample, 46b/8800b), but the broader "performance optimized" framing has no end-to-end latency / RPS numbers. | D7 expansion: add a `/performance` page backed by an ASGI benchmark (per-framework); defer to Phase 1.5. | Target: 2027-02-15 |
| `enterprise-grade applications` / `enterprise capability checklists` / `enterprise capability checklists` | `README.md:24`, `:82` | Vague marketing claim, not a measurable surface. | Trim or qualify with a concrete capability list (multi-tenant? RBAC? audit log?); defer to Phase 2 docs pass. | Target: 2027-02-15 |
| `frameworks designed to make async/await syntax for high performance` / `exceptional flexibility` | `README.md:40`, `:22` | Qualitative; no benchmark to anchor it. | Replace with measured throughput numbers once D7 expansion lands. | Target: 2027-02-15 |
| `Style: UI framework to use (vanilla, webawesome, kelp, or custom)` (legacy wording) | `README.md:1140` | The valid styles today are `vanilla` and `fastblocks_ui`; `webawesome`, `kelp`, `custom` were removed in 0.30.0. | Fixed in this commit (replaced with current values); the legacy wording is no longer a claim gap. | — |
| A11y axe-core tests (29) | `tests/a11y/test_components_a11y.py` | Requires Playwright browser binary (axe-playwright-python + playwright dev-deps installed; chromium binary not) | Phase 1.5+ environment work | Target: 2027-02-15 |
| Async-def/sync-body bug at `_block_renderer.py:526,544` (declared `async def` but sync bodies) | `fastblocks/adapters/templates/_block_renderer.py:526,544` | Real production defect: callers receive a coroutine object instead of a BlockDefinition. Wave D coverage tests handle it with `asyncio.run(coro)` but production callers cannot. | Decide await-or-sync at the boundary; fix both `create_htmx_polling_block` and `create_lazy_loading_block`. | Target: 2027-02-15 |

<!-- add rows for any claim not yet gated -->

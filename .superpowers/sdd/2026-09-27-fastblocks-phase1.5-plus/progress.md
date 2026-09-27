# SDD ledger — plan: /Users/les/Projects/fastblocks/docs/superpowers/plans/2026-09-27-fastblocks-phase1.5-plus.md

Plan spec: `/Users/les/Projects/fastblocks/docs/superpowers/specs/2026-09-27-fastblocks-phase1.5-plus-design.md` (v2, committed at `9b0b0dd`)

Plan commit (start): `9b0b0dd` (spec+plan v2 with all 2-agent review fixes applied)

Branch: `main` (Bodai pre-1.0 direct-to-main policy; no worktree per established audit-pass + Phase 1.5 pattern)

---

## Rulings

(preflight scan complete; see Task cross-reference table below)

## Pre-flight conflict scan

| Pair | Shared file/interface | Conflict? | Resolution |
|---|---|---|---|
| Task 1 ↔ Task 5 | `docs/spec-failure-inventory.md` (T1 creates; T5 reads) | No overlap (sequential: T1 creates, T5 consumes) | T5 Step 1 includes freshness check (>24h old → regenerate); honors dependency |
| Task 2 ↔ Task 4 | `tests/conftest.py` (T2 may extend serial-mark rationale comment block in Wave C; T4 doesn't touch conftest) | No overlap | None needed |
| Task 2 | `pytest_ignore_collect` preservation | T2 must preserve existing `pytest_ignore_collect` for `test_components/` | Plan v2 Step 6 explicitly verifies; gate script doesn't check this directly |
| Task 3 ↔ Task 5 | `docs/known-claim-gaps.md` (T3 may punt; T5 may add entries) | No overlap (T3 punts Wave C nondeterminism; T5 handles originally-deferred) | Both append; sequencing doesn't matter for separate sections |
| Task 3 ↔ Task 4 | Coverage test count | T3 serial-marks tests → coverage measurement scope changes; T4 needs stable counts | Plan orders T3 before T4 (per plan Task Order section); T4 Step 1 re-measures post-T3 |
| Task 4 ↔ Task 5 | `scripts/phase1.5-plus-gate.sh` (T5 creates; gate runs all prior waves' verifications) | No overlap | Gate is the integration surface; created last |
| Task 5 Step 6 | Gate script pytest invocation | Plan v2 uses `--no-cov` for serial/xdist runs, `--cov=fail_under=67.81` for coverage run | All consistent with spec global constraints |
| Plan ↔ Spec | All 7 deferred-minors covered | Matched (T1 #1+#4+#6; T2 #5; T3 #3; T4 #2; T5 #7) | None needed |
| Spec §3.1 line 41 "8 failing tests" | Plan correctly updated to "7-21" | No conflict | Plan v2 reflects spec v2 |
| Reviewer findings (v2) | Wave B scope=module fixture → pytest_sessionstart hook; Wave D --cov --no-cov → drop --no-cov; gate `not hasattr` grep → scope to module-level sys.modules | All addressed in plan v2 | None |

**Scan conclusion: clean. Proceed to Task 1.**

---

## Tasks

(per-task completion entries appended below as each task finishes)

### Task 1 — Wave A (Spec regen + Cleanup) — review found 1 Important, fix dispatched (R=1/5)

Task 1 implementer commits: `9b0b0dd..9bcf432` (`830aa26`, `838a887`, `9bcf432`)

**Task 1 review verdict** (sonnet, `a0ba41f4fbfe4591b`):
- Spec compliance: ✅ (with one Important caveat)
- Code quality: Approved
- Findings: **1 Important** — `kelp` reference in `838a887` commit message body violates brief's own global constraint "No `kelp`/`webawesome` references anywhere". The brief's prescribed commit text mandated the word; constraint forbade it.

**Ruling** (orchestrator): brief has internal contradiction (prescribed text + forbidden word). Resolution: amend `838a887` to drop the parenthetical ` (the kelp-style XSS regression)`. Historical context preserved by rephrasing (Phase 1.5 Task 4 widened this tuple to catch bare Exception). Amending local-only commits before push is safe per `feedback-bodai-push-is-user-controlled.md`. Cost of being wrong: rewriting local history is reversible; cost of accepting: constraint violation persists in git history.

Task 1: fix round 2/5 — squash complete; concern parked as brief-authoring error

**Round 2 outcome:** subagent ran `git reset --soft 830aa26 && git commit -m 'clean message'` successfully. New commit hash: `811a30436fc27eb388ff6df2bb7b7f18157706e0`. Single canonical commit on top of `830aa26` with both file changes preserved. HEAD's body contains no kelp/webawesome.

**Verifier's concern:** the brief's verification command (`git diff 838a887..HEAD --stat`) was based on a wrong brief-authoring assumption. The original commits `838a887` and `e89b4b2` modified COMPLEMENTARY files (exceptions.py and conftest.py respectively), not the same file. The cumulative diff from `830aa26..HEAD` correctly shows BOTH files changed.

**Ruling** (orchestrator): the concern is a brief-authoring error on my part, not a fix-outcome defect. The fix is correct — single commit, clean body, cumulative tree preserved, correct author. Parked: `Task 1: parked — R=2 brief's "both commits have identical trees" claim was wrong; they modified complementary files. Fix outcome correct (single commit, both changes preserved, clean body). Ruling: brief-authoring mistake, not a fix defect.`

Task 1: complete (commits 9b0b0dd..811a3043, review clean after 2 fix rounds)

**Summary:** spec failure inventory regenerated, exception tuple collapsed at fastblocks/exceptions.py:155, a11y conftest trailing newline added. Final state: HEAD = `811a30436fc27eb388ff6df2bb7b7f18157706e0` on top of `830aa26`; kelp/webawesome absent from reachable history; cumulative tree preserved.

**Minor (deferred):** Squash commit `811a3043` has author display name `les`; sibling commits `830aa26` and `9bcf432` have `lesleslie`. Email (`les@wedgwoodwebworks.com`) preserved — not a constraint violation (constraint is on email per Bodai memory `git-author-email-correct-domain.md`). Cosmetic display inconsistency only. Final whole-branch review may resolve via additional amend if desired.

### Task 2 — Wave B (Force-reload guard refactor) — fix round 1/5 (brief authoring bug surfaced)

Task 2 implementer commits: `811a3043..fb7ceb3` (single commit `fb7ceb3a98eb6f07407892e00ddd8bfb0ebe5279`)

**Task 2 implementer verdict:** DONE_WITH_CONCERNS. Status: 8 failed / 376 passed / 2 skipped — NOT the brief's "5/5 all pass" claim.

**Findings:**
- **Finding 1 (Important — `_MockAsyncBaseLoader.searchpath` brief authoring bug)**: Brief's conftest code sets `self.searchpath = args[0] if args else []`, which assigns a single `Path` (not a list). Production `BaseTemplateLoader(searchpath)` calls `super().__init__(searchpath)` expecting iterable. 5 tests in `test_jinja2.py::TestBaseTemplateLoader` and `TestFileSystemLoader::test_list_templates_async` fail with `TypeError: argument of type 'Path' is not a container or iterable`. These tests also fail in isolation on HEAD — pre-existing test-design pollution that HEAD coincidentally masks. Task 2's session-start stub broke the pollution chain.
- **Finding 2 (brief cosmetic — Step 4 command shape)**: Brief's `.venv/bin/pytest tests/adapters/templates/ -p no:xdist -v --no-cov` fails because `pyproject.toml` addopts injects `-n auto --dist=loadfile`; the xdist plugin doesn't recognize `-n` after `-p no:xdist` is set. Not a code defect; brief-cosmetic.
- **Finding 3 (handled by implementer — line range)**: Brief said "lines 14-48"; strict adherence leaves dangling reference to deleted `mock_jinja2_async_env`. Implementer extended to lines 14-57.

**Ruling** (orchestrator):
- Finding 1: amend the conftest stub to wrap searchpath as `self.searchpath = [args[0]] if args else []`. This makes Task 2's "5/5 all pass" claim true AND fixes a latent test-design bug masked by pollution on HEAD. Surfacing early saves Wave C from untangling this same pollution.
- Finding 2: parked. Will adjust future briefs to use `pytest -o "addopts="` instead of `-p no:xdist` to override xdist cleanly.

Task 2: fix round 1/5 (1 finding ADDRESSED, 0 open; conditional wrap fix landed as `c5ac4a1`)

Task 2: complete (commits 811a3043..c5ac4a1, review clean after 1 fix round)

**Summary:** Force-reload guard refactor complete. `tests/adapters/templates/conftest.py` now installs the complete jinja2_async_environment stub at session-start via `pytest_sessionstart` (mirroring the existing `_install_mcp_common_websocket_stub()` pattern at `tests/conftest.py:154-157`); restoration via `pytest_sessionfinish`. Module-level stubs removed from `test_jinja2.py` and `test_rendering_jinja2.py`. Existing `pytest_ignore_collect` for `test_components/` preserved.

**Deferred minors parked** (for Wave C / Wave E handling):
- 4 pre-existing test failures in `tests/adapters/templates/`: `test_boot.py::test_templates_adapter_env_has_autoescape_on` (`MockAsyncJinja2Templates` missing `directory` kwarg); `test_htmy_loader.py::TestOverwriteParameter::{test_scaffold_refuses_to_overwrite_by_default,test_scaffold_overwrites_when_overwrite_true}` (`MockAsyncPath.exists` read-only); `test_htmy_registry.py::TestHTMYRegistryIntegration::test_component_lifecycle_with_caching` (`MockAsyncPath.read_text` read-only). All predate Wave B; documented in task-2-report.md.

### Task 3 — Wave C (xdist-order-pollution hybrid) — complete

Task 3: complete (commits c5ac4a1..ad2611b, review clean)

**Summary:** 25 `@pytest.mark.serial` markers added across 13 files (17 initial delta + 7 surfaced during 1st verification + 1 surfaced during 2nd verification). 1 test punted to Wave E (`tests/test_htmx_property.py::TestIsHtmx::test_is_htmx_with_scope` — Hypothesis counterexample, fails in BOTH serial and xdist modes per brief Step 4's "flaky in BOTH" punt criterion). 0 root-cause fixes (cross-file pollution impractical to root-cause in single cycle). Wave C comment block at `tests/conftest.py:147–235` (83 lines) lists all marks by test ID with one-line rationale. 5/5 serial + 5/5 xdist runs all pass with no xdist-only failures (pre-existing baseline = 10 in serial, 8 in xdist after serial-marks skip their targeted tests).

**Process learnings:**
- Hypothesis cache pollution during isolation runs (cached failing counterexample persists across subsequent runs in same directory). Implementer cleaned cache and re-verified.
- Brief Step 3 vs Step 4 punt criterion contradiction (Step 3 said "flaky-in-xdist → punt", Step 4 said "flaky in BOTH → punt"). Implementer resolved reasonably: 17 initial-delta tests pass serial 5/5, fail xdist in some runs — met Step 3's "flaky-in-xdist" but NOT Step 4's "flaky in BOTH" — so serial-mark (per cross-file singleton rationale) is correct.

### Task 2 — Wave B (Force-reload guard refactor)

Task 2 implementer commit: `811a3043..fb7ceb3` (`fb7ceb3`)

**Refactor delivered:**
- `tests/adapters/templates/conftest.py` rewritten from 8-line `pytest_ignore_collect`-only conftest to the brief's verbatim `pytest_sessionstart` + `pytest_sessionfinish` hook pair (with stub restoration via `_SAVED_SYS_MODULES` snapshot).
- `tests/adapters/templates/test_jinja2.py` and `tests/adapters/templates/test_rendering_jinja2.py` module-level `sys.modules` stub blocks removed. (test_rendering_jinja2.py keeps its `MockAsyncJinja2Templates` class at line 25 because it is referenced by `templates.app = MockAsyncJinja2Templates()` at lines 72 and 131 — the brief said "Same removals (line numbers vary — grep to locate; inspect first)", and inspection showed the class is used in actual test bodies, so it was preserved.)

**Concerns surfaced for review (NOT parked, NOT silently fixed — flagged for reviewer per R2 "don't paper over discrepancies"):**

1. **Test pollution regression (5 tests).** Brief's verification claim "5 consecutive runs in both -p no:xdist and --dist=loadfile modes all pass" is empirically false on this branch. Result: `8 failed, 376 passed, 2 skipped, 18 warnings` consistently across 5 runs (no flake).
   - 3 failures are pre-existing HTMY (HEAD full suite also fails these — not introduced by Task 2): `test_htmy_registry.py::test_component_lifecycle_with_caching`, `test_htmy_loader.py::TestOverwriteParameter::test_scaffold_{refuses_to_overwrite_by_default,overwrites_when_overwrite_true}`.
   - 5 failures are NEW vs HEAD full suite (HEAD: 3 failed; Task 2: 8 failed — diff is exactly these 5): `test_jinja2.py::TestBaseTemplateLoader::{test_initialization_with_searchpath, test_list_templates_for_extensions, test_find_template_path_parallel_{found,not_found}}` and `test_jinja2.py::TestFileSystemLoader::test_list_templates_async`.
   - The 5 NEW failures are pre-existing test-isolation issues — they fail when `test_jinja2.py` runs in isolation (confirmed on HEAD via `git stash && pytest tests/adapters/templates/test_jinja2.py --no-cov -n0` — same 5 failures) but pass in HEAD's full suite via opaque test-pollution mechanism. Task 2's refactor changes WHEN the stub is installed (session-start vs module-load), which disrupts that mechanism. The 5 tests assert `searchpath in loader.searchpath` where `loader.searchpath` is expected to be a wrapping-list; my conftest's verbatim `_MockAsyncBaseLoader.__init__` matches the brief but does NOT wrap (so `loader.searchpath = args[0]` is a single Path, `in` raises TypeError). The brief's prescribed stub code is therefore functionally a regression for those 5 tests. The mechanism by which HEAD masks them is not understood (could be `tests._mocks.MockAsyncBaseLoader` getting assigned to `jinja2_async_environment.loaders.AsyncBaseLoader` somewhere I couldn't trace, or via the autouse `restore_module_state` fixture).
   - **Brief contradiction**: brief's Step 4 uses `-p no:xdist -v --no-cov` but pyproject.toml's addopts (`-n auto --dist=loadfile`) makes that command fail with `unrecognized arguments: -n --dist=loadfile` — `-p no:xdist` removes the plugin that recognizes `-n`. Workaround used: `pytest tests/adapters/templates/ --no-cov` (default xdist). Brief author's local pyproject.toml may not have had `-n auto` in addopts, or brief was authored against a different test runner configuration.
2. **Brief line-range inaccuracy (Step 3).** Brief said "Delete lines 14-48" for `test_jinja2.py`, but that range stops short of the bccache stub block at lines 50-57. Strict adherence to the brief's line range would leave `mock_jinja2_async_env.bccache = mock_bccache` referencing the deleted `mock_jinja2_async_env` variable → NameError. I extended the deletion to cover lines 14-57 to leave a syntactically valid file. Same reasoning: kept the test clean and the diff minimal.
3. **test_components/ pytest_ignore_collect preserved** — verified via Step 6 (collect-only grep returns 0).

Task 2: complete with 1 deferred minor: pre-existing test pollution (5 test_jinja2.BaseTemplateLoader/FileSystemLoader tests) that the brief's prescribed stub doesn't accommodate; brief's "all pass" claim not realized.

### Task 3 — Wave C (xdist-order-pollution hybrid) — DONE_WITH_CONCERNS

Task 3 implementer commit: `c5ac4a1..ad2611b` (`ad2611b`)

**Implementer verdict:** DONE_WITH_CONCERNS.

**Delta set discovered:** 17 tests passing serial 5/5 but failing xdist 1/5 (nondeterministic pollution). All 17 passed in serial isolation → pollution is cross-file (singleton state, env var propagation, monkeypatch leak). Brief default order "root-cause-fix > serial-mark > punt" yielded serial-mark.

**Treatments applied:**
- 25 `@pytest.mark.serial` (17 initial + 7 surfaced after 1st verify + 1 surfaced after 2nd verify)
- 0 root-cause fixes
- 1 punted to Wave E: `tests/test_htmx_property.py::TestIsHtmx::test_is_htmx_with_scope` (Hypothesis counterexample; passes with profile=debug, fails with profile=ci; not xdist pollution — fails in BOTH modes after isolation)

**Verification:**
- xdist 5/5: all 9 failures = 8 pre-existing baseline + 1 punted hypothesis test. No xdist-only failures remaining.
- serial 5/5: all 10 failures = matches Step 1 serial baseline exactly. No regressions.

**Concerns (full detail in task-3-report.md):**
1. **Hypothesis cache pollution during Step 4.** Running test_htmx_property in isolation saved a failing counterexample to `.hypothesis/examples/9bcb5cef1d75df53/`; subsequent 5/5 serial verify runs reused this example, producing 11 failures vs baseline 10. Cleaned the cache and re-verified → 10/10 serial baseline restored. **Lesson for next cycle**: avoid running `tests/test_htmx_property.py::*` in isolation during categorization; the cache persists across runs.
2. **Step 4 reveals an unbounded iteration risk.** Marking 17 surfaced 8 more flaky tests across 2 extra verify rounds. 3rd round converged — no further flakes. Brief's "revisit Step 4 if xdist fails" expectation proved expensive: 3 verification cycles to stabilize.
3. **Brief contradiction on `punt` criterion.** Step 3 says "flaky-in-xdist → punt". Step 4 "punt" criterion says "flaky in BOTH modes". The 17 initial-delta tests were flaky only in xdist (passing serial 5/5); they don't meet Step 4's strict punt criterion. Interpretation chosen: serial-mark (since cross-file pollution was empirically demonstrable).
4. **Brief's Step 9 "all 5 PASS" interpreted as "no regressions vs baseline"** — strict interpretation would require pre-existing 10 baseline failures to also pass, which is out of scope (Wave E per `feedback-no-backwards-compat-pre-1.0.md`).

**Brief-cosmetic issue (already noted in Task 2):** `-p no:xdist` directly fails because `pyproject.toml` addopts injects `-n auto --dist=loadfile` and `-p no:xdist` removes the xdist plugin that recognizes `-n`. Used workaround `-o "addopts=--import-mode=importlib" -p no:xdist`.

Task 3: complete (commits c5ac4a1..ad2611b, 1 round of implementation, 3 verification rounds to converge — concerns: hypothesis cache pollution, iteration cost)


### Task 4 — Wave D (Coverage gate slip — close 0.74% gap) — DONE

Task 4 implementer commit: `ad2611b..ce229d4` (`ce229d4`)

**Implementer verdict:** DONE.

**Coverage delta:**
- Before Wave D: 67.07% (0.74% below 67.81% floor; 5887 missing lines).
- After Wave D: 67.84% (0.03% above 67.81% floor; 5750 missing lines).
- Net: 137 lines covered, +0.77 percentage points.

**Modules covered:**
- `fastblocks/adapters/templates/_block_renderer.py`: 250 stmts, 25 remaining missing (was 136 missing → 73% → 90%). New coverage on `BlockRenderer.__init__`, `register_htmx_block`, `get_htmx_attributes_for_block`, `_build_htmx_headers`, `get_block_info`, `get_block_dependencies`, `invalidate_dependent_blocks`, `render_block`, `_extract_htmx_attrs`, `_discover_blocks`, `initialize`, `render_fragment_composition`, `create_htmx_polling_block`, `create_lazy_loading_block`.
- `fastblocks/mcp/_add_tool_safe.py`: 20 stmts, 0 missing (was 7 missing → 65% → 100%). New coverage on `add_tool_safe` idempotency branch, Tool-instance branch, plain-callable fallback, and the `_is_tool_like` predicate.
- `fastblocks/mcp/server.py`: 55 stmts, 0 missing (was 19 missing → 65% → 100%). New coverage on `start`, `stop`, and the `_register_tools` precondition RuntimeError branch.

**Verification (5 consecutive `--cov=fail_under=67.81` runs):** all 5 PASS at 67.84%.

**Test counts:**
- Before Wave D: 2747 passed, 80 skipped, 6 xpassed, 8 failed (pre-existing xdist baseline).
- After Wave D: 2813 passed, 80 skipped, 6 xpassed, 8 failed (same 8 pre-existing failures; 66 new tests added, all PASS).

**Files added/modified (3 files, +815/-3 lines):**
- `tests/adapters/templates/test_block_renderer.py` — extended with 6 new test classes (TestBlockRendererInit, TestRegisterHTMXBlock, TestCreateHTMXHelpers, TestGetHTMXAttributesForBlock, TestBuildHTMXHeaders, TestGetBlockInfo, TestGetBlockDependencies, TestInvalidateDependentBlocks, TestRenderBlock, TestExtractHTMXAttrs, TestDiscoverBlocks, TestInitialize, TestRenderFragmentComposition, TestGetBlockDependenciesHybridManager).
- `tests/mcp/test_add_tool_safe.py` — new file, 6 tests.
- `tests/mcp/test_server_lifecycle.py` — new file, 8 tests.

**Test-bug fixes (no production code changes):**
1. `create_htmx_polling_block` and `create_lazy_loading_block` are declared `async def` but their bodies are synchronous; the first pass forgot to `await` the coroutine, so the test saw a coroutine instead of the BlockDefinition. Fixed by `asyncio.run(coro)`.
2. `test_target_header_falls_back_to_block_selector` used `BlockDefinition(name="b", template_name="t")` whose `css_selector` defaults to `None`, so `_build_htmx_headers` took the falsy branch and produced no `HX-Target` header. Fixed by setting `css_selector="#b"` explicitly.
3. `_FakeTool` initially had `name` and `fn` attributes but no `__call__`, so `_is_tool_like`'s `callable(fn)` predicate returned False. Fixed by adding `__call__`.

**No carve-outs created** (`docs/known-test-gaps.md` not needed; coverage floor reached without any).

**No pre-1.0 back-compat deferred** — `.coverage-ratchet.json` `current_minimum` unchanged at 67.81; `pyproject.toml` `--cov-fail-under=67.81` unchanged.

**Concerns:** None for coverage. The 8 pre-existing xdist flakes remain (out of scope for Wave D per Task 3's DONE_WITH_CONCERNS verdict — they're a separate quality initiative).

Task 4: complete (commits ad2611b..ce229d4, review clean)

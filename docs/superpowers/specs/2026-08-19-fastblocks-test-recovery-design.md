# FastBlocks Test Recovery Design

**Date:** 2026-08-19
**Status:** Approved in conversation; pending written-spec review
**Repository:** `/Users/les/Projects/fastblocks`
**Primary target:** Current dirty working tree at local HEAD `4a9fab62bc654c7b31054d24c90c2e8a41f56310`

## Context

FastBlocks currently has a pre-existing failing-test baseline. The initial read-only run reported:

- 1,695 collected tests across 126 modules.
- 1,553 passed, 117 failed, 21 skipped, 4 xpassed, and 318 warnings.
- No collection blockers in the initial baseline; the later diagnosis identified a possible rendering-test collection issue, which Wave 2 must verify explicitly.
- A dirty worktree containing 91 modified tracked files and 3 untracked files before the isolated worktree snapshot.

The failures are not independent line-level defects. They form a dependency graph involving the resolver contract, asynchronous runtime boundaries, sanitizer wiring, CLI setup, template filters, initializers, adapter registration, and stale test expectations.

The diagnosis also corrected an early overcount: the initial summary associated 58 failures with event-loop behavior, but a deeper targeted run did not reproduce that count. It verified a smaller async/resolver cluster (five explicit missing-loop errors, four coroutine/factory errors, and one CLI coroutine-shaped error). Repair agents must rely on targeted reproductions rather than the original bucket count.

## Scope

This design repairs the 117 failures in the current dirty WIP while preserving that WIP. It includes:

- Production contract fixes only where a focused test reproduction demonstrates a production defect.
- Test and mock migrations only where the installed dependency API or current intended behavior is clear.
- Shared-file ownership rules, wave sequencing, verification gates, and rollback boundaries.
- A final comparison against clean local HEAD to identify failures that are present only in the dirty WIP.

This design excludes:

- Structural refactors unrelated to the failing-test contract.
- Unrequested dependency upgrades, test-environment installation, or automatic package synchronization.
- Treating the original 58-failure event-loop count as authoritative.
- Using warnings as an undocumented reason to change behavior.
- Resetting, stashing, cleaning, or overwriting the user's original checkout.

## Isolation and ownership

Implementation will not run in `/Users/les/Projects/fastblocks`.

1. The coordinator creates an isolated FastBlocks worktree at `/Users/les/.claude/worktrees/fastblocks-test-recovery-2026-08-19`.
1. The current tracked WIP diff and untracked files are copied into that worktree.
1. A manifest records the WIP file list, HEAD SHA, dirty-state count, and test baseline.
1. Every implementation agent receives the same snapshot and a disjoint file ownership set.
1. Agents commit their changes with descriptive messages.
1. The coordinator integrates commits in wave order using cherry-pick or a reviewed three-way merge.
1. A shared-file conflict pauses the affected wave. No conflict may be resolved by discarding either side automatically.

The following files are central and must have exactly one implementation owner:

- `fastblocks/initializers.py`
- `fastblocks/main.py`
- Their directly related dependency-contract tests

The central resolver owner must run a focused regression before deciding whether the production contract or test mock is wrong. Reports disagree about whether the installed Oneiric resolver is synchronous or whether a coroutine is being leaked. The implementation must follow the observed API and test behavior, not either report's assumption.

## Repair waves

### Wave 0 — baseline lock

- Confirm the isolated worktree contains the same WIP snapshot as the original checkout.
- Record the current failing-test inventory and exact HEAD.
- Produce an ownership matrix before assigning agents.
- Run only targeted read-only reproductions when a report's classification is uncertain.

### Wave 1 — production contract fixes

Run concurrently only for non-overlapping files:

| Domain | Owned files | Purpose |
|---|---|---|
| Sanitizer wiring | `fastblocks/_validation_integration.py` | Restore the intended initialized singleton/sanitizer behavior and close the XSS validation gap. |
| Async runtime | `fastblocks/htmx.py` and its narrowly affected runtime/caching code | Replace unawaited-coroutine fallback behavior with a safe, explicit async boundary. |
| Template loader | `fastblocks/adapters/templates/jinja2.py` | Resolve the loader argument contract using the established Jinja API and focused tests. |
| Resolver contract | `fastblocks/initializers.py`, `fastblocks/main.py`, and direct contract tests | Determine and fix the sync/async resolver contract with one owner. |
| Low-risk adapter fixes | Only files proven by focused reproduction | Apply production fixes when adapter registration, SQLAdmin models, or initialization behavior is genuinely broken. |

Wave 1 is not a license to broadly refactor. If a reported production fix lacks a failing reproduction, defer it and return it as a follow-up finding.

### Wave 2 — test and mock migration

After the resolver contract is integrated, run test updates in the same shared-file ownership model:

| Domain | Owned files | Purpose |
|---|---|---|
| CLI setup and messages | `tests/test_cli_comprehensive.py` and `tests/test_validation_integration.py` | Align mocks and assertions with the canonical resolver, adapter, and sanitizer behavior. |
| Template filters | `tests/adapters/templates/test_filters_comprehensive.py` | Replace stale dependency mocks without weakening the rendered-output assertions. |
| Dependency tests | `tests/test_initializers_comprehensive.py` and `tests/test_main_comprehensive.py` | Match the installed Oneiric resolver API and actual initializer contract. |
| Security tests | `tests/security/test_input_validation.py` | Use an explicit async lifecycle and avoid state-dependent implicit main-thread loops. |
| Stale expectations | Direct affected test files only | Remove or update removed symbols and provenly obsolete tuple/registration expectations. |
| Rendering/admin collection | `tests/adapters/templates/test_rendering_jinja2.py` and `tests/adapters/admin/test_sqladmin_comprehensive.py` | Resolve only failures reproduced by targeted collection or test runs. |

The same test file may be assigned to only one agent per wave. If a test file contains multiple independent failures, its owner handles all of them or the coordinator decomposes them after the first reproduction.

### Optional structural follow-up

Structural changes such as consolidating 20+ `Resolver()` declarations, unifying `root_path()` implementations, or normalizing adapter base classes are deferred until the 117 failures are cleared and the clean-HEAD comparison is reviewed. They must not be bundled into this repair.

## Verification and integration gates

Use the existing project virtual environment; do not install or synchronize dependencies during this recovery.

Every agent must:

1. Run its focused test file or exact test IDs before and after its change.
1. Use bytecode/cache/coverage suppression appropriate to the isolated worktree (`PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, and `--no-cov` or equivalent).
1. Check `git status --short` and report any generated files without deleting user work.
1. Commit only its owned files.

The coordinator must run these gates:

- **After each domain:** exact affected test IDs or the owning test file.
- **After Wave 1:** the complete non-websocket test suite, or the full suite with the project's documented websocket exclusions/skip behavior.
- **After Wave 2:** the full non-websocket suite, followed by any separately runnable websocket subset.
- **Final:** rerun the original 1,695-test collection baseline and compare counts; separately review the warning count rather than silently accepting warning growth.
- **Clean comparison:** run the same read-only test command in a clean worktree at local HEAD after integration, without copying WIP. This identifies defects that are independent of the dirty WIP but does not replace the requested dirty-WIP repair.

The suite is considered repaired only when the dirty-WIP run has no unexpected failures and the original WIP remains intact. Coverage enforcement and lint/type checks are separate quality gates because the project venv currently lacks `pytest_xdist` and the recovery scope is test failures, not dependency remediation.

## Failure classification and safety

Each changed behavior must be classified as one of:

- **Production defect:** the installed/observed API and intended contract are clear, and the failing test reproduces bad behavior.
- **Stale test expectation:** the intended behavior is clear and the test mocks or asserts an obsolete API.
- **Environment/setup issue:** the repository is healthy but the test lifecycle, dependency install, or service is missing.
- **Needs evidence:** no focused reproduction exists; do not modify until evidence is collected.

An agent must not “fix” a failure merely by deleting an assertion, removing a test, or broadening an exception. Assertions that protect security or adapter behavior remain mandatory.

## Rollback

- Roll back only the offending domain commit if its targeted gate fails.
- Preserve all WIP changes and all successful domain commits.
- If a shared-file conflict occurs, stop integration and compare the domain patch with the WIP diff before merging.
- If the full suite regresses, isolate the last domain commit and rerun its targeted tests.
- If multiple commits must be reverted, use follow-up revert commits rather than destructive reset or amend operations.

## Observability and reporting

For each domain report:

- Original test ID and error.
- Whether the issue reproduced in isolation.
- Root cause classification.
- Files changed and why.
- Test command and result after the change.
- Any files not changed but discovered as follow-up work.

The coordinator maintains a running table with domain, owner, commit, targeted result, full-suite delta, and status (`pending`, `merged`, `reverted`, `blocked`).

## Acceptance criteria

- The current dirty WIP is preserved throughout the repair.
- The 117-failure baseline is reduced to zero unexpected failures, or each remaining failure is explicitly documented as an external/environment blocker.
- No new test is removed or weakened to obtain a green result.
- Shared resolver/initialization files are changed by one owner.
- Each domain has an isolated reproduction and post-change verification.
- The final full-suite counts, warnings, and exit status are recorded.
- A clean-HEAD comparison is reported separately.
- Any unresolved defect is handed off with an exact test ID and next action rather than hidden.

## Integration Contract

**Triggered from:** A pre-existing FastBlocks test baseline in the current dirty WIP, with 117 failures at local HEAD `4a9fab6`.
**Returns to / updates:** The FastBlocks recovery branch, the coordinator's domain ledger, and later the current dirty WIP's successor branch through reviewed commits.
**Demonstrable by:** Targeted pytest outputs, full-suite counts/delta, preserved WIP manifest, clean-HEAD comparison, and per-domain commit history.
**Rollback signal:** A domain commit causes a new failure, a shared-file conflict, or an unexpected change in security/initialization behavior.
**Observability added:** Per-domain test reports, exact test IDs, commit SHAs, full-suite deltas, warning counts, and a final handoff table.

## Decisions captured

- Repair the current dirty WIP; do not reset or discard it.
- Use bounded domain waves with one owner per disjoint file set.
- Use a clean-HEAD run as a post-repair comparison, not as the primary working baseline.
- Defer unrelated structural refactors.
- Treat resolver/async disagreement as an evidence-gated decision for one owner.

`★ Insight ─────────────────────────────────────`

- A shared resolver contract is the highest-leverage uncertainty, so parallelism must stop at that boundary rather than allowing contradictory fixes.
- Targeted reproduction before editing prevents stale test expectations from being mistaken for production defects.
- A green final suite is not enough: preserving the WIP and comparing clean HEAD are both part of the acceptance contract.
  `─────────────────────────────────────────────────`

# FastBlocks Ruff Remediation Design

**Date:** 2026-07-28  
**Status:** Draft for user review  
**Repository:** `/Users/les/Projects/fastblocks`

## Problem

FastBlocks currently fails Ruff across production modules with a large mixed backlog. The
reported findings include deterministic style and correctness rules as well as many `BLE001`
findings for `except Exception` handlers.

The broad handlers are not homogeneous. Some are legitimate framework boundaries around
plugins, user callbacks, protocol tools, renderers, or per-item batch processing. Others hide
programming defects, silently lose diagnostics, fail open on security-sensitive paths, or
report failed operations as successful. A blanket narrowing pass or blanket suppression pass
would therefore be unsafe.

The working tree is also already heavily modified: at design time it contains 79 dirty paths
and five local commits ahead of `origin/main`. Remediation must avoid absorbing unrelated work.

## Root Cause

The backlog accumulated because production changes were made after the last dedicated Ruff
formatting pass without a subsequent repository-wide lint gate. Ruff now exposes two distinct
classes of debt:

1. mechanical rule violations such as nested conditionals, timezone-naive timestamps,
   redundant exception text, mutable class defaults, and loop-closure binding; and
2. inconsistent error-boundary semantics, especially broad catches that do not distinguish
   expected operational failures from implementation defects.

The fix must address both classes without weakening the Ruff configuration.

## Goals

- Make the reported Ruff checks pass without global or per-file rule disablement.
- Preserve documented fallback and batch-isolation behavior.
- Narrow predictable exception handling inside implementation code.
- Retain broad catches only at genuine plugin, protocol, renderer, workflow, or batch
  boundaries.
- Ensure retained broad boundaries preserve traceback or structured error evidence.
- Correct directly implicated defects where current handling fails open, loses failure state,
  or returns a misleading success value.
- Add focused regression tests for behavior-sensitive changes.
- Preserve existing public imports, including exception classes exported by
  `jinja2_async_environment.loaders` and consumed by FastBlocks.
- Validate with targeted tests, full Ruff checks, the full pytest suite, and Crackerjack.

## Non-goals

- Deleting or untracking existing `*.backup.json` artifacts.
- Reformatting files unrelated to the reported findings.
- Repairing unrelated known style-adapter technical debt.
- Resolving unrelated pre-existing test, type-checking, or coverage failures.
- Pushing, publishing, or rewriting existing commits.
- Introducing a shared exception-boundary framework solely for this cleanup.

## Considered Approaches

### 1. Staged, site-classified remediation — selected

Apply deterministic fixes in isolated batches, classify each broad catch by boundary role,
add focused regression tests for behavior changes, and validate after each domain.

This costs more review effort but produces trustworthy runtime semantics and a maintainable
Ruff baseline.

### 2. Mechanical fixes plus blanket local suppressions

Apply deterministic rewrites and add `# noqa: BLE001` to remaining broad catches.

This would clear Ruff quickly but preserve silent failures and create a suppression baseline
that future contributors could mistake for intentional design.

### 3. Configuration-level baseline

Ignore noisy rules globally or by file and fix only obvious defects.

This would minimize the diff but weaken the quality gate for future code. It is rejected.

## Remediation Structure

### Wave A: Deterministic rules

Resolve non-`BLE001` findings with the smallest behavior-preserving edits:

- collapse nested conditionals reported by `SIM102`;
- remove redundant exception interpolation reported by `TRY401`;
- use timezone-aware timestamps for `DTZ005` and `DTZ006`, preserving comparison and
  serialization contracts;
- replace mutable settings defaults with Pydantic `Field(default_factory=...)` for `RUF012`;
- bind loop variables correctly for `B023`;
- replace the mutable `ContextVar` default for `B039` using a Python 3.13-compatible pattern;
- add explicit subprocess `check=` behavior for `PLW1510` without unintentionally changing
  CLI failure policy;
- address `B005`, `B018`, `PLC0206`, `D205`, `TRY002`, and `TRY203` according to the intent of
  each site;
- retain the justified `S102` dynamic execution only when its AST validation and local
  security annotation remain intact.

Behavior-sensitive changes receive focused tests before implementation.

### Wave B: Internal exception narrowing

Replace broad catches with stable, explicit exception sets in implementation internals,
including:

- JSON and YAML parsing and serialization;
- filesystem and path operations;
- dynamic import and attribute lookup;
- Pydantic or schema validation;
- optional dependency and adapter resolution;
- subprocess and configuration operations.

Programming defects must propagate to the next legitimate boundary rather than being
misclassified as an expected fallback.

### Wave C: Intentional broad boundaries

A broad catch may remain around:

- external or user-supplied callbacks;
- adapter and plugin implementations;
- workflow action execution;
- MCP tool and resource protocol boundaries;
- template rendering boundaries;
- per-item processing in independent batches.

Every retained broad boundary must:

1. preserve traceback or structured failure details;
2. identify the failed operation or item;
3. avoid returning an unexplained truthy or success value; and
4. include a narrowly scoped `# noqa: BLE001` justification when Ruff cannot infer the
   boundary contract.

No global or per-file `BLE001` ignore will be added.

### Wave D: Directly exposed correctness defects

Correct defects identified through lint classification when they directly determine the safe
handler design. Priority cases include:

- sanitizer failure returning unsanitized input;
- subscriber failure being reported as successful delivery;
- partial MCP registration being marked fully initialized;
- failed callables becoming truthy template values;
- adapter, loader, or validator implementation failures being reported as ordinary absence or
  invalid user input;
- cleanup failure replacing the primary exception;
- resilient background loops failing silently without a health or log signal.

Unrelated defects discovered during implementation are recorded and reported, not folded into
this change.

### Wave E: Validation

Validate each domain before moving to the next, then run the complete repository gates.

## Exception Classification Policy

### Expected-failure internals

Low-level code must catch the smallest stable exception set because it knows which failures are
part of its contract. Unexpected implementation failures propagate.

### Pluggable execution boundaries

A framework boundary may catch `Exception` because third-party implementations can fail with
arbitrary exception types. It must convert failure into an explicit result or logged traceback.

### Batch-isolation boundaries

One item may fail without aborting an independent batch. The result or log must retain the
failed item identity and error. Silent `continue` is prohibited.

### Cleanup and rollback

Cleanup must not mask the primary failure. Secondary cleanup errors are logged or attached as
context, and queue or task bookkeeping remains balanced.

### Security-sensitive paths

Sanitization, validation, authentication, origin, and path-safety failures fail closed. An
unexpected error must not return the original potentially unsafe value or announce success.

## Testing Design

Before a behavior-sensitive fix, add or repair a test that demonstrates the required contract.
Priority tests cover:

- sanitizer failure rejects unsafe input;
- failed subscribers make delivery observably fail;
- partial MCP registration does not produce a successful initialized state;
- adapter and loader faults remain distinguishable from ordinary absence;
- generated cache closures bind the intended cache key;
- timezone-aware values preserve freshness comparisons and serialized timestamp contracts;
- retained broad boundaries emit structured diagnostics;
- package exports and external loader exception imports remain available.

Pure syntax or documentation rewrites may rely on existing tests when the relevant path is
already exercised.

## Verification Ladder

Run from `/Users/les/Projects/fastblocks`.

### Baseline and lint checks

```bash
uv run ruff check --no-fix fastblocks tests
uv run ruff format --check fastblocks tests
```

### Per-wave checks

- Run Ruff against only the changed files.
- Run the relevant domain tests with `--no-cov -n 0` to avoid whole-package coverage and xdist
  noise during focused feedback.
- Surface skipped integration tests with `-rs` when validating validation and workflow modules.

### Final checks

```bash
uv run ruff check --no-fix fastblocks tests
uv run ruff format --check fastblocks tests
uv run pytest
uv run crackerjack run
```

Also run a public import smoke check for FastBlocks template exports and the externally consumed
`jinja2_async_environment.loaders` exception classes.

If unrelated pre-existing failures remain, report them with exact commands and output. Do not
claim the repository is fully passing unless all requested gates pass.

## Working-tree Safety

- Capture status and changed-path inventories before editing.
- Touch only files required by the findings and their focused tests.
- Review diffs after every wave to separate existing changes from new edits.
- Compare the final path inventory with the baseline.
- Do not delete tracked backup artifacts, archived test data, or untracked template assets.
- Use sequential writes in the existing tree. Parallel agents may analyze or review but must
  not independently modify overlapping files.
- Do not commit, push, or rewrite history unless explicitly requested.

## Integration Contract

### Triggered from

The repository Ruff gate (`uv run ruff check --no-fix fastblocks tests`) and the Crackerjack
quality workflow.

### Returns to or updates

- Source-level exception contracts in affected FastBlocks modules.
- Focused tests that pin behavior-sensitive fallback and failure reporting.
- Ruff-compliant code without weakening project rule selection.

### Demonstrable by

- zero reported findings from the requested Ruff check;
- passing targeted tests for each modified domain;
- preserved public import smoke checks;
- passing full pytest and Crackerjack gates, or exact disclosure of unrelated pre-existing
  failures.

### Rollback signal

Rollback a wave if its focused tests regress documented fallback behavior, if a retained plugin
boundary starts leaking third-party exceptions, or if timestamp/public API contracts change
without an explicit compatibility test.

### Observability added

- traceback logging or structured error records at retained broad boundaries;
- failed-item identity in resilient batch processing;
- explicit failure state for event delivery, initialization, rendering, and validation paths.

## Acceptance Criteria

1. The reported Ruff findings are resolved without global or per-file rule suppression.
2. Every remaining broad catch is a justified framework boundary with diagnostics.
3. Security-sensitive failures fail closed.
4. Behavior-sensitive changes have focused regression tests.
5. Public imports remain compatible.
6. No unrelated working-tree files are absorbed into the remediation.
7. The final verification ladder is run and reported faithfully.

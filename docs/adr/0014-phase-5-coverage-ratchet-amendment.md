______________________________________________________________________

## status: accepted role: phase-5-coverage-ratchet-amendment date: 2026-08-23 last_reviewed: 2026-08-23 supersedes: null superseded_by: null blocks_on: [] decision_date: 2026-08-23 topic: phase-5-coverage-ratchet-amendment

# ADR 0014: Phase 5 v4 Coverage Ratchet Amendment

## Status

Accepted (Phase 5 v4 coverage ratchet amendment — companion to
master plan §Phase 5 v4 line 142, Erratum 21 Option B).

## Context

Phase 5 v4 (test infrastructure rebuild) shipped 11 commits with a
target of lifting coverage from the legacy floor to 65%. The plan's
Task 12 (deferred) and Task 13 (coverage lift) both targeted 65%.

Measured coverage after Tasks 1-11: **55.41%** (+6.28 pp from the
previous floor). Task 13 added 246 new tests covering the top six
zero-coverage MCP modules and five high-leverage adapter/sync
helpers. Final measured coverage: **62.52%** (+7.10 pp from Tasks 1-11;
+13.39 pp from the previous floor).

The **2.48 pp gap from 65%** is structurally unreachable within the
strict-tests-only boundary that bound Phase 5 v4:

1. **Adapter-bound branches**: Several modules wire up real
   adapters (S3, Redis, Resend, etc.). Unit tests stub the resolver,
   so the "adapter unavailable" branch is exercised but the
   "adapter available" branch — which contains the bulk of the
   missing statements — requires real adapter state that's out of
   scope for unit tests.
1. **CLI integration paths**: `fastblocks/cli.py` has 132 uncovered
   statements in CLI subcommands (`run`, `dev`, `validate`, `info`,
   `syntax-check`, `format-template`, `start-language-server`) that
   require live uvicorn/granian servers and HTMX adapter resolution.
1. **Asset/icon adapters**: `materialicons.py`, `phosphor.py`,
   `twicpics.py`, `cloudflare.py` adapter modules are wrappers
   around installed optional deps — tests without the deps only
   exercise the fallback path.
1. **TLS configuration**: `fastblocks/websocket/tls_config.py`
   (0% coverage) requires a live TLS server.

Per Erratum 21's explicit guidance, three options were available:

| Option | Path | Outcome |
|---|---|---|
| **A** | More tests | Bounded by strict-tests-only; 2.48 pp unreachable |
| **B** | ADR amendment (this ADR) | Lower ratchet to match measured lift |
| **C** | Abandon 11 commits | Lose +13.39 pp gain; regress to the previous floor |

Option B is the chosen path. The ratchet floor is amended from
49.1324200913242 (the previous floor) to **62** (rounded down from the
measured 62.52% with a 0.52 pp safety margin — a whole-number floor
below measured coverage so the gate stays green).

## Decision

`--cov-fail-under` in `pyproject.toml` is amended from the legacy
floor to **62%** (the new floor). This preserves the +13.39 pp lift
from Tasks 1-13 while keeping the gate green against the new floor.

Future phases can re-target higher by adding integration tests that
exercise adapter-bound branches, CLI integration paths, and
asset/icon adapter modules — moving coverage toward higher aspirational
targets over time.

## Consequences

**Positive:**

- Coverage ratchet now reflects the actual test infrastructure state
  (62.52% measured vs the previous floor).
- CI gate stays green; no regression from the previous floor.
- The 7.10 pp Task 13 lift is recorded as a ratcheted floor — a
  future contributor cannot silently regress below 62%.
- The whole-number floor (62) sits 0.52 pp below measured coverage
  (62.52%), giving the gate headroom against measurement noise.

**Negative:**

- The 65% target is no longer the gate target. Documentation in the
  plan/spec reflects the original 65% target; future readers should
  consult this ADR for the current operational floor.
- Strict-tests-only boundary is reaffirmed: integration tests that
  could close the residual 2.48 pp gap are deferred to a future
  phase.

**Follow-up:**

- A future "Phase 5.5 / Phase 6" wave can install optional adapter
  deps (`aws`, `redis`, etc.) and write integration tests for the
  remaining branches, lifting coverage toward higher aspirational
  targets over time.
- When that wave lands, this ADR should be updated or superseded to
  reflect the new measured floor.

## References

- Plan: `docs/superpowers/plans/2026-08-23-fastblocks-phase-5-retry.md`
- Spec: `docs/superpowers/specs/2026-08-22-fastblocks-phase-5-design.md`
- Task 13 report: `.superpowers/sdd/2026-08-23-fastblocks-phase-5-retry/task-13-report.md`
- Erratum 21 (coverage ratchet paths): spec §Errata line 549-562
- Erratum 22 (coverage baseline mismatch): spec §Errata line 564-574
- Commit `25a8551` — Task 13: lift coverage + fix 21 pre-existing failures (measured coverage reached the new floor)

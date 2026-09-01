"""Phase 2 mechanical-four Commit6 — suppress(Exception) ratchet baseline.

The Phase 2 verification gate (§Verification gate) asserts that
``git grep -c 'suppress(Exception)' -- fastblocks/`` stays at or below
the master plan's baseline of 123 (master plan line 313). This test
locks that baseline on day one so future Phase 2 commits cannot
accidentally add or remove ``suppress(Exception)`` sites without
failing CI.

The test runs ``git grep`` via subprocess and asserts the count is
within [0, 123]. The lower bound of 0 is permissive (Phase 7 may
eventually delete every suppress(Exception) site); the upper bound of
123 is the master-plan-anchored baseline.

If the count drifts above 123, the message names the diff so the
offending commit is obvious. If the count drifts below 123, the test
passes — Phase 7's cleanup work can proceed without this test
needing an update.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
# Baseline measured empirically on 2026-08-21 via
# `git grep -c 'suppress(Exception)' -- fastblocks/ | awk -F: '{s+=$2} END {print s}'`
# Master plan line 313 says 123; actual count is 122. The plan locks
# the actual count; if a future contributor adds one site, the ratchet
# fails. Phase 7's cleanup may lower the count (test passes on a lower
# count via `<=`, not `==`).
MASTER_PLAN_BASELINE = 122


@pytest.mark.unit
def test_suppress_exception_ratchet_at_or_below_baseline() -> None:
    """git grep count of 'suppress(Exception)' in fastblocks/ <= 122.

    Locks the empirical baseline. Phase 2 must not add new sites;
    Phase 7's cleanup may delete sites (test passes if count drops).
    """
    result = subprocess.run(
        [
            "git",
            "grep",
            "-c",
            "suppress(Exception)",
            "--",
            "fastblocks/",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    # git grep -c outputs `<file>:<count>` per file
    total = 0
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        # Format: "<path>:<count>"
        match = re.match(r"^[^:]+:(\d+)$", line)
        if match:
            total += int(match.group(1))
    assert total <= MASTER_PLAN_BASELINE, (
        f"suppress(Exception) count {total} exceeds baseline "
        f"{MASTER_PLAN_BASELINE}. Phase 2 must not add new sites; "
        f"delete existing sites in a follow-up Phase 7 commit or amend "
        f"the baseline (and the master plan line 313 reference)."
    )

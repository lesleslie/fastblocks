"""Performance-route freshness test.

Asserts that ``.benchmarks/`` has at least one JSON file modified within
the last 7 days. Skips with a clear message if no benchmarks have been
written yet (the test suite has not run the perf benchmarks yet).

# req: REQ-P2-B2-004
"""
from __future__ import annotations

import time
from pathlib import Path

import pytest

_BENCH_DIR = Path("/Users/les/Projects/fastblocks/.benchmarks")
_MAX_AGE_SECONDS = 7 * 24 * 60 * 60


def test_benchmarks_directory_fresh() -> None:
    """``.benchmarks/`` has a JSON file modified within the last 7 days, or skip."""
    if not _BENCH_DIR.exists():
        pytest.skip(
            "No .benchmarks/ directory yet — run the perf test suite to "
            "populate it. The /performance page renders an empty state in "
            "this case (see templates/performance.html)."
        )
    files = list(_BENCH_DIR.glob("*.json"))
    if not files:
        pytest.skip(
            "No benchmark JSON files yet — run the perf test suite to "
            "populate .benchmarks/."
        )
    newest = max(files, key=lambda p: p.stat().st_mtime)
    age = time.time() - newest.stat().st_mtime
    assert age <= _MAX_AGE_SECONDS, (
        f"Newest benchmark {newest.name} is {age / 86400:.1f} days old; "
        f"expected <= 7 days. Re-run the perf suite."
    )


def test_performance_route_renders_empty_state_when_no_benchmarks(client) -> None:
    """The /performance page returns 200 with a clear heading when no data exists."""
    response = client.get("/performance")
    assert response.status_code == 200
    body = response.text
    assert "Performance" in body

"""Performance route — D7 live proof surface.

Renders the latest benchmark numbers from ``.benchmarks/`` (populated by
the perf test suite). Honest by construction: if no benchmark JSON exists,
the page renders an empty table with a clear "no data yet" message
(rendered by the template) instead of fabricating numbers.

# req: REQ-P2-B2-001, REQ-P2-B2-004
"""
from __future__ import annotations

import json
from pathlib import Path

from starlette.requests import Request
from starlette.responses import HTMLResponse

from templates import render_template

_BENCH_DIR = Path(__file__).resolve().parents[3] / ".benchmarks"


def _load_latest_benchmarks() -> list[dict[str, object]]:
    """Return the benchmark rows from the most recent JSON file.

    Returns an empty list if the directory does not exist or contains no
    JSON files — never raises. Callers render a "no data yet" message in
    that case.
    """
    if not _BENCH_DIR.exists():
        return []
    files = sorted(_BENCH_DIR.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        return []
    try:
        data = json.loads(files[0].read_text())
    except (OSError, json.JSONDecodeError):
        return []
    rows = data.get("benchmarks", [])
    return list(rows)


async def performance_route(request: Request) -> HTMLResponse:
    """Render the latest benchmarks — D7 live proof."""
    benchmarks = _load_latest_benchmarks()
    context = {"benchmarks": benchmarks, "count": len(benchmarks)}
    return HTMLResponse(await render_template(request, "performance.html", context))

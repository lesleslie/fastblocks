"""Adapter-matrix route — auto-generated D3 proof surface.

Lists every adapter candidate currently registered in the FastBlocks-owned
Oneiric resolver. A row is marked ``✓`` iff
``tests/adapters/<domain>/<key>/test_boot.py`` exists on disk. Honest by
construction: never mark a candidate as boot-tested without a real
passing test.

The brief's pseudocode used ``oneiric.core.resolution.resolve_adapters``
which is not a real public function in the installed Oneiric; this
implementation iterates the resolver's registry directly via the
``_candidates`` mapping (the same internal API the FastBlocks facade
uses for diagnostics — see ``fastblocks.core.resolver``).

# req: REQ-P2-B2-001, REQ-P2-B2-003
"""
from __future__ import annotations

from pathlib import Path

from fastblocks.core.resolver import get_resolver
from starlette.requests import Request
from starlette.responses import HTMLResponse

from templates import render_template

_REPO_ROOT = Path("/Users/les/Projects/fastblocks")


def _gather_candidates() -> list[dict[str, object]]:
    """Return one row per registered Oneiric candidate in the fastblocks domain.

    We scope to ``domain == "fastblocks"`` to surface the framework-owned
    adapter surface (template_handler, admin_handler, health, validation,
    fastblocks_workflows, etc.). The full resolver dump would also include
    Oneiric and mcp-common candidates, which belong on a different page.
    """
    resolver = get_resolver()
    rows: list[dict[str, object]] = []
    for (domain, key), candidates in sorted(resolver.registry._candidates.items()):
        if domain != "fastblocks":
            continue
        for cand in candidates:
            rows.append(
                {
                    "domain": domain,
                    "key": key,
                    "provider": cand.provider or "(default)",
                    "priority": cand.priority,
                    "stack_level": cand.stack_level,
                    "boot_tested": _is_boot_tested(domain, key),
                    "source": cand.source.value,
                }
            )
    return rows


def _is_boot_tested(domain: str, key: str) -> bool:
    """Return True iff ``tests/adapters/<domain>/<key>/test_boot.py`` exists."""
    test_path = _REPO_ROOT / "tests" / "adapters" / domain / key / "test_boot.py"
    return test_path.exists()


async def adapter_matrix_route(request: Request) -> HTMLResponse:
    """Render the adapter matrix — D3 live proof surface."""
    rows = _gather_candidates()
    context = {"rows": rows, "total": len(rows)}
    return HTMLResponse(await render_template(request, "adapter_matrix.html", context))

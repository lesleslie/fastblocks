"""Adapter-matrix route — spec §D3 in-scope adapter enumeration.

Lists every adapter the spec marks as in-scope for the dogfood-readiness
D3 dimension: the ones the starter + landing exercise and whose boot
status is the live proof surface.

A row is marked ``✓`` for two independent gates:

* **resolver** — `tests/adapters/<domain>/<key>/test_boot.py` exists, OR
  for middleware rows the relevant `tests/middleware/test_<name>.py`
  exists.
* **adapter** — `get_resolver().resolve(domain, key)` returns a
  registered Oneiric candidate (None for middleware rows; middleware
  lives in `fastblocks/middleware.py`, not the resolver).

Spec §D3 in-scope set (single source of truth — see
`docs/superpowers/specs/2026-09-27-fastblocks-dogfood-readiness-design.md`
§D3 and the verify report §D3 entry):

* `templates/jinja2`              → `("fastblocks", "templates")`
* `templates/_async_renderer`     → `("fastblocks", "async_template_renderer")`
* `style/fastblocks_ui`           → `("fastblocks", "styles")`
* `icons` (one default set)       → `("fastblocks", "icons")`
* `fonts/squirrel`                → `("fastblocks", "font_squirrel")`
* `middleware/brotli`             → middleware (not a resolver adapter)
* `middleware/csrf`               → middleware (not a resolver adapter)
* `middleware/security_headers`   → middleware (not a resolver adapter)

The brief's pseudocode listed `("templates", "jinja2")` etc. as
resolver pairs; the real Oneiric registrations all live under
`domain="fastblocks"` with these domain-specific keys (verified at
`fastblocks/adapters/templates/jinja2.py:1125`,
`_async_renderer.py:723`, `style/fastblocks_ui.py:203`, `icons/_base.py:48`,
`fonts/squirrel.py:55`). This module maps the conceptual spec label to
the actual resolver pair so a single `r.resolve(domain, key)` check
works end-to-end.

The route was previously an iterator over `resolver.registry._candidates`
(filtered to `domain == "fastblocks"`); that surfaced framework handlers
(`template_handler`, `admin_handler`, `health`, `validation`,
`fastblocks_workflows`) instead of the spec §D3 in-scope adapters, so
`/adapter-matrix` rendered `?` for every row in the verify report. The
fix narrows the enumeration to the spec's in-scope set and replaces the
"any registered candidate" view with a "spec-scoped" one.

# req: REQ-P2-B2-001, REQ-P2-B2-003
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from landing_templates import render_template
from starlette.requests import Request
from starlette.responses import HTMLResponse
from fastblocks.core.resolver import get_resolver

_REPO_ROOT = Path(__file__).resolve().parents[3]

_DOMAIN: Final = "fastblocks"


# Spec §D3 in-scope adapter enumeration (single source of truth).
#
# Tuple shape: (spec_label, resolver_key_or_None, boot_test_relative_path).
# - `resolver_key` is the Oneiric candidate key to query against
#   `domain="fastblocks"`. `None` means the row is middleware-resident
#   (not a Oneiric adapter) — the resolver check is skipped.
# - `boot_test_relative_path` is the path under `_REPO_ROOT` whose
#   existence flips the row to `boot_tested=True`. Task 7
#   (F1.5-D3-T2) populates the adapter paths; the middleware paths
#   already exist (`tests/middleware/test_csrf.py`,
#   `tests/middleware/test_security_headers.py`); Brotli has no
#   dedicated test yet — surfaces as `?` honestly.
_IN_SCOPE_ADAPTERS: Final[tuple[tuple[str, str | None, str], ...]] = (
    ("templates/jinja2", "templates", "tests/adapters/templates/test_boot.py"),
    (
        "templates/_async_renderer",
        "async_template_renderer",
        "tests/adapters/templates/test_async_renderer_boot.py",
    ),
    (
        "style/fastblocks_ui",
        "styles",
        "tests/adapters/style/test_fastblocks_ui_boot.py",
    ),
    ("icons/default", "icons", "tests/adapters/icons/test_icons_boot.py"),
    (
        "fonts/squirrel",
        "font_squirrel",
        "tests/adapters/fonts/test_fonts_boot.py",
    ),
    ("middleware/brotli", None, "tests/middleware/test_brotli.py"),
    ("middleware/csrf", None, "tests/middleware/test_csrf.py"),
    (
        "middleware/security_headers",
        None,
        "tests/middleware/test_security_headers.py",
    ),
)


def _gather_rows() -> list[dict[str, object]]:
    """Return one row per spec §D3 in-scope adapter.

    Each row carries the fields the existing template
    (``templates/adapter_matrix.html``) expects:

    - ``domain``: the Oneiric domain (``"fastblocks"``) or
      ``"—"`` for middleware-resident rows.
    - ``key``: the resolver key, or ``"—"`` for middleware.
    - ``provider``: a short status string — ``"✓ resolved"`` when
      the Oneiric resolver returns a Candidate for the row, or
      ``"? not registered"`` otherwise. Middleware rows render as
      ``"module-resident"`` since middleware isn't a resolver
      concern.
    - ``priority``: priority of the resolved Candidate (``"—"`` when
      not resolved or when middleware).
    - ``stack_level``: stack_level of the resolved Candidate
      (``"—"`` when not resolved or when middleware).
    - ``boot_tested``: ``True`` iff the row's documented
      ``tests/adapters/...test_boot.py`` path exists on disk.
    - ``source``: source enum string of the resolved Candidate
      (``"—"`` when not resolved or when middleware).
    - ``spec_label``: the conceptual spec §D3 path (e.g.
      ``"templates/jinja2"``) — surfaced so the row reads
      unambiguously even when two rows share a domain.
    """
    resolver = get_resolver()
    rows: list[dict[str, object]] = []
    for spec_label, resolver_key, boot_test_relpath in _IN_SCOPE_ADAPTERS:
        candidate = resolver.resolve(_DOMAIN, resolver_key) if resolver_key else None
        is_resolved = candidate is not None
        boot_tested = (_REPO_ROOT / boot_test_relpath).exists()
        if resolver_key is None:
            rows.append(
                {
                    "domain": "—",
                    "key": "—",
                    "provider": "module-resident",
                    "priority": "—",
                    "stack_level": "—",
                    "boot_tested": boot_tested,
                    "source": "—",
                    "spec_label": spec_label,
                    "resolved": False,
                }
            )
            continue
        rows.append(
            {
                "domain": _DOMAIN,
                "key": resolver_key,
                "provider": "✓ resolved" if is_resolved else "? not registered",
                "priority": candidate.priority if is_resolved else "—",
                "stack_level": candidate.stack_level if is_resolved else "—",
                "boot_tested": boot_tested,
                "source": candidate.source.value if is_resolved else "—",
                "spec_label": spec_label,
                "resolved": is_resolved,
            }
        )
    return rows


async def adapter_matrix_route(request: Request) -> HTMLResponse:
    """Render the adapter matrix — D3 spec-scoped proof surface."""
    rows = _gather_rows()
    context = {"rows": rows, "total": len(rows)}
    return HTMLResponse(await render_template(request, "adapter_matrix.html", context))

"""Docs route — link to full docs.

# req: REQ-P2-B2-001
"""

from __future__ import annotations

from fastblocks_ui import button
from landing_templates import render_template
from starlette.requests import Request
from starlette.responses import HTMLResponse


async def docs_route(request: Request) -> HTMLResponse:
    """Render the docs landing — link to full docs + CTA."""
    context = {
        "cta": button(
            href="https://github.com/lesleslie/fastblocks", label="Full docs on GitHub"
        ),
    }
    return HTMLResponse(await render_template(request, "docs.html", context))

"""Install route — one-command install + 3-line hello-world.

# req: REQ-P2-B2-001
"""
from __future__ import annotations

from fastblocks_ui import button
from starlette.requests import Request
from starlette.responses import HTMLResponse

from templates import render_template


async def install_route(request: Request) -> HTMLResponse:
    """Render the install page — one-command install + hello-world."""
    context = {
        "cta": button(href="/demo", label="See it live"),
    }
    return HTMLResponse(await render_template(request, "install.html", context))

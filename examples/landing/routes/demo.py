"""Demo route — search-as-you-type HTMX pattern.

Mirrors the B1 starter's ``routes/demo.py`` (REQ-P2-B1-005). The route
serves a full page on a normal GET and an HTMX fragment when the
``HX-Request`` header is present, demonstrating the dual-response pattern
that fastblocks-ui apps use to keep server logic simple.

# req: REQ-P2-B2-001
"""
from __future__ import annotations

from fastblocks_ui import field, text_input
from starlette.requests import Request
from starlette.responses import HTMLResponse

from templates import render_template

_PARTIAL_TEMPLATE = "partials/results.html"
_PAGE_TEMPLATE = "demo.html"


async def demo_route(request: Request) -> HTMLResponse:
    """Search-as-you-type HTMX demo."""
    q = request.query_params.get("q", "")
    results = _fake_search(q) if q else []
    context = {
        "field": field(label="Search", input=text_input(name="q", value=q)),
        "results": results,
    }
    if request.headers.get("HX-Request"):
        return HTMLResponse(
            await render_template(request, _PARTIAL_TEMPLATE, context)
        )
    return HTMLResponse(await render_template(request, _PAGE_TEMPLATE, context))


def _fake_search(q: str) -> list[str]:
    """Placeholder search — replace with real query in consumer app."""
    corpus = [
        "alpha",
        "beta",
        "gamma",
        "delta",
        "fastblocks",
        "htmx",
        "jinja2",
        "oneiric",
    ]
    return [w for w in corpus if q.lower() in w][:5]

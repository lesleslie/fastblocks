"""Greeting route — three render modes (?render=jinja|htmy|hybrid).

Each mode produces semantically equivalent markup for the same
GreetingCard (HTMY component) so the consumer can swap renderers
without rewriting client code. The render-mode is also surfaced as
an HTML comment so the snapshot test can strip it before comparing.

# req: REQ-P2-B3-002
"""
from __future__ import annotations

from htmy import Renderer
from starlette.requests import Request
from starlette.responses import HTMLResponse

from components.greeting_card import GreetingCardProps, greeting_card
from templates import render_template as render_jinja

_PROPS = GreetingCardProps(
    name="Ada Lovelace",
    avatar="/static/ada.png",
    bio="First programmer.",
)

# Templates per render mode. The Jinja2 templates both extend base.html;
# the hybrid template embeds the HTMY-rendered card via {{ component_html | safe }}.
_JINJA_TEMPLATE = "greeting/jinja.html"
_HYBRID_TEMPLATE = "greeting/hybrid.html"


async def greeting_route(request: Request) -> HTMLResponse:
    """Render the greeting card via the chosen renderer.

    Query string controls the render mode:
    - ``render=jinja`` — pure Jinja2 (macro in ``greeting/_macros.html``)
    - ``render=htmy`` — pure HTMY component
    - ``render=hybrid`` — HTMY component rendered to HTML, then embedded
      inside a Jinja2 layout (the spirit of HybridTemplatesManager)
    """
    mode = (request.query_params.get("render") or "hybrid").lower()
    if mode == "htmy":
        body = await _render_htmy()
    elif mode == "jinja":
        body = await render_jinja(request, _JINJA_TEMPLATE, {})
    elif mode == "hybrid":
        body = await _render_hybrid(request)
    else:
        body = await _render_hybrid(request)

    return HTMLResponse(body)


async def _render_htmy() -> str:
    """Render the GreetingCard via HTMY directly."""
    body = await Renderer().render(greeting_card(_PROPS))
    # Wrap in the same base.html shell so the response shape matches
    # the other modes — the snapshot test asserts on the inner card,
    # not the wrapper.
    return (
        "<!DOCTYPE html><html lang=\"en\">"
        "<head><meta charset=\"utf-8\"><title>HTMY Hybrid Demo</title></head>"
        "<body><!--render:htmy-->" + body + "</body></html>"
    )


async def _render_hybrid(request: Request) -> str:
    """Render via the hybrid path: HTMY component embedded in a Jinja2 layout.

    ``HybridTemplatesManager`` does not expose a ``render_hybrid(component,
    layout=...)`` API in the version installed here (see the report's
    ``HybridTemplatesManager_quirks`` section), so we compose the two
    engines manually: render the HTMY component to a string, then pass
    it as ``component_html`` into a Jinja2 layout template.
    """
    component_html = await Renderer().render(greeting_card(_PROPS))
    return await render_jinja(
        request,
        _HYBRID_TEMPLATE,
        {"component_html": component_html},
    )
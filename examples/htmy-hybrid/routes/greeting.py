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
_BASE_TEMPLATE = "base.html"

_VALID_MODES = frozenset({"jinja", "htmy", "hybrid"})


async def greeting_route(request: Request) -> HTMLResponse:
    """Render the greeting card via the chosen renderer.

    Query string controls the render mode:
    - ``render=jinja`` — pure Jinja2 (macro in ``greeting/_macros.html``)
    - ``render=htmy`` — pure HTMY component
    - ``render=hybrid`` — HTMY component rendered to HTML, then embedded
      inside a Jinja2 layout (the spirit of HybridTemplatesManager)

    Unknown render modes return a 400 with an explicit error message so
    typos in ``?render=...`` are surfaced instead of silently falling
    back to hybrid output.
    """
    mode = (request.query_params.get("render") or "hybrid").lower()
    if mode not in _VALID_MODES:
        return HTMLResponse(
            f"Unknown render mode: {mode!r}. Expected one of: {sorted(_VALID_MODES)}.",
            status_code=400,
        )

    if mode == "htmy":
        component_html = await _render_component_html()
        body = await _render_base(request, component_html, "htmy")
    elif mode == "jinja":
        body = await render_jinja(request, _JINJA_TEMPLATE, {})
    else:  # hybrid — passed the membership check above.
        component_html = await _render_component_html()
        body = await render_jinja(
            request,
            _HYBRID_TEMPLATE,
            {"component_html": component_html},
        )

    return HTMLResponse(body)


async def _render_component_html() -> str:
    """Render the GreetingCard HTMY component to an HTML string.

    Shared by the pure-HTMY mode (``_render_base``) and the hybrid branch
    above — both need the same component output.
    """
    return await Renderer().render(greeting_card(_PROPS))


async def _render_base(request: Request, content: str, render_mode: str) -> str:
    """Wrap ``content`` in the shared base.html shell with a per-mode marker.

    ``base.html`` defaults its ``{% block content %}`` to ``{{ content | safe }}``,
    so direct renders inject the supplied content while child templates
    (``greeting/jinja.html``, ``greeting/hybrid.html``) can still override
    the block. The ``<!--render:<mode>-->`` marker is placed inside the
    body so the snapshot test can strip it before comparing.
    """
    return await render_jinja(
        request,
        _BASE_TEMPLATE,
        {"content": f"<!--render:{render_mode}-->{content}"},
    )

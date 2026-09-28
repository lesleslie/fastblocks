"""Greeting route — three render modes (?render=jinja|htmy|hybrid).

Each mode produces semantically equivalent markup for the same
GreetingCard (HTMY component) so the consumer can swap renderers
without rewriting client code. The render-mode is also surfaced as
an HTML comment so the snapshot test can strip it before comparing.

The ``hybrid`` mode exercises the framework's
``HybridTemplatesManager.render_hybrid`` API (F1.5-F-FW-1) so the
demo is an end-to-end test of the Jinja2+HTMY composition contract.

# req: REQ-P2-B3-002
"""
from __future__ import annotations

from pathlib import Path

from htmy import Renderer
from jinja2 import Environment, FileSystemLoader
from starlette.requests import Request
from starlette.responses import HTMLResponse

from components.greeting_card import (
    GreetingCardProps,
    greeting_card,
    greeting_card_from_context,
)
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

# Lazily-initialised HybridTemplatesManager used by the ``hybrid`` branch.
# The manager's Jinja2 environment is pointed at the demo's templates
# directory so the framework and the demo's own Jinja2 wrapper resolve
# the same template paths.
_hybrid_manager: "HybridTemplatesManager | None" = None


def _get_hybrid_manager() -> "HybridTemplatesManager":
    """Return the lazily-initialised ``HybridTemplatesManager`` for this demo."""
    global _hybrid_manager
    if _hybrid_manager is None:
        from fastblocks.adapters.templates._advanced_manager import (
            HybridTemplatesManager,
        )

        _hybrid_manager = HybridTemplatesManager()
        # Wire the manager's env to the demo's templates directory so
        # ``render_hybrid`` can resolve ``greeting/hybrid.html`` etc.
        # The manager's own ``base_templates`` field stays None — the
        # demo bypasses the full FastBlocks template stack — but
        # ``_get_template_environment`` falls back to the env we set.
        templates_dir = Path(__file__).resolve().parent.parent / "templates"
        env = Environment(
            loader=FileSystemLoader(str(templates_dir)),
            autoescape=True,
        )
        # Stub out ``base_templates`` with a shape that exposes the env
        # at ``base_templates.app.env`` — that's what
        # ``_get_template_environment`` reads.
        from types import SimpleNamespace

        _hybrid_manager.base_templates = SimpleNamespace(app=SimpleNamespace(env=env))
    return _hybrid_manager


async def greeting_route(request: Request) -> HTMLResponse:
    """Render the greeting card via the chosen renderer.

    Query string controls the render mode:
    - ``render=jinja`` — pure Jinja2 (macro in ``greeting/_macros.html``)
    - ``render=htmy`` — pure HTMY component
    - ``render=hybrid`` — framework's ``HybridTemplatesManager.render_hybrid``
      composes the HTMY component into a Jinja2 layout

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
        manager = _get_hybrid_manager()
        body = await manager.render_hybrid(
            jinja_template=_HYBRID_TEMPLATE,
            htmy_component=greeting_card_from_context,
            context={"props": _PROPS},
        )

    return HTMLResponse(body)


async def _render_component_html() -> str:
    """Render the GreetingCard HTMY component to an HTML string.

    Shared by the pure-HTMY mode (``_render_base``). The hybrid branch
    goes through ``HybridTemplatesManager.render_hybrid`` instead, so
    it does not call this helper.
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

"""Landing route — hero + 3-bullet 'why FastBlocks' + CTA.

Uses the fastblocks-ui helpers (``shell``, ``navbar``, ``hero``, ``card``,
``button``) which return SafeHTML strings — Jinja2 renders them via
``|safe``.

# req: REQ-P2-B2-001
"""

from __future__ import annotations

from fastblocks_ui import button, card, hero, navbar, shell
from landing_templates import render_template
from starlette.requests import Request
from starlette.responses import HTMLResponse


async def home_route(request: Request) -> HTMLResponse:
    """Landing hero + 3-bullet 'why FastBlocks' + CTA."""
    cards_markup = "".join(
        [
            card(header="Async", body="Concurrent template rendering."),
            card(header="Typed", body="Pydantic models + Oneiric config."),
            card(header="Honest", body="No claim without a passing test."),
        ]
    )
    navbar_markup = navbar(brand="FastBlocks", is_sticky=True)
    hero_markup = hero(
        title="FastBlocks",
        subtitle="Async web framework on Starlette + HTMX",
        cta=button(href="/demo", label="See it in action"),
    )
    # ``shell`` wraps the main content in ``<div class="ui-shell"><main>...``
    main_markup = shell(f"{navbar_markup}{hero_markup}{cards_markup}")
    context = {"main": main_markup}
    return HTMLResponse(await render_template(request, "home.html", context))

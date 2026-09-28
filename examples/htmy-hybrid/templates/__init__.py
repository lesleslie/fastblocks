"""Thin Jinja2 wrapper used by the B3 greeting route.

Mirrors the B1 starter's ``templates/__init__.py`` and B2 landing's
``templates/__init__.py``. The full FastBlocks framework resolves a
registered template adapter via Oneiric; this scaffold exposes a
``render_template`` coroutine backed by Jinja2 so the routes are
runnable without going through the Oneiric resolver at scaffold time.

# req: REQ-P2-B3-001
"""
from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from starlette.requests import Request

_TEMPLATES_DIR = Path(__file__).parent
_ENVIRONMENT = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=True,
)


async def render_template(
    request: Request, name: str, context: dict[str, object] | None = None
) -> str:
    """Render a Jinja2 template to a string.

    ``context`` is merged on top of ``{"request": request}`` so templates
    can use ``{{ request.url }}`` etc.
    """
    merged: dict[str, object] = {"request": request}
    if context:
        merged.update(context)
    return _ENVIRONMENT.get_template(name).render(merged)
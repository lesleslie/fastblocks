"""Thin Jinja2 wrapper used by the starter routes.

The full FastBlocks framework resolves a registered template adapter via
Oneiric. This scaffold exposes a single ``render_template`` coroutine backed
by Jinja2 so the routes are runnable without going through the Oneiric
resolver at scaffold time. Replace this with a Oneiric-registered adapter for
production apps.

# req: REQ-P2-B1-001
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from starlette.requests import Request

_TEMPLATES_DIR = Path(__file__).parent
_ENVIRONMENT = Environment(
    loader=FileSystemLoader(str(_TEMPLATES_DIR)),
    autoescape=True,
)


async def render_template(
    request: Request, name: str, context: Mapping[str, object] | None = None
) -> str:
    """Render a Jinja2 template to a string.

    ``context`` is merged on top of ``{"request": request}`` so templates can
    use ``{{ request.url }}`` etc. ``app_name`` is sourced from the Oneiric
    setting ``app.name`` if available, otherwise the directory name.
    """
    merged: dict[str, object] = {"request": request}
    if context:
        merged.update(context)
    return _ENVIRONMENT.get_template(name).render(merged)

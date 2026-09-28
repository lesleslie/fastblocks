"""Thin Jinja2 wrapper used by the landing routes.

Mirrors the B1 starter's `templates/__init__.py` (REQ-P2-B1-001). The full
FastBlocks framework resolves a registered template adapter via Oneiric;
this scaffold exposes a single ``render_template`` coroutine backed by
Jinja2 so the routes are runnable without going through the Oneiric
resolver at scaffold time. Production apps should register the
``HybridTemplatesManager`` via ``register_default_adapters``.

# req: REQ-P2-B2-001
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
    can use ``{{ request.url }}`` etc. ``app_name`` is intentionally not
    surfaced here — the scaffold deliberately avoids pulling oneiric
    settings at template-render time; routes that need ``app.name``
    should resolve it via oneiric explicitly and pass it in ``context``.
    """
    merged: dict[str, object] = {"request": request}
    if context:
        merged.update(context)
    return _ENVIRONMENT.get_template(name).render(merged)

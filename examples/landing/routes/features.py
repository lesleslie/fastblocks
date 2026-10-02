"""Features route — per-feature section with cards.

Each feature is a ``ui-section`` containing a ``ui-card`` with title +
body. ``[data-reveal]`` is applied at the template level (per-element IO
observer, skipped under reduced-motion via the fastblocks-ui runtime).

# req: REQ-P2-B2-001
"""

from __future__ import annotations

from dataclasses import dataclass

from fastblocks_ui import card, section
from starlette.requests import Request
from starlette.responses import HTMLResponse
from templates import render_template


@dataclass(frozen=True)
class Feature:
    """Single feature row — title + one-line body."""

    title: str
    body: str


_FEATURES: tuple[Feature, ...] = (
    Feature("Async everywhere", "Starlette + asyncio from the ground up."),
    Feature("Type-safe", "Pydantic models and Oneiric config layers."),
    Feature("HTMX-native", "Stable-id fragment swaps, no client JS framework."),
    Feature("Honest by construction", "No claim without a passing test."),
    Feature("Adapter-driven", "Oneiric resolver picks the right backend."),
    Feature("Theme discipline", "`--ui-*` tokens only, no `--fb-*` drift."),
)


async def features_route(request: Request) -> HTMLResponse:
    """Per-feature section + cards."""
    sections_markup = "".join(
        section(title=f.title, body=card(title=f.title, body=f.body)) for f in _FEATURES
    )
    context = {"sections_markup": sections_markup}
    return HTMLResponse(await render_template(request, "features.html", context))

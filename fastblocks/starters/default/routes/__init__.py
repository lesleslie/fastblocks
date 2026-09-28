from __future__ import annotations

from fastblocks.applications import FastBlocks

from .demo import demo_route
from .home import home_route

# req: REQ-P2-B1-001, REQ-P2-B1-005


def register_routes(app: FastBlocks) -> None:
    """Register all routes with the FastBlocks app."""
    app.add_route("/", home_route)
    app.add_route("/demo", demo_route)

"""Routes package — registers the B3 greeting route.

# req: REQ-P2-B3-001
"""

from __future__ import annotations

from fastblocks.applications import FastBlocks

from .greeting import greeting_route


def register_routes(app: FastBlocks) -> None:
    """Register the B3 greeting route with the FastBlocks app."""
    app.add_route("/", greeting_route)

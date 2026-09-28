"""FastBlocks landing-page app — dogfood demo of the framework itself.

This is the B2 deliverable for the Phase 2 dogfood-readiness build wave.
Eight routes, all auto-resolved through Oneiric, all themed via the
`--ui-*` token surface. See `examples/landing/README.md` for the route map
and the integration contract.

# req: REQ-P2-B2-001
"""
from __future__ import annotations

from fastblocks.applications import FastBlocks

from routes import register_routes


def create_app() -> FastBlocks:
    """Application factory — Oneiric resolves adapters via settings/."""
    app = FastBlocks()
    register_routes(app)
    return app


app = create_app()


def cli() -> None:
    """CLI entry — runs uvicorn against the ASGI app on port 8001."""
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8001)


if __name__ == "__main__":
    cli()

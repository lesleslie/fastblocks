"""FastBlocks app entry point — HTMY ↔ Jinja2 hybrid demo (B3).

ASGI-compatible; run with `uv run fastblocks run` (or `uvicorn main:app`).
Visit `/?render=<jinja|htmy|hybrid>` to compare all three render modes.

# req: REQ-P2-B3-001
"""

from __future__ import annotations

from routes import register_routes
from fastblocks.applications import FastBlocks


def create_app() -> FastBlocks:
    """Application factory — Oneiric resolves adapters via settings/."""
    app = FastBlocks()
    register_routes(app)
    return app


app = create_app()


def cli() -> None:
    """CLI entry — runs uvicorn against the ASGI app on port 8002."""
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8002)


if __name__ == "__main__":
    cli()

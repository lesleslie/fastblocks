"""Read-only MCP introspection surface for the scaffolded app.

Exposes ``list_routes`` and ``render_template`` so an AI assistant can
discover the app's surface and preview a template with a sample context. No
mutating tools — per framework policy the MCP surface is read-only and
product operations belong in the consumer application, not here.

# req: REQ-P2-B1-001
"""
from __future__ import annotations

import json

from fastmcp import FastMCP
from fastblocks.starters.default.templates import render_template

mcp = FastMCP(name="{app_name}-mcp")


@mcp.tool()
async def list_routes() -> str:
    """Return the registered app routes as a JSON list."""
    from main import app

    routes = [{"path": getattr(route, "path", str(route))} for route in app.routes]
    return json.dumps(routes)


@mcp.tool()
async def render_template_tool(
    name: str, context: dict[str, object] | None = None
) -> str:
    """Render a Jinja2 template to a string. ``context`` is optional."""
    from starlette.requests import Request

    fake_scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "raw_path": b"/",
        "query_string": b"",
        "headers": [],
        "client": ("127.0.0.1", 8000),
        "server": ("127.0.0.1", 8000),
        "scheme": "http",
        "http_version": "1.1",
    }
    request = Request(fake_scope)
    return await render_template(request, name, context or {})

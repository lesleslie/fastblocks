"""Default Routes Adapter for FastBlocks.

Provides dynamic route discovery and registration for FastBlocks applications.
Includes automatic route gathering from adapters, static file serving, and HTMX endpoint support.

Features:
- Dynamic route discovery from adapter modules
- HTMX-aware endpoints with template fragment rendering
- Built-in static routes (favicon, robots.txt)
- Automatic static file serving for storage adapters
- Template block rendering endpoints
- Route gathering from base routes.py files
- Integration with FastBlocks template system

Requirements:
- starlette>=0.47.1
- jinja2>=3.1.6

Usage:
```python
# Oneiric imports - ACB imports removed
# routes = depends.resolve("fastblocks", "routes")
# Routes = import_adapter("routes")
# app_routes = routes.routes
```

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

import typing as t
from contextlib import suppress
from importlib import import_module
from uuid import UUID

from anyio import Path as AsyncPath
from jinja2.exceptions import TemplateNotFound

# Oneiric imports
from oneiric.core.resolution import Resolver
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Host, Mount, Route, Router, WebSocketRoute
from starlette.types import Receive, Scope, Send
from fastblocks.actions.query import create_query_context
from fastblocks.htmx import HtmxRequest


# Custom implementations for ACB compatibility
def debug(msg: str) -> None:
    """Custom debug function for Oneiric compatibility."""
    print(f"[DEBUG] {msg}")


class AdapterStatus:
    """Custom AdapterStatus for Oneiric compatibility."""

    STABLE = "STABLE"
    BETA = "BETA"
    ALPHA = "ALPHA"
    EXPERIMENTAL = "EXPERIMENTAL"


def root_path():
    """Custom implementation for Oneiric compatibility."""
    return "/"


# Oneiric resolver for dependency injection
depends = Resolver()

from ._base import RoutesBase, RoutesBaseSettings

# Placeholder for templates (will be resolved via Oneiric)
Templates = None

base_routes_path = AsyncPath(root_path()) / "routes.py"


class RoutesSettings(RoutesBaseSettings):
    """Routes settings using OneiricSettings."""

    def __init__(self, **data: dict) -> None:
        super().__init__(**data)


class FastBlocksEndpoint(HTTPEndpoint):
    def __init__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        config: t.Any | None = None,
    ) -> None:
        super().__init__(scope, receive, send)
        self.config = config
        # Resolve templates via Oneiric resolver (fail gracefully)
        with suppress(Exception):
            self.templates = depends.resolve("templates")


class Index(FastBlocksEndpoint):
    async def get(self, request: HtmxRequest | Request) -> Response:
        debug(request)
        path_params = getattr(request, "path_params", {})
        page = path_params.get("page") or "home"
        template = "index.html"
        headers = {"vary": "hx-request"}
        scope = getattr(request, "scope", {})
        if htmx := scope.get("htmx"):
            debug(htmx)
            template = f"{page.lstrip('/')}.html"
            headers["hx-push-url"] = "/" if page == "home" else page
        debug(page, template)
        context = await create_query_context(
            request, base_context={"page": page.lstrip("/")}
        )
        query_params = getattr(request, "query_params", {})
        if "model" in query_params:
            model_name = query_params["model"]
            if f"{model_name}_parser" in context:
                parser = context[f"{model_name}_parser"]
                context[f"{model_name}_list"] = await parser.parse_and_execute()
                context[f"{model_name}_count"] = await parser.get_count()
        try:
            result = await self.templates.render_template(
                request,
                template,
                headers=headers,
                context=context,
            )
            return t.cast(Response, result)
        except TemplateNotFound:
            raise HTTPException(status_code=404)


class Block(FastBlocksEndpoint):
    async def get(self, request: HtmxRequest | Request) -> Response:
        debug(request)
        path_params = getattr(request, "path_params", {})
        block = f"blocks/{path_params.get('block', 'default')}.html"
        context = await create_query_context(request)
        query_params = getattr(request, "query_params", {})
        if "model" in query_params:
            model_name = query_params["model"]
            if f"{model_name}_parser" in context:
                parser = context[f"{model_name}_parser"]
                context[f"{model_name}_list"] = await parser.parse_and_execute()
                context[f"{model_name}_count"] = await parser.get_count()
        try:
            result = await self.templates.render_template(
                request, block, context=context
            )
            return t.cast(Response, result)
        except TemplateNotFound:
            raise HTTPException(status_code=404)


class Component(FastBlocksEndpoint):
    async def get(self, request: HtmxRequest | Request) -> Response:
        debug(request)
        component_name = getattr(request, "path_params", {}).get("component", "default")
        query_params = getattr(request, "query_params", {})
        context = await create_query_context(request, base_context=dict(query_params))
        if "model" in query_params:
            model_name = query_params["model"]
            if f"{model_name}_parser" in context:
                parser = context[f"{model_name}_parser"]
                context[f"{model_name}_list"] = await parser.parse_and_execute()
                context[f"{model_name}_count"] = await parser.get_count()
        try:
            htmy = await depends.resolve("fastblocks", "htmy")
            if htmy is None:
                raise HTTPException(
                    status_code=500, detail="HTMY adapter not available"
                )
            result = await htmy.render_component(
                request, component_name, context=context
            )
            return t.cast(Response, result)
        except Exception as e:
            debug(f"Component '{component_name}' not found: {e}")
            raise HTTPException(status_code=404)


class Routes(RoutesBase):
    routes: list[Route | Router | Mount | Host | WebSocketRoute] = []

    async def gather_routes(self, path: AsyncPath) -> None:
        depth = -2
        if "adapters" in path.parts:
            depth = -4
        module_path = ".".join(path.parts[depth:]).removesuffix(".py")
        debug(path, depth, module_path)
        with suppress(ModuleNotFoundError):
            module = import_module(module_path)
            module_routes = getattr(module, "routes", None)
            if module_routes and isinstance(module_routes, list):
                self.routes = module.routes + self.routes

    @staticmethod
    async def favicon(request: Request) -> Response:
        return PlainTextResponse("", 200)

    @staticmethod
    async def robots(request: Request) -> Response:
        txt = "User-agent: *\nDisallow: /dashboard/\nDisallow: /blocks/"
        return PlainTextResponse(txt, 200)

    async def init(self) -> None:
        self.routes.extend(
            [
                Route("/favicon.ico", endpoint=self.favicon, methods=["GET"]),
                Route("/robots.txt", endpoint=self.robots, methods=["GET"]),
                Route("/", Index, methods=["GET"]),
                Route("/{page}", Index, methods=["GET"]),
                Route("/block/{block}", Block, methods=["GET"]),
                Route("/component/{component}", Component, methods=["GET"]),
            ],
        )
        # For Oneiric, we'll use a simpler approach
        # In practice, this would be replaced with actual adapter discovery
        if await base_routes_path.exists():
            await self.gather_routes(base_routes_path)
        # Static file serving (simplified for Oneiric)
        with suppress(Exception):
            from starlette.staticfiles import StaticFiles

            # Placeholder for storage path (would be resolved via Oneiric)
            storage_path = AsyncPath("/tmp") / "media"
            self.routes.append(
                Mount(
                    "/media",
                    app=StaticFiles(directory=storage_path),
                    name="media",
                ),
            )
            # Development static files
            static_path = AsyncPath("/tmp") / "static"
            self.routes.append(
                Mount(
                    "/static",
                    app=StaticFiles(directory=static_path),
                    name="static",
                ),
            )
        debug(self.routes)


MODULE_ID = UUID("01937d86-6f4c-7d5e-a01f-3456789012cd")
MODULE_STATUS = AdapterStatus.STABLE

# Register with Oneiric resolver (fail gracefully if not supported)
with suppress(Exception):
    depends.set(Routes, "default")

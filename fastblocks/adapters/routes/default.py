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
import typing as t

from acb.depends import Inject, depends
from acb.adapters import import_adapter

routes = depends.get("routes")

Routes = import_adapter("routes")

app_routes = routes.routes
```

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

import typing as t
from contextlib import suppress
from importlib import import_module
from uuid import UUID

try:
    from acb.adapters import (
        AdapterStatus,
        get_adapters,
        get_installed_adapter,
        import_adapter,
        root_path,
    )
except ImportError:  # acb >= 0.19 removed get_installed_adapter
    from acb.adapters import (
        AdapterStatus,
        get_adapter,
        get_adapters,
        get_installed_adapters,
        import_adapter,
        root_path,
    )

    def get_installed_adapter(adapter_name: str) -> str | None:
        """Compatibility shim that resolves an installed adapter name."""
        for adapter in get_installed_adapters():
            meta = getattr(adapter, "metadata", None)
            provider = getattr(meta, "provider", None)
            if adapter_name in (adapter.category, adapter.name, provider):
                return provider or adapter.name
        adapter = get_adapter(adapter_name)
        if adapter:
            meta = getattr(adapter, "metadata", None)
            provider = getattr(meta, "provider", None)
            return provider or adapter.name
        return None


from acb.config import Config
from acb.debug import debug
from acb.depends import depends
from anyio import Path as AsyncPath
from jinja2.exceptions import TemplateNotFound
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Host, Mount, Route, Router, WebSocketRoute
from starlette.types import Receive, Scope, Send
from fastblocks.actions.query import create_query_context
from fastblocks.htmx import HtmxRequest

from ._base import RoutesBase, RoutesBaseSettings

try:
    Templates = import_adapter("templates")
except Exception:
    Templates = None

base_routes_path = root_path / "routes.py"


class RoutesSettings(RoutesBaseSettings): ...


class FastBlocksEndpoint(HTTPEndpoint):
    def __init__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        config: Config | None = None,
    ) -> None:
        super().__init__(scope, receive, send)
        self.config = config or depends.get_sync(Config)
        self.templates = depends.get_sync("templates")


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
            htmy = await depends.get("htmy")
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
        for adapter in get_adapters():
            routes_path = adapter.path.parent / "_routes.py"
            if await routes_path.exists():
                await self.gather_routes(routes_path)
        if await base_routes_path.exists():
            await self.gather_routes(base_routes_path)
        if get_installed_adapter("storage") in ("file", "memory"):
            from starlette.staticfiles import StaticFiles

            self.routes.append(
                Mount(
                    "/media",
                    app=StaticFiles(directory=self.config.storage.local_path / "media"),
                    name="media",
                ),
            )
        if not self.config.deployed:
            from starlette.staticfiles import StaticFiles

            self.routes.append(
                Mount(
                    "/static",
                    app=StaticFiles(
                        directory=self.config.storage.local_path / "static"
                    ),
                    name="media",
                ),
            )
        debug(self.routes)


MODULE_ID = UUID("01937d86-6f4c-7d5e-a01f-3456789012cd")
MODULE_STATUS = AdapterStatus.STABLE

with suppress(Exception):
    depends.set(Routes, "default")

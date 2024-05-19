import typing as t
from importlib import import_module

from acb import base_path
from acb.adapters import get_installed_adapters
from acb.adapters import import_adapter
from acb.debug import debug
from acb.depends import depends
from aiopath import AsyncPath
from asgi_htmx import HtmxRequest
from starlette.endpoints import HTTPEndpoint
from starlette.responses import PlainTextResponse
from starlette.responses import Response
from starlette.routing import Host
from starlette.routing import Mount
from starlette.routing import Route
from starlette.routing import Router
from starlette.routing import WebSocketRoute
from starlette_async_jinja import AsyncJinja2Templates
from ._base import RoutesBase
from ._base import RoutesBaseSettings

Templates = import_adapter()

base_routes_paths = [AsyncPath(base_path / "routes.py")]


class RoutesSettings(RoutesBaseSettings): ...


class Index(HTTPEndpoint):
    templates: Templates = depends()  # type: ignore

    async def get(self, request: HtmxRequest) -> Response:
        request.path_params["page"] = request.scope["path"].lstrip("/") or "home"
        debug(request.path_params.get("page"))
        return await self.templates.app.render_template(
            request, "index.html"  # type: ignore
        )


class Block(HTTPEndpoint):
    templates: Templates = depends()  # type: ignore

    async def get(self, request: HtmxRequest) -> Response:
        debug(request)
        block = f"blocks/{request.path_params['block']}.html"
        return await self.templates.app.render_template(request, block)


class Routes(RoutesBase):
    templates: t.Optional[AsyncJinja2Templates] = None
    routes: list[Route | Router | Mount | Host | WebSocketRoute] = []

    async def gather_routes(self, path: AsyncPath) -> None:
        depth = -2
        if "adapters" in path.parts:
            depth = -5
        module_path = ".".join(path.parts[depth:]).removesuffix(".py")
        module = import_module(module_path)
        module_routes = getattr(module, "routes", None)
        if module_routes and isinstance(module_routes, list):
            self.routes.extend(module.routes)
        else:
            self.routes.extend(
                [
                    r
                    for r in vars(module).items()
                    if isinstance(r, Route | Router | Mount | Host | WebSocketRoute)
                ]
            )

    @staticmethod
    async def favicon(request: HtmxRequest) -> Response:
        return PlainTextResponse("", 200)

    @depends.inject
    async def init(self, templates: Templates = depends()) -> None:  # type: ignore
        self.templates = templates.app
        self.routes.extend(
            [
                Route("/favicon.ico", endpoint=self.favicon, methods=["GET"]),
                Route("/", Index, methods=["GET"]),
                Route("/block/{block}", Block, methods=["GET"]),
            ]
        )
        async for page in self.templates.env.loader.searchpath[-1].glob("*.html"):
            self.routes.append(Route(f"/{page.stem}", Index, methods=["GET"]))
        for adapter in get_installed_adapters():
            _routes_path = adapter.path / "_routes.py"
            if await _routes_path.exists():
                await self.gather_routes(_routes_path)
        for _routes_path in base_routes_paths:
            if await _routes_path.exists():
                await self.gather_routes(_routes_path)


depends.set(Routes)

import typing as t
from importlib import import_module

from acb.adapters import get_installed_adapters, import_adapter, root_path
from acb.config import Config
from acb.debug import debug
from acb.depends import depends
from aiopath import AsyncPath
from asgi_htmx import HtmxRequest
from jinja2.exceptions import TemplateNotFound
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Host, Mount, Route, Router, WebSocketRoute
from starlette_async_jinja import AsyncJinja2Templates
from ._base import RoutesBase, RoutesBaseSettings

Templates = import_adapter()

base_routes_paths = [AsyncPath(root_path / "routes.py")]


class RoutesSettings(RoutesBaseSettings): ...


class Index(HTTPEndpoint):
    config: Config = depends()
    templates: Templates = depends()  # type: ignore

    async def get(self, request: HtmxRequest) -> Response:
        debug(request)
        page = request.path_params.get("page") or "home"
        template = "index.html"
        headers = dict(vary="hx-request")
        if htmx := request.scope["htmx"]:
            debug(htmx)
            template = f"{page.lstrip('/')}.html"
            headers["hx-push-url"] = "/" if page == "home" else page
        debug(page, template)
        try:
            return await self.templates.app.render_template(
                request, template, headers=headers, context=dict(page=page.lstrip("/"))
            )
        except TemplateNotFound:
            raise HTTPException(status_code=404)


class Block(HTTPEndpoint):
    templates: Templates = depends()  # type: ignore

    async def get(self, request: HtmxRequest) -> Response:
        debug(request)
        block = f"blocks/{request.path_params['block']}.html"
        try:
            return await self.templates.app.render_template(request, block)
        except TemplateNotFound:
            raise HTTPException(status_code=404)


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
    async def favicon(request: Request) -> Response:
        return PlainTextResponse("", 200)

    @staticmethod
    async def robots(request: Request) -> Response:
        txt = "User-agent: *\nDisallow: /dashboard/\nDisallow: /blocks/"
        return PlainTextResponse(txt, 200)

    @depends.inject
    async def init(self, templates: Templates = depends()) -> None:  # type: ignore
        self.routes.extend(
            [
                Route("/favicon.ico", endpoint=self.favicon, methods=["GET"]),
                Route("/robots.txt", endpoint=self.robots, methods=["GET"]),
                Route("/", Index, methods=["GET"]),
                Route("/{page}", Index, methods=["GET"]),
                Route("/block/{block}", Block, methods=["GET"]),
            ]
        )
        for adapter in get_installed_adapters():
            _routes_path = adapter.path / "_routes.py"
            if await _routes_path.exists():
                await self.gather_routes(_routes_path)
        for _routes_path in base_routes_paths:
            if await _routes_path.exists():
                await self.gather_routes(_routes_path)
        debug(self.routes)


depends.set(Routes)

from contextlib import suppress
from importlib import import_module

from acb.adapters import get_adapters, get_installed_adapter, import_adapter, root_path
from acb.config import Config
from acb.debug import debug
from acb.depends import depends
from anyio import Path as AsyncPath
from asgi_htmx import HtmxRequest
from jinja2.exceptions import TemplateNotFound
from starlette.endpoints import HTTPEndpoint
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.routing import Host, Mount, Route, Router, WebSocketRoute
from starlette.types import Receive, Scope, Send

from ._base import RoutesBase, RoutesBaseSettings

try:
    Templates = import_adapter("templates")
except Exception:
    Templates = None

base_routes_path = root_path / "routes.py"


class RoutesSettings(RoutesBaseSettings): ...


class FastBlocksEndpoint(HTTPEndpoint):
    config: Config = depends()

    def __init__(self, scope: Scope, receive: Receive, send: Send) -> None:
        super().__init__(scope, receive, send)
        self.templates = depends.get("templates")


class Index(FastBlocksEndpoint):
    @depends.inject
    async def get(self, request: HtmxRequest) -> Response:
        debug(request)
        page = request.path_params.get("page") or "home"
        template = "index.html"
        headers = {"vary": "hx-request"}
        if htmx := request.scope["htmx"]:
            debug(htmx)
            template = f"{page.lstrip('/')}.html"
            headers["hx-push-url"] = "/" if page == "home" else page
        debug(page, template)
        try:
            return await self.templates.render_template(
                request,
                template,
                headers=headers,
                context={"page": page.lstrip("/")},
            )
        except TemplateNotFound:
            raise HTTPException(status_code=404)


class Block(FastBlocksEndpoint):
    async def get(self, request: HtmxRequest) -> Response:
        debug(request)
        block = f"blocks/{request.path_params['block']}.html"
        try:
            return await self.templates.render_template(request, block)
        except TemplateNotFound:
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

    @depends.inject
    async def init(self) -> None:
        self.routes.extend(
            [
                Route("/favicon.ico", endpoint=self.favicon, methods=["GET"]),
                Route("/robots.txt", endpoint=self.robots, methods=["GET"]),
                Route("/", Index, methods=["GET"]),
                Route("/{page}", Index, methods=["GET"]),
                Route("/block/{block}", Block, methods=["GET"]),
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
        debug(self.routes)


with suppress(Exception):
    depends.set(Routes)

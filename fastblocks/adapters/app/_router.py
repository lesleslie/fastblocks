from fastblocks.routing import BaseRouter
from fastblocks import Router
from fastblocks import JsonResponse
from fastblocks import Request
from fastblocks import Response
from acb.adapters.cache import Cache
from acb.depends import depends


class AppRouter(BaseRouter):
    router = Router()  # type: ignore
    cache: Cache = depends()  # type: ignore

    def __init__(self) -> None:
        self.templates = self.templates.app

    @staticmethod
    @router.get("/")
    @cache(ttl=42)  # type: ignore
    async def index(request: Request):
        return JsonResponse({"message": "Hello World"})

    @router.get("/privacy_policy")
    @router.get("/service_terms")
    @router.get("/offline")
    @cache()  # type: ignore
    async def service_policy(
        self,
        request: Request,
    ) -> Response:
        template = f"{self.config.app.style}{request.path_params}.html".lstrip("/")
        return await self.templates.render_template(template, request.path_params)

    @staticmethod
    @router.get("/favicon.ico")
    async def favicon():
        return "", 200

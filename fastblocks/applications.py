import typing as t

from acb.config import Config
from acb.depends import depends

from asgi_htmx import HtmxRequest as Request
from middleware import middlewares
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp


class FastBlocks(Starlette):
    config: Config = depends()

    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)
        self.debug = self.config.debug.main

    def build_middleware_stack(self) -> ASGIApp:
        debug = self.debug
        error_handler = None
        exception_handlers: dict[t.Any, t.Callable[[Request, Exception], Response]] = {}
        for key, value in self.exception_handlers.items():
            if key in (500, Exception):
                error_handler = value
            else:
                exception_handlers[key] = value  # type: ignore
        middleware = (
            [Middleware(ServerErrorMiddleware, handler=error_handler, debug=debug)]
            + self.user_middleware
            + middlewares()
            + [
                Middleware(
                    ExceptionMiddleware, handlers=exception_handlers, debug=debug
                )
            ]
        )
        app = self.router
        for cls, options in reversed(middleware):
            app = cls(app=app, **options)
        return app

import typing as t

from acb.config import ac
from acb.config import package_registry
from asgi_htmx import HtmxRequest as Request
from starlette.applications import Starlette
from starlette.datastructures import State
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.responses import Response
from starlette.routing import BaseRoute
from starlette.routing import Router
from starlette.types import AppType
from starlette.types import ASGIApp
from starlette.types import Lifespan
from .middleware import fastblocks_middleware

package_registry.register()


class FastBlocks(Starlette):
    def __init__(
        self: "AppType",
        debug: bool = False,
        routes: t.Optional[t.Sequence[BaseRoute]] = None,
        middleware: t.Optional[t.Sequence[Middleware]] = None,
        exception_handlers: t.Optional[
            t.Mapping[
                t.Any,
                t.Callable[
                    [Request, Exception],
                    t.Union[Response, t.Awaitable[Response]],
                ],
            ]
        ] = None,
        lifespan: t.Optional[Lifespan["AppType"]] = None,
    ) -> None:
        super().__init__(
            debug,
            routes,
            middleware,
            exception_handlers,
            lifespan,
        )
        self.debug = debug or ac.debug.app
        self.state = State()
        self.router = Router(routes, lifespan=lifespan)
        self.exception_handlers = (
            {} if exception_handlers is None else dict(exception_handlers)
        )
        self.user_middleware = [] if middleware is None else list(middleware)
        self.middleware_stack: t.Optional[ASGIApp] = None

    def build_middleware_stack(self) -> ASGIApp:
        debug = self.debug
        error_handler = None
        exception_handlers: t.Dict[
            t.Any, t.Callable[[Request, Exception], Response]
        ] = {}
        for key, value in self.exception_handlers.items():
            if key in (500, Exception):
                error_handler = value
            else:
                exception_handlers[key] = value
        middleware = (
            [Middleware(ServerErrorMiddleware, handler=error_handler, debug=debug)]
            + self.user_middleware
            + fastblocks_middleware
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

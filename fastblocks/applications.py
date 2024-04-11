import logging
import typing as t
from platform import system

from acb.adapters import import_adapter
from acb.adapters import register_adapters
from acb.adapters.logger.loguru import InterceptHandler
from acb.config import Config
from acb.depends import depends
from asgi_htmx import HtmxRequest
from starception import add_link_template
from starception import install_error_handler
from starception import set_editor
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp
from starlette.types import ExceptionHandler
from starlette.types import Lifespan
from .middleware import middlewares

register_adapters()

Logger = import_adapter()

AppType = t.TypeVar("AppType", bound="FastBlocks")

match system():
    case "Windows":
        add_link_template("pycharm", "pycharm64.exe --line {lineno} {path}")
    case "Darwin":
        add_link_template("pycharm", "pycharm --line {lineno} {path}")
    case "Linux":
        add_link_template("pycharm", "pycharm.sh --line {lineno} {path}")
    case _:
        ...


class FastBlocks(Starlette):
    @depends.inject
    def __init__(
        self: AppType,
        middleware: t.Sequence[Middleware] | None = None,
        exception_handlers: t.Mapping[t.Any, ExceptionHandler] | None = None,
        lifespan: t.Optional[Lifespan["AppType"]] = None,
        config: Config = depends(),
    ) -> None:
        self.debug = config.debug.app
        install_error_handler()
        super().__init__(
            debug=self.debug,
            routes=[],
            middleware=middleware,
            lifespan=lifespan,
            exception_handlers=exception_handlers,
        )
        self.exception_handlers = exception_handlers or {}
        self.user_middleware = middleware or []
        self.models = depends.get(import_adapter("models"))
        self.templates = None
        set_editor("pycharm")
        for _logger in ("uvicorn", "uvicorn.access"):
            _logger = logging.getLogger(_logger)
            _logger.handlers.clear()
            _logger.handlers = [InterceptHandler()]

    @depends.inject
    def build_middleware_stack(
        self, logger: Logger = depends()  # type: ignore
    ) -> ASGIApp:
        error_handler = None
        exception_handlers: dict[
            t.Any, t.Callable[[HtmxRequest, Exception], Response]
        ] = {}
        for key, value in self.exception_handlers.items():
            if key in (500, Exception):
                error_handler = value
            else:
                exception_handlers[key] = value  # type: ignore
        middleware = (
            [
                Middleware(
                    ServerErrorMiddleware,  # type: ignore
                    handler=error_handler,  # type: ignore
                    debug=self.debug,
                )
            ]
            + self.user_middleware
            + middlewares()
            + [
                Middleware(
                    ExceptionMiddleware,  # type: ignore
                    handlers=exception_handlers,  # type: ignore
                    debug=self.debug,
                )
            ]
        )
        app = self.router
        for cls, args, kwargs in reversed(middleware):
            logger.debug(f"Adding middleware: {cls.__name__}")
            app = cls(app=app, *args, **kwargs)
        logger.info("Middleware stack built")
        return app

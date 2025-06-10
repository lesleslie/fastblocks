import logging
import typing as t
from platform import system

from acb import register_pkg
from acb.adapters import get_installed_adapter
from acb.config import Config
from acb.depends import depends
from acb.logger import InterceptHandler, Logger
from starception import add_link_template, install_error_handler, set_editor
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.types import ASGIApp, ExceptionHandler, Lifespan

from .exceptions import handle_exception

register_pkg()
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
        lifespan: Lifespan["AppType"] | None = None,
        config: Config = depends(),
        logger: Logger = depends(),
    ) -> None:
        if not getattr(config, "deployed", False) or not getattr(
            config.debug, "production", False
        ):
            install_error_handler()
        self.debug = getattr(config.debug, "fastblocks", False)
        logger.info(f"Fastblocks debug: {self.debug}")
        super().__init__(
            debug=self.debug,
            routes=[],
            middleware=middleware,
            lifespan=lifespan,
            exception_handlers=exception_handlers,
        )
        self.exception_handlers = exception_handlers or {
            404: handle_exception,
            500: handle_exception,
        }
        self.user_middleware = middleware or []
        self.models = depends.get()
        self.templates = None
        set_editor("pycharm")
        for _logger in ("uvicorn", "uvicorn.access", "_granian, granian.access"):
            _logger = logging.getLogger(_logger)
            _logger.handlers.clear()
            _logger.handlers = [InterceptHandler()]
        if get_installed_adapter("logfire"):
            from logfire import instrument_starlette

            instrument_starlette(self)

    @depends.inject
    def build_middleware_stack(
        self, config: Config = depends(), logger: Logger = depends()
    ) -> ASGIApp:
        error_handler = None
        exception_handlers: dict[t.Any, ExceptionHandler] = {}
        for key, value in self.exception_handlers.items():
            if key in (500, Exception):
                error_handler = value
            else:
                exception_handlers[key] = t.cast(ExceptionHandler, value)
        from .middleware import middlewares

        middleware_list = [
            Middleware(
                ServerErrorMiddleware,
                handler=t.cast(t.Any, error_handler),
                debug=self.debug,
            )
        ]
        middleware_list.extend(self.user_middleware)
        middleware_list.extend(middlewares())
        middleware_list.append(
            Middleware(
                ExceptionMiddleware,
                handlers=t.cast(t.Any, exception_handlers),
                debug=self.debug,
            )
        )
        middleware = middleware_list
        app = self.router
        for cls, args, kwargs in reversed(middleware):
            logger.debug(f"Adding middleware: {cls.__name__}")
            app = cls(*args, app=app, **kwargs)
        logger.info("Middleware stack built")
        return app

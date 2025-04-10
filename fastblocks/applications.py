import logging
import typing as t
from platform import system

from acb import register_pkg
from acb.actions.encode import dump, load
from acb.adapters import (
    adapter_settings_path,
    debug_settings_path,
    get_adapter,
    get_installed_adapter,
)
from acb.config import Config
from acb.depends import depends
from acb.logger import InterceptHandler, Logger
from asgi_htmx import HtmxRequest
from starception import add_link_template, install_error_handler, set_editor
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp, ExceptionHandler, Lifespan

from .exceptions import handle_exception

register_pkg()

default_adapters = dict(
    routes="default", templates="jinja2", auth="basic", sitemap="asgi"
)


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
        if not hasattr(config.debug, "fastblocks"):
            debug = load.yaml(debug_settings_path)
            setattr(config.debug, "fastblocks", False)
            debug["fastblocks"] = False
            if not config.deployed and not config.debug.production:
                dump.yaml(debug, debug_settings_path)
        self.debug = config.debug.fastblocks
        if self.debug or not config.deployed or not config.debug.production:
            install_error_handler()
        if not get_adapter("routes") or not get_adapter("templates"):
            adapters = load.yaml(adapter_settings_path)
            for category, name in {c: n for c, n in default_adapters.items() if not n}:
                adapters[category] = name
            if not config.deployed or not config.debug.production:
                dump.yaml(adapters, adapter_settings_path)
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
        self,
        logger: Logger = depends(),
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
        from .middleware import middlewares

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

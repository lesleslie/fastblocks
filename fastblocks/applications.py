import typing as t
from platform import system

from acb.adapters.logger import Logger
from acb.adapters.logger._base import ExternalLogger
from acb.config import Config
from acb.depends import depends
from asgi_htmx import HtmxRequest as Request
from starception import add_link_template
from starception import install_error_handler
from starception import set_editor
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.responses import Response
from starlette.types import ASGIApp
from .middleware import middlewares

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
    config: Config = depends()
    logger: Logger = depends()  # type: ignore

    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)
        set_editor("pycharm")
        install_error_handler()
        loggers = ["uvicorn", "uvicorn.access", "uvicorn.error"]
        self.logger.register_external_loggers(
            [
                ExternalLogger(name=name, package="fastblocks", module="main")
                for name in loggers
            ]
        )
        self.debug = not self.config.deployed or not self.config.debug.production

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

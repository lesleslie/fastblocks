import logging
import typing as t
from platform import system
import asyncio

from acb.config import logger_registry
from acb.config import Config
from acb.config import register_package
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

asyncio.run(register_package())

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

    def __init__(self, **kwargs: t.Any) -> None:
        set_editor("pycharm")
        install_error_handler()
        logging.getLogger("uvicorn").handlers.clear()
        logger_registry.get().update(("uvicorn.access", "uvicorn.error"))
        super().__init__(**kwargs)
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

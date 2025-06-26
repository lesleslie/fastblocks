import logging
import typing as t
from platform import system

from starception import add_link_template, install_error_handler, set_editor
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.exceptions import ExceptionMiddleware
from starlette.types import ASGIApp, ExceptionHandler, Lifespan

from .exceptions import handle_exception

depends = None

Config = None
AdapterBase = None
InterceptHandler = None
Logger = None


def _import_acb_modules():
    global Config, AdapterBase, InterceptHandler, Logger, depends
    if Config is None:
        from acb import register_pkg
        from acb.adapters import get_installed_adapter
        from acb.config import AdapterBase as _AdapterBase
        from acb.config import Config as _Config
        from acb.depends import depends as _depends
        from acb.logger import InterceptHandler as _InterceptHandler
        from acb.logger import Logger as _Logger

        Config = _Config
        AdapterBase = _AdapterBase
        InterceptHandler = _InterceptHandler
        Logger = _Logger
        depends = _depends
        return (
            register_pkg,
            get_installed_adapter,
            Config,
            AdapterBase,
            InterceptHandler,
            Logger,
            depends,
        )
    else:
        from acb import register_pkg
        from acb.adapters import get_installed_adapter

        return (
            register_pkg,
            get_installed_adapter,
            Config,
            AdapterBase,
            InterceptHandler,
            Logger,
            depends,
        )


class FastBlocksSettings:
    def __init_subclass__(cls, **kwargs: t.Any) -> None:
        _, _, _Config, AdapterBase, _InterceptHandler, _Logger, _depends = (
            _import_acb_modules()
        )
        if AdapterBase not in cls.__bases__:
            cls.__bases__ = (AdapterBase,) + cls.__bases__
        super().__init_subclass__(**kwargs)


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
    def __init__(
        self: AppType,
        middleware: t.Sequence[Middleware] | None = None,
        exception_handlers: t.Mapping[t.Any, ExceptionHandler] | None = None,
        lifespan: Lifespan["AppType"] | None = None,
        config: t.Any = None,
        logger: t.Any = None,
    ) -> None:
        (
            _register_pkg,
            get_installed_adapter,
            _Config,
            _AdapterBase,
            InterceptHandler,
            _Logger,
            depends,
        ) = _import_acb_modules()

        if config is None:
            config = depends.get("config")
        if logger is None:
            logger = depends.get("logger")

        if not getattr(config, "deployed", False) or not getattr(
            getattr(config, "debug", None), "production", False
        ):
            install_error_handler()
        debug_config = getattr(config, "debug", None)
        self.debug = (
            getattr(debug_config, "fastblocks", False) if debug_config else False
        )
        if logger:
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
            _logger.handlers.clear()
            _logger.addHandler(InterceptHandler())
        if get_installed_adapter("logfire"):
            from logfire import instrument_starlette

            instrument_starlette(self)

    def build_middleware_stack(
        self, config: t.Any = None, logger: t.Any = None
    ) -> ASGIApp:
        (
            _register_pkg,
            _get_installed_adapter,
            _Config,
            _AdapterBase,
            _InterceptHandler,
            _Logger,
            depends,
        ) = _import_acb_modules()

        if config is None:
            config = depends.get("config")
        if logger is None:
            try:
                logger = depends.get("logger")
            except Exception:
                logger = None
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
            if logger:
                logger.debug(f"Adding middleware: {cls.__name__}")
            app = cls(*args, app=app, **kwargs)
        if logger:
            logger.info("Middleware stack built")
        return app

"""Application initialization components for FastBlocks.

This module contains classes responsible for initializing various aspects
of a FastBlocks application, separating concerns from the main application class.
"""

import logging
import typing as t

from acb import register_pkg
from acb.adapters import get_installed_adapter
from acb.config import AdapterBase, Config
from acb.depends import depends
from starception import install_error_handler
from starlette.applications import Starlette


class ApplicationInitializer:
    def __init__(self, app: Starlette, **kwargs: t.Any) -> None:
        self.app = app
        self.kwargs = kwargs
        self.config: t.Any | None = None
        self.logger: t.Any | None = None
        self.depends: t.Any | None = None
        self._acb_modules: tuple[t.Any, ...] = ()

    def initialize(self) -> None:
        self._load_acb_modules()
        self._setup_dependencies()
        self._configure_error_handling()
        self._configure_debug_mode()
        self._initialize_starlette()
        self._configure_exception_handlers()
        self._setup_models()
        self._configure_logging()

    def _load_acb_modules(self) -> None:
        try:
            logger_class: type[t.Any] | None = depends.get("logger").__class__
            from acb.logger import InterceptHandler

            interceptor_class: type[t.Any] | None = InterceptHandler
        except Exception:
            logger_class = None
            interceptor_class = None
        self._acb_modules = (
            register_pkg,
            get_installed_adapter,
            Config,
            AdapterBase,
            interceptor_class,
            logger_class,
            depends,
        )

    def _setup_dependencies(self) -> None:
        self.config = (
            self.kwargs.get("config")
            if self.kwargs.get("config") is not None
            else depends.get("config")
        )
        self.logger = (
            self.kwargs.get("logger")
            if self.kwargs.get("logger") is not None
            else depends.get("logger")
        )
        self.depends = depends

    def _configure_error_handling(self) -> None:
        if not getattr(self.config, "deployed", False) or not getattr(
            getattr(self.config, "debug", None),
            "production",
            False,
        ):
            install_error_handler()

    def _configure_debug_mode(self) -> None:
        debug_config = getattr(self.config, "debug", None)
        self.app.debug = (
            getattr(debug_config, "fastblocks", False) if debug_config else False
        )
        if self.logger:
            self.logger.warning(f"Fastblocks debug: {self.app.debug}")

    def _initialize_starlette(self) -> None:
        Starlette.__init__(
            self.app,
            debug=self.app.debug,
            routes=[],
            middleware=self.kwargs.get("middleware")
            if self.kwargs.get("middleware") is not None
            else [],
            lifespan=self.kwargs.get("lifespan"),
            exception_handlers=self.kwargs.get("exception_handlers")
            if self.kwargs.get("exception_handlers") is not None
            else {},
        )
        middleware = self.kwargs.get("middleware")
        self.app.user_middleware = list(middleware) if middleware is not None else []

    def _configure_exception_handlers(self) -> None:
        from .exceptions import handle_exception

        exception_handlers = self.kwargs.get("exception_handlers")
        if exception_handlers is None:
            exception_handlers = {
                404: handle_exception,
                500: handle_exception,
            }
        object.__setattr__(self.app, "exception_handlers", exception_handlers)

    def _setup_models(self) -> None:
        try:
            models = self.depends.get("models")
        except Exception:
            models = None
        object.__setattr__(self.app, "models", models)

    def _configure_logging(self) -> None:
        if get_installed_adapter("logfire"):
            from logfire import instrument_starlette  # type: ignore[import-untyped]

            instrument_starlette(self.app)
        interceptor_class = self._acb_modules[4]
        if interceptor_class:
            for logger_name in (
                "uvicorn",
                "uvicorn.access",
                "granian",
                "granian.access",
            ):
                server_logger = logging.getLogger(logger_name)
                server_logger.handlers.clear()
                server_logger.addHandler(interceptor_class())
                server_logger.setLevel(logging.DEBUG)
                server_logger.propagate = False

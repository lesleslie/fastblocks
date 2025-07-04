"""Application initialization components for FastBlocks.

This module contains classes responsible for initializing various aspects
of a FastBlocks application, separating concerns from the main application class.
"""

import logging
import typing as t

from starception import install_error_handler
from starlette.applications import Starlette

from .dependencies import get_acb_subset


class ApplicationInitializer:
    def __init__(self, app: Starlette, **kwargs: t.Any) -> None:
        self.app = app
        self.kwargs = kwargs
        self.config: t.Any = None
        self.logger: t.Any = None
        self.depends: t.Any = None
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
        self._acb_modules = get_acb_subset(
            "register_pkg",
            "get_installed_adapter",
            "Config",
            "AdapterBase",
            "InterceptHandler",
            "Logger",
            "depends",
        )

    def _setup_dependencies(self) -> None:
        depends = self._acb_modules[6]
        self.config = self.kwargs.get("config") or depends.get("config")
        self.logger = self.kwargs.get("logger") or depends.get("logger")
        self.depends = depends

    def _configure_error_handling(self) -> None:
        if not getattr(self.config, "deployed", False) or not getattr(
            getattr(self.config, "debug", None), "production", False
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
            middleware=self.kwargs.get("middleware") or [],
            lifespan=self.kwargs.get("lifespan"),
            exception_handlers=self.kwargs.get("exception_handlers") or {},
        )
        self.app.user_middleware = list(self.kwargs.get("middleware") or [])

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
        get_installed_adapter = self._acb_modules[1]
        InterceptHandler = self._acb_modules[4]
        if get_installed_adapter("logfire"):
            from logfire import instrument_starlette  # type: ignore[import-untyped]

            instrument_starlette(self.app)
        for logger_name in ("uvicorn", "uvicorn.access", "granian", "granian.access"):
            server_logger = logging.getLogger(logger_name)
            server_logger.handlers.clear()
            server_logger.addHandler(InterceptHandler())

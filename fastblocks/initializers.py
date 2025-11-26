"""Application initialization components for FastBlocks.

This module contains classes responsible for initializing various aspects
of a FastBlocks application, separating concerns from the main application class.
"""

import logging
import typing as t

from acb import register_pkg

try:
    from acb.adapters import get_installed_adapter
except ImportError:  # acb >= 0.19 removed this helper
    from acb.adapters import get_adapter, get_installed_adapters

    def get_installed_adapter(adapter_name: str) -> str | None:
        """Compatibility shim that resolves an installed adapter name."""
        for adapter in get_installed_adapters():
            meta = getattr(adapter, "metadata", None)
            provider = getattr(meta, "provider", None)
            if adapter_name in (adapter.category, adapter.name, provider):
                provider_str = str(provider) if provider is not None else None
                adapter_name_str = (
                    str(adapter.name) if hasattr(adapter, "name") else None
                )
                return provider_str or adapter_name_str
        adapter = get_adapter(adapter_name)
        if adapter:
            meta = getattr(adapter, "metadata", None)
            provider = getattr(meta, "provider", None)
            provider_str = str(provider) if provider is not None else None
            adapter_name_str = str(adapter.name) if hasattr(adapter, "name") else None
            return provider_str or adapter_name_str
        return None


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
        self._register_event_handlers()

    def _load_acb_modules(self) -> None:
        try:
            logger = depends.get_sync("logger")
            logger_class: type[t.Any] | None = (
                logger.__class__ if logger is not None else None
            )
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
        self.config = self.kwargs.get("config")
        if self.config is None:
            try:
                self.config = depends.get_sync("config")
            except Exception:
                self.config = None

        self.logger = self.kwargs.get("logger")
        if self.logger is None:
            try:
                self.logger = depends.get_sync("logger")
            except Exception:
                self.logger = None

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
            models = self.depends.get_sync("models")  # type: ignore[union-attr]
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

    def _register_integrations_async(self) -> None:
        """Run async integration registration in background."""
        from contextlib import suppress

        from ._events_integration import register_fastblocks_event_handlers
        from ._health_integration import register_fastblocks_health_checks
        from ._validation_integration import register_fastblocks_validation
        from ._workflows_integration import register_fastblocks_workflows

        with suppress(Exception):
            import asyncio

            async def register_all() -> None:
                """Register all FastBlocks integrations concurrently."""
                try:
                    await asyncio.gather(
                        register_fastblocks_event_handlers(),
                        register_fastblocks_health_checks(),
                        register_fastblocks_validation(),
                        register_fastblocks_workflows(),
                        return_exceptions=True,
                    )
                    if self.logger:
                        self.logger.info("All FastBlocks integrations registered")
                except Exception as e:
                    if self.logger:
                        self.logger.warning(
                            f"Some integrations failed to register: {e}"
                        )

            # Use running loop when available, otherwise start a new one
            with suppress(Exception):  # Graceful degradation
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(register_all())
                except RuntimeError:
                    asyncio.run(register_all())

    def _register_event_handlers(self) -> None:
        """Register FastBlocks event handlers, health checks, validation, and workflows with ACB."""
        try:
            self._register_integrations_async()

            if self.logger:
                self.logger.info(
                    "FastBlocks integrations registered (events, health, validation, workflows)"
                )

        except ImportError:
            # ACB integrations not available - graceful degradation
            if self.logger:
                self.logger.debug(
                    "ACB integrations not available - running without enhanced features"
                )
        except Exception as e:
            # Log error but don't fail application startup
            if self.logger:
                self.logger.warning(
                    f"Failed to register ACB integrations: {e} - continuing with degraded features"
                )

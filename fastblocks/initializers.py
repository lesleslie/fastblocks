"""Application initialization components for FastBlocks.

This module contains classes responsible for initializing various aspects
of a FastBlocks application, separating concerns from the main application class.
"""

import logging
import typing as t

# Oneiric imports
from oneiric.core.config import OneiricSettings
from oneiric.core.logging import get_logger as oneiric_get_logger
from oneiric.core.resolution import Resolver, register_pkg

# Create resolver instance
_resolver = Resolver()


async def _get_dependency(name: str) -> t.Any:
    """Get dependency using Oneiric resolver."""
    return await _resolver.resolve(name)


def _get_dependency_sync(name: str) -> t.Any:
    """Get dependency synchronously using Oneiric resolver."""
    import asyncio

    return asyncio.run(_get_dependency(name))


# Oneiric adapter resolution
def get_installed_adapter(adapter_name: str) -> str | None:
    """Oneiric adapter resolution."""
    try:
        # Try to get adapter metadata
        adapter_metadata = _resolver.registry.get(adapter_name)
        if adapter_metadata:
            return adapter_name
        return None
    except Exception:
        return None


# Oneiric config and adapter base
Config = OneiricSettings
AdapterBase = object  # Oneiric uses different adapter structure

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
        # Initialize variables to default values
        logger_class: type[t.Any] | None = None
        interceptor_class: type[t.Any] | None = None

        try:
            # Oneiric: Get logger using Oneiric method
            logger = oneiric_get_logger("fastblocks")
            logger_class = logger.__class__ if logger is not None else None
            # Oneiric doesn't have InterceptHandler, use None
            interceptor_class = None
        except Exception:
            logger_class = None
            interceptor_class = None

        depends_resolver = None

        self._acb_modules = (
            register_pkg,
            get_installed_adapter,
            Config,
            AdapterBase,
            interceptor_class,
            logger_class,
            depends_resolver,
        )

    def _setup_dependencies(self) -> None:
        self.config = self.kwargs.get("config")
        if self.config is None:
            try:
                self.config = _get_dependency_sync("config")
            except Exception:
                self.config = None

        self.logger = self.kwargs.get("logger")
        if self.logger is None:
            try:
                self.logger = oneiric_get_logger("fastblocks")
            except Exception:
                self.logger = None

        self.depends = None

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
            models = _get_dependency_sync("models")
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
            # Integration modules not available - graceful degradation
            if self.logger:
                self.logger.debug(
                    "Integration modules not available - running without enhanced features"
                )
        except Exception as e:
            # Log error but don't fail application startup
            if self.logger:
                self.logger.warning(
                    f"Failed to register ACB integrations: {e} - continuing with degraded features"
                )

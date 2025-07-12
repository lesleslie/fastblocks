"""Common module for app adapter test fixtures."""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportArgumentType=false, reportMissingTypeArgument=false, reportUntypedFunctionDecorator=false

import inspect
import sys
import types
import typing as t
from contextlib import asynccontextmanager, suppress


def create_adapter_modules() -> dict[str, types.ModuleType]:  # noqa: C901
    """Create adapter modules for testing.

    Returns:
        Dictionary of module paths to module objects
    """
    modules = {}

    # Create base module structure
    fastblocks_module = types.ModuleType("fastblocks")
    adapters_module = types.ModuleType("fastblocks.adapters")
    app_module = types.ModuleType("fastblocks.adapters.app")
    base_module = types.ModuleType("fastblocks.adapters.app._base")
    default_module = types.ModuleType("fastblocks.adapters.app.default")

    # Set __path__ for package modules
    fastblocks_module.__path__ = ["/mock/path/to/fastblocks"]
    adapters_module.__path__ = ["/mock/path/to/fastblocks/adapters"]
    app_module.__path__ = ["/mock/path/to/fastblocks/adapters/app"]

    # Create base classes
    class AppBaseSettings:
        """Base settings for app adapters."""

        def __init__(self) -> None:
            """Initialize app settings."""
            self.style = "bulma"
            self.theme = "light"

    @t.runtime_checkable
    class AppProtocol(t.Protocol):
        """Protocol for app adapters."""

        def __call__(self) -> None:
            """Make protocol callable."""
            ...

        async def lifespan(self) -> t.AsyncIterator[None]:
            """App lifespan handler."""
            ...

    class AppBase:
        """Base class for app adapters."""

        def __init__(self) -> None:
            """Initialize app base."""
            self.settings = AppBaseSettings()
            self.router = None

        def startup(self) -> None:
            """Start the app."""

        def shutdown(self) -> None:
            """Shutdown the app."""

    # Add classes to base module
    base_module.AppBaseSettings = AppBaseSettings
    base_module.AppProtocol = AppProtocol
    base_module.AppBase = AppBase

    # Create default module classes
    class AppSettings(AppBaseSettings):
        """Settings for default app adapter."""

        def __init__(self, **kwargs) -> None:
            """Initialize app settings."""
            super().__init__()
            self.name = kwargs.get("name", "test_app")
            self.url = kwargs.get("url", "https://example.com")

    class App(AppBase):
        """Default app adapter."""

        def __init__(self) -> None:
            """Initialize default app adapter."""
            super().__init__()
            self.settings = AppSettings()
            self._hooks = []

        async def init(self) -> None:
            """Initialize app adapter."""
            # This would normally set up templates, routes, etc.

        def register_post_startup(self, hook: t.Callable) -> None:
            """Register post-startup hook."""
            self._hooks.append(hook)

        async def post_startup(self) -> None:
            """Post-startup tasks."""
            # Call any registered hooks
            for hook in self._hooks:
                await hook() if inspect.iscoroutinefunction(hook) else hook()

        @asynccontextmanager
        async def lifespan(self, app: object) -> t.AsyncIterator[None]:
            """App lifespan handler."""
            with suppress(Exception):
                # Suppress exceptions for testing but still yield
                await self.post_startup()
            # Always yield to ensure the context manager works
            yield

    class FastBlocks:
        """FastBlocks ASGI application."""

        def __init__(self) -> None:
            """Initialize FastBlocks app."""
            self.admin = None

        def mount_admin(self, admin: object) -> None:
            """Mount admin interface."""
            self.admin = admin

    # Add classes to default module
    default_module.AppSettings = AppSettings
    default_module.App = App
    default_module.FastBlocks = FastBlocks
    default_module.AppBase = AppBase

    # Set up module hierarchy
    modules["fastblocks"] = fastblocks_module
    modules["fastblocks.adapters"] = adapters_module
    modules["fastblocks.adapters.app"] = app_module
    modules["fastblocks.adapters.app._base"] = base_module
    modules["fastblocks.adapters.app.default"] = default_module

    return modules


def ensure_adapter_modules() -> dict[str, types.ModuleType]:
    """Ensure adapter modules exist.

    Returns:
        Dictionary of module paths to module objects
    """
    # Create modules if not present
    modules = {}

    # Always create fresh modules for testing to avoid interference
    adapter_modules = create_adapter_modules()

    # Register with sys.modules
    for name, module in adapter_modules.items():
        sys.modules[name] = module
        modules[name] = module

    return modules

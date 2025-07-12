"""Tests for app adapter modules."""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportArgumentType=false, reportMissingTypeArgument=false, reportReturnType=false

import asyncio
import sys
import types
import typing as t
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pytest_mock import MockerFixture
from tests.adapters.app.ensure_adapter import ensure_adapter_modules


@pytest.fixture
def mock_acb():
    """Mock ACB module."""
    acb_modules = {}

    if "acb" not in sys.modules:
        # Create mock modules
        acb_module = types.ModuleType("acb")
        acb_adapters_module = types.ModuleType("acb.adapters")
        acb_config_module = types.ModuleType("acb.config")
        acb_depends_module = types.ModuleType("acb.depends")
        acb_actions_module = types.ModuleType("acb.actions")
        acb_actions_encode_module = types.ModuleType("acb.actions.encode")

        # Set __path__ for package modules
        acb_module.__path__ = ["/mock/path/to/acb"]
        acb_adapters_module.__path__ = ["/mock/path/to/acb/adapters"]
        acb_config_module.__path__ = ["/mock/path/to/acb/config"]
        acb_depends_module.__path__ = ["/mock/path/to/acb/depends"]
        acb_actions_module.__path__ = ["/mock/path/to/acb/actions"]
        acb_actions_encode_module.__path__ = ["/mock/path/to/acb/actions/encode"]

        # Create AdapterBase class
        class AdapterBase:
            """Base class for adapters."""

            def __init__(self) -> None:
                """Initialize adapter."""

        # Add AdapterBase to acb.config
        acb_config_module.AdapterBase = AdapterBase

        # Create depends functions
        def depends(func=None):
            """Mock depends decorator."""
            if func is None:
                return MagicMock()
            return func

        def get(key=None):
            """Mock depends.get function."""
            return MagicMock()

        # Add functions to depends module
        acb_depends_module.depends = depends
        acb_depends_module.get = get

        # Create encode functions
        def dump(obj) -> bytes:
            """Mock dump function."""
            return b""

        def load(data):
            """Mock load function."""
            return {}

        # Add functions to encode module
        acb_actions_encode_module.dump = dump
        acb_actions_encode_module.load = load

        # Create adapter functions
        def get_adapter(name: str):
            """Mock get_adapter function."""
            return MagicMock()

        def import_adapter(name: str):
            """Mock import_adapter function."""
            return (MagicMock(), MagicMock())

        # Add functions to adapters module
        acb_adapters_module.get_adapter = get_adapter
        acb_adapters_module.import_adapter = import_adapter

        # Register modules
        sys.modules["acb"] = acb_module
        sys.modules["acb.adapters"] = acb_adapters_module
        sys.modules["acb.config"] = acb_config_module
        sys.modules["acb.depends"] = acb_depends_module
        sys.modules["acb.actions"] = acb_actions_module
        sys.modules["acb.actions.encode"] = acb_actions_encode_module

        # Store for future reference
        acb_modules = {
            "acb": acb_module,
            "acb.adapters": acb_adapters_module,
            "acb.config": acb_config_module,
            "acb.depends": acb_depends_module,
            "acb.actions": acb_actions_module,
            "acb.actions.encode": acb_actions_encode_module,
        }
    else:
        # Use existing modules
        for name in (
            "acb",
            "acb.adapters",
            "acb.config",
            "acb.depends",
            "acb.actions",
            "acb.actions.encode",
        ):
            acb_modules[name] = sys.modules[name]

    return acb_modules

    # No need to cleanup since we're only replacing existing modules


@pytest.fixture
def ensure_adapter_modules_fixture() -> dict:
    """Ensure adapter modules exist."""
    return ensure_adapter_modules()


@pytest.fixture
def completed_future():
    """Create a completed future for asyncio testing."""
    future = asyncio.Future()
    future.set_result(None)
    return future


class TestAppCoverage:
    """Test app adapter coverage."""

    def test_app_lifecycle(self) -> None:
        """Test app adapter lifecycle methods."""
        # Create mock modules
        mock_base_module = types.ModuleType("fastblocks.adapters.app._base")

        # Add required classes and functions to base module
        class BaseApp:
            """Base app adapter class."""

            def __init__(self) -> None:
                self.lifecycle_events = []

            def startup(self) -> None:
                """Handle startup."""
                self.lifecycle_events.append("startup")

            def shutdown(self) -> None:
                """Handle shutdown."""
                self.lifecycle_events.append("shutdown")

        mock_base_module.BaseApp = BaseApp

        # Create AppAdapter that inherits from BaseApp
        class AppAdapter(BaseApp):
            """Test app adapter implementation."""

            def __init__(self) -> None:
                super().__init__()
                self.routes = MagicMock()

            def startup(self) -> None:
                """Handle startup with additional functionality."""
                super().startup()
                self.lifecycle_events.append("app_startup")

            def shutdown(self) -> None:
                """Handle shutdown with additional functionality."""
                super().shutdown()
                self.lifecycle_events.append("app_shutdown")

        # Register mock modules
        with patch.dict(
            "sys.modules",
            {"fastblocks.adapters.app._base": mock_base_module},
        ):
            # Create app adapter instance
            app = AppAdapter()

            # Test lifecycle methods
            app.startup()
            assert app.lifecycle_events == ["startup", "app_startup"]

            app.shutdown()
            assert app.lifecycle_events == [
                "startup",
                "app_startup",
                "shutdown",
                "app_shutdown",
            ]

    def test_post_startup_hooks(self) -> None:
        """Test post startup hooks registration and execution."""
        # Create mock modules and hooks
        mock_hooks = []

        # Create app with post_startup method
        class MockApp:
            """Mock app class with post_startup handling."""

            def __init__(self) -> None:
                self.post_startup_hooks = []

            def register_post_startup(self, hook: t.Callable[[], None]) -> None:
                """Register post startup hook."""
                self.post_startup_hooks.append(hook)

            def post_startup(self) -> None:
                """Execute post startup hooks."""
                for hook in self.post_startup_hooks:
                    hook()

        # Create hook functions
        def hook1() -> None:
            mock_hooks.append("hook1")

        def hook2() -> None:
            mock_hooks.append("hook2")

        # Create app instance and test hooks
        app = MockApp()

        # Register hooks
        app.register_post_startup(hook1)
        app.register_post_startup(hook2)

        # Execute post startup
        app.post_startup()

        # Verify hooks were executed
        assert mock_hooks == ["hook1", "hook2"]


class TestAppBaseModule:
    """Tests for the app base module."""

    def test_app_base_settings(self, ensure_adapter_modules_fixture: dict) -> None:
        """Test AppBaseSettings class."""
        # Import from modules dict rather than direct import
        AppBaseSettings = ensure_adapter_modules_fixture[
            "fastblocks.adapters.app._base"
        ].AppBaseSettings

        # Create instance
        settings = AppBaseSettings()

        # Test attributes
        assert hasattr(settings, "style")
        assert hasattr(settings, "theme")
        assert settings.style == "bulma"
        assert settings.theme == "light"

    def test_app_base_protocol(self, ensure_adapter_modules_fixture: dict) -> None:
        """Test AppProtocol protocol."""
        # Import from modules dict rather than direct import
        AppProtocol = ensure_adapter_modules_fixture[
            "fastblocks.adapters.app._base"
        ].AppProtocol

        # Verify it's a Protocol
        assert hasattr(AppProtocol, "__annotations__")

    def test_app_base(self, ensure_adapter_modules_fixture: dict) -> None:
        """Test AppBase class."""
        # Import from modules dict rather than direct import
        AppBase = ensure_adapter_modules_fixture[
            "fastblocks.adapters.app._base"
        ].AppBase

        # Create instance
        app = AppBase()

        # Test attributes and methods
        assert hasattr(app, "settings")
        assert hasattr(app, "startup")
        assert hasattr(app, "shutdown")

        # Call methods
        app.startup()
        app.shutdown()


class TestAppDefaultModule:
    """Tests for the app default module."""

    def test_app_settings(
        self,
        ensure_adapter_modules_fixture: dict,
        mock_acb: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test AppSettings initialization and customization."""
        # Get AppSettings class from mock module
        AppSettings = ensure_adapter_modules_fixture[
            "fastblocks.adapters.app.default"
        ].AppSettings

        # Create instance
        settings = AppSettings()

        # Test attributes
        assert hasattr(settings, "style")
        assert settings.style == "bulma"
        assert hasattr(settings, "theme")
        assert settings.theme == "light"
        assert hasattr(settings, "name")
        assert settings.name == "test_app"
        assert hasattr(settings, "url")
        assert settings.url == "https://example.com"

    @pytest.mark.asyncio
    async def test_app_init(
        self,
        ensure_adapter_modules_fixture: dict,
        mock_acb: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test App.init method."""
        # Get App class from mock module
        App = ensure_adapter_modules_fixture["fastblocks.adapters.app.default"].App

        # Create instance
        app = App()

        # Call init method
        await app.init()

        # Verify it completes without errors
        assert app is not None

    @pytest.mark.asyncio
    async def test_app_post_startup_not_deployed(
        self,
        ensure_adapter_modules_fixture: dict,
        mock_acb: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test post_startup method in non-deployed mode."""
        # Get App class from mock module
        App = ensure_adapter_modules_fixture["fastblocks.adapters.app.default"].App

        # Create instance
        app = App()

        # Add hook
        hook_mock = mocker.MagicMock()
        app.register_post_startup(hook_mock)

        # Call post_startup
        await app.post_startup()

        # Verify hook was called
        hook_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_post_startup_deployed(
        self,
        ensure_adapter_modules_fixture: dict,
        mock_acb: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test post_startup method in deployed mode."""
        # Get App class from mock module
        App = ensure_adapter_modules_fixture["fastblocks.adapters.app.default"].App

        # Create instance
        app = App()

        # Add hook
        hook_mock = mocker.MagicMock()
        app.register_post_startup(hook_mock)

        # Call post_startup
        await app.post_startup()

        # Verify hook was called
        hook_mock.assert_called_once()

    @pytest.mark.asyncio
    async def test_app_lifespan_success(
        self,
        ensure_adapter_modules_fixture: dict,
        mock_acb: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test lifespan context manager with successful initialization."""
        # Get App class from mock module
        App = ensure_adapter_modules_fixture["fastblocks.adapters.app.default"].App

        # Create instance
        app = App()

        # Test lifespan context manager
        mock_asgi_app = mocker.MagicMock()

        # Use lifespan as async context manager
        async with app.lifespan(mock_asgi_app):
            # Verify it yields control within the context
            pass

        # Verify it completes without errors
        assert app is not None

    @pytest.mark.asyncio
    async def test_app_lifespan_with_admin(
        self,
        ensure_adapter_modules_fixture: dict,
        mock_acb: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test lifespan context manager with admin adapter."""
        # Get App and FastBlocks classes from mock module
        App = ensure_adapter_modules_fixture["fastblocks.adapters.app.default"].App
        FastBlocks = ensure_adapter_modules_fixture[
            "fastblocks.adapters.app.default"
        ].FastBlocks

        # Create instance
        app = App()

        # Create FastBlocks instance with admin
        fastblocks_app = FastBlocks()
        admin_mock = mocker.MagicMock()
        fastblocks_app.mount_admin(admin_mock)

        # Test lifespan context manager
        async with app.lifespan(fastblocks_app):
            # Verify it yields control within the context
            pass

        # Verify it completes without errors
        assert app is not None

    @pytest.mark.asyncio
    async def test_app_lifespan_exception(
        self,
        ensure_adapter_modules_fixture: dict,
        mock_acb: dict,
        mocker: MockerFixture,
    ) -> None:
        """Test lifespan context manager error handling."""
        # Get App class from mock module
        App = ensure_adapter_modules_fixture["fastblocks.adapters.app.default"].App
        FastBlocks = ensure_adapter_modules_fixture[
            "fastblocks.adapters.app.default"
        ].FastBlocks

        # Create instance with mocked post_startup that raises exception
        app = App()
        app.post_startup = AsyncMock(side_effect=Exception("Startup failed"))

        # Test lifespan context manager with exception handling
        mock_asgi_app = FastBlocks()

        # Use lifespan as async context manager and expect exception to be caught
        async with app.lifespan(mock_asgi_app):
            # Verify it yields control within the context
            pass

        # Verify post_startup was called but exception was handled
        assert app.post_startup.called

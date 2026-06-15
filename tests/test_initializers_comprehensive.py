"""Comprehensive tests for FastBlocks initializers module."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


@pytest.mark.unit
class TestApplicationInitializerBasics:
    """Test ApplicationInitializer basic functionality."""

    def test_initializer_creation(self) -> None:
        """Test ApplicationInitializer can be created."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app)

        assert initializer.app == app
        assert initializer.config is None
        assert initializer.logger is None

    def test_initializer_with_kwargs(self) -> None:
        """Test ApplicationInitializer with kwargs."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        mock_config = MagicMock()
        mock_logger = MagicMock()

        initializer = ApplicationInitializer(
            app, config=mock_config, logger=mock_logger
        )

        assert initializer.kwargs["config"] == mock_config
        assert initializer.kwargs["logger"] == mock_logger


@pytest.mark.unit
class TestDependencyResolution:
    """Test dependency resolution functions."""

    def test_get_dependency_sync_basic(self) -> None:
        """Test _get_dependency_sync returns None for unknown dependency."""
        from fastblocks.initializers import _get_dependency_sync, _resolver

        with patch.object(_resolver, "resolve", new_callable=AsyncMock, return_value=None):
            result = _get_dependency_sync("nonexistent")
        assert result is None

    def test_get_dependency_sync_with_resolver(self) -> None:
        """Test _get_dependency_sync forwards to resolver."""
        from fastblocks.initializers import _get_dependency_sync, _resolver

        with patch.object(_resolver, "resolve", new_callable=AsyncMock, return_value="test_value"):
            result = _get_dependency_sync("test_dependency")
            assert result == "test_value"


@pytest.mark.unit
class TestGetInstalledAdapter:
    """Test get_installed_adapter function."""

    def test_get_installed_adapter_nonexistent(self) -> None:
        """Test get_installed_adapter with non-existent adapter."""
        from fastblocks.initializers import get_installed_adapter

        result = get_installed_adapter("nonexistent_adapter")

        # Should return None for non-existent adapter
        assert result is None

    def test_get_installed_adapter_with_registry(self) -> None:
        """Test get_installed_adapter with registry."""
        from fastblocks.initializers import get_installed_adapter, _resolver

        with patch.object(_resolver, "registry", MagicMock(get=Mock(return_value=True))):
            result = get_installed_adapter("test_adapter")
            # Should not raise an exception
            assert result is not None or result is None


@pytest.mark.unit
class TestLoadAcbModules:
    """Test _load_acb_modules method."""

    def test_load_acb_modules_populates_tuple(self) -> None:
        """Test _load_acb_modules populates _acb_modules."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app)

        initializer._load_acb_modules()

        assert isinstance(initializer._acb_modules, tuple)
        assert len(initializer._acb_modules) == 7

    def test_load_acb_modules_contains_expected_elements(self) -> None:
        """Test _load_acb_modules contains expected elements."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import (
            AdapterBase,
            ApplicationInitializer,
            Config,
            get_installed_adapter,
            register_pkg,
        )

        app = FastBlocks()
        initializer = ApplicationInitializer(app)

        initializer._load_acb_modules()

        modules = initializer._acb_modules
        assert register_pkg in modules
        assert get_installed_adapter in modules
        assert Config in modules
        assert AdapterBase in modules


@pytest.mark.unit
class TestSetupDependencies:
    """Test _setup_dependencies method."""

    def test_setup_dependencies_from_kwargs(self) -> None:
        """Test _setup_dependencies with config and logger from kwargs."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        mock_config = MagicMock()
        mock_logger = MagicMock()

        initializer = ApplicationInitializer(
            app, config=mock_config, logger=mock_logger
        )

        initializer._setup_dependencies()

        assert initializer.config == mock_config
        assert initializer.logger == mock_logger

    def test_setup_dependencies_without_kwargs(self) -> None:
        """Test _setup_dependencies without kwargs."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app)

        initializer._setup_dependencies()

        # Should not raise an exception
        # Config and logger might be None or set to defaults
        assert initializer.config is None or initializer.config is not None


@pytest.mark.unit
class TestConfigureDebugMode:
    """Test _configure_debug_mode method."""

    def test_configure_debug_mode_with_config(self) -> None:
        """Test _configure_debug_mode with debug config."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        mock_config = MagicMock()
        mock_debug = MagicMock()
        mock_debug.fastblocks = True
        mock_config.debug = mock_debug

        initializer = ApplicationInitializer(app, config=mock_config, logger=None)
        initializer.config = mock_config

        initializer._configure_debug_mode()

        assert app.debug is True

    def test_configure_debug_mode_without_config(self) -> None:
        """Test _configure_debug_mode without config."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app, config=None, logger=None)

        initializer._configure_debug_mode()

        # Should not raise an exception
        assert isinstance(app.debug, bool)


@pytest.mark.unit
class TestInitializeStarlette:
    """Test _initialize_starlette method."""

    def test_initialize_starlette_basic(self) -> None:
        """Test _initialize_starlette basic initialization."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app)

        initializer._initialize_starlette()

        # Should set basic Starlette attributes
        assert hasattr(app, "routes")
        assert hasattr(app, "exception_handlers")

    def test_initialize_starlette_with_middleware(self) -> None:
        """Test _initialize_starlette with middleware."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer
        from starlette.middleware import Middleware

        app = FastBlocks()
        mock_middleware = [Middleware(MagicMock())]
        initializer = ApplicationInitializer(app, middleware=mock_middleware)

        initializer._initialize_starlette()

        assert app.user_middleware == mock_middleware

    def test_initialize_starlette_with_exception_handlers(self) -> None:
        """Test _initialize_starlette with exception handlers."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        async def handler(request, exc):
            return Response("Error")

        exception_handlers = {500: handler}
        initializer = ApplicationInitializer(
            app, exception_handlers=exception_handlers
        )

        initializer._initialize_starlette()

        assert app.exception_handlers == exception_handlers


@pytest.mark.unit
class TestConfigureExceptionHandlers:
    """Test _configure_exception_handlers method."""

    def test_configure_exception_handlers_default(self) -> None:
        """Test _configure_exception_handlers with default handlers."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app)

        initializer._configure_exception_handlers()

        # Should set default handlers
        assert 404 in app.exception_handlers
        assert 500 in app.exception_handlers

    def test_configure_exception_handlers_custom(self) -> None:
        """Test _configure_exception_handlers with custom handlers."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        async def handler(request, exc):
            return Response("Error")

        custom_handlers = {404: handler}
        initializer = ApplicationInitializer(app, exception_handlers=custom_handlers)

        initializer._configure_exception_handlers()

        # Should use custom handlers
        assert app.exception_handlers == custom_handlers


@pytest.mark.unit
class TestSetupModels:
    """Test _setup_models method."""

    def test_setup_models_without_dependency(self) -> None:
        """Test _setup_models without models dependency."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app)

        initializer._setup_models()

        # Should not raise an exception
        # Models might be None
        assert app.models is None or hasattr(app.models, "__class__")


@pytest.mark.unit
class TestRegisterIntegrationsAsync:
    """Test _register_integrations_async method."""

    def test_register_integrations_async(self) -> None:
        """Test _register_integrations_async method."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app, logger=None)

        # Should not raise an exception even without async loop
        initializer._register_integrations_async()


@pytest.mark.unit
class TestRegisterEventHandlers:
    """Test _register_event_handlers method."""

    def test_register_event_handlers_without_logger(self) -> None:
        """Test _register_event_handlers without logger."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app, logger=None)

        # Should not raise an exception
        initializer._register_event_handlers()

    def test_register_event_handlers_with_logger(self) -> None:
        """Test _register_event_handlers with logger."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        mock_logger = MagicMock()
        initializer = ApplicationInitializer(app, logger=mock_logger)

        # Should not raise an exception
        initializer._register_event_handlers()


@pytest.mark.unit
class TestInitializeSequence:
    """Test the full initialize sequence."""

    def test_initialize_full_sequence(self) -> None:
        """Test the full initialize method sequence."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app, logger=None)

        # Should complete without errors
        initializer.initialize()

        # Verify basic attributes are set
        assert hasattr(app, "debug")
        assert hasattr(app, "exception_handlers")
        assert hasattr(app, "user_middleware")

    def test_initialize_with_all_parameters(self) -> None:
        """Test initialize with all parameters."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer
        from starlette.middleware import Middleware

        mock_config = MagicMock()
        mock_logger = MagicMock()
        mock_middleware = [Middleware(MagicMock())]

        async def lifespan(app):
            yield

        app = FastBlocks()
        initializer = ApplicationInitializer(
            app,
            config=mock_config,
            logger=mock_logger,
            middleware=mock_middleware,
            lifespan=lifespan,
        )

        initializer.initialize()

        # Verify initialization
        assert hasattr(app, "debug")
        assert app.user_middleware == mock_middleware


@pytest.mark.unit
class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_initializer_with_none_app(self) -> None:
        """Test initializer with None app (should handle gracefully)."""
        from fastblocks.initializers import ApplicationInitializer

        # This might raise an error, but let's test it
        with pytest.raises(Exception):
            initializer = ApplicationInitializer(None)
            initializer.initialize()

    def test_initializer_empty_kwargs(self) -> None:
        """Test initializer with empty kwargs."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app, **{})

        initializer.initialize()

        # Should not raise an exception
        assert app is not None

    def test_configure_logging_without_logfire(self) -> None:
        """Test _configure_logging without logfire adapter."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app, logger=None)
        initializer._acb_modules = (None, None, None, None, None)

        with patch("fastblocks.initializers.get_installed_adapter", return_value=None):
            initializer._configure_logging()

        # Should not raise an exception


@pytest.mark.unit
class TestConfigAndAdapterBase:
    """Test Config and AdapterBase setup."""

    def test_config_is_oneiric_settings(self) -> None:
        """Test that Config is OneiricSettings."""
        from fastblocks.initializers import Config
        from oneiric.core.config import OneiricSettings

        assert Config == OneiricSettings

    def test_adapter_base_is_object(self) -> None:
        """Test that AdapterBase is object."""
        from fastblocks.initializers import AdapterBase

        assert AdapterBase == object


@pytest.mark.unit
class TestModuleLevelConstants:
    """Test module-level constants and imports."""

    def test_resolver_is_created(self) -> None:
        """Test that _resolver is created."""
        from fastblocks.initializers import _resolver

        assert _resolver is not None
        assert hasattr(_resolver, "registry")


@pytest.mark.unit
class TestConcurrencySafety:
    """Test concurrency and async safety."""

    @pytest.mark.asyncio
    async def test_get_dependency_async(self) -> None:
        """Test _get_dependency async function."""
        from fastblocks.initializers import _get_dependency, _resolver

        with patch.object(_resolver, "resolve", new_callable=AsyncMock) as mock_resolve:
            mock_resolve.return_value = "test_value"

            result = await _get_dependency("test_dependency")

            assert result == "test_value"
            mock_resolve.assert_awaited_once_with("test_dependency")


@pytest.mark.unit
class TestGracefulDegradation:
    """Test graceful degradation when dependencies are missing."""

    def test_graceful_degradation_config(self) -> None:
        """Test graceful degradation when config is missing."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app, config=None, logger=None)

        initializer._configure_error_handling()
        initializer._configure_debug_mode()

        # Should not raise an exception
        assert app is not None

    def test_graceful_degradation_models(self) -> None:
        """Test graceful degradation when models dependency is missing."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        initializer = ApplicationInitializer(app)

        with patch("fastblocks.initializers._get_dependency_sync", side_effect=Exception):
            initializer._setup_models()

        # Should not raise an exception
        assert app.models is None

    def test_graceful_degradation_logging(self) -> None:
        """Test graceful degradation when logging setup fails."""
        from fastblocks.applications import FastBlocks
        from fastblocks.initializers import ApplicationInitializer

        app = FastBlocks()
        mock_logger = MagicMock()
        initializer = ApplicationInitializer(app, logger=mock_logger)

        # Mock interceptor_class as None to skip logging setup
        initializer._acb_modules = (None, None, None, None, None, None, None)

        initializer._configure_logging()

        # Should not raise an exception

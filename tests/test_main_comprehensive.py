"""Comprehensive tests for fastblocks.main module.

This test suite covers:
- LazyApp initialization and behavior
- LazyLogger initialization and behavior
- get_app() function
- get_logger() function
- Error handling for missing dependencies
- Dev mode checks
"""

import asyncio
import logging
from unittest import mock

import pytest

from fastblocks import main


class TestLazyApp:
    """Test LazyApp proxy class."""

    def test_lazyapp_attribute_error_before_init(self) -> None:
        """Test that LazyApp raises AttributeError before initialization."""
        lazy_app = main.LazyApp()
        with pytest.raises(AttributeError, match="has not finished initializing"):
            _ = lazy_app.nonexistent_attr

    def test_lazyapp_getattr_after_init(self) -> None:
        """Test that LazyApp proxy attributes after initialization."""
        # Create a mock app instance
        mock_app = mock.MagicMock()
        mock_app.test_attr = "test_value"
        mock_app.route = mock.MagicMock()

        # Set the global instance
        main._app_instance = mock_app

        try:
            lazy_app = main.LazyApp()
            assert lazy_app.test_attr == "test_value"
            lazy_app.route("/test", lambda: None)
            mock_app.route.assert_called_once()
        finally:
            main._app_instance = None

    def test_lazyapp_call(self) -> None:
        """Test LazyApp async call interface."""

        async def run_test() -> None:
            # Mock the get_app function
            mock_app = mock.MagicMock()

            async def mock_asgi_app(scope, receive, send):
                await send({"type": "http.response.start"})

            mock_app.side_effect = mock_asgi_app

            with mock.patch.object(main, "get_app", return_value=mock_app):
                lazy_app = main.LazyApp()
                scope = {"type": "http"}
                receive = mock.MagicMock()
                send = mock.MagicMock()

                await lazy_app(scope, receive, send)
                mock_app.assert_called_once_with(scope, receive, send)

        asyncio.run(run_test())


class TestLazyLogger:
    """Test LazyLogger proxy class."""

    def test_lazylogger_attribute_error_before_init(self) -> None:
        """Test that LazyLogger raises AttributeError before initialization."""
        lazy_logger = main.LazyLogger()
        with pytest.raises(AttributeError, match="logger has not finished initializing"):
            _ = lazy_logger.nonexistent_attr

    def test_lazylogger_getattr_after_init(self) -> None:
        """Test that LazyLogger proxy attributes after initialization."""
        # Create a mock logger instance
        mock_logger = mock.MagicMock()
        mock_logger.test_method = mock.MagicMock(return_value="result")

        # Set the global instance
        main._logger_instance = mock_logger

        try:
            lazy_logger = main.LazyLogger()
            assert lazy_logger.test_method() == "result"
            mock_logger.test_method.assert_called_once()
        finally:
            main._logger_instance = None

    def test_lazylogger_call_callable(self) -> None:
        """Test LazyLogger when logger is callable."""
        # Create a callable logger
        def mock_callable_logger(*args, **kwargs):
            return f"logged: {args[0] if args else ''}"

        main._logger_instance = mock_callable_logger

        try:
            lazy_logger = main.LazyLogger()
            result = lazy_logger("test message")
            assert result == "logged: test message"
        finally:
            main._logger_instance = None

    def test_lazylogger_call_non_callable(self) -> None:
        """Test LazyLogger when logger is not callable."""
        # Create a non-callable logger
        mock_logger = mock.MagicMock()
        mock_logger.test_attr = "value"

        main._logger_instance = mock_logger

        try:
            lazy_logger = main.LazyLogger()
            # Should return the logger itself when called
            result = lazy_logger()
            assert result == mock_logger
        finally:
            main._logger_instance = None


class TestGetApp:
    """Test get_app() function."""

    def test_check_dev_mode_same_dir(self, tmp_path: pytest.TempPathFactory) -> None:
        """Test dev mode check when in same directory."""
        # This test verifies the dev mode check logic
        with mock.patch("pathlib.Path.cwd", return_value=tmp_path):
            with mock.patch(
                "fastblocks.main.Path.__eq__", return_value=True
            ):  # Simulate being in dev mode
                with pytest.raises(RuntimeError, match="cannot be run from its own package"):
                    main._check_dev_mode()

    @pytest.mark.asyncio
    async def test_get_app_first_call(self) -> None:
        """Test get_app() on first call (initialization)."""
        mock_app = mock.MagicMock()
        mock_logger = mock.MagicMock()

        async def mock_get_app_dependency(name: str):
            if name == "app":
                return mock_app
            raise RuntimeError(f"No dependency: {name}")

        with mock.patch.object(main, "_get_dependency", side_effect=mock_get_app_dependency):
            with mock.patch.object(main, "_check_dev_mode"):
                with mock.patch.object(main, "register_pkg"):
                    with mock.patch.object(
                        main, "_handle_registration"
                    ):  # Mock this to avoid actual registration
                        with mock.patch.object(
                            main, "_handle_adapter_registration"
                        ):  # Mock this too
                            with mock.patch.object(
                                main, "_get_logger_instance", return_value=mock_logger
                            ):
                                app = await main.get_app()
                                assert app == mock_app
                                assert main._app_instance == mock_app

    @pytest.mark.asyncio
    async def test_get_app_cached(self) -> None:
        """Test get_app() returns cached instance on subsequent calls."""
        mock_app = mock.MagicMock()
        main._app_instance = mock_app

        try:
            app = await main.get_app()
            assert app == mock_app
            # Should not reinitialize
        finally:
            main._app_instance = None

    @pytest.mark.asyncio
    async def test_get_app_registration_failure(self) -> None:
        """Test get_app() when adapter registration fails."""

        async def mock_handle_registration():
            raise RuntimeError("Registration failed")

        with mock.patch.object(main, "_check_dev_mode"):
            with mock.patch.object(main, "register_pkg"):
                with mock.patch.object(
                    main, "_handle_registration", side_effect=mock_handle_registration
                ):
                    with pytest.raises(RuntimeError, match="Failed to register"):
                        await main.get_app()

    @pytest.mark.asyncio
    async def test_get_app_package_registration_failure(self) -> None:
        """Test get_app() when package registration fails."""
        with mock.patch.object(main, "_check_dev_mode"):
            with mock.patch.object(
                main, "register_pkg", side_effect=RuntimeError("Package registration failed")
            ):
                with pytest.raises(RuntimeError, match="Failed to register FastBlocks adapters"):
                    await main.get_app()


class TestGetLogger:
    """Test get_logger() function."""

    def test_get_logger_before_init(self) -> None:
        """Test get_logger() before logger initialization."""
        # Reset logger instance
        main._logger_instance = None
        logger = main.get_logger()
        assert logger is None

    def test_get_logger_after_init(self) -> None:
        """Test get_logger() after logger initialization."""
        mock_logger = mock.MagicMock()
        main._logger_instance = mock_logger

        try:
            logger = main.get_logger()
            assert logger == mock_logger
        finally:
            main._logger_instance = None


class TestGetLoggerInstance:
    """Test _get_logger_instance() function."""

    @pytest.mark.asyncio
    async def test_get_logger_instance_success(self) -> None:
        """Test _get_logger_instance() with successful resolution."""
        mock_logger = mock.MagicMock()

        async def mock_resolve(name: str):
            if name == "logger":
                return mock_logger
            raise RuntimeError(f"No dependency: {name}")

        with mock.patch.object(main, "_get_dependency", side_effect=mock_resolve):
            logger = await main._get_logger_instance()
            assert logger == mock_logger

    @pytest.mark.asyncio
    async def test_get_logger_instance_fallback(self) -> None:
        """Test _get_logger_instance() fallback to logging.getLogger()."""

        async def mock_resolve(name: str):
            raise RuntimeError(f"No dependency: {name}")

        with mock.patch.object(main, "_get_dependency", side_effect=mock_resolve):
            logger = await main._get_logger_instance()
            assert isinstance(logger, logging.Logger)
            assert logger.name == "fastblocks"


class TestGetAppInstance:
    """Test _get_app_instance() function."""

    @pytest.mark.asyncio
    async def test_get_app_instance_success(self) -> None:
        """Test _get_app_instance() with successful resolution."""
        mock_app = mock.MagicMock()

        async def mock_resolve(name: str):
            if name == "app":
                return mock_app
            raise RuntimeError(f"No dependency: {name}")

        with mock.patch.object(main, "_get_dependency", side_effect=mock_resolve):
            app = await main._get_app_instance()
            assert app == mock_app

    @pytest.mark.asyncio
    async def test_get_app_instance_failure(self) -> None:
        """Test _get_app_instance() when dependency resolution fails."""

        async def mock_resolve(name: str):
            raise RuntimeError(f"No dependency: {name}")

        with mock.patch.object(main, "_get_dependency", side_effect=mock_resolve):
            with pytest.raises(RuntimeError, match="Failed to get app adapter"):
                await main._get_app_instance()


class TestHandleRegistration:
    """Test _handle_registration() function."""

    @pytest.mark.asyncio
    async def test_handle_registration_success(self) -> None:
        """Test successful adapter registration."""

        async def mock_register_builtin_adapters():
            return None

        with mock.patch(
            "fastblocks.main.register_builtin_adapters",
            side_effect=mock_register_builtin_adapters,
        ):
            # Should not raise
            await main._handle_registration()

    @pytest.mark.asyncio
    async def test_handle_registration_failure(self) -> None:
        """Test adapter registration failure."""

        async def mock_register_builtin_adapters():
            raise RuntimeError("Registration error")

        with mock.patch(
            "fastblocks.main.register_builtin_adapters",
            side_effect=mock_register_builtin_adapters,
        ):
            with pytest.raises(RuntimeError, match="Failed to register builtin adapters"):
                await main._handle_registration()


class TestHandleAdapterRegistration:
    """Test _handle_adapter_registration() function."""

    @pytest.mark.asyncio
    async def test_handle_adapter_registration_success(self) -> None:
        """Test successful adapter metadata registration."""

        async def mock_register_adapter_metadata(path):
            return None

        with mock.patch(
            "fastblocks.main.register_adapter_metadata",
            side_effect=mock_register_adapter_metadata,
        ):
            # Should not raise even if it fails internally (has suppress)
            await main._handle_adapter_registration()

    @pytest.mark.asyncio
    async def test_handle_adapter_registration_exception(self) -> None:
        """Test adapter metadata registration with exception."""

        async def mock_register_adapter_metadata(path):
            raise RuntimeError("Metadata registration error")

        with mock.patch(
            "fastblocks.main.register_adapter_metadata",
            side_effect=mock_register_adapter_metadata,
        ):
            # Should suppress exception
            await main._handle_adapter_registration()


class TestGetDependency:
    """Test _get_dependency() function."""

    @pytest.mark.asyncio
    async def test_get_dependency_success(self) -> None:
        """Test successful dependency resolution."""
        mock_value = mock.MagicMock()

        with mock.patch.object(main._resolver, "resolve", return_value=mock_value):
            result = await main._get_dependency("test_dependency")
            assert result == mock_value

    @pytest.mark.asyncio
    async def test_get_dependency_failure(self) -> None:
        """Test dependency resolution failure."""

        async def mock_resolve(name: str):
            raise RuntimeError(f"No dependency: {name}")

        with mock.patch.object(main._resolver, "resolve", side_effect=mock_resolve):
            with pytest.raises(RuntimeError):
                await main._get_dependency("nonexistent_dependency")


class TestModuleAttributes:
    """Test module-level attributes."""

    def test_root_path_exists(self) -> None:
        """Test that root_path is properly set."""
        assert main.root_path is not None
        assert main.root_path.exists()

    def test_lazy_app_and_logger_instances(self) -> None:
        """Test that module-level app and logger are Lazy instances."""
        assert isinstance(main.app, main.LazyApp)
        assert isinstance(main.logger, main.LazyLogger)

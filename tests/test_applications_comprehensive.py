"""Comprehensive tests for FastBlocks applications module."""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send


@pytest.mark.unit
class TestMiddlewareManager:
    """Test MiddlewareManager class."""

    def test_middleware_manager_initialization(self) -> None:
        """Test MiddlewareManager initialization."""
        from fastblocks.applications import MiddlewareManager

        manager = MiddlewareManager()

        assert manager._system_middleware == {}
        assert manager._middleware_stack_cache is None
        assert manager.user_middleware == []

    def test_add_user_middleware_without_position(self) -> None:
        """Test adding user middleware without position."""
        from fastblocks.applications import MiddlewareManager

        manager = MiddlewareManager()
        mock_middleware = MagicMock()
        mock_middleware_class = Mock(return_value=mock_middleware)

        manager.add_user_middleware(mock_middleware_class, arg1="value1")

        assert len(manager.user_middleware) == 1
        assert manager._middleware_stack_cache is None

    def test_add_user_middleware_with_position(self) -> None:
        """Test adding user middleware with position."""
        from fastblocks.applications import MiddlewareManager

        manager = MiddlewareManager()
        mock_middleware1 = MagicMock()
        mock_middleware2 = MagicMock()
        mock_middleware_class1 = Mock(return_value=mock_middleware1)
        mock_middleware_class2 = Mock(return_value=mock_middleware2)

        manager.add_user_middleware(mock_middleware_class1)
        manager.add_user_middleware(mock_middleware_class2, position=0)

        assert len(manager.user_middleware) == 2
        assert manager._middleware_stack_cache is None

    def test_add_system_middleware(self) -> None:
        """Test adding system middleware."""
        from fastblocks.applications import MiddlewareManager, MiddlewarePosition

        manager = MiddlewareManager()
        mock_middleware = (MagicMock(), {"option": "value"})

        manager.add_system_middleware(
            MagicMock(), position=MiddlewarePosition.CSRF, option="value"
        )

        assert MiddlewarePosition.CSRF in manager._system_middleware
        assert manager._middleware_stack_cache is None

    def test_get_middleware_stack(self) -> None:
        """Test getting middleware stack info."""
        from fastblocks.applications import MiddlewareManager, MiddlewarePosition

        manager = MiddlewareManager()

        # Add user middleware
        mock_class = Mock()
        mock_class.__name__ = "TestMiddleware"
        manager.add_user_middleware(mock_class)

        # Add system middleware
        manager.add_system_middleware(
            Mock(__name__="SystemMiddleware"), position=MiddlewarePosition.SESSION
        )

        stack = manager.get_middleware_stack()

        assert "user_middleware" in stack
        assert "system_middleware" in stack
        assert isinstance(stack["user_middleware"], list)
        assert isinstance(stack["system_middleware"], dict)


@pytest.mark.unit
class TestFastBlocksSettings:
    """Test FastBlocksSettings class."""

    def test_fastblocks_settings_subclass_hook(self) -> None:
        """Test FastBlocksSettings __init_subclass__ hook."""
        from fastblocks.applications import FastBlocksSettings

        # Creating a subclass should not raise an error
        class MySettings(FastBlocksSettings):
            pass

        assert MySettings is not None

    def test_fastblocks_settings_multiple_subclasses(self) -> None:
        """Test FastBlocksSettings with multiple subclasses."""
        from fastblocks.applications import FastBlocksSettings

        class Settings1(FastBlocksSettings):
            pass

        class Settings2(FastBlocksSettings):
            pass

        # Both should exist and be different
        assert Settings1 is not Settings2


@pytest.mark.unit
class TestFastBlocksBasics:
    """Test basic FastBlocks functionality."""

    def test_fastblocks_initialization_minimal(self) -> None:
        """Test FastBlocks initialization with minimal arguments."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()

        assert app is not None
        assert hasattr(app, "middleware_manager")
        assert hasattr(app, "templates")
        assert hasattr(app, "models")
        assert app.templates is None
        assert app.models is None

    def test_fastblocks_initialization_with_middleware(self) -> None:
        """Test FastBlocks initialization with middleware."""
        from fastblocks.applications import FastBlocks

        middleware = [Middleware(MagicMock())]
        app = FastBlocks(middleware=middleware)

        assert app is not None
        assert app.user_middleware == middleware

    def test_fastblocks_initialization_with_exception_handlers(self) -> None:
        """Test FastBlocks initialization with exception handlers."""
        from fastblocks.applications import FastBlocks

        async def handler(request: Request, exc: Exception) -> Response:
            return Response("Error", status_code=500)

        exception_handlers = {Exception: handler}
        app = FastBlocks(exception_handlers=exception_handlers)

        assert app is not None
        assert Exception in app.exception_handlers

    def test_fastblocks_add_middleware(self) -> None:
        """Test FastBlocks.add_middleware method."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        mock_middleware_class = MagicMock()

        app.add_middleware(mock_middleware_class, arg1="value1")

        assert len(app.user_middleware) == 1


@pytest.mark.unit
class TestFastBlocksMiddlewareProperties:
    """Test FastBlocks middleware-related properties."""

    def test_user_middleware_property(self) -> None:
        """Test user_middleware property getter/setter."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        middleware = [Middleware(MagicMock())]

        app.user_middleware = middleware

        assert app.user_middleware == middleware

    def test_system_middleware_property(self) -> None:
        """Test _system_middleware property getter/setter."""
        from fastblocks.applications import FastBlocks, MiddlewarePosition

        app = FastBlocks()
        system_middleware = {MiddlewarePosition.CSRF: (MagicMock(), {})}

        app._system_middleware = system_middleware

        assert app._system_middleware == system_middleware

    def test_middleware_stack_cache_property(self) -> None:
        """Test _middleware_stack_cache property getter/setter."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        mock_cache = MagicMock()

        app._middleware_stack_cache = mock_cache

        assert app._middleware_stack_cache == mock_cache


@pytest.mark.unit
class TestFastBlocksMiddlewareOperations:
    """Test FastBlocks middleware operations."""

    def test_add_system_middleware(self) -> None:
        """Test add_system_middleware method."""
        from fastblocks.applications import FastBlocks, MiddlewarePosition

        app = FastBlocks()
        mock_middleware_class = MagicMock()

        app.add_system_middleware(
            mock_middleware_class, position=MiddlewarePosition.CSRF, option="value"
        )

        assert MiddlewarePosition.CSRF in app._system_middleware

    def test_extract_middleware_info_from_middleware_object(self) -> None:
        """Test _extract_middleware_info with Middleware object."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        mock_cls = MagicMock()
        mock_cls.__name__ = "TestMiddleware"
        middleware = Middleware(mock_cls, arg1="value1")

        info = app._extract_middleware_info(middleware)

        assert info is not None
        assert isinstance(info, tuple)
        assert len(info) == 2
        assert isinstance(info[0], str)
        assert info[1] == mock_cls

    def test_extract_middleware_info_from_tuple(self) -> None:
        """Test _extract_middleware_info with tuple."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        mock_cls = MagicMock()
        middleware = (mock_cls, {"option": "value"})

        info = app._extract_middleware_info(middleware)

        assert info is not None
        assert isinstance(info, tuple)

    def test_extract_middleware_info_invalid(self) -> None:
        """Test _extract_middleware_info with invalid input."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()

        info = app._extract_middleware_info(None)

        assert info is None


@pytest.mark.unit
class TestFastBlocksDependencies:
    """Test FastBlocks dependency resolution."""

    def test_get_dependencies_with_none(self) -> None:
        """Test _get_dependencies when both config and logger are None."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()

        config, logger = app._get_dependencies(None, None)

        # Should return None values when dependencies not available
        assert config is None
        assert logger is None

    def test_get_dependencies_with_provided_values(self) -> None:
        """Test _get_dependencies with provided config and logger."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        mock_config = MagicMock()
        mock_logger = MagicMock()

        config, logger = app._get_dependencies(mock_config, mock_logger)

        assert config == mock_config
        assert logger == mock_logger


@pytest.mark.unit
class TestFastBlocksExceptionHandling:
    """Test FastBlocks exception handling."""

    def test_separate_exception_handlers_with_500(self) -> None:
        """Test _separate_exception_handlers with 500 error."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        async def handler(request: Request, exc: Exception) -> Response:
            return Response("Error", status_code=500)

        app.exception_handlers = {500: handler, Exception: handler}

        error_handler, other_handlers = app._separate_exception_handlers()

        assert error_handler is not None
        assert len(other_handlers) == 0

    def test_separate_exception_handlers_without_500(self) -> None:
        """Test _separate_exception_handlers without 500 error."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        async def handler(request: Request, exc: Exception) -> Response:
            return Response("Error", status_code=404)

        app.exception_handlers = {404: handler}

        error_handler, other_handlers = app._separate_exception_handlers()

        assert error_handler is None
        assert len(other_handlers) == 1
        assert 404 in other_handlers


@pytest.mark.unit
class TestFastBlocksMiddlewareBuilding:
    """Test FastBlocks middleware stack building."""

    def test_build_base_middleware_list(self) -> None:
        """Test _build_base_middleware_list."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        app.debug = True

        error_handler = MagicMock()
        middleware_list = app._build_base_middleware_list(error_handler)

        assert len(middleware_list) == 1
        assert middleware_list[0].cls.__name__ == "ServerErrorMiddleware"

    def test_apply_system_middleware_overrides_empty(self) -> None:
        """Test _apply_system_middleware_overrides with no overrides."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        system_middleware = [(MagicMock(), {}), (MagicMock(), {})]
        app._system_middleware = {}
        mock_logger = MagicMock()

        result = app._apply_system_middleware_overrides(system_middleware, mock_logger)

        assert result == system_middleware

    def test_get_system_middleware_with_overrides(self) -> None:
        """Test _get_system_middleware_with_overrides."""
        from fastblocks.applications import FastBlocks, MiddlewarePosition

        app = FastBlocks()
        mock_middleware = (MagicMock(), {})
        app._system_middleware = {MiddlewarePosition.CSRF: mock_middleware}

        middleware = app._get_system_middleware_with_overrides()

        assert isinstance(middleware, list)


@pytest.mark.unit
class TestFastBlocksBuildMiddlewareStack:
    """Test FastBlocks.build_middleware_stack."""

    def test_build_middleware_stack_with_cache(self) -> None:
        """Test build_middleware_stack returns cached value."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        mock_cache = MagicMock()
        app._middleware_stack_cache = mock_cache

        result = app.build_middleware_stack()

        assert result == mock_cache

    def test_build_middleware_stack_without_cache(self) -> None:
        """Test build_middleware_stack without cache."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        app.exception_handlers = {}
        app.debug = False

        result = app.build_middleware_stack()

        assert result is not None
        # Should cache the result
        assert app._middleware_stack_cache is not None


@pytest.mark.unit
class TestFastBlocksGetMiddlewareStack:
    """Test FastBlocks.get_middleware_stack."""

    def test_get_middleware_stack_returns_list(self) -> None:
        """Test get_middleware_stack returns a list."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()

        stack = app.get_middleware_stack()

        assert isinstance(stack, list)
        assert len(stack) > 0

    def test_get_middleware_stack_includes_exception_middleware(self) -> None:
        """Test get_middleware_stack includes ExceptionMiddleware."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()

        stack = app.get_middleware_stack()

        middleware_names = [m[0] for m in stack]
        assert "ExceptionMiddleware" in middleware_names


@pytest.mark.unit
class TestFastBlocksEdgeCases:
    """Test FastBlocks edge cases."""

    def test_fastblocks_with_empty_exception_handlers(self) -> None:
        """Test FastBlocks with empty exception handlers."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks(exception_handlers={})

        assert app is not None

    def test_fastblocks_with_no_user_middleware(self) -> None:
        """Test FastBlocks with no user middleware."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()

        assert len(app.user_middleware) == 0

    def test_fastblocks_logger_validation(self) -> None:
        """Test _get_dependencies validates logger."""
        from fastblocks.applications import FastBlocks

        app = FastBlocks()
        invalid_logger = "not_a_logger"  # Has no debug method

        config, logger = app._get_dependencies(None, invalid_logger)

        # Should reject invalid logger
        assert logger is None

    def test_middleware_manager_with_existing_user_middleware(self) -> None:
        """Test MiddlewareManager when user_middleware already exists."""
        from fastblocks.applications import MiddlewareManager

        manager = MiddlewareManager()
        manager.user_middleware = [MagicMock()]

        # Should not overwrite existing middleware
        manager.add_user_middleware(MagicMock())

        assert len(manager.user_middleware) == 2


@pytest.mark.unit
class TestMiddlewareManagerInfoExtraction:
    """Test MiddlewareManager._extract_middleware_info."""

    def test_extract_info_from_middleware_class(self) -> None:
        """Test extracting info from Middleware class instance."""
        from fastblocks.applications import MiddlewareManager

        manager = MiddlewareManager()

        class TestMiddleware:
            def __init__(self, app, **kwargs):
                self.app = app
                self.kwargs = kwargs

        middleware = Middleware(TestMiddleware, option="value")
        info = manager._extract_middleware_info(middleware)

        assert info["class"] == "TestMiddleware"
        assert info["kwargs"] == {"option": "value"}

    def test_extract_info_from_tuple(self) -> None:
        """Test extracting info from tuple format."""
        from fastblocks.applications import MiddlewareManager

        manager = MiddlewareManager()

        class TestMiddleware:
            pass

        middleware = (TestMiddleware, {"option": "value"})
        info = manager._extract_middleware_info(middleware)

        assert info["class"] == "TestMiddleware"
        assert info["kwargs"] == {"option": "value"}

    def test_extract_info_from_unknown_format(self) -> None:
        """Test extracting info from unknown format."""
        from fastblocks.applications import MiddlewareManager

        manager = MiddlewareManager()

        info = manager._extract_middleware_info("unknown")

        assert "class" in info
        assert info["class"] == "str"


@pytest.mark.unit
class TestMiddlewarePosition:
    """Test MiddlewarePosition enum."""

    def test_middleware_position_values(self) -> None:
        """Test MiddlewarePosition enum values."""
        from fastblocks.applications import MiddlewarePosition

        assert MiddlewarePosition.CSRF.value == 0
        assert MiddlewarePosition.SESSION.value == 1
        assert MiddlewarePosition.HTMX.value == 2
        assert MiddlewarePosition.CURRENT_REQUEST.value == 3
        assert MiddlewarePosition.COMPRESSION.value == 4
        assert MiddlewarePosition.SECURITY_HEADERS.value == 5

    def test_middleware_position_uniqueness(self) -> None:
        """Test that all MiddlewarePosition values are unique."""
        from fastblocks.applications import MiddlewarePosition

        values = [p.value for p in MiddlewarePosition]
        assert len(values) == len(set(values))

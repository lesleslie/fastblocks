"""Comprehensive tests for FastBlocks exceptions."""

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response

from fastblocks.exceptions import (
    ConfigurationError,
    DefaultErrorHandler,
    DependencyError,
    DuplicateCaching,
    ErrorCategory,
    ErrorHandler,
    ErrorHandlerRegistry,
    ErrorContext,
    ErrorSeverity,
    FastBlocksException,
    MissingCaching,
    RequestNotCachable,
    ResponseNotCachable,
    handle_exception,
    register_error_handler,
    safe_depends_get,
)
from fastblocks.htmx import HtmxRequest


class CustomError(FastBlocksException):
    """Custom error for testing."""

    pass


class TestErrorSeverity:
    """Test ErrorSeverity enum."""

    def test_severity_values(self) -> None:
        """Test severity enum values."""
        assert ErrorSeverity.CRITICAL.value == "critical"
        assert ErrorSeverity.ERROR.value == "error"
        assert ErrorSeverity.WARNING.value == "warning"
        assert ErrorSeverity.INFO.value == "info"


class TestErrorCategory:
    """Test ErrorCategory enum."""

    def test_category_values(self) -> None:
        """Test category enum values."""
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.DEPENDENCY.value == "dependency"
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.AUTHORIZATION.value == "authorization"
        assert ErrorCategory.VALIDATION.value == "validation"
        assert ErrorCategory.CACHING.value == "caching"
        assert ErrorCategory.TEMPLATE.value == "template"
        assert ErrorCategory.MIDDLEWARE.value == "middleware"
        assert ErrorCategory.APPLICATION.value == "application"


class TestErrorContext:
    """Test ErrorContext dataclass."""

    def test_error_context_creation(self) -> None:
        """Test creating ErrorContext."""
        context = ErrorContext(
            error_id="test_error",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.WARNING,
            message="Test error message",
        )
        assert context.error_id == "test_error"
        assert context.category == ErrorCategory.VALIDATION
        assert context.severity == ErrorSeverity.WARNING
        assert context.message == "Test error message"
        assert context.details is None
        assert context.request_id is None
        assert context.user_id is None

    def test_error_context_with_details(self) -> None:
        """Test ErrorContext with all fields."""
        details = {"field": "value", "count": 42}
        context = ErrorContext(
            error_id="test_error",
            category=ErrorCategory.APPLICATION,
            severity=ErrorSeverity.ERROR,
            message="Test error",
            details=details,
            request_id="req_123",
            user_id="user_456",
        )
        assert context.details == details
        assert context.request_id == "req_123"
        assert context.user_id == "user_456"


class TestFastBlocksException:
    """Test FastBlocksException base class."""

    def test_basic_exception(self) -> None:
        """Test basic FastBlocksException."""
        exc = FastBlocksException("Test error")
        assert str(exc) == "Test error"
        assert exc.message == "Test error"
        assert exc.category == ErrorCategory.APPLICATION
        assert exc.severity == ErrorSeverity.ERROR
        assert exc.details == {}
        assert exc.status_code is None

    def test_exception_with_category(self) -> None:
        """Test exception with custom category."""
        exc = FastBlocksException(
            "Test error",
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.CRITICAL,
        )
        assert exc.category == ErrorCategory.CONFIGURATION
        assert exc.severity == ErrorSeverity.CRITICAL

    def test_exception_with_details(self) -> None:
        """Test exception with details."""
        details = {"key": "value"}
        exc = FastBlocksException("Test error", details=details)
        assert exc.details == details

    def test_exception_with_status_code(self) -> None:
        """Test exception with status code."""
        exc = FastBlocksException("Test error", status_code=404)
        assert exc.status_code == 404

    def test_to_error_context(self) -> None:
        """Test converting to ErrorContext."""
        exc = FastBlocksException(
            "Test error",
            category=ErrorCategory.CACHING,
            severity=ErrorSeverity.WARNING,
            details={"cache": "miss"},
        )
        context = exc.to_error_context()
        assert context.message == "Test error"
        assert context.category == ErrorCategory.CACHING
        assert context.severity == ErrorSeverity.WARNING
        assert context.details == {"cache": "miss"}

    def test_to_error_context_with_custom_id(self) -> None:
        """Test converting to ErrorContext with custom error_id."""
        exc = FastBlocksException("Test error")
        context = exc.to_error_context(error_id="custom_id")
        assert context.error_id == "custom_id"


class TestConfigurationError:
    """Test ConfigurationError."""

    def test_configuration_error_basic(self) -> None:
        """Test basic ConfigurationError."""
        exc = ConfigurationError("Invalid config")
        assert exc.message == "Invalid config"
        assert exc.category == ErrorCategory.CONFIGURATION
        assert exc.severity == ErrorSeverity.CRITICAL

    def test_configuration_error_with_key(self) -> None:
        """Test ConfigurationError with config key."""
        exc = ConfigurationError("Invalid config", config_key="app.port")
        assert exc.details == {"config_key": "app.port"}


class TestDependencyError:
    """Test DependencyError."""

    def test_dependency_error_basic(self) -> None:
        """Test basic DependencyError."""
        exc = DependencyError("Missing dependency")
        assert exc.message == "Missing dependency"
        assert exc.category == ErrorCategory.DEPENDENCY
        assert exc.severity == ErrorSeverity.ERROR

    def test_dependency_error_with_key(self) -> None:
        """Test DependencyError with dependency key."""
        exc = DependencyError("Missing dependency", dependency_key="cache.backend")
        assert exc.details == {"dependency_key": "cache.backend"}


class TestCachingExceptions:
    """Test caching-related exceptions."""

    def test_starlette_caches_exception(self) -> None:
        """Test StarletteCachesException."""
        from fastblocks.exceptions import StarletteCachesException
        exc = StarletteCachesException("Cache failed")
        assert exc.message == "Cache failed"
        assert exc.category == ErrorCategory.CACHING

    def test_duplicate_caching(self) -> None:
        """Test DuplicateCaching."""
        exc = DuplicateCaching()
        assert "duplicate" in exc.message.lower()

    def test_duplicate_caching_custom_message(self) -> None:
        """Test DuplicateCaching with custom message."""
        exc = DuplicateCaching("Custom duplicate message")
        assert exc.message == "Custom duplicate message"

    def test_missing_caching(self) -> None:
        """Test MissingCaching."""
        exc = MissingCaching()
        assert "not found" in exc.message.lower()

    def test_request_not_cachable(self) -> None:
        """Test RequestNotCachable."""
        mock_request = Mock(spec=Request)
        mock_request.method = "POST"
        mock_request.url.path = "/submit"

        exc = RequestNotCachable(mock_request)
        assert "POST" in exc.message
        assert "/submit" in exc.message
        assert exc.request is mock_request

    def test_response_not_cachable(self) -> None:
        """Test ResponseNotCachable."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 500

        exc = ResponseNotCachable(mock_response)
        assert "500" in exc.message
        assert exc.response is mock_response


class TestErrorHandler:
    """Test ErrorHandler."""

    @pytest.mark.asyncio
    async def test_custom_error_handler(self) -> None:
        """Test custom error handler implementation."""

        class CustomHandler(ErrorHandler):
            async def can_handle(self, exception: Exception, context: ErrorContext) -> bool:
                return isinstance(exception, ValueError)

            async def handle(
                self,
                exception: Exception,
                context: ErrorContext,
                request: Request,
            ) -> Response:
                return PlainTextResponse(f"Handled: {exception}", status_code=400)

        handler = CustomHandler()
        context = ErrorContext(
            error_id="test",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR,
            message="Test",
        )

        # Test can_handle
        assert await handler.can_handle(ValueError("test"), context) is True
        assert await handler.can_handle(RuntimeError("test"), context) is False


class TestErrorHandlerRegistry:
    """Test ErrorHandlerRegistry."""

    @pytest.fixture
    def registry(self) -> ErrorHandlerRegistry:
        """Create a fresh registry for each test."""
        return ErrorHandlerRegistry()

    @pytest.mark.asyncio
    async def test_register_handler(self, registry: ErrorHandlerRegistry) -> None:
        """Test registering a handler."""

        class TestHandler(ErrorHandler):
            async def can_handle(self, exception: Exception, context: ErrorContext) -> bool:
                return True

            async def handle(
                self,
                exception: Exception,
                context: ErrorContext,
                request: Request,
            ) -> Response:
                return PlainTextResponse("Handled")

        handler = TestHandler()
        registry.register(handler, priority=10)
        assert len(registry._handlers) == 1

    @pytest.mark.asyncio
    async def test_handler_priority_sorting(self, registry: ErrorHandlerRegistry) -> None:
        """Test that handlers are sorted by priority."""

        class Handler1(ErrorHandler):
            async def can_handle(self, exception: Exception, context: ErrorContext) -> bool:
                return True

            async def handle(
                self,
                exception: Exception,
                context: ErrorContext,
                request: Request,
            ) -> Response:
                return PlainTextResponse("Handler1")

        class Handler2(ErrorHandler):
            async def can_handle(self, exception: Exception, context: ErrorContext) -> bool:
                return True

            async def handle(
                self,
                exception: Exception,
                context: ErrorContext,
                request: Request,
            ) -> Response:
                return PlainTextResponse("Handler2")

        registry.register(Handler1(), priority=5)
        registry.register(Handler2(), priority=10)

        # Higher priority should be first
        assert registry._handlers[0][0] == 10
        assert registry._handlers[1][0] == 5

    @pytest.mark.asyncio
    async def test_handle_error_with_handler(self, registry: ErrorHandlerRegistry) -> None:
        """Test handling error with registered handler."""

        class TestHandler(ErrorHandler):
            async def can_handle(self, exception: Exception, context: ErrorContext) -> bool:
                return isinstance(exception, ValueError)

            async def handle(
                self,
                exception: Exception,
                context: ErrorContext,
                request: Request,
            ) -> Response:
                return PlainTextResponse("ValueError handled", status_code=400)

        handler = TestHandler()
        registry.register(handler)

        mock_request = Mock(spec=Request)
        context = ErrorContext(
            error_id="test",
            category=ErrorCategory.VALIDATION,
            severity=ErrorSeverity.ERROR,
            message="Test",
        )

        response = await registry.handle_error(ValueError("test"), context, mock_request)
        assert response.status_code == 400
        assert b"ValueError handled" in response.body

    @pytest.mark.asyncio
    async def test_handle_error_fallback(self, registry: ErrorHandlerRegistry) -> None:
        """Test fallback handler."""

        class FallbackHandler(ErrorHandler):
            async def can_handle(self, exception: Exception, context: ErrorContext) -> bool:
                return True

            async def handle(
                self,
                exception: Exception,
                context: ErrorContext,
                request: Request,
            ) -> Response:
                return PlainTextResponse("Fallback", status_code=500)

        fallback = FallbackHandler()
        registry.set_fallback(fallback)

        mock_request = Mock(spec=Request)
        context = ErrorContext(
            error_id="test",
            category=ErrorCategory.APPLICATION,
            severity=ErrorSeverity.ERROR,
            message="Test",
        )

        response = await registry.handle_error(RuntimeError("test"), context, mock_request)
        assert response.status_code == 500
        assert b"Fallback" in response.body

    @pytest.mark.asyncio
    async def test_handle_error_no_fallback(self, registry: ErrorHandlerRegistry) -> None:
        """Test handling error when no handler matches and no fallback."""
        mock_request = Mock(spec=Request)
        context = ErrorContext(
            error_id="test",
            category=ErrorCategory.APPLICATION,
            severity=ErrorSeverity.ERROR,
            message="Test",
        )

        response = await registry.handle_error(RuntimeError("test"), context, mock_request)
        assert response.status_code == 500
        assert b"Internal Server Error" in response.body


class TestDefaultErrorHandler:
    """Test DefaultErrorHandler."""

    @pytest.mark.asyncio
    async def test_can_handle_always_true(self) -> None:
        """Test that DefaultErrorHandler can handle any exception."""
        handler = DefaultErrorHandler()
        context = ErrorContext(
            error_id="test",
            category=ErrorCategory.APPLICATION,
            severity=ErrorSeverity.ERROR,
            message="Test",
        )

        assert await handler.can_handle(ValueError("test"), context) is True
        assert await handler.can_handle(RuntimeError("test"), context) is True

    @pytest.mark.asyncio
    async def test_handle_404_error(self) -> None:
        """Test handling 404 error."""
        handler = DefaultErrorHandler()
        exc = HTTPException(status_code=404, detail="Not found")
        context = ErrorContext(
            error_id="http_404",
            category=ErrorCategory.APPLICATION,
            severity=ErrorSeverity.WARNING,
            message="Not found",
        )

        mock_request = Mock(spec=Request)
        mock_request.scope = {}

        response = await handler.handle(exc, context, mock_request)
        assert response.status_code == 404
        assert b"Content not found" in response.body

    @pytest.mark.asyncio
    async def test_handle_500_error(self) -> None:
        """Test handling 500 error."""
        handler = DefaultErrorHandler()
        exc = HTTPException(status_code=500, detail="Server error")
        context = ErrorContext(
            error_id="http_500",
            category=ErrorCategory.APPLICATION,
            severity=ErrorSeverity.ERROR,
            message="Server error",
        )

        mock_request = Mock(spec=Request)
        mock_request.scope = {}

        response = await handler.handle(exc, context, mock_request)
        assert response.status_code == 500
        assert b"Server error" in response.body

    @pytest.mark.asyncio
    async def test_handle_htmx_request(self) -> None:
        """Test handling HTMX request."""
        handler = DefaultErrorHandler()
        exc = HTTPException(status_code=404, detail="Not found")
        context = ErrorContext(
            error_id="http_404",
            category=ErrorCategory.APPLICATION,
            severity=ErrorSeverity.WARNING,
            message="Not found",
        )

        mock_request = Mock(spec=Request)
        mock_request.scope = {"htmx": Mock()}

        response = await handler.handle(exc, context, mock_request)
        # HTMX requests should return plain text
        assert isinstance(response, PlainTextResponse)


class TestSafeDependsGet:
    """Test safe_depends_get function."""

    @pytest.mark.asyncio
    async def test_cache_miss_success(self) -> None:
        """Test successful resolution on cache miss."""
        cache: dict = {}

        # Mock the resolver
        from unittest.mock import patch

        with patch("fastblocks.exceptions.depends.resolve", return_value="resolved_value"):
            result = await safe_depends_get("test_key", cache)
            assert result == "resolved_value"
            assert cache["test_key"] == "resolved_value"

    @pytest.mark.asyncio
    async def test_cache_hit(self) -> None:
        """Test cache hit returns cached value."""
        cache = {"test_key": "cached_value"}
        result = await safe_depends_get("test_key", cache)
        assert result == "cached_value"

    @pytest.mark.asyncio
    async def test_resolution_error_returns_default(self) -> None:
        """Test that resolution errors return default."""
        cache: dict = {}

        from unittest.mock import patch

        with patch("fastblocks.exceptions.depends.resolve", side_effect=Exception("Resolve failed")):
            result = await safe_depends_get("test_key", cache, default="default_value")
            assert result == "default_value"

    @pytest.mark.asyncio
    async def test_resolution_error_no_default(self) -> None:
        """Test resolution error without default returns None."""
        cache: dict = {}

        from unittest.mock import patch

        with patch("fastblocks.exceptions.depends.resolve", side_effect=Exception("Resolve failed")):
            result = await safe_depends_get("test_key", cache)
            assert result is None


class TestHandleException:
    """Test handle_exception function."""

    @pytest.mark.asyncio
    async def test_handle_http_exception(self) -> None:
        """Test handling HTTPException."""
        exc = HTTPException(status_code=404, detail="Not found")

        mock_request = Mock(spec=HtmxRequest)
        mock_request.scope = {}
        mock_request.receive = Mock()

        response = await handle_exception(mock_request, exc)
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_handle_exception_with_url(self) -> None:
        """Test handling exception with request URL."""
        exc = HTTPException(status_code=500, detail="Error")

        mock_request = Mock(spec=HtmxRequest)
        mock_request.scope = {}
        mock_request.receive = Mock()
        mock_url = Mock()
        mock_url.path = "/test/path"
        mock_request.url = mock_url

        response = await handle_exception(mock_request, exc)
        assert response.status_code == 500

    @pytest.mark.asyncio
    async def test_handle_exception_custom_status(self) -> None:
        """Test handling exception with custom status code."""
        exc = HTTPException(status_code=418, detail="I'm a teapot")

        mock_request = Mock(spec=HtmxRequest)
        mock_request.scope = {}
        mock_request.receive = Mock()

        response = await handle_exception(mock_request, exc)
        assert response.status_code == 418


class TestRegisterErrorHandler:
    """Test register_error_handler function."""

    def test_register_handler(self) -> None:
        """Test registering a handler globally."""

        class TestHandler(ErrorHandler):
            async def can_handle(self, exception: Exception, context: ErrorContext) -> bool:
                return False

            async def handle(
                self,
                exception: Exception,
                context: ErrorContext,
                request: Request,
            ) -> Response:
                return PlainTextResponse("Test")

        handler = TestHandler()
        # Should not raise
        register_error_handler(handler, priority=5)

    def test_register_with_default_priority(self) -> None:
        """Test registering handler with default priority."""

        class TestHandler(ErrorHandler):
            async def can_handle(self, exception: Exception, context: ErrorContext) -> bool:
                return False

            async def handle(
                self,
                exception: Exception,
                context: ErrorContext,
                request: Request,
            ) -> Response:
                return PlainTextResponse("Test")

        handler = TestHandler()
        # Should not raise
        register_error_handler(handler)

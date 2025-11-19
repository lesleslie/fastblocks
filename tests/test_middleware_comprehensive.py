"""Tests for the FastBlocks middleware module."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from starlette.types import Message, Receive, Scope, Send
from fastblocks.middleware import (
    CacheControlMiddleware,
    CurrentRequestMiddleware,
    MiddlewarePosition,
    MiddlewareStackManager,
    MiddlewareUtils,
    SecureHeadersMiddleware,
    get_middleware_positions,
    secure_headers,
)


@pytest.mark.unit
class TestMiddlewarePosition:
    """Test MiddlewarePosition enum."""

    def test_middleware_position_values(self) -> None:
        """Test MiddlewarePosition enum values."""
        assert MiddlewarePosition.CSRF == 0
        assert MiddlewarePosition.SESSION == 1
        assert MiddlewarePosition.HTMX == 2
        assert MiddlewarePosition.CURRENT_REQUEST == 3
        assert MiddlewarePosition.COMPRESSION == 4
        assert MiddlewarePosition.SECURITY_HEADERS == 5


@pytest.mark.unit
class TestMiddlewareUtils:
    """Test MiddlewareUtils class."""

    def test_get_request(self) -> None:
        """Test get_request method."""
        # Test when no request is set
        assert MiddlewareUtils.get_request() is None

        # Test when request is set
        mock_scope = {"type": "http"}
        MiddlewareUtils.set_request(mock_scope)
        assert MiddlewareUtils.get_request() == mock_scope

        # Reset
        MiddlewareUtils.set_request(None)

    def test_secure_headers(self) -> None:
        """Test secure_headers object."""
        assert secure_headers is not None


@pytest.mark.unit
class TestCurrentRequestMiddleware:
    """Test CurrentRequestMiddleware class."""

    @pytest.mark.asyncio
    async def test_current_request_middleware_http(self) -> None:
        """Test CurrentRequestMiddleware with HTTP request."""
        app = AsyncMock()
        middleware = CurrentRequestMiddleware(app)

        scope: Scope = {"type": "http"}
        receive: Receive = AsyncMock()
        send: Send = AsyncMock()

        await middleware(scope, receive, send)

        # Verify app was called
        app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_current_request_middleware_websocket(self) -> None:
        """Test CurrentRequestMiddleware with WebSocket request."""
        app = AsyncMock()
        middleware = CurrentRequestMiddleware(app)

        scope: Scope = {"type": "websocket"}
        receive: Receive = AsyncMock()
        send: Send = AsyncMock()

        await middleware(scope, receive, send)

        # Verify app was called
        app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_current_request_middleware_lifespan(self) -> None:
        """Test CurrentRequestMiddleware with lifespan request."""
        app = AsyncMock()
        middleware = CurrentRequestMiddleware(app)

        scope: Scope = {"type": "lifespan"}
        receive: Receive = AsyncMock()
        send: Send = AsyncMock()

        await middleware(scope, receive, send)

        # Verify app was called
        app.assert_called_once_with(scope, receive, send)


@pytest.mark.unit
class TestSecureHeadersMiddleware:
    """Test SecureHeadersMiddleware class."""

    @pytest.mark.asyncio
    async def test_secure_headers_middleware_http(self) -> None:
        """Test SecureHeadersMiddleware with HTTP request."""
        app = AsyncMock()
        middleware = SecureHeadersMiddleware(app)

        # Mock the secure headers
        with patch("fastblocks.middleware.secure_headers") as mock_secure_headers:
            mock_secure_headers.headers = {"X-Content-Type-Options": "nosniff"}

            scope: Scope = {"type": "http"}
            receive: Receive = AsyncMock()

            # Create a mock send function
            async def mock_send(message: Message) -> None:
                if message["type"] == "http.response.start":
                    # Verify headers are added
                    headers = list(message.get("headers", []))
                    # We expect the secure header to be added
                    assert any(
                        b"x-content-type-options" in header for header, _ in headers
                    )

            await middleware(scope, receive, mock_send)

            # Verify app was called
            app.assert_called_once()

    @pytest.mark.asyncio
    async def test_secure_headers_middleware_non_http(self) -> None:
        """Test SecureHeadersMiddleware with non-HTTP request."""
        app = AsyncMock()
        middleware = SecureHeadersMiddleware(app)

        scope: Scope = {"type": "websocket"}
        receive: Receive = AsyncMock()
        send: Send = AsyncMock()

        await middleware(scope, receive, send)

        # Verify app was called directly
        app.assert_called_once_with(scope, receive, send)


@pytest.mark.unit
class TestCacheControlMiddleware:
    """Test CacheControlMiddleware class."""

    def test_cache_control_middleware_init(self) -> None:
        """Test CacheControlMiddleware initialization."""
        app = Mock()
        middleware = CacheControlMiddleware(
            app, max_age=3600, public=True, no_cache=True
        )

        assert middleware.app == app
        assert middleware.max_age == 3600
        assert middleware.public is True
        assert middleware.no_cache is True

    @pytest.mark.asyncio
    async def test_cache_control_middleware_http(self) -> None:
        """Test CacheControlMiddleware with HTTP request."""
        app = AsyncMock()
        middleware = CacheControlMiddleware(app, max_age=3600, public=True)

        scope: Scope = {"type": "http"}
        receive: Receive = AsyncMock()
        send: Send = AsyncMock()

        await middleware(scope, receive, send)

        # Verify app was called
        app.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_control_middleware_non_http(self) -> None:
        """Test CacheControlMiddleware with non-HTTP request."""
        app = AsyncMock()
        middleware = CacheControlMiddleware(app, max_age=3600, public=True)

        scope: Scope = {"type": "websocket"}
        receive: Receive = AsyncMock()
        send: Send = AsyncMock()

        await middleware(scope, receive, send)

        # Verify app was called directly
        app.assert_called_once_with(scope, receive, send)


@pytest.mark.unit
class TestCacheControlResponder:
    """Test CacheControlResponder class."""

    def test_kvformat(self) -> None:
        """Test kvformat method."""
        # We can't directly test this since CacheControlResponder is from caching module
        # but we can test that the middleware uses it correctly
        pass


@pytest.mark.unit
class TestMiddlewareStackManager:
    """Test MiddlewareStackManager class."""

    def test_get_middleware_positions(self) -> None:
        """Test get_middleware_positions function."""
        positions = get_middleware_positions()
        assert isinstance(positions, dict)
        assert "CSRF" in positions
        assert "SESSION" in positions
        assert "HTMX" in positions
        assert "CURRENT_REQUEST" in positions
        assert "COMPRESSION" in positions
        assert "SECURITY_HEADERS" in positions

    def test_middleware_stack_manager_init(self) -> None:
        """Test MiddlewareStackManager initialization."""
        manager = MiddlewareStackManager()
        assert manager._initialized is False

    def test_middleware_stack_manager_build_stack(self) -> None:
        """Test MiddlewareStackManager build_stack method."""
        manager = MiddlewareStackManager()
        stack = manager.build_stack()
        assert isinstance(stack, list)

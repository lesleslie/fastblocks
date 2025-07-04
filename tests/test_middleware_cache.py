"""Tests for the CacheMiddleware."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from starlette.types import Scope
from fastblocks.exceptions import DuplicateCaching, MissingCaching
from fastblocks.middleware import (
    CacheMiddleware,
    _BaseCacheMiddlewareHelper,
)


@pytest.mark.asyncio
async def test_cache_middleware_initialization() -> None:
    """Test CacheMiddleware initialization with default parameters."""
    # Create mock app
    mock_app = MagicMock()
    mock_app.middleware = []

    # Create the middleware (cache will be None initially)
    middleware = CacheMiddleware(mock_app)

    # Verify the app was set correctly
    assert middleware.app is mock_app
    # Cache should be None initially (lazy initialization)
    assert middleware.cache is None

    # Verify that rules were set to the default
    assert len(middleware.rules) == 1

    # Verify that the middleware was not added to the app's middleware list
    # (this is handled by the application, not the middleware itself)
    assert mock_app.middleware == []


@pytest.mark.asyncio
async def test_cache_middleware_initialization_with_custom_parameters() -> None:
    """Test CacheMiddleware initialization with custom parameters."""
    # Create mock app
    mock_app = MagicMock()
    mock_app.middleware = []

    # Mock the cache and rules
    mock_cache = MagicMock()
    mock_rules = [MagicMock(), MagicMock()]

    # Create the middleware with custom parameters
    middleware = CacheMiddleware(mock_app, cache=mock_cache, rules=mock_rules)

    # Verify the app, cache, and rules were set correctly
    assert middleware.app is mock_app
    assert middleware.cache is mock_cache
    assert middleware.rules is mock_rules


@pytest.mark.asyncio
async def test_cache_middleware_duplicate_detection() -> None:
    """Test that CacheMiddleware detects duplicate instances."""
    # Create mock app with an existing CacheMiddleware
    mock_app = MagicMock()
    existing_middleware = MagicMock(spec=CacheMiddleware)
    mock_app.middleware = [existing_middleware]

    # Mock the cache
    mock_cache = MagicMock()

    # Create the middleware with a mocked cache using the new dependency system
    with patch("fastblocks.exceptions.safe_depends_get", return_value=mock_cache):
        # Attempting to create another CacheMiddleware should raise DuplicateCaching
        with pytest.raises(DuplicateCaching):
            CacheMiddleware(mock_app)


@pytest.mark.asyncio
async def test_cache_middleware_non_http_request() -> None:
    """Test CacheMiddleware with a non-HTTP request."""
    # Create mock app, receive, and send functions
    mock_app = AsyncMock()
    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock WebSocket scope
    mock_scope: Scope = {"type": "websocket", "path": "/ws"}

    # Mock the cache
    mock_cache = MagicMock()

    # Create the middleware with a mocked cache using the new dependency system
    with patch("fastblocks.exceptions.safe_depends_get", return_value=mock_cache):
        middleware = CacheMiddleware(mock_app)

        # Call the middleware
        await middleware(mock_scope, mock_receive, mock_send)

        # Verify the app was called with the original arguments
        mock_app.assert_called_once_with(mock_scope, mock_receive, mock_send)


@pytest.mark.asyncio
async def test_cache_middleware_http_request() -> None:
    """Test CacheMiddleware with an HTTP request."""
    # Create mock app, receive, and send functions
    mock_app = AsyncMock()
    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock HTTP scope with required fields
    mock_scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [],
        "query_string": b"",
        "scheme": "http",
        "server": ("localhost", 8000),
    }

    # Mock the cache with async methods
    mock_cache = AsyncMock()
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()
    mock_cache.delete = AsyncMock()

    # Create logger mock using the MockLogger from conftest
    from acb.logger import Logger

    Logger()

    # Create the middleware with mocked dependencies using the new dependency system
    with patch("fastblocks.exceptions.safe_depends_get", return_value=mock_cache):
        with patch(
            "fastblocks.caching.get_from_cache", return_value=None
        ) as mock_get_cache:
            middleware = CacheMiddleware(mock_app)

            # Call the middleware
            await middleware(mock_scope, mock_receive, mock_send)

            # Verify that the scope was updated with the middleware instance
            assert mock_scope["__starlette_caches__"] is middleware

            # Verify that get_from_cache was called during the process
            mock_get_cache.assert_called_once()


@pytest.mark.asyncio
async def test_cache_middleware_duplicate_in_scope() -> None:
    """Test CacheMiddleware when another instance is already in the scope."""
    # Create mock app, receive, and send functions
    mock_app = AsyncMock()
    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock HTTP scope with an existing CacheMiddleware
    mock_scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "__starlette_caches__": MagicMock(),
    }

    # Mock the cache
    mock_cache = MagicMock()

    # Create the middleware with a mocked cache using the new dependency system
    with patch("fastblocks.exceptions.safe_depends_get", return_value=mock_cache):
        middleware = CacheMiddleware(mock_app)

        # Call the middleware and expect a DuplicateCaching exception
        with pytest.raises(DuplicateCaching):
            await middleware(mock_scope, mock_receive, mock_send)


@pytest.mark.asyncio
async def test_base_cache_middleware_helper_initialization() -> None:
    """Test _BaseCacheMiddlewareHelper initialization."""
    # Create a mock request with a CacheMiddleware in the scope
    mock_middleware = MagicMock(spec=CacheMiddleware)
    mock_scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "__starlette_caches__": mock_middleware,
    }
    mock_request = MagicMock()
    mock_request.scope = mock_scope

    # Create the helper
    helper = _BaseCacheMiddlewareHelper(mock_request)

    # Verify that the request and middleware were set correctly
    assert helper.request is mock_request
    assert helper.middleware is mock_middleware


@pytest.mark.asyncio
async def test_base_cache_middleware_helper_missing_middleware() -> None:
    """Test _BaseCacheMiddlewareHelper when no middleware is in the scope."""
    # Create a mock request without a CacheMiddleware in the scope
    mock_scope: Scope = {"type": "http", "method": "GET", "path": "/"}
    mock_request = MagicMock()
    mock_request.scope = mock_scope

    # Creating the helper should raise MissingCaching
    with pytest.raises(MissingCaching):
        _BaseCacheMiddlewareHelper(mock_request)


@pytest.mark.asyncio
async def test_base_cache_middleware_helper_wrong_type() -> None:
    """Test _BaseCacheMiddlewareHelper when the scope contains the wrong type."""
    # Create a mock request with something other than a CacheMiddleware in the scope
    mock_scope: Scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "__starlette_caches__": "not a middleware",
    }
    mock_request = MagicMock()
    mock_request.scope = mock_scope

    # Creating the helper should raise MissingCaching
    with pytest.raises(MissingCaching):
        _BaseCacheMiddlewareHelper(mock_request)

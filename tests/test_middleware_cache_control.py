"""Tests for the CacheControlMiddleware."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from typing import TYPE_CHECKING

from fastblocks.middleware import CacheControlMiddleware

if TYPE_CHECKING:
    from starlette.types import Scope


@pytest.mark.asyncio
async def test_cache_control_middleware_initialization() -> None:
    """Test CacheControlMiddleware initialization with default parameters."""
    # Create mock app
    mock_app = MagicMock()

    # Create the middleware
    middleware = CacheControlMiddleware(mock_app)

    # Verify the app was set correctly
    assert middleware.app is mock_app

    # Verify that the default values were set correctly
    assert middleware.max_age is None
    assert middleware.s_maxage is None
    assert not middleware.no_cache
    assert not middleware.no_store
    assert not middleware.no_transform
    assert not middleware.must_revalidate
    assert not middleware.proxy_revalidate
    assert not middleware.must_understand
    assert not middleware.private
    assert not middleware.public
    assert not middleware.immutable
    assert middleware.stale_while_revalidate is None
    assert middleware.stale_if_error is None


@pytest.mark.asyncio
async def test_cache_control_middleware_initialization_with_custom_parameters() -> None:
    """Test CacheControlMiddleware initialization with custom parameters."""
    # Create mock app
    mock_app = MagicMock()

    # Create the middleware with custom parameters
    middleware = CacheControlMiddleware(
        mock_app,
        max_age=300,
        public=True,
        must_revalidate=True,
    )

    # Verify the app was set correctly
    assert middleware.app is mock_app

    # Verify that the custom values were set correctly
    assert middleware.max_age == 300
    assert middleware.public
    assert middleware.must_revalidate

    # Verify that the other values are still at their defaults
    assert middleware.s_maxage is None
    assert not middleware.no_cache
    assert not middleware.no_store
    assert not middleware.no_transform
    assert not middleware.proxy_revalidate
    assert not middleware.must_understand
    assert not middleware.private
    assert not middleware.immutable
    assert middleware.stale_while_revalidate is None
    assert middleware.stale_if_error is None


@pytest.mark.asyncio
async def test_cache_control_middleware_non_http_request() -> None:
    """Test CacheControlMiddleware with a non-HTTP request."""
    # Create mock app, receive, and send functions
    mock_app = AsyncMock()
    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock WebSocket scope
    mock_scope: Scope = {"type": "websocket", "path": "/ws"}

    # Create the middleware
    middleware = CacheControlMiddleware(mock_app)

    # Call the middleware
    await middleware(mock_scope, mock_receive, mock_send)

    # Verify the app was called with the original arguments
    mock_app.assert_called_once_with(mock_scope, mock_receive, mock_send)


@pytest.mark.asyncio
async def test_cache_control_middleware_process_response() -> None:
    """Test CacheControlMiddleware.process_response method."""
    # Create mock app
    mock_app = MagicMock()

    # Create a mock response with headers
    mock_response = MagicMock()
    mock_response.headers = {}

    # Create the middleware with various cache control directives
    middleware = CacheControlMiddleware(
        mock_app,
        max_age=300,
        public=True,
        must_revalidate=True,
        no_cache=True,
        no_store=True,
    )

    # Call process_response
    middleware.process_response(mock_response)

    # Verify that the Cache-Control header was set correctly
    assert "Cache-Control" in mock_response.headers

    # The header should contain all the directives
    cache_control = mock_response.headers["Cache-Control"]
    assert "public" in cache_control
    assert "max-age=300" in cache_control
    assert "must-revalidate" in cache_control
    assert "no-cache" in cache_control
    assert "no-store" in cache_control


@pytest.mark.asyncio
async def test_cache_control_middleware_process_response_private() -> None:
    """Test CacheControlMiddleware.process_response method with private directive."""
    # Create mock app
    mock_app = MagicMock()

    # Create a mock response with headers
    mock_response = MagicMock()
    mock_response.headers = {}

    # Create the middleware with private directive
    middleware = CacheControlMiddleware(
        mock_app,
        max_age=300,
        private=True,
        must_revalidate=True,
    )

    # Call process_response
    middleware.process_response(mock_response)

    # Verify that the Cache-Control header was set correctly
    assert "Cache-Control" in mock_response.headers

    # The header should contain the private directive
    cache_control = mock_response.headers["Cache-Control"]
    assert "private" in cache_control
    assert "public" not in cache_control
    assert "max-age=300" in cache_control
    assert "must-revalidate" in cache_control

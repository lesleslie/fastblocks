"""Tests for the CurrentRequestMiddleware."""

from unittest.mock import AsyncMock

import pytest
from starlette.types import Receive, Scope, Send
from fastblocks.middleware import CurrentRequestMiddleware, get_request


@pytest.mark.asyncio
async def test_current_request_middleware_http_request() -> None:
    """Test CurrentRequestMiddleware with an HTTP request."""
    # Create mock app, receive, and send functions
    mock_app = AsyncMock()
    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock HTTP scope
    mock_scope: Scope = {"type": "http", "method": "GET", "path": "/"}

    # Create the middleware
    middleware = CurrentRequestMiddleware(mock_app)

    # Call the middleware
    await middleware(mock_scope, mock_receive, mock_send)

    # Verify the app was called with the correct arguments
    mock_app.assert_called_once_with(mock_scope, mock_receive, mock_send)


@pytest.mark.asyncio
async def test_current_request_middleware_websocket_request() -> None:
    """Test CurrentRequestMiddleware with a WebSocket request."""
    # Create mock app, receive, and send functions
    mock_app = AsyncMock()
    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock WebSocket scope
    mock_scope: Scope = {"type": "websocket", "path": "/ws"}

    # Create the middleware
    middleware = CurrentRequestMiddleware(mock_app)

    # Call the middleware
    await middleware(mock_scope, mock_receive, mock_send)

    # Verify the app was called with the correct arguments
    mock_app.assert_called_once_with(mock_scope, mock_receive, mock_send)


@pytest.mark.asyncio
async def test_current_request_middleware_lifespan_request() -> None:
    """Test CurrentRequestMiddleware with a lifespan request."""
    # Create mock app, receive, and send functions
    mock_app = AsyncMock()
    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock lifespan scope
    mock_scope: Scope = {"type": "lifespan"}

    # Create the middleware
    middleware = CurrentRequestMiddleware(mock_app)

    # Call the middleware
    await middleware(mock_scope, mock_receive, mock_send)

    # Verify the app was called with the correct arguments
    mock_app.assert_called_once_with(mock_scope, mock_receive, mock_send)


@pytest.mark.asyncio
async def test_get_request_function() -> None:
    """Test the get_request function."""
    # Create mock app, receive, and send functions
    mock_app = AsyncMock()
    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock HTTP scope
    mock_scope: Scope = {"type": "http", "method": "GET", "path": "/"}

    # Create the middleware
    middleware = CurrentRequestMiddleware(mock_app)

    # Before middleware call, get_request should return None
    assert get_request() is None

    # Call the middleware
    await middleware(mock_scope, mock_receive, mock_send)

    # After middleware call, get_request should still return None
    # because the context var is reset after the middleware call
    assert get_request() is None


@pytest.mark.asyncio
async def test_current_request_middleware_context_var() -> None:
    """Test that the context var is properly set and reset."""

    # Create a mock app that checks the context var
    async def mock_app(scope: Scope, receive: Receive, send: Send) -> None:
        # Inside the app, the context var should be set to the scope
        assert get_request() is scope

    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock HTTP scope
    mock_scope: Scope = {"type": "http", "method": "GET", "path": "/"}

    # Create the middleware
    middleware = CurrentRequestMiddleware(mock_app)

    # Before middleware call, get_request should return None
    assert get_request() is None

    # Call the middleware
    await middleware(mock_scope, mock_receive, mock_send)

    # After middleware call, get_request should return None again
    assert get_request() is None

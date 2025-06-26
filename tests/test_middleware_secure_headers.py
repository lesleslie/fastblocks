"""Tests for the SecureHeadersMiddleware."""

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from starlette.types import Scope
from fastblocks.middleware import SecureHeadersMiddleware


@pytest.mark.asyncio
async def test_secure_headers_middleware_http_request() -> None:
    """Test SecureHeadersMiddleware with an HTTP request."""
    # Create mock app, receive, and send functions
    mock_app = AsyncMock()
    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock HTTP scope
    mock_scope: Scope = {"type": "http", "method": "GET", "path": "/"}

    # Create the middleware
    middleware = SecureHeadersMiddleware(mock_app)

    # Mock the logger
    MagicMock()

    # Mock secure_headers
    mock_secure_headers = {
        "X-Frame-Options": "DENY",
        "X-XSS-Protection": "1; mode=block",
    }

    with patch("fastblocks.middleware.secure_headers") as mock_secure:
        mock_secure.headers = mock_secure_headers

        # Call the middleware
        await middleware(mock_scope, mock_receive, mock_send)

        # Verify the app was called with the correct scope and receive
        mock_app.assert_called_once()
        assert mock_app.call_args[0][0] == mock_scope
        assert mock_app.call_args[0][1] == mock_receive

        # The send function should be wrapped, so it won't be the original mock_send
        assert mock_app.call_args[0][2] != mock_send


@pytest.mark.asyncio
async def test_secure_headers_middleware_non_http_request() -> None:
    """Test SecureHeadersMiddleware with a non-HTTP request."""
    # Create mock app, receive, and send functions
    mock_app = AsyncMock()
    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock WebSocket scope
    mock_scope: Scope = {"type": "websocket", "path": "/ws"}

    # Create the middleware
    middleware = SecureHeadersMiddleware(mock_app)

    # Mock the logger
    MagicMock()

    # Call the middleware
    await middleware(mock_scope, mock_receive, mock_send)

    # Verify the app was called with the original arguments
    mock_app.assert_called_once_with(mock_scope, mock_receive, mock_send)

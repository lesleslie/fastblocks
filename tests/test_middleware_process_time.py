"""Tests for the ProcessTimeHeaderMiddleware."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.types import Receive, Scope, Send
from fastblocks.middleware import ProcessTimeHeaderMiddleware


@pytest.mark.asyncio
async def test_process_time_middleware_normal_request() -> None:
    """Test ProcessTimeHeaderMiddleware with a normal request."""
    # Create mock app, receive, and send functions
    mock_app = AsyncMock()
    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock HTTP scope
    mock_scope: Scope = {"type": "http", "method": "GET", "path": "/"}

    # Mock the logger
    mock_logger = MagicMock()

    # Create the middleware with a mocked logger using the new dependency system
    with patch(
        "fastblocks.middleware.get_acb_modules_for_middleware"
    ) as mock_get_modules:
        # Mock the return value for _get_acb_modules() call in ProcessTimeHeaderMiddleware
        # _get_acb_modules returns (get_adapter, Config, depends, Logger)
        mock_depends = type(
            "MockDepends",
            (),
            {"get": lambda self, x: mock_logger if x == "logger" else None},
        )()
        mock_get_modules.return_value = (None, None, mock_depends, None)
        middleware = ProcessTimeHeaderMiddleware(mock_app)

        # Call the middleware
        await middleware(mock_scope, mock_receive, mock_send)

        # Verify the app was called with the correct arguments
        mock_app.assert_called_once_with(mock_scope, mock_receive, mock_send)

        # Verify that the logger.debug was called with a message containing "Request processed in"
        assert mock_logger.debug.call_count == 1
        debug_message = mock_logger.debug.call_args[0][0]
        assert "Request processed in" in debug_message


@pytest.mark.asyncio
async def test_process_time_middleware_exception() -> None:
    """Test ProcessTimeHeaderMiddleware when the app raises an exception."""
    # Create mock receive and send functions
    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock app that raises an exception
    mock_app = AsyncMock(side_effect=ValueError("Test exception"))

    # Create a mock HTTP scope
    mock_scope: Scope = {"type": "http", "method": "GET", "path": "/"}

    # Mock the logger
    mock_logger = MagicMock()

    # Create the middleware with a mocked logger using the new dependency system
    with patch(
        "fastblocks.middleware.get_acb_modules_for_middleware"
    ) as mock_get_modules:
        # Mock the return value for _get_acb_modules() call in ProcessTimeHeaderMiddleware
        # _get_acb_modules returns (get_adapter, Config, depends, Logger)
        mock_depends = type(
            "MockDepends",
            (),
            {"get": lambda self, x: mock_logger if x == "logger" else None},
        )()
        mock_get_modules.return_value = (None, None, mock_depends, None)
        middleware = ProcessTimeHeaderMiddleware(mock_app)

        # Call the middleware and expect an exception
        with pytest.raises(ValueError, match="Test exception"):
            await middleware(mock_scope, mock_receive, mock_send)

        # Verify the app was called with the correct arguments
        mock_app.assert_called_once_with(mock_scope, mock_receive, mock_send)

        # Verify that logger.exception was called with the exception
        mock_logger.exception.assert_called_once()

        # Verify that logger.debug was still called (in the finally block)
        assert mock_logger.debug.call_count == 1
        debug_message = mock_logger.debug.call_args[0][0]
        assert "Request processed in" in debug_message


@pytest.mark.asyncio
async def test_process_time_middleware_performance() -> None:
    """Test that ProcessTimeHeaderMiddleware correctly measures processing time."""

    # Create mock app, receive, and send functions
    async def mock_app(scope: Scope, receive: Receive, send: Send) -> None:
        # Simulate some processing time
        await asyncio.sleep(0.01)

    mock_receive = AsyncMock()
    mock_send = AsyncMock()

    # Create a mock HTTP scope
    mock_scope: Scope = {"type": "http", "method": "GET", "path": "/"}

    # Mock the logger
    mock_logger = MagicMock()

    # Create the middleware with a mocked logger using the new dependency system
    with patch(
        "fastblocks.middleware.get_acb_modules_for_middleware"
    ) as mock_get_modules:
        # Mock the return value for _get_acb_modules() call in ProcessTimeHeaderMiddleware
        # _get_acb_modules returns (get_adapter, Config, depends, Logger)
        mock_depends = type(
            "MockDepends",
            (),
            {"get": lambda self, x: mock_logger if x == "logger" else None},
        )()
        mock_get_modules.return_value = (None, None, mock_depends, None)
        middleware = ProcessTimeHeaderMiddleware(mock_app)

        # Call the middleware
        await middleware(mock_scope, mock_receive, mock_send)

        # Verify that logger.debug was called with a message containing a positive time
        assert mock_logger.debug.call_count == 1
        debug_message = mock_logger.debug.call_args[0][0]

        # Extract the time value from the debug message
        import re

        time_match = re.search(r"Request processed in ([\d.]+) s", debug_message)
        assert time_match is not None

        process_time = float(time_match.group(1))

        # The process time should be positive and at least 0.01 seconds
        assert process_time > 0
        assert process_time >= 0.01

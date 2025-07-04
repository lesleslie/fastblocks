"""Tests for the FastBlocks exceptions."""

import sys
import typing as t
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from starlette.exceptions import HTTPException
from starlette.responses import PlainTextResponse
from fastblocks.exceptions import (
    DuplicateCaching,
    MissingCaching,
    RequestNotCachable,
    ResponseNotCachable,
    StarletteCachesException,
    handle_exception,
)


@pytest.fixture
def mock_templates() -> MagicMock:
    """Create a mock templates object."""
    mock_templates = MagicMock()
    mock_templates.app.render_template = AsyncMock()
    return mock_templates


@pytest.fixture
def mock_depends(mock_templates: MagicMock) -> t.Generator[MagicMock]:
    """Create a mock depends object for the new dependency system."""
    # Create mock depends object
    mock_depends_obj = MagicMock()
    mock_depends_obj.get = MagicMock(return_value=mock_templates)

    # Patch the new safe_depends_get function
    with patch("fastblocks.exceptions.safe_depends_get", return_value=mock_templates):
        yield mock_depends_obj


@pytest.mark.asyncio
async def test_handle_exception_htmx_request(mock_depends: MagicMock) -> None:
    """Test handle_exception with an HTMX request."""
    # Create a mock HTMX request
    mock_request = MagicMock()
    mock_request.scope = {"htmx": True}

    # Create a mock HTTPException
    mock_exception = HTTPException(status_code=404)

    # Call handle_exception
    response = await handle_exception(mock_request, mock_exception)

    # Verify the response
    assert isinstance(response, PlainTextResponse)
    assert response.status_code == 404
    assert response.body == b"Content not found"


@pytest.mark.asyncio
async def test_handle_exception_server_error(mock_depends: MagicMock) -> None:
    """Test handle_exception with a 500 error."""
    # Create a mock HTMX request
    mock_request = MagicMock()
    mock_request.scope = {"htmx": True}

    # Create a mock HTTPException with status_code 500
    mock_exception = HTTPException(status_code=500)

    # Call handle_exception
    response = await handle_exception(mock_request, mock_exception)

    # Verify the response
    assert isinstance(response, PlainTextResponse)
    assert response.status_code == 500
    assert response.body == b"Server error"


@pytest.mark.asyncio
async def test_handle_exception_default_status_code(mock_depends: MagicMock) -> None:
    """Test handle_exception with an exception that has no status_code."""
    # Create a mock HTMX request
    mock_request = MagicMock()
    mock_request.scope = {"htmx": True}

    # Create a mock HTTPException with status_code 500
    mock_exception = HTTPException(status_code=500)

    # Call handle_exception
    response = await handle_exception(mock_request, mock_exception)

    # Verify the response
    assert isinstance(response, PlainTextResponse)
    assert response.status_code == 500
    assert response.body == b"Server error"


def test_starlette_caches_exception() -> None:
    """Test StarletteCachesException."""
    # Create an instance of the exception
    exception = StarletteCachesException("Test message")

    # Verify it's an Exception
    assert isinstance(exception, Exception)
    assert str(exception) == "Test message"


def test_duplicate_caching_exception_message() -> None:
    """Test DuplicateCaching exception."""
    message = "Test exception message"
    exception = DuplicateCaching(message)
    assert str(exception) == message
    assert isinstance(exception, StarletteCachesException)


def test_missing_caching() -> None:
    """Test MissingCaching exception."""
    # Create an instance of the exception
    exception = MissingCaching("Test message")

    # Verify it's a StarletteCachesException
    assert isinstance(exception, StarletteCachesException)
    assert str(exception) == "Test message"


def test_request_not_cachable_exception() -> None:
    """Test RequestNotCachable exception."""
    request = Mock()
    exception = RequestNotCachable(request)
    assert exception.request == request
    assert isinstance(exception, StarletteCachesException)


def test_response_not_cachable_exception() -> None:
    """Test ResponseNotCachable exception."""
    response = Mock()
    exception = ResponseNotCachable(response)
    assert exception.response == response
    assert isinstance(exception, StarletteCachesException)

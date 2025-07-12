"""Tests for the jinja2 template rendering functionality."""
# pyright: reportAttributeAccessIssue=false, reportUnusedImport=false, reportMissingParameterType=false, reportUnknownParameterType=false

import sys
import typing as t
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent.parent))

# Mock AsyncJinja2Templates before importing
import types

# Set up the mock modules
sys.modules["starlette_async_jinja"] = types.ModuleType("starlette_async_jinja")
# MockAsyncJinja2Templates will be defined below

# Mock AsyncRedisBytecodeCache
sys.modules["jinja2_async_environment"] = types.ModuleType("jinja2_async_environment")
sys.modules["jinja2_async_environment"].bccache = types.ModuleType(
    "jinja2_async_environment.bccache",
)
sys.modules["jinja2_async_environment"].bccache.AsyncRedisBytecodeCache = MagicMock
sys.modules["jinja2_async_environment"].loaders = types.ModuleType(
    "jinja2_async_environment.loaders",
)
sys.modules["jinja2_async_environment"].loaders.AsyncBaseLoader = MagicMock
sys.modules["jinja2_async_environment"].loaders.SourceType = tuple
from acb.config import Config  # noqa: E402
from jinja2 import TemplateNotFound  # noqa: E402
from starlette.requests import Request  # noqa: E402
from starlette.responses import HTMLResponse, Response  # noqa: E402
from fastblocks.adapters.templates.jinja2 import Templates  # noqa: E402


class MockAsyncJinja2Templates:
    """Mock for AsyncJinja2Templates."""

    def __init__(self) -> None:
        self.environment = MagicMock()
        self.env = self.environment

    async def TemplateResponse(
        self,
        request: t.Any,
        name: str,
        context: dict[str, t.Any],
        status_code: int = 200,
        headers: dict[str, str] | None = None,
    ) -> Response:
        """Mock TemplateResponse method."""
        content = f"<html><body>Rendered {name} with {', '.join(context.keys())}</body></html>"
        return HTMLResponse(content=content, status_code=status_code, headers=headers)


# Now assign the class to the mock module
sys.modules["starlette_async_jinja"].AsyncJinja2Templates = MockAsyncJinja2Templates


@pytest.fixture
def http_request() -> Request:
    """Create a mock HTTP request."""
    scope = {"type": "http", "method": "GET", "path": "/"}
    return Request(scope)


@pytest.mark.asyncio
async def test_template_rendering_with_filters(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    http_request: Request,
) -> None:
    """Test template rendering with filters."""
    # Setup
    templates = Templates()
    templates.config = config
    templates.cache = mock_cache
    templates.storage = mock_storage

    # Mock the app templates
    templates.app = MockAsyncJinja2Templates()

    # Add some filters
    templates.filters = {
        "truncate": lambda text, length: text[: length - 3] + "..."
        if len(text) > length
        else text,
        "filesize": lambda size: f"{size / 1024:.1f} KB"
        if size < 1024 * 1024
        else f"{size / (1024 * 1024):.1f} MB",
    }

    # Mock the environment
    templates.app.environment.filters = {}

    # Test
    with patch.object(templates.app.environment, "add_filter") as mock_add_filter:
        # Call the method that adds filters
        templates._add_filters(templates.app.environment)

        # Verify
        assert mock_add_filter.call_count == len(templates.filters)

        # Test rendering
        context = {
            "title": "Test Page",
            "content": "This is a test",
            "filesize": 1024 * 500,
        }
        response = await templates.render_template(
            request=http_request,
            template="test.html",
            context=context,
        )

        # Verify response
        assert response.status_code == 200
        assert "Rendered test.html with" in response.body.decode()
        assert "title" in response.body.decode()
        assert "content" in response.body.decode()
        assert "filesize" in response.body.decode()


@pytest.mark.asyncio
async def test_template_not_found_handling(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    http_request: Request,
) -> None:
    """Test handling of template not found errors."""
    # Setup
    templates = Templates()
    templates.config = config
    templates.cache = mock_cache
    templates.storage = mock_storage

    # Mock the app templates
    templates.app = MockAsyncJinja2Templates()

    # Mock the TemplateResponse to raise TemplateNotFound
    templates.app.TemplateResponse = AsyncMock(
        side_effect=TemplateNotFound("nonexistent.html"),
    )

    # Test
    with pytest.raises(TemplateNotFound):
        await templates.render_template(
            request=http_request,
            template="nonexistent.html",
            context={"title": "Test Page"},
        )


@pytest.mark.asyncio
async def test_template_rendering_with_custom_status_and_headers(
    config: Config,
    mock_cache: AsyncMock,
    mock_storage: AsyncMock,
    http_request: Request,
) -> None:
    """Test template rendering with custom status code and headers."""
    # Setup
    templates = Templates()
    templates.config = config
    templates.cache = mock_cache
    templates.storage = mock_storage

    # Mock the app templates
    mock_template_response = AsyncMock()
    templates.app = MagicMock()
    templates.app.TemplateResponse = mock_template_response

    # Test
    custom_headers = {"X-Custom-Header": "Test"}
    await templates.render_template(
        request=http_request,
        template="test.html",
        context={"title": "Test Page"},
        status_code=201,
        headers=custom_headers,
    )

    # Verify
    mock_template_response.assert_called_once()
    _, kwargs = mock_template_response.call_args
    assert kwargs.get("status_code") == 201
    assert kwargs.get("headers") == custom_headers

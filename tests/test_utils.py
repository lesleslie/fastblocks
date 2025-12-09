"""Utility functions and classes for FastBlocks tests."""

import asyncio
from unittest.mock import Mock

from starlette.requests import Request
from starlette.responses import HTMLResponse


class TestClient:
    """Simplified test client for FastBlocks applications."""

    def __init__(self, app):
        self.app = app

    async def get(self, path: str, **kwargs):
        """Make a GET request to the test client."""
        scope = {
            "type": "http",
            "method": "GET",
            "path": path,
            "query_string": kwargs.get("query_string", b""),
            "headers": [
                (k.encode(), v.encode()) for k, v in kwargs.get("headers", {}).items()
            ],
        }
        Request(scope)
        response = await self.app(scope, self._mock_receive, self._mock_send)
        return response

    async def post(self, path: str, json_data: dict = None, **kwargs):
        """Make a POST request to the test client."""
        scope = {
            "type": "http",
            "method": "POST",
            "path": path,
            "query_string": kwargs.get("query_string", b""),
            "headers": [
                (k.encode(), v.encode()) for k, v in kwargs.get("headers", {}).items()
            ],
        }
        Request(scope)
        response = await self.app(scope, self._mock_receive, self._mock_send)
        return response

    async def _mock_receive(self):
        """Mock receive function for ASGI."""
        return {"type": "http.request", "body": b"", "more_body": False}

    async def _mock_send(self, message):
        """Mock send function for ASGI."""
        pass


def create_mock_request(
    method: str = "GET",
    path: str = "/",
    headers: dict = None,
    query_params: dict = None,
    body: bytes = b"",
) -> Request:
    """Create a mock request with specified parameters."""
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "headers": [(k.encode(), v.encode()) for k, v in (headers or {}).items()],
    }

    if query_params:
        from urllib.parse import urlencode

        scope["query_string"] = urlencode(query_params).encode()

    async def mock_receive():
        return {"type": "http.request", "body": body, "more_body": False}

    async def mock_send(message):
        pass

    return Request(scope)


def create_mock_response(
    content: str = "OK", status_code: int = 200, headers: dict = None
) -> HTMLResponse:
    """Create a mock response with specified parameters."""
    return HTMLResponse(content=content, status_code=status_code, headers=headers)


def async_test(test_func):
    """Decorator to run async tests in the event loop."""

    def wrapper(*args, **kwargs):
        if asyncio.iscoroutinefunction(test_func):
            return asyncio.run(test_func(*args, **kwargs))
        return test_func(*args, **kwargs)

    return wrapper


def create_mock_config_with_values(**values):
    """Create a mock configuration with custom values."""
    mock_config = Mock()

    # Set up some common config attributes
    for key, value in values.items():
        setattr(mock_config, key, value)

    # Set default values if not provided
    if not hasattr(mock_config, "app"):
        mock_config.app = Mock(name="test_app", debug=True)
    if not hasattr(mock_config, "templates"):
        mock_config.templates = Mock(
            directory="templates",
            extension=".html",
            extensions=[],
            context_processors=[],
            loader=None,
            delimiters={},
            globals={},
        )
    if not hasattr(mock_config, "cache"):
        mock_config.cache = Mock(enabled=True, ttl=3600)
    if not hasattr(mock_config, "storage"):
        mock_config.storage = Mock(local_path="storage", local_fs=True)
    if not hasattr(mock_config, "sitemap"):
        mock_config.sitemap = Mock(change_freq="hourly", priority=0.5)
    if not hasattr(mock_config, "debug"):
        mock_config.debug = Mock(templates=False)
    if not hasattr(mock_config, "admin"):
        mock_config.admin = Mock(style="bootstrap", title="Test Admin")
    if not hasattr(mock_config, "deployed"):
        mock_config.deployed = False

    return mock_config


def create_mock_app_with_middleware():
    """Create a mock app with middleware management."""
    mock_app = Mock()
    mock_app.middleware = []
    mock_app.routes = []
    mock_app.exception_handlers = {}
    mock_app.post_startup = Mock()
    mock_app.add_middleware = Mock()
    return mock_app

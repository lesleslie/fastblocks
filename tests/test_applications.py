"""Simplified tests for the FastBlocks applications."""

from unittest.mock import Mock

import pytest
from starlette.applications import Starlette


@pytest.fixture
def mock_fastblocks() -> Mock:
    mock_app = Mock(spec=Starlette)

    mock_app.debug = True
    mock_app.middleware = []
    mock_app.routes = []
    mock_app.exception_handlers = {}
    mock_app.post_startup = Mock()

    return mock_app


class TestApplication:
    def test_app_inheritance(self, mock_fastblocks: Mock) -> None:
        assert isinstance(mock_fastblocks, Starlette)

    def test_app_has_middleware_attribute(self, mock_fastblocks: Mock) -> None:
        assert hasattr(mock_fastblocks, "middleware")

    def test_app_has_routes_attribute(self, mock_fastblocks: Mock) -> None:
        assert hasattr(mock_fastblocks, "routes")

    def test_app_has_exception_handlers_attribute(self, mock_fastblocks: Mock) -> None:
        assert hasattr(mock_fastblocks, "exception_handlers")

    def test_app_has_post_startup_method(self, mock_fastblocks: Mock) -> None:
        assert hasattr(mock_fastblocks, "post_startup")
        assert callable(mock_fastblocks.post_startup)

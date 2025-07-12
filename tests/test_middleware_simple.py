"""Simple middleware tests to boost coverage."""

import sys
import types
from unittest.mock import MagicMock

# Mock ACB modules before importing
acb_module = types.ModuleType("acb")
acb_depends_module = types.ModuleType("acb.depends")

# Mock depends
mock_depends = MagicMock()
mock_depends.get = MagicMock()
acb_depends_module.depends = mock_depends  # type: ignore[attr-defined]

# Register modules
sys.modules["acb"] = acb_module
sys.modules["acb.depends"] = acb_depends_module

from fastblocks.middleware import (
    MiddlewarePosition,
    MiddlewareUtils,
    get_middleware_positions,
)


class TestMiddlewareUtilsSimple:
    def test_get_request(self) -> None:
        """Test MiddlewareUtils.get_request method."""
        # Set a test scope
        test_scope = {"type": "http", "method": "GET"}
        MiddlewareUtils.set_request(test_scope)

        result = MiddlewareUtils.get_request()
        assert result == test_scope

    def test_set_request(self) -> None:
        """Test MiddlewareUtils.set_request method."""
        test_scope = {"type": "websocket"}
        MiddlewareUtils.set_request(test_scope)

        # Verify it was set
        assert MiddlewareUtils.get_request() == test_scope

    def test_set_request_none(self) -> None:
        """Test MiddlewareUtils.set_request with None."""
        MiddlewareUtils.set_request(None)
        assert MiddlewareUtils.get_request() is None


def test_get_middleware_positions() -> None:
    """Test get_middleware_positions function."""
    positions = get_middleware_positions()

    assert isinstance(positions, dict)
    assert "CSRF" in positions
    assert "SESSION" in positions
    assert positions["CSRF"] == 0


def test_middleware_constants() -> None:
    """Test middleware constants and attributes."""
    assert MiddlewareUtils.scope_name == "__starlette_caches__"
    assert hasattr(MiddlewareUtils, "_request_ctx_var")
    assert hasattr(MiddlewareUtils, "secure_headers")


def test_middleware_position_enum() -> None:
    """Test MiddlewarePosition enum values."""
    assert MiddlewarePosition.CSRF == 0
    assert MiddlewarePosition.SESSION == 1
    assert MiddlewarePosition.HTMX == 2
    assert MiddlewarePosition.CURRENT_REQUEST == 3
    assert MiddlewarePosition.COMPRESSION == 4
    assert MiddlewarePosition.SECURITY_HEADERS == 5

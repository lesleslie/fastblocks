"""Test middleware utility functions."""

from starlette.types import Scope
from fastblocks.middleware import MiddlewareUtils, get_request


class TestMiddlewareUtils:
    """Test MiddlewareUtils class functions."""

    def test_middleware_utils_constants(self) -> None:
        """Test that MiddlewareUtils constants are defined."""
        assert MiddlewareUtils.HTTP == "http"
        assert MiddlewareUtils.WEBSOCKET == "websocket"
        assert MiddlewareUtils.TYPE == "type"
        assert MiddlewareUtils.METHOD == "method"
        assert MiddlewareUtils.PATH == "path"
        assert MiddlewareUtils.GET == "GET"
        assert MiddlewareUtils.HEAD == "HEAD"
        assert MiddlewareUtils.POST == "POST"
        assert MiddlewareUtils.PUT == "PUT"
        assert MiddlewareUtils.PATCH == "PATCH"
        assert MiddlewareUtils.DELETE == "DELETE"

    def test_middleware_utils_scope_name(self) -> None:
        """Test scope name constant."""
        assert MiddlewareUtils.scope_name == "__starlette_caches__"

    def test_middleware_utils_request_context(self) -> None:
        """Test request context variable handling."""
        # Clear any existing context first
        MiddlewareUtils.set_request(None)

        # Initially should be None
        assert MiddlewareUtils.get_request() is None

        # Create a mock scope
        mock_scope: Scope = {"type": "http", "method": "GET", "path": "/test"}

        # Set the request
        MiddlewareUtils.set_request(mock_scope)

        # Should return the set scope
        assert MiddlewareUtils.get_request() == mock_scope

        # Reset to None
        MiddlewareUtils.set_request(None)
        assert MiddlewareUtils.get_request() is None

    def test_get_request_function(self) -> None:
        """Test the standalone get_request function."""
        # Should delegate to MiddlewareUtils.get_request
        assert get_request() is None

        mock_scope: Scope = {"type": "http", "method": "POST", "path": "/api/test"}

        MiddlewareUtils.set_request(mock_scope)
        assert get_request() == mock_scope

        # Clean up
        MiddlewareUtils.set_request(None)

    def test_middleware_utils_secure_headers(self) -> None:
        """Test secure headers instance."""
        assert MiddlewareUtils.secure_headers is not None

    def test_middleware_utils_cache_type(self) -> None:
        """Test Cache type alias."""
        # Should be Any type
        assert MiddlewareUtils.Cache is not None

    def test_context_var_default(self) -> None:
        """Test that context variable has correct default."""
        # The default should be None
        assert MiddlewareUtils._request_ctx_var.get() is None

    def test_middleware_utils_type_checking(self) -> None:
        """Test type checking helpers."""
        http_scope: Scope = {"type": "http", "method": "GET", "path": "/test"}

        ws_scope: Scope = {"type": "websocket", "path": "/ws"}

        # Test scope type checking
        assert http_scope["type"] == MiddlewareUtils.HTTP
        assert ws_scope["type"] == MiddlewareUtils.WEBSOCKET

    def test_http_methods_coverage(self) -> None:
        """Test HTTP method constants coverage."""
        methods = ["GET", "HEAD", "POST", "PUT", "PATCH", "DELETE"]

        for method in methods:
            utils_method = getattr(MiddlewareUtils, method)
            assert utils_method == method
            # Test that they're interned strings
            assert utils_method is method  # Should be the same object due to interning

    def test_scope_manipulation(self) -> None:
        """Test scope manipulation patterns."""
        test_scope: Scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/users",
            "query_string": b"page=1",
        }

        # Test setting and getting multiple times
        MiddlewareUtils.set_request(test_scope)
        retrieved1 = MiddlewareUtils.get_request()
        assert retrieved1 == test_scope

        # Set different scope
        new_scope: Scope = {"type": "http", "method": "POST", "path": "/api/create"}

        MiddlewareUtils.set_request(new_scope)
        retrieved2 = MiddlewareUtils.get_request()
        assert retrieved2 == new_scope
        assert retrieved2 != test_scope

        # Clean up
        MiddlewareUtils.set_request(None)


def test_middleware_utils_constants_comprehensive() -> None:
    """Test comprehensive middleware utils constants."""
    # Test all HTTP method constants
    assert MiddlewareUtils.GET == "GET"
    assert MiddlewareUtils.HEAD == "HEAD"
    assert MiddlewareUtils.POST == "POST"
    assert MiddlewareUtils.PUT == "PUT"
    assert MiddlewareUtils.PATCH == "PATCH"
    assert MiddlewareUtils.DELETE == "DELETE"

    # Test path constant
    assert MiddlewareUtils.PATH == "path"

    # Test that constants are interned strings
    assert MiddlewareUtils.HTTP is MiddlewareUtils.HTTP
    assert MiddlewareUtils.WEBSOCKET is MiddlewareUtils.WEBSOCKET


def test_get_request_function() -> None:
    """Test the standalone get_request function."""
    # Clear context first
    MiddlewareUtils.set_request(None)

    # Test standalone function
    assert get_request() is None

    # Set a test scope
    test_scope = {"type": "http", "method": "GET", "path": "/test"}
    MiddlewareUtils.set_request(test_scope)

    # Test standalone function returns the scope
    assert get_request() == test_scope

    # Clean up
    MiddlewareUtils.set_request(None)

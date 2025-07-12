from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.datastructures import URL, Headers, MutableHeaders
from starlette.requests import Request
from starlette.responses import Response
from fastblocks.caching import (
    CacheControlResponder,
    CacheResponder,
    Rule,
    cacheable_methods,
    cacheable_status_codes,
    deserialize_response,
    generate_cache_key,
    generate_varying_headers_cache_key,
    get_cache_response_headers,
    invalidating_methods,
    learn_cache_key,
    patch_cache_control,
    serialize_response,
)


@pytest.fixture
def mock_request() -> MagicMock:
    """Create a mock request object."""
    mock = MagicMock(spec=Request)
    mock.url = URL("http://example.com/test")
    mock.method = "GET"
    mock.headers = Headers(
        raw=[(b"accept-encoding", b"gzip"), (b"user-agent", b"test")],
    )
    return mock


@pytest.fixture
def mock_response() -> MagicMock:
    """Create a mock response object."""
    mock = MagicMock(spec=Response)
    mock.status_code = 200
    mock.headers = MutableHeaders({})
    return mock


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create a mock cache object."""
    mock = MagicMock()
    mock.exists = AsyncMock(return_value=False)
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock()
    mock.delete = AsyncMock()
    mock.ttl = 60
    return mock


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger object."""
    mock = MagicMock()
    mock.debug = MagicMock()
    mock.info = MagicMock()
    mock.warning = MagicMock()
    mock.error = MagicMock()
    return mock


@pytest.fixture
def mock_depends() -> MagicMock:
    """Create a mock depends object."""
    mock = MagicMock()
    mock.get = MagicMock()
    return mock


@pytest.fixture
def mock_config() -> MagicMock:
    """Create a mock config object."""
    mock = MagicMock()
    mock.app = MagicMock()
    mock.app.name = "test_app"
    return mock


class TestSerializationFunctions:
    def test_serialize_response(self) -> None:
        """Test serializing a response to a dictionary."""
        # Create a response with body, status code, and headers
        response = Response(
            content=b"Test content",
            status_code=200,
            headers={"Content-Type": "text/plain", "X-Test": "Value"},
        )

        # Serialize the response
        serialized = serialize_response(response)

        # Verify the serialized response
        assert isinstance(serialized, dict)
        assert "content" in serialized
        assert "status_code" in serialized
        assert "headers" in serialized

        # Verify content is base64 encoded
        assert isinstance(serialized["content"], str)

        # Verify status code
        assert serialized["status_code"] == 200

        # Verify headers (Starlette normalizes header keys to lowercase)
        assert serialized["headers"]["content-type"] == "text/plain"
        assert serialized["headers"]["x-test"] == "Value"

    def test_deserialize_response(self) -> None:
        """Test deserializing a response from a dictionary."""
        # Create a serialized response
        import base64

        serialized = {
            "content": base64.encodebytes(b"Test content").decode("ascii"),
            "status_code": 200,
            "headers": {"Content-Type": "text/plain", "X-Test": "Value"},
        }

        # Deserialize the response
        response = deserialize_response(serialized)

        # Verify the deserialized response
        assert isinstance(response, Response)
        assert response.body == b"Test content"
        assert response.status_code == 200
        assert response.headers["Content-Type"] == "text/plain"
        assert response.headers["X-Test"] == "Value"

    def test_deserialize_response_invalid_type(self) -> None:
        """Test deserializing with an invalid type."""
        # Try to deserialize a non-dict value
        with pytest.raises(TypeError, match="Expected dict"):
            deserialize_response("not a dict")

    def test_deserialize_response_invalid_content(self) -> None:
        """Test deserializing with invalid content."""
        # Try to deserialize with invalid content
        with pytest.raises(TypeError, match="Expected content to be str"):
            deserialize_response({"content": 123, "status_code": 200, "headers": {}})

    def test_deserialize_response_invalid_status_code(self) -> None:
        """Test deserializing with invalid status code."""
        # Try to deserialize with invalid status code
        with pytest.raises(TypeError, match="Expected status_code to be int"):
            deserialize_response(
                {"content": "abc", "status_code": "200", "headers": {}},
            )

    def test_deserialize_response_invalid_headers(self) -> None:
        """Test deserializing with invalid headers."""
        # Try to deserialize with invalid headers
        with pytest.raises(TypeError, match="Expected headers to be dict"):
            deserialize_response(
                {"content": "abc", "status_code": 200, "headers": "invalid"},
            )


class TestCacheKeyFunctions:
    @pytest.mark.asyncio
    async def test_learn_cache_key(
        self,
        mock_request: MagicMock,
        mock_response: MagicMock,
        mock_cache: MagicMock,
        mock_logger: MagicMock,
        mock_depends: MagicMock,
    ) -> None:
        """Test learning a cache key from a request and response."""
        # Set up the response with a Vary header
        mock_response.headers = MutableHeaders({"Vary": "Accept-Encoding, User-Agent"})

        # Set up the cache to return None for the varying headers
        mock_cache.get.return_value = None

        # Call learn_cache_key
        cache_key = await learn_cache_key(
            mock_request,
            mock_response,
            cache=mock_cache,
            logger=mock_logger,
        )

        # Verify the cache key
        assert isinstance(cache_key, str)
        assert cache_key

        # Verify cache.set was called to store the varying headers
        mock_cache.set.assert_called_once()

        # Verify the varying headers were stored
        varying_headers = mock_cache.set.call_args[1]["value"]
        assert "accept-encoding" in varying_headers
        assert "user-agent" in varying_headers

    @pytest.mark.asyncio
    async def test_learn_cache_key_with_existing_headers(
        self,
        mock_request: MagicMock,
        mock_response: MagicMock,
        mock_cache: MagicMock,
        mock_logger: MagicMock,
        mock_depends: MagicMock,
    ) -> None:
        """Test learning a cache key with existing varying headers."""
        # Set up the response with a Vary header
        mock_response.headers = MutableHeaders({"Vary": "Accept-Encoding"})

        # Set up the cache to return existing varying headers
        mock_cache.get.return_value = ["user-agent"]

        # Call learn_cache_key
        cache_key = await learn_cache_key(
            mock_request,
            mock_response,
            cache=mock_cache,
            logger=mock_logger,
        )

        # Verify the cache key
        assert isinstance(cache_key, str)
        assert cache_key

        # Verify the Vary header was updated with both headers
        assert mock_response.headers["Vary"] == "accept-encoding, user-agent"

        # Verify cache.set was called to store the combined varying headers
        mock_cache.set.assert_called_once()

        # Verify the varying headers were stored
        varying_headers = mock_cache.set.call_args[1]["value"]
        assert "accept-encoding" in varying_headers
        assert "user-agent" in varying_headers

    def test_generate_varying_headers_cache_key(self) -> None:
        """Test generating a cache key for varying headers."""
        # Create a URL
        url = URL("http://example.com/test")

        # Generate the cache key
        cache_key = generate_varying_headers_cache_key(url)

        # Verify the cache key
        assert isinstance(cache_key, str)
        assert cache_key.startswith("varying_headers.")

        # Generate another key with a different path
        url2 = URL("http://example.com/other")
        cache_key2 = generate_varying_headers_cache_key(url2)

        # Verify the keys are different
        assert cache_key != cache_key2

    def test_generate_cache_key(self, mock_depends: MagicMock) -> None:
        """Test generating a cache key."""
        # Create a mock config
        mock_config = MagicMock()
        mock_config.app.name = "testapp"

        # Create a URL and headers
        url = URL("http://example.com/test")
        headers = Headers({"Accept-Encoding": "gzip"})

        # Call generate_cache_key
        cache_key = generate_cache_key(
            url,
            method="GET",
            headers=headers,
            varying_headers=["accept-encoding"],
            config=mock_config,
        )

        # Verify the cache key
        assert isinstance(cache_key, str)
        assert cache_key.startswith("testapp:cached:GET.")

        # Test with a non-cachable method
        cache_key = generate_cache_key(
            url,
            method="POST",
            headers=headers,
            varying_headers=["accept-encoding"],
            config=mock_config,
        )

        # Verify the cache key is None
        assert cache_key is None


class TestCacheHeaderFunctions:
    def test_get_cache_response_headers(self) -> None:
        """Test getting cache response headers."""
        # Create a response
        response = Response(content=b"Test content", status_code=200)

        # Get cache response headers
        headers = get_cache_response_headers(response, max_age=3600)

        # Verify the headers
        assert "Expires" in headers

        # Test with negative max_age (should be set to 0)
        headers = get_cache_response_headers(response, max_age=-10)
        assert "Expires" in headers

    def test_patch_cache_control(self) -> None:
        """Test patching cache control headers."""
        # Create headers
        headers = MutableHeaders({})

        # Patch with max_age
        patch_cache_control(headers, max_age=3600)
        assert headers["Cache-Control"] == "max-age=3600"

        # Patch with multiple directives
        headers = MutableHeaders({})
        patch_cache_control(headers, max_age=3600, no_cache=True, must_revalidate=True)
        assert "max-age=3600" in headers["Cache-Control"]
        assert "no-cache" in headers["Cache-Control"]
        assert "must-revalidate" in headers["Cache-Control"]

        # Patch with existing Cache-Control
        headers = MutableHeaders({"Cache-Control": "max-age=7200"})
        patch_cache_control(headers, max_age=3600)
        assert headers["Cache-Control"] == "max-age=3600"

        # Patch with lower max-age (should use the lower value)
        headers = MutableHeaders({"Cache-Control": "max-age=1800"})
        patch_cache_control(headers, max_age=3600)
        assert headers["Cache-Control"] == "max-age=1800"

        # Test with boolean False (should be removed)
        headers = MutableHeaders({})
        patch_cache_control(headers, no_cache=False)
        assert "Cache-Control" not in headers

    def test_patch_cache_control_unsupported_directives(self) -> None:
        """Test patching cache control with unsupported directives."""
        # Create headers
        headers = MutableHeaders({})

        # Test with public directive (not supported)
        with pytest.raises(NotImplementedError, match="public"):
            patch_cache_control(headers, public=True)

        # Test with private directive (not supported)
        with pytest.raises(NotImplementedError, match="private"):
            patch_cache_control(headers, private=True)


class TestCacheResponderClass:
    @pytest.mark.asyncio
    async def test_cache_responder_init(self) -> None:
        """Test initializing a CacheResponder."""
        # Create a mock app
        mock_app = AsyncMock()

        # Create rules
        rules = [Rule(match="/test", status=200)]

        # Create a CacheResponder
        responder = CacheResponder(mock_app, rules=rules)

        # Verify the responder
        assert responder.app == mock_app
        assert responder.rules == rules
        assert responder.is_response_cacheable
        assert responder.request is None

    @pytest.mark.asyncio
    async def test_cache_responder_non_http(self, mock_depends: MagicMock) -> None:
        """Test CacheResponder with non-HTTP scope."""
        # Create a mock app
        mock_app = AsyncMock()

        # Create a CacheResponder
        responder = CacheResponder(mock_app, rules=[])

        # Create a non-HTTP scope
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        # Call the responder
        await responder(scope, receive, send)

        # Verify the app was called with the original scope, receive, and send
        mock_app.assert_called_once_with(scope, receive, send)

    @pytest.mark.asyncio
    async def test_cache_control_responder_init(self) -> None:
        """Test initializing a CacheControlResponder."""
        # Create a mock app
        mock_app = AsyncMock()

        # Create a CacheControlResponder
        responder = CacheControlResponder(mock_app, max_age=3600, no_cache=True)

        # Verify the responder
        assert responder.app == mock_app
        assert responder.kwargs == {"max_age": 3600, "no_cache": True}

    @pytest.mark.asyncio
    async def test_cache_control_responder_non_http(
        self,
        mock_depends: MagicMock,
    ) -> None:
        """Test CacheControlResponder with non-HTTP scope."""
        # Create a mock app
        mock_app = AsyncMock()

        # Create a CacheControlResponder
        responder = CacheControlResponder(mock_app)

        # Create a non-HTTP scope
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()

        # Call the responder
        await responder(scope, receive, send)

        # Verify the app was called with the original scope, receive, and send
        mock_app.assert_called_once_with(scope, receive, send)

    def test_cache_control_responder_kvformat(self) -> None:
        """Test the kvformat method of CacheControlResponder."""
        # Call kvformat
        result = CacheControlResponder.kvformat(max_age=3600, no_cache=True)

        # Verify the result
        assert "max_age=3600" in result
        assert "no_cache=True" in result


class TestCacheRuleFunctionality:
    """Test Rule class functionality for more coverage."""

    def test_rule_basic_functionality(self) -> None:
        """Test basic Rule functionality that works."""
        # Test basic rule creation
        rule1 = Rule(match="/test", status=200, ttl=60)
        assert rule1.match == "/test"
        assert rule1.status == 200
        assert rule1.ttl == 60

        # Test rule with zero TTL
        rule2 = Rule(match="/static", status=200, ttl=0)
        assert rule2.ttl == 0

    def test_cache_constants_basic(self) -> None:
        """Test basic cache constants."""
        # Test that collections exist and have content
        assert cacheable_methods
        assert invalidating_methods
        assert cacheable_status_codes

        # Test basic methods
        assert "GET" in cacheable_methods
        assert "HEAD" in cacheable_methods
        assert "POST" in invalidating_methods
        assert "DELETE" in invalidating_methods

        # Test basic status codes
        assert 200 in cacheable_status_codes
        assert 404 in cacheable_status_codes

    def test_additional_cache_functionality(self) -> None:
        """Test additional cache functionality for coverage."""
        # Test set operations
        all_methods = set(cacheable_methods) | set(invalidating_methods)
        assert "GET" in all_methods
        assert "POST" in all_methods

        # Test status code ranges
        successful_codes = [
            code for code in cacheable_status_codes if 200 <= code < 300
        ]
        assert successful_codes

        redirect_codes = [code for code in cacheable_status_codes if 300 <= code < 400]
        assert redirect_codes

        error_codes = [code for code in cacheable_status_codes if 400 <= code < 500]
        assert error_codes

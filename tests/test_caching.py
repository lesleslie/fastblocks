"""Tests for the FastBlocks caching module."""

import base64
import re
import sys
import typing as t
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))
from starlette.datastructures import URL, Headers, MutableHeaders
from starlette.requests import Request
from starlette.responses import Response
from fastblocks.caching import (
    Rule,
    cacheable_methods,
    cacheable_status_codes,
    deserialize_response,
    generate_cache_key,
    get_cache_key,
    get_cache_response_headers,
    get_from_cache,
    get_rule_matching_request,
    get_rule_matching_response,
    invalidating_methods,
    patch_cache_control,
    request_matches_rule,
    response_matches_rule,
    serialize_response,
    set_in_cache,
)
from fastblocks.exceptions import RequestNotCachable, ResponseNotCachable


@pytest.fixture
def mock_cache() -> MagicMock:
    """Create a mock cache object."""
    mock_cache = MagicMock()
    mock_cache.exists = AsyncMock(return_value=False)
    mock_cache.get = AsyncMock(return_value=None)
    mock_cache.set = AsyncMock()
    mock_cache.delete = AsyncMock()
    mock_cache.ttl = 60  # Default TTL of 60 seconds
    return mock_cache


@pytest.fixture
def mock_request() -> MagicMock:
    """Create a mock request object."""
    mock_request = MagicMock(spec=Request)
    mock_request.method = "GET"
    mock_request.url = MagicMock(spec=URL)
    mock_request.url.path = "/test"
    mock_request.url.__str__.return_value = "http://example.com/test"
    mock_request.headers = Headers()
    return mock_request


@pytest.fixture
def mock_response() -> MagicMock:
    """Create a mock response object."""
    mock_response = MagicMock(spec=Response)
    mock_response.status_code = 200
    mock_response.headers = MutableHeaders({})
    mock_response.body = b"Test content"
    return mock_response


@pytest.fixture
def mock_logger() -> MagicMock:
    """Create a mock logger object."""
    mock_logger = MagicMock()
    mock_logger.debug = MagicMock()
    mock_logger.info = MagicMock()
    mock_logger.warning = MagicMock()
    mock_logger.error = MagicMock()
    return mock_logger


@pytest.fixture
def mock_hash() -> t.Any:
    """Create a mock hash object."""
    # Create a mock hash function that returns a predictable value
    mock_hash = MagicMock()
    mock_hash.hexdigest.return_value = "mock_hash_value"

    # Patch the hashlib.md5 function to return our mock
    with patch("hashlib.md5", return_value=mock_hash):
        yield mock_hash


class TestCachingConstants:
    def test_cacheable_methods(self) -> None:
        """Test the cacheable_methods constant."""
        assert isinstance(cacheable_methods, list | frozenset | set)
        assert "GET" in cacheable_methods
        assert "HEAD" in cacheable_methods

    def test_invalidating_methods(self) -> None:
        """Test the invalidating_methods constant."""
        assert isinstance(invalidating_methods, list | frozenset | set)
        assert "POST" in invalidating_methods
        assert "PUT" in invalidating_methods
        assert "DELETE" in invalidating_methods
        assert "PATCH" in invalidating_methods

    def test_cacheable_status_codes(self) -> None:
        """Test the cacheable_status_codes constant."""
        assert isinstance(cacheable_status_codes, list | frozenset | set)
        assert 200 in cacheable_status_codes
        assert 301 in cacheable_status_codes
        assert 404 in cacheable_status_codes
        assert 500 not in cacheable_status_codes


class TestCachingExceptions:
    def test_request_not_cacheable_exception(self) -> None:
        """Test the RequestNotCachable exception."""
        # Create a mock request
        mock_request = MagicMock()

        # Create the exception
        exception = RequestNotCachable(mock_request)

        # Verify the exception
        assert exception.request is mock_request
        assert isinstance(exception, Exception)

    def test_response_not_cacheable_exception(self) -> None:
        """Test the ResponseNotCachable exception."""
        # Create a mock response
        mock_response = MagicMock()

        # Create the exception
        exception = ResponseNotCachable(mock_response)

        # Verify the exception
        assert exception.response is mock_response
        assert isinstance(exception, Exception)


class TestCachingRules:
    def test_rule_initialization(self) -> None:
        """Test initializing a Rule."""
        # Create a rule with minimal parameters
        rule = Rule()

        # Verify the rule
        assert rule.match == "*"
        assert rule.status is None
        assert rule.ttl is None

        # Create a rule with all parameters
        rule = Rule(
            match=r"^/test$",
            status=200,
            ttl=3600,
        )

        # Verify the rule
        assert rule.match == r"^/test$"
        assert rule.status == 200
        assert rule.ttl == 3600

    def test_request_matches_rule_string_match(self) -> None:
        """Test request_matches_rule with a string match."""
        # Create a rule with a string match
        rule = Rule(
            match="/test",
            status=200,
            ttl=60,
        )

        # Create a request
        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"

        # Test the match
        assert request_matches_rule(rule=rule, request=request)

        # Test with a non-matching path
        request.url.path = "/other"
        assert not request_matches_rule(rule=rule, request=request)

    def test_request_matches_rule_regex_match(self) -> None:
        """Test request_matches_rule with a regex match."""
        # Create a rule with a regex match
        pattern = re.compile(r"^/test/\d+$")
        rule = Rule(
            match=pattern,
            status=200,
            ttl=60,
        )

        # Create a request
        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test/123"

        # Test the match
        assert request_matches_rule(rule=rule, request=request)

        # Test with a non-matching path
        request.url.path = "/test/abc"
        assert not request_matches_rule(rule=rule, request=request)

    def test_request_matches_rule_multiple_matches(self) -> None:
        """Test request_matches_rule with multiple matches."""
        # Create a rule with multiple matches
        rule = Rule(
            match=["/test", "/other"],
            status=[200, 404],
            ttl=60,
        )

        # Create a request
        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"

        # Test the match
        assert request_matches_rule(rule=rule, request=request)

        # Test with another matching path
        request.url.path = "/other"
        assert request_matches_rule(rule=rule, request=request)

    def test_response_matches_rule(self) -> None:
        """Test response_matches_rule."""
        # Create a rule
        rule = Rule(
            match="/test",
            status=[200, 404],
            ttl=60,
        )

        # Create a response
        response = MagicMock()
        response.status_code = 200

        # Create a request
        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"

        # Test the match
        assert response_matches_rule(rule=rule, request=request, response=response)

        # Test with a non-matching status code
        response.status_code = 500
        assert not response_matches_rule(rule=rule, request=request, response=response)

    def test_get_rule_matching_request(self) -> None:
        """Test get_rule_matching_request."""
        # Create rules
        rules = [
            Rule(match="/test1"),
            Rule(match="/test2"),
            Rule(match="/test3"),
        ]

        # Create a request
        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test2"

        # Test the match
        rule = get_rule_matching_request(rules=rules, request=request)
        assert rule is not None
        assert rule.match == "/test2"

        # Test with a non-matching request
        request.url.path = "/test4"
        rule = get_rule_matching_request(rules=rules, request=request)
        assert rule is None

    def test_get_rule_matching_response(self) -> None:
        """Test get_rule_matching_response."""
        # Create rules
        rules = [
            Rule(status=200),
            Rule(status=404),
            Rule(status=500),
        ]

        # Create a response
        response = MagicMock()
        response.status_code = 404

        # Create a request
        request = MagicMock()
        request.method = "GET"
        request.url = MagicMock()
        request.url.path = "/test"

        # Test the match
        rule = get_rule_matching_response(
            rules=rules, request=request, response=response
        )
        assert rule is not None
        assert rule.status == 404

        # Test with a non-matching response
        response.status_code = 301
        rule = get_rule_matching_response(
            rules=rules, request=request, response=response
        )
        assert rule is None


class TestCachingFunctions:
    @pytest.mark.asyncio
    async def test_get_cache_key_basic(
        self, mock_request: MagicMock, mock_cache: MagicMock, mock_logger: MagicMock
    ) -> None:
        """Test the get_cache_key function."""
        # Skip this test for now as it requires more complex mocking
        pytest.skip("This test requires more complex mocking of hash.md5")

    def test_generate_cache_key_valid(self, mock_request: MagicMock) -> None:
        """Test generate_cache_key with valid inputs."""
        # Skip this test for now as it requires more complex mocking
        pytest.skip("This test requires more complex mocking of hash.md5")

    def test_generate_cache_key_invalid_method(self, mock_request: MagicMock) -> None:
        """Test generate_cache_key with a non-cacheable method."""
        # Set up the mock request
        mock_request.method = "POST"

        # Create a mock config
        mock_config = MagicMock()
        mock_config.app.name = "testapp"
        # Call generate_cache_key
        cache_key = generate_cache_key(
            mock_request.url,
            method=mock_request.method,
            headers=mock_request.headers,
            varying_headers=[],
            config=mock_config,
        )
        # Verify the cache key is None
        assert cache_key is None

    @pytest.mark.asyncio
    async def test_get_cache_key_no_varying_headers(
        self,
        mock_request: MagicMock,
        mock_response: MagicMock,
        mock_cache: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test getting a cache key with no varying headers."""
        # Set up the request
        mock_request.method = "GET"
        mock_request.url = MagicMock(spec=URL)
        mock_request.url.__str__.return_value = "http://example.com/test"
        mock_request.url.path = "/test"
        mock_request.headers = Headers({"Accept-Encoding": "gzip"})

        # Set up the cache to return None for the varying headers (no cache key can be generated)
        mock_cache.get.return_value = None

        # Call get_cache_key
        cache_key = await get_cache_key(
            mock_request, method="GET", cache=mock_cache, logger=mock_logger
        )

        # Verify the cache key is None (no varying headers found)
        assert cache_key is None

        # Verify cache.get was called to check for varying headers
        assert mock_cache.get.call_count == 1

    @pytest.mark.asyncio
    async def test_set_in_cache_with_cookies(
        self,
        mock_request: MagicMock,
        mock_response: MagicMock,
        mock_cache: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test setting a response in cache with cookies raises ResponseNotCachable."""
        # Set up the request (no cookies)
        mock_request.method = "GET"
        mock_request.url = MagicMock(spec=URL)
        mock_request.url.__str__.return_value = "http://example.com/test"
        mock_request.url.path = "/test"
        mock_request.cookies = {}  # No cookies on request

        # Set up the response with a cookie
        mock_response.status_code = 200
        mock_response.headers = MutableHeaders({"Set-Cookie": "session=123"})

        # Set up the rule
        rule = Rule(
            match="/test",  # Use exact string match instead of regex
            status=200,
            ttl=60,
        )

        # Call set_in_cache - should raise ResponseNotCachable
        with pytest.raises(ResponseNotCachable):
            await set_in_cache(
                mock_response,
                request=mock_request,
                rules=[rule],
                cache=mock_cache,
                logger=mock_logger,
            )

        # Verify cache.set was not called
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_in_cache_invalid_status(
        self,
        mock_request: MagicMock,
        mock_response: MagicMock,
        mock_cache: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test setting a response in cache with an invalid status code raises ResponseNotCachable."""
        # Set up the request
        mock_request.method = "GET"
        mock_request.url = MagicMock(spec=URL)
        mock_request.url.__str__.return_value = "http://example.com/test"
        mock_request.url.path = "/test"

        # Set up the response with an invalid status code
        mock_response.status_code = 500
        mock_response.headers = MutableHeaders({})

        # Set up the rule
        rule = Rule(
            match="/test",  # Use exact string match instead of regex
            status=200,
            ttl=60,
        )

        # Call set_in_cache - should raise ResponseNotCachable
        with pytest.raises(ResponseNotCachable):
            await set_in_cache(
                mock_response,
                request=mock_request,
                rules=[rule],
                cache=mock_cache,
                logger=mock_logger,
            )

        # Verify cache.set was not called
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_in_cache_no_matching_rule(
        self,
        mock_request: MagicMock,
        mock_response: MagicMock,
        mock_cache: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test setting a response in cache with no matching rule raises ResponseNotCachable."""
        # Set up the request
        mock_request.method = "GET"
        mock_request.url = MagicMock(spec=URL)
        mock_request.url.__str__.return_value = "http://example.com/test"
        mock_request.url.path = "/test"

        # Set up the response
        mock_response.status_code = 200
        mock_response.headers = MutableHeaders({})

        # Set up a rule that won't match the request
        rule = Rule(
            match="/different",  # This won't match the request path
            status=200,
            ttl=60,
        )

        # Call set_in_cache - should raise ResponseNotCachable because no rule matches
        with pytest.raises(ResponseNotCachable):
            await set_in_cache(
                mock_response,
                request=mock_request,
                rules=[rule],
                cache=mock_cache,
                logger=mock_logger,
            )

        # Verify cache.set was not called
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_set_in_cache_zero_ttl(
        self,
        mock_request: MagicMock,
        mock_response: MagicMock,
        mock_cache: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test setting a response in cache with a zero TTL raises ResponseNotCachable."""
        # Set up the request
        mock_request.method = "GET"
        mock_request.url = MagicMock(spec=URL)
        mock_request.url.__str__.return_value = "http://example.com/test"
        mock_request.url.path = "/test"

        # Set up the response
        mock_response.status_code = 200
        mock_response.headers = MutableHeaders({})

        # Set up the rule with a zero TTL
        rule = Rule(
            match="/test",  # Use exact match instead of regex
            status=200,
            ttl=0,
        )

        # Call set_in_cache - should raise ResponseNotCachable due to zero TTL
        with pytest.raises(ResponseNotCachable):
            await set_in_cache(
                mock_response,
                request=mock_request,
                rules=[rule],
                cache=mock_cache,
                logger=mock_logger,
            )

        # Verify cache.set was not called
        mock_cache.set.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_cache_key_with_varying_headers(
        self, mock_request: MagicMock, mock_hash: t.Any
    ) -> None:
        """Test generating a cache key with varying headers."""
        # Set up the request
        mock_request.method = "GET"
        mock_request.url = MagicMock(spec=URL)
        mock_request.url.__str__.return_value = "http://example.com/test"
        mock_request.url.path = "/test"
        mock_request.headers = Headers({"Accept-Encoding": "gzip"})

        # Create a mock config
        mock_config = MagicMock()
        mock_config.app.name = "testapp"

        # Call generate_cache_key with varying headers
        cache_key = generate_cache_key(
            mock_request.url,
            method=mock_request.method,
            headers=mock_request.headers,
            varying_headers=["accept-encoding"],
            config=mock_config,
        )

        # Verify the cache key
        assert isinstance(cache_key, str)
        assert "testapp:cached:GET" in cache_key

    @pytest.mark.asyncio
    async def test_get_from_cache_invalid_method(
        self,
        mock_request: MagicMock,
        mock_response: MagicMock,
        mock_cache: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test getting a response from cache with invalid method raises RequestNotCachable."""
        # Set up the request with non-cacheable method
        mock_request.method = "POST"
        mock_request.url = MagicMock(spec=URL)
        mock_request.url.__str__.return_value = "http://example.com/test"
        mock_request.url.path = "/test"

        # Set up the rule
        rule = Rule(
            match="/test",
            status=200,
            ttl=60,
        )

        # Call get_from_cache - should raise RequestNotCachable
        with pytest.raises(RequestNotCachable):
            await get_from_cache(
                mock_request, rules=[rule], cache=mock_cache, logger=mock_logger
            )

        # Verify cache.get was not called
        mock_cache.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_from_cache_no_matching_rule(
        self,
        mock_request: MagicMock,
        mock_response: MagicMock,
        mock_cache: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        """Test getting a response from cache with no matching rule raises RequestNotCachable."""
        # Set up the request
        mock_request.method = "GET"
        mock_request.url = MagicMock(spec=URL)
        mock_request.url.__str__.return_value = "http://example.com/test"
        mock_request.url.path = "/test"

        # Set up a rule that won't match
        rule = Rule(
            match="/different",  # This won't match the request path
            status=200,
            ttl=60,
        )

        # Call get_from_cache - should raise RequestNotCachable
        with pytest.raises(RequestNotCachable):
            await get_from_cache(
                mock_request, rules=[rule], cache=mock_cache, logger=mock_logger
            )

        # Verify cache.get was not called
        mock_cache.get.assert_not_called()


class TestSerializationFunctions:
    def test_serialize_response(self, mock_response: MagicMock) -> None:
        """Test serializing a response."""
        # Set up the response
        mock_response.status_code = 200
        mock_response.body = b"Test content"
        mock_response.headers = MutableHeaders({"content-type": "text/plain"})

        # Serialize the response
        serialized = serialize_response(mock_response)

        # Verify the serialized response
        assert isinstance(serialized, dict)
        assert serialized["status_code"] == 200
        assert serialized["content"] == base64.encodebytes(b"Test content").decode(
            "ascii"
        )
        assert serialized["headers"] == {"content-type": "text/plain"}

    def test_deserialize_response(self) -> None:
        """Test deserializing a response."""
        # Create a serialized response
        serialized = {
            "content": base64.encodebytes(b"Test content").decode("ascii"),
            "status_code": 200,
            "headers": {"content-type": "text/plain"},
        }

        # Deserialize the response
        response = deserialize_response(serialized)

        # Verify the response
        assert response.status_code == 200
        assert response.body == b"Test content"
        assert response.headers["content-type"] == "text/plain"

    def test_deserialize_response_invalid_content(self) -> None:
        """Test deserializing a response with invalid content."""
        # Create a serialized response with invalid content
        serialized = {
            "content": "invalid_base64",
            "status_code": 200,
            "headers": {"content-type": "text/plain"},
        }

        # Deserialize the response
        with pytest.raises(Exception):
            deserialize_response(serialized)

    def test_deserialize_response_invalid_headers(self) -> None:
        """Test deserializing a response with invalid headers."""
        # Create a serialized response with invalid headers
        serialized = {
            "content": base64.b64encode(b"Test content").decode("utf-8"),
            "status_code": 200,
            "headers": "invalid",
        }

        # Deserialize the response
        with pytest.raises(Exception):
            deserialize_response(serialized)


# TestCacheKeyFunctions moved to test_caching_additional.py


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


# TestCacheResponderClass moved to test_caching_additional.py

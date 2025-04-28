"""Simplified tests for the FastBlocks caching."""

from unittest.mock import Mock

import pytest
from fastblocks.caching import (
    cachable_methods,
    cachable_status_codes,
    invalidating_methods,
)
from fastblocks.exceptions import RequestNotCachable, ResponseNotCachable


class TestCaching:
    def test_cachable_methods(self) -> None:
        assert "GET" in cachable_methods
        assert "HEAD" in cachable_methods

    def test_cachable_status_codes(self) -> None:
        assert 200 in cachable_status_codes
        assert 404 in cachable_status_codes

    def test_invalidating_methods(self) -> None:
        assert "POST" in invalidating_methods
        assert "DELETE" in invalidating_methods

    def test_request_not_cachable_exception(self) -> None:
        request: Mock = Mock()
        with pytest.raises(RequestNotCachable):
            raise RequestNotCachable(request)

    def test_response_not_cachable_exception(self) -> None:
        response: Mock = Mock()
        with pytest.raises(ResponseNotCachable):
            raise ResponseNotCachable(response)

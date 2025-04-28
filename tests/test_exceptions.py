"""Simplified tests for the FastBlocks exceptions."""

from unittest.mock import Mock

from fastblocks.exceptions import (
    DuplicateCaching,
    RequestNotCachable,
    ResponseNotCachable,
)


class TestExceptions:
    def test_duplicate_caching_exception_message(self) -> None:
        message: str = "Test exception message"
        exception: DuplicateCaching = DuplicateCaching(message)
        assert str(exception) == message

    def test_request_not_cachable_exception(self) -> None:
        request: Mock = Mock()
        exception: RequestNotCachable = RequestNotCachable(request)
        assert exception.request == request

    def test_response_not_cachable_exception(self) -> None:
        response: Mock = Mock()
        exception: ResponseNotCachable = ResponseNotCachable(response)
        assert exception.response == response

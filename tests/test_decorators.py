"""Simplified tests for the FastBlocks decorators."""

from unittest.mock import Mock, patch

from starlette.requests import Request
from fastblocks.decorators import cache_control, cached


class TestDecorators:
    def test_cached_decorator_creates_middleware(self) -> None:
        with patch("fastblocks.decorators.CacheMiddleware") as mock_cache_middleware:

            async def endpoint(request: Request) -> str:
                return "response"

            cached(cache=Mock())(endpoint)  # type: ignore

            mock_cache_middleware.assert_called_once()

    def test_cache_control_decorator_creates_middleware(self) -> None:
        with patch("fastblocks.decorators.CacheControlMiddleware") as mock_middleware:

            async def endpoint(request: Request) -> str:
                return "response"

            cache_control(max_age=300, public=True)(endpoint)  # type: ignore

            mock_middleware.assert_called_once()
            call_args = mock_middleware.call_args
            assert call_args is not None
            assert call_args[1]["max_age"] == 300
            assert call_args[1]["public"] is True

"""Simplified tests for the FastBlocks middleware."""

from unittest.mock import Mock, patch

import pytest
from fastblocks.exceptions import DuplicateCaching
from fastblocks.middleware import (
    CacheControlMiddleware,
    CacheMiddleware,
    ProcessTimeHeaderMiddleware,
)


class TestMiddleware:
    def test_process_time_middleware_initialization(self) -> None:
        with patch("fastblocks.middleware.Logger"):
            app = Mock()
            middleware = ProcessTimeHeaderMiddleware(app=app)

            assert middleware.app == app
            assert hasattr(middleware, "logger")

    def test_cache_middleware_initialization(self) -> None:
        with patch("fastblocks.middleware.depends.get") as mock_get:
            mock_cache = Mock()
            mock_get.return_value = mock_cache

            app = Mock()
            middleware = CacheMiddleware(app=app)

            assert middleware.app == app
            assert middleware.cache == mock_cache

    def test_cache_middleware_duplicate_initialization(self) -> None:
        with patch("fastblocks.middleware.depends.get") as mock_get:
            mock_cache = Mock()
            mock_get.return_value = mock_cache

            app = Mock()
            app.middleware = []
            middleware = CacheMiddleware(app=app)

            app.middleware.append(middleware)

            with pytest.raises(DuplicateCaching):
                CacheMiddleware(app=app)

    def test_cache_control_middleware_initialization(self) -> None:
        app = Mock()
        middleware = CacheControlMiddleware(
            app=app,
            max_age=300,
            public=True,
            no_cache=False,
            no_store=False,
            must_revalidate=False,
        )

        assert middleware.app == app
        assert middleware.max_age == 300
        assert middleware.public
        assert not middleware.no_cache
        assert not middleware.no_store
        assert not middleware.must_revalidate

    def test_cache_control_middleware_process_response(self) -> None:
        middleware = CacheControlMiddleware(
            app=Mock(),
            max_age=300,
            public=True,
        )

        response = Mock()
        response.headers = {}

        middleware.process_response(response)

        assert "Cache-Control" in response.headers
        assert response.headers["Cache-Control"] == "public, max-age=300"

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from fastblocks.exceptions import DuplicateCaching, MissingCaching
from fastblocks.middleware import CacheHelper, CacheMiddleware


class TestDuplicateCaching:
    def test_duplicate_caching_exception(self, basic_app: Starlette) -> None:
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()

        mock_hash = MagicMock()
        mock_hash.md5 = MagicMock(return_value="test_hash")

        with (
            patch("fastblocks.caching.hash", mock_hash),
            patch("fastblocks.caching.get_cache_key", AsyncMock(return_value=None)),
            patch("fastblocks.caching.get_from_cache", AsyncMock(return_value=None)),
            patch("fastblocks.caching.set_in_cache", AsyncMock()),
        ):
            app = CacheMiddleware(basic_app, cache=mock_cache)
            app = CacheMiddleware(app, cache=mock_cache)

            client = TestClient(app)

            with pytest.raises(DuplicateCaching) as excinfo:
                client.get("/")

            assert "Another `CacheMiddleware` was detected" in str(excinfo.value)


class TestMissingCaching:
    def test_missing_caching_exception(self, basic_app: Starlette) -> None:
        async def homepage(request: Request) -> PlainTextResponse:
            CacheHelper(request)
            return PlainTextResponse("Hello, world!")

        basic_app.routes.append(Route("/missing-cache", homepage))

        client = TestClient(basic_app)

        with pytest.raises(MissingCaching) as excinfo:
            client.get("/missing-cache")

        assert "No CacheMiddleware instance found" in str(excinfo.value)

    def test_incompatible_middleware_exception(self, basic_app: Starlette) -> None:
        async def homepage(request: Request) -> PlainTextResponse:
            request.scope["__starlette_caches__"] = "not a middleware"
            CacheHelper(request)
            return PlainTextResponse("Hello, world!")

        basic_app.routes.append(Route("/incompatible-middleware", homepage))

        client = TestClient(basic_app)

        with pytest.raises(MissingCaching) as excinfo:
            client.get("/incompatible-middleware")

        assert "incompatible middleware" in str(excinfo.value)

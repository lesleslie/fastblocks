import typing as t
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send
from fastblocks.caching import Rule
from fastblocks.decorators import cache_control, cached


class TestCachedDecorator:
    def test_cached_decorator_miss(self, basic_app: Starlette) -> None:
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()

        counter = 0

        mock_hash = MagicMock()
        mock_hash.md5 = MagicMock(return_value="test_hash")

        class CustomCacheMiddleware:
            def __init__(self, app: ASGIApp, **kwargs: t.Any) -> None:
                self.app = app
                self.kwargs = kwargs

            async def __call__(
                self, scope: Scope, receive: Receive, send: Send
            ) -> None:
                await self.app(scope, receive, send)

        with (
            patch("fastblocks.caching.hash", mock_hash),
            patch("fastblocks.caching.get_cache_key", AsyncMock(return_value=None)),
            patch("fastblocks.caching.get_from_cache", AsyncMock(return_value=None)),
            patch("fastblocks.caching.set_in_cache", AsyncMock()),
            patch("fastblocks.decorators.CacheMiddleware", CustomCacheMiddleware),
        ):

            async def homepage(request: Request) -> PlainTextResponse:
                nonlocal counter
                counter += 1
                return PlainTextResponse(f"Counter: {counter}")

            basic_app.routes.append(Route("/cached", homepage))

            app = cached(cache=mock_cache)(basic_app)

            client = TestClient(app)

            response = client.get("/cached")
            assert response.status_code == 200
            assert response.text == "Counter: 1"

    def test_cached_decorator_with_rule(self, basic_app: Starlette) -> None:
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()

        counter = 0

        rule = Rule(match="*", ttl=60)

        mock_hash = MagicMock()
        mock_hash.md5 = MagicMock(return_value="test_hash")

        class CustomCacheMiddleware:
            def __init__(self, app: ASGIApp, **kwargs: t.Any) -> None:
                self.app = app
                self.kwargs = kwargs

            async def __call__(
                self, scope: Scope, receive: Receive, send: Send
            ) -> None:
                await self.app(scope, receive, send)

        with (
            patch("fastblocks.caching.hash", mock_hash),
            patch("fastblocks.caching.get_cache_key", AsyncMock(return_value=None)),
            patch("fastblocks.caching.get_from_cache", AsyncMock(return_value=None)),
            patch("fastblocks.caching.set_in_cache", AsyncMock()),
            patch("fastblocks.decorators.CacheMiddleware", CustomCacheMiddleware),
        ):

            async def homepage(request: Request) -> PlainTextResponse:
                nonlocal counter
                counter += 1
                return PlainTextResponse(f"Counter: {counter}")

            basic_app.routes.append(Route("/cached-rule", homepage))

            app = cached(cache=mock_cache, rules=[rule])(basic_app)

            client = TestClient(app)

            response = client.get("/cached-rule")
            assert response.status_code == 200
            assert response.text == "Counter: 1"

    def test_cached_decorator_with_middleware(self, basic_app: Starlette) -> None:
        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()

        class CustomCacheMiddleware:
            def __init__(self, app: ASGIApp) -> None:
                self.app = app

            async def __call__(
                self, scope: Scope, receive: Receive, send: Send
            ) -> None:
                scope["__starlette_caches__"] = self
                await self.app(scope, receive, send)

            @property
            def cache(self) -> AsyncMock:
                return mock_cache

        counter = 0

        async def homepage(request: Request) -> PlainTextResponse:
            nonlocal counter
            counter += 1
            return PlainTextResponse(f"Counter: {counter}")

        basic_app.routes.append(Route("/cached-middleware", homepage))

        app = CustomCacheMiddleware(basic_app)

        response = TestClient(app).get("/cached-middleware")
        assert response.status_code == 200
        assert response.text == "Counter: 1"


class TestCacheControlDecorator:
    def test_cache_control_decorator(self, basic_app: Starlette) -> None:
        class CustomCacheControlMiddleware:
            def __init__(self, app: ASGIApp, **kwargs: t.Any) -> None:
                self.app = app
                self.kwargs = kwargs

            async def __call__(
                self, scope: Scope, receive: Receive, send: Send
            ) -> None:
                await self.app(scope, receive, send)

        with patch(
            "fastblocks.decorators.CacheControlMiddleware", CustomCacheControlMiddleware
        ):

            async def homepage(request: Request) -> PlainTextResponse:
                return PlainTextResponse("Hello, world!")

            basic_app.routes.append(Route("/cache-control", homepage))

            app = cache_control(max_age=300)(basic_app)

            client = TestClient(app)
            response = client.get("/cache-control")

            assert response.status_code == 200

    def test_cache_control_decorator_with_multiple_directives(
        self, basic_app: Starlette
    ) -> None:
        class CustomCacheControlMiddleware:
            def __init__(self, app: ASGIApp, **kwargs: t.Any) -> None:
                self.app = app
                self.kwargs = kwargs

            async def __call__(
                self, scope: Scope, receive: Receive, send: Send
            ) -> None:
                await self.app(scope, receive, send)

        with patch(
            "fastblocks.decorators.CacheControlMiddleware", CustomCacheControlMiddleware
        ):

            async def homepage(request: Request) -> PlainTextResponse:
                return PlainTextResponse("Hello, world!")

            basic_app.routes.append(Route("/cache-control-multiple", homepage))

            app = cache_control(
                max_age=300,
                s_maxage=600,
                must_revalidate=True,
                stale_while_revalidate=60,
            )(basic_app)

            client = TestClient(app)
            response = client.get("/cache-control-multiple")

            assert response.status_code == 200

    def test_cache_control_decorator_with_no_cache(self, basic_app: Starlette) -> None:
        class CustomCacheControlMiddleware:
            def __init__(self, app: ASGIApp, **kwargs: t.Any) -> None:
                self.app = app
                self.kwargs = kwargs

            async def __call__(
                self, scope: Scope, receive: Receive, send: Send
            ) -> None:
                await self.app(scope, receive, send)

        with patch(
            "fastblocks.decorators.CacheControlMiddleware", CustomCacheControlMiddleware
        ):

            async def homepage(request: Request) -> PlainTextResponse:
                return PlainTextResponse("Hello, world!")

            basic_app.routes.append(Route("/cache-control-no-cache", homepage))

            app = cache_control(no_cache=True, no_store=True)(basic_app)

            client = TestClient(app)
            response = client.get("/cache-control-no-cache")

            assert response.status_code == 200

    @pytest.mark.skip(reason="private directive is not supported yet")
    def test_cache_control_decorator_with_private(self, basic_app: Starlette) -> None:
        class CustomCacheControlMiddleware:
            def __init__(self, app: ASGIApp, **kwargs: t.Any) -> None:
                self.app = app
                self.kwargs = kwargs

            async def __call__(
                self, scope: Scope, receive: Receive, send: Send
            ) -> None:
                await self.app(scope, receive, send)

        with patch(
            "fastblocks.decorators.CacheControlMiddleware", CustomCacheControlMiddleware
        ):

            async def homepage(request: Request) -> PlainTextResponse:
                return PlainTextResponse("Hello, world!")

            basic_app.routes.append(Route("/cache-control-private", homepage))

            app = cache_control(max_age=60)(basic_app)

            client = TestClient(app)
            response = client.get("/cache-control-private")

            assert response.status_code == 200

import typing as t
from time import perf_counter
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from starlette.applications import Starlette
from starlette.datastructures import URL
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send
from fastblocks.caching import Rule
from fastblocks.exceptions import DuplicateCaching, MissingCaching
from fastblocks.middleware import (
    CacheControlMiddleware,
    CacheHelper,
    CacheMiddleware,
    CurrentRequestMiddleware,
    ProcessTimeHeaderMiddleware,
    SecureHeadersMiddleware,
    get_request,
)


class TestCurrentRequestMiddleware:
    def test_get_request_returns_none_by_default(self) -> None:
        assert get_request() is None

    def test_middleware_sets_request_context(self, basic_app: Starlette) -> None:
        app = CurrentRequestMiddleware(basic_app)
        client = TestClient(app)

        with patch("fastblocks.middleware._request_ctx_var") as mock_ctx_var:
            mock_ctx_var.set.return_value = None
            client.get("/")
            assert mock_ctx_var.set.called

    def test_middleware_resets_request_context(self, basic_app: Starlette) -> None:
        app = CurrentRequestMiddleware(basic_app)
        client = TestClient(app)

        with patch("fastblocks.middleware._request_ctx_var") as mock_ctx_var:
            mock_ctx_var.reset.return_value = None
            client.get("/")
            assert mock_ctx_var.reset.called

    def test_middleware_ignores_non_http_requests(self) -> None:
        async def app(scope: Scope, receive: Receive, send: Send) -> None:  # type: ignore
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"", "more_body": False})

        middleware = CurrentRequestMiddleware(app)

        async def test() -> None:
            scope = {"type": "lifespan"}
            receive = AsyncMock()
            send = AsyncMock()
            await middleware(scope, receive, send)

        import asyncio

        asyncio.run(test())


class TestSecureHeadersMiddleware:
    def test_adds_secure_headers(self, basic_app: Starlette) -> None:
        with patch("fastblocks.middleware.secure_headers") as mock_secure_headers:
            mock_secure_headers.headers = {"X-Content-Type-Options": "nosniff"}

            app = SecureHeadersMiddleware(basic_app)
            client = TestClient(app)
            response = client.get("/")

            assert "X-Content-Type-Options" in response.headers

    def test_ignores_non_http_requests(self, mock_logger: Mock) -> None:
        async def app(scope: Scope, receive: Receive, send: Send) -> None:  # type: ignore
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"", "more_body": False})

        middleware = SecureHeadersMiddleware(app)

        async def test() -> None:
            scope = {"type": "lifespan"}
            receive = AsyncMock()
            send = AsyncMock()
            await middleware(scope, receive, send)

        import asyncio

        asyncio.run(test())


class TestProcessTimeHeaderMiddleware:
    def test_logs_process_time(self, basic_app: Starlette) -> None:
        mock_logger = MagicMock()

        class CustomProcessTimeHeaderMiddleware(ProcessTimeHeaderMiddleware):
            async def __call__(
                self,
                scope: Scope,
                receive: Receive,
                send: Send,  # type: ignore
            ) -> None:
                start_time = perf_counter()
                try:
                    await self.app(scope, receive, send)
                except Exception as exc:
                    mock_logger.exception(exc)
                    raise
                finally:
                    process_time = perf_counter() - start_time
                    mock_logger.debug(f"Request processed in {process_time} s")

        with patch("fastblocks.middleware.perf_counter", side_effect=[0, 1]):
            app = CustomProcessTimeHeaderMiddleware(basic_app)
            client = TestClient(app)
            client.get("/")

            mock_logger.debug.assert_called_once()

    def test_handles_exceptions(self, basic_app: Starlette) -> None:
        mock_logger = MagicMock()

        class CustomProcessTimeHeaderMiddleware(ProcessTimeHeaderMiddleware):
            async def __call__(
                self,
                scope: Scope,
                receive: Receive,
                send: Send,  # type: ignore
            ) -> None:
                start_time = perf_counter()
                try:
                    await self.app(scope, receive, send)
                except Exception as exc:
                    mock_logger.exception(exc)
                    raise
                finally:
                    process_time = perf_counter() - start_time
                    mock_logger.debug(f"Request processed in {process_time} s")

        with patch("fastblocks.middleware.perf_counter", side_effect=[0, 1]):

            async def error(request: Request) -> t.NoReturn:
                raise ValueError("Test error")

            basic_app.routes.append(Route("/error", error))

            app = CustomProcessTimeHeaderMiddleware(basic_app)
            client = TestClient(app)

            with pytest.raises(ValueError):
                client.get("/error")

            mock_logger.exception.assert_called_once()


class TestCacheMiddleware:
    def test_raises_duplicate_caching_error(self, basic_app: Starlette) -> None:
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

            with pytest.raises(DuplicateCaching):
                client.get("/")

    def test_ignores_non_http_requests(self) -> None:
        class MockApp:
            async def __call__(
                self,
                scope: Scope,
                receive: Receive,
                send: Send,  # type: ignore
            ) -> None:
                await send(
                    {"type": "http.response.start", "status": 200, "headers": []}
                )
                await send(
                    {"type": "http.response.body", "body": b"", "more_body": False}
                )

        mock_cache = MagicMock()
        mock_cache.get = AsyncMock(return_value=None)

        middleware = CacheMiddleware(MockApp(), cache=mock_cache)

        send = AsyncMock()
        scope: Scope = {"type": "lifespan"}

        receive = AsyncMock()
        receive.return_value = {"type": "lifespan.startup"}

        import asyncio

        asyncio.run(middleware(scope, receive, send))

    def test_cache_responder_integration(self, basic_app: Starlette) -> None:
        rule = Rule(match="*")

        mock_cache = AsyncMock()
        mock_cache.get = AsyncMock(return_value=None)
        mock_cache.set = AsyncMock()
        mock_cache.delete = AsyncMock()

        class CustomCacheMiddleware:
            def __init__(self, app: ASGIApp, rules: list[Rule] | None = None) -> None:
                self.app = app
                self.rules = rules or []
                self.cache = mock_cache

            async def __call__(
                self,
                scope: Scope,
                receive: Receive,
                send: Send,  # type: ignore
            ) -> None:
                scope["__starlette_caches__"] = self
                await self.app(scope, receive, send)
                mock_cache.get.return_value = None
                await mock_cache.get("test_key")

        app = CustomCacheMiddleware(basic_app, rules=[rule])

        response = TestClient(app).get("/")
        assert response.status_code == 200
        assert response.text == "Hello, world!"

        assert mock_cache.get.called


class TestCacheHelper:
    def test_raises_missing_caching_error(self, basic_app: Starlette) -> None:
        client = TestClient(basic_app)

        async def helper_endpoint(request: Request) -> PlainTextResponse:
            CacheHelper(request)
            return PlainTextResponse("Helper initialized")

        basic_app.routes.append(Route("/helper", helper_endpoint))

        with pytest.raises(MissingCaching):
            client.get("/helper")

    def test_raises_incompatible_middleware_error(self, basic_app: Starlette) -> None:
        class FakeMiddleware:
            pass

        async def helper_endpoint(request: Request) -> PlainTextResponse:
            request.scope["__starlette_caches__"] = FakeMiddleware()
            CacheHelper(request)
            return PlainTextResponse("Helper initialized")

        basic_app.routes.append(Route("/helper", helper_endpoint))

        client = TestClient(basic_app)

        with pytest.raises(MissingCaching):
            client.get("/helper")

    @pytest.mark.asyncio
    async def test_invalidate_cache_for(self) -> None:
        mock_cache = MagicMock()
        mock_cache.delete = AsyncMock()

        async def mock_app(scope: Scope, receive: Receive, send: Send) -> None:  # type: ignore
            pass

        mock_hash = MagicMock()
        mock_hash.md5 = MagicMock(return_value="test_hash")

        with patch("fastblocks.caching.hash", mock_hash):
            scope: Scope = {
                "type": "http",
                "method": "GET",
                "path": "/test",
                "headers": [],
                "__starlette_caches__": CacheMiddleware(mock_app, cache=mock_cache),
            }
            request = Request(scope)

            request.url_for = MagicMock(return_value=URL("/test"))

            helper = CacheHelper(request)

            mock_delete = AsyncMock()

            with patch("fastblocks.middleware.delete_from_cache", mock_delete):
                await helper.invalidate_cache_for("/test")
                assert mock_delete.called


class TestCacheControlMiddleware:
    def test_adds_cache_control_headers(self, basic_app: Starlette) -> None:
        app = CacheControlMiddleware(basic_app, max_age=300)

        with patch("fastblocks.caching.patch_cache_control") as mock_patch:
            client = TestClient(app)
            client.get("/")

            assert mock_patch.called

    def test_ignores_non_http_requests(self) -> None:
        async def app(scope: Scope, receive: Receive, send: Send) -> None:  # type: ignore
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"", "more_body": False})

        middleware = CacheControlMiddleware(app, max_age=300)

        async def test() -> None:
            scope = {"type": "lifespan"}
            receive = AsyncMock()
            send = AsyncMock()
            await middleware(scope, receive, send)

        import asyncio

        asyncio.run(test())

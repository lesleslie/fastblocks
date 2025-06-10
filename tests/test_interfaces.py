"""Standardized test interfaces for FastBlocks components."""

from collections.abc import Callable
from typing import Any
from unittest.mock import Mock, patch

import pytest
from acb.depends import depends
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.types import Receive, Scope, Send
from fastblocks.applications import FastBlocks
from fastblocks.decorators import cache_control, cached
from fastblocks.exceptions import (
    DuplicateCaching,
    RequestNotCachable,
    ResponseNotCachable,
)
from fastblocks.middleware import (
    CacheControlMiddleware,
    CacheMiddleware,
    ProcessTimeHeaderMiddleware,
)


class ApplicationTestInterface:
    def test_app_inheritance(self, app: FastBlocks) -> None:
        assert isinstance(app, Starlette)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_app_middleware(self, app: FastBlocks) -> None:
        assert hasattr(app, "middleware_stack")

    def test_app_models(self, app: FastBlocks) -> None:
        assert hasattr(app, "models")

    def test_app_templates(self, app: FastBlocks) -> None:
        assert hasattr(app, "templates")

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_app_basic_request(self, client: TestClient) -> None:
        response = client.get("/test")
        assert response.status_code == 200

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_app_not_found(self, client: TestClient) -> None:
        response = client.get("/nonexistent")
        assert response.status_code == 404


class MiddlewareTestInterface:
    def test_process_time_middleware(self, app: FastBlocks, client: TestClient) -> None:
        app.add_middleware(ProcessTimeHeaderMiddleware)

        with patch("fastblocks.middleware.Logger") as mock_logger:
            response = client.get("/")
            assert response.status_code == 200
            mock_logger.debug.assert_called()

    def test_cache_middleware(self, app: FastBlocks) -> None:
        app.add_middleware(CacheMiddleware)

        with pytest.raises(Exception) as exc_info:
            app.add_middleware(CacheMiddleware)
        assert "DuplicateCaching" in str(exc_info.value)

    def test_cache_control_middleware(
        self, app: FastBlocks, client: TestClient
    ) -> None:
        app.add_middleware(CacheControlMiddleware, max_age=300, public=True)

        response = client.get("/")
        assert "Cache-Control" in response.headers
        assert "public" in response.headers["Cache-Control"]
        assert "max-age=300" in response.headers["Cache-Control"]


class DecoratorTestInterface:
    @pytest.mark.anyio(backends=["asyncio"])
    async def test_cached_decorator(self, app: FastBlocks, client: TestClient) -> None:
        with patch("fastblocks.decorators.CacheMiddleware") as mock_cache_middleware:
            mock_instance = Mock()
            mock_cache_middleware.return_value = mock_instance

            @app.route("/cached")
            @cached(cache=Mock())  # type: ignore
            async def cached_endpoint(request: Any) -> PlainTextResponse:  # noqa # type: ignore
                return PlainTextResponse("Original response")

            response = client.get("/cached")
            assert response.status_code == 200
            mock_cache_middleware.assert_called_once()

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_cache_control_decorator(
        self, app: FastBlocks, client: TestClient
    ) -> None:
        with patch("fastblocks.decorators.CacheControlMiddleware") as mock_middleware:
            mock_instance = Mock()
            mock_middleware.return_value = mock_instance

            @app.route("/cache-control")
            @cache_control(max_age=300, public=True)  # type: ignore
            async def cache_control_endpoint(request: Any) -> PlainTextResponse:  # noqa # type: ignore
                return PlainTextResponse("Cache-controlled response")

            response = client.get("/cache-control")
            assert response.status_code == 200
            mock_middleware.assert_called_once()


class CachingTestInterface:
    def test_cachable_methods(self) -> None:
        from fastblocks.caching import cachable_methods

        assert "GET" in cachable_methods
        assert "HEAD" in cachable_methods

    def test_cachable_status_codes(self) -> None:
        from fastblocks.caching import cachable_status_codes

        assert 200 in cachable_status_codes
        assert 404 in cachable_status_codes

    def test_invalidating_methods(self) -> None:
        from fastblocks.caching import invalidating_methods

        assert "POST" in invalidating_methods
        assert "DELETE" in invalidating_methods

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_request_not_cachable_exception(self) -> None:
        request = Mock()
        with pytest.raises(RequestNotCachable):
            raise RequestNotCachable(request)

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_response_not_cachable_exception(self) -> None:
        response = Mock()
        with pytest.raises(ResponseNotCachable):
            raise ResponseNotCachable(response)


class ExceptionTestInterface:
    def test_duplicate_caching_exception(self) -> None:
        with pytest.raises(DuplicateCaching):
            raise DuplicateCaching("Test exception")

    def test_request_not_cachable_exception(self) -> None:
        request = Mock()
        with pytest.raises(RequestNotCachable):
            raise RequestNotCachable(request)

    def test_response_not_cachable_exception(self) -> None:
        response = Mock()
        with pytest.raises(ResponseNotCachable):
            raise ResponseNotCachable(response)


class MockApp(FastBlocks):
    def __init__(self) -> None:
        super().__init__()
        self.debug: bool = True
        self.routes: list[Route] = []
        # Use type: ignore to suppress the incompatible method override warning
        self.middleware: list[Middleware] = []  # type: ignore
        self.exception_handlers: dict[Any, Callable[..., Any]] = {}
        self.models: Any = depends.get()
        self.templates: Any | None = None
        self.user_middleware: list[Middleware] = []

    async def post_startup(self) -> None:
        pass


class MockMiddleware:
    def __init__(self, app: Any) -> None:
        self.app: Any = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        await self.app(scope, receive, send)


class StorageTestInterface:
    @pytest.mark.anyio(backends=["asyncio"])
    async def test_storage_init(self, storage: Any) -> None:
        assert hasattr(storage, "init")
        assert hasattr(storage, "_initialized")
        assert storage._initialized is True

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_storage_exists(self, storage: Any) -> None:
        assert hasattr(storage, "exists")

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_storage_open(self, storage: Any) -> None:
        assert hasattr(storage, "open")

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_storage_write(self, storage: Any) -> None:
        assert hasattr(storage, "write")

    @pytest.mark.anyio(backends=["asyncio"])
    async def test_storage_delete(self, storage: Any) -> None:
        assert hasattr(storage, "delete")


class MockCache:
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        self._data[key] = value
        return True

    async def delete(self, key: str) -> int:
        if key in self._data:
            del self._data[key]
            return 1
        return 0

    async def exists(self, key: str) -> bool:
        return key in self._data

    async def clear(self, namespace: str | None = None) -> bool:
        if namespace:
            keys_to_delete = [
                k for k in self._data.keys() if k.startswith(f"{namespace}:")
            ]
            for key in keys_to_delete:
                del self._data[key]
        else:
            self._data.clear()
        return True

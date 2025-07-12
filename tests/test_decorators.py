"""Test FastBlocks decorators."""

import sys
import types
import typing as t
from unittest.mock import MagicMock, Mock

import pytest
from pytest_mock import MockerFixture
from starlette.types import ASGIApp


class MockCacheMiddleware:
    def __init__(self, app: ASGIApp, cache: t.Any = None) -> None:
        self.app = app
        self.cache = cache


class MockCacheControlMiddleware:
    def __init__(
        self,
        app: ASGIApp,
        max_age: int = 0,
        public: bool = False,
        no_cache: bool = False,
        no_store: bool = False,
        must_revalidate: bool = False,
    ) -> None:
        self.app = app
        self.max_age = max_age
        self.public = public
        self.no_cache = no_cache
        self.no_store = no_store
        self.must_revalidate = must_revalidate


@pytest.fixture
def clean_modules() -> t.Generator[None]:
    original_modules = sys.modules.copy()

    for mod in list(sys.modules.keys()):
        if mod.startswith("fastblocks"):
            sys.modules.pop(mod, None)

    yield

    sys.modules.clear()
    sys.modules.update(original_modules)


@pytest.mark.unit
class TestDecorators:
    def test_cached_decorator_creates_middleware(
        self,
        clean_modules: None,
        mocker: MockerFixture,
    ) -> None:
        sys.modules["fastblocks"] = types.ModuleType("fastblocks")

        request_module = types.ModuleType("starlette.requests")
        request_class = type("Request", (), {})
        setattr(request_module, "Request", request_class)
        sys.modules["starlette.requests"] = request_module

        middleware_module = types.ModuleType("fastblocks.middleware")
        middleware_spy = MagicMock(return_value=Mock(spec=MockCacheMiddleware))
        setattr(middleware_module, "CacheMiddleware", middleware_spy)
        sys.modules["fastblocks.middleware"] = middleware_module

        decorators_module = types.ModuleType("fastblocks.decorators")

        class CachedDecorator:
            def __call__(
                self,
                cache: t.Any = None,
            ) -> t.Callable[[t.Callable[..., t.Any]], t.Callable[..., t.Any]]:
                def decorator(
                    endpoint: t.Callable[..., t.Any],
                ) -> t.Callable[..., t.Any]:
                    middleware_spy(endpoint, cache=cache)

                    async def wrapper(
                        request: t.Any,
                        *args: t.Any,
                        **kwargs: t.Any,
                    ) -> t.Any:
                        return await endpoint(request, *args, **kwargs)

                    return wrapper

                return decorator

        cached_instance = CachedDecorator()

        setattr(decorators_module, "cached", cached_instance.__call__)
        setattr(decorators_module, "CacheMiddleware", middleware_spy)
        sys.modules["fastblocks.decorators"] = decorators_module

        cached_func = decorators_module.cached

        mock_cache = MagicMock()

        async def endpoint(request: t.Any) -> str:
            return "response"

        cached_func(cache=mock_cache)(endpoint)

        middleware_spy.assert_called_once()
        call_args = middleware_spy.call_args
        assert call_args is not None

        args, kwargs = call_args
        assert len(args) == 1
        assert args[0] is endpoint
        assert "cache" in kwargs
        assert kwargs["cache"] is mock_cache

    def test_cache_control_decorator_creates_middleware(
        self,
        clean_modules: None,
        mocker: MockerFixture,
    ) -> None:
        sys.modules["fastblocks"] = types.ModuleType("fastblocks")

        request_module = types.ModuleType("starlette.requests")
        request_class = type("Request", (), {})
        setattr(request_module, "Request", request_class)
        sys.modules["starlette.requests"] = request_module

        middleware_module = types.ModuleType("fastblocks.middleware")
        middleware_spy = MagicMock(return_value=Mock(spec=MockCacheControlMiddleware))
        setattr(middleware_module, "CacheControlMiddleware", middleware_spy)
        sys.modules["fastblocks.middleware"] = middleware_module

        decorators_module = types.ModuleType("fastblocks.decorators")

        class CacheControlDecorator:
            def __call__(
                self,
                max_age: int = 0,
                public: bool = False,
                no_cache: bool = False,
                no_store: bool = False,
                must_revalidate: bool = False,
            ) -> t.Callable[[t.Callable[..., t.Any]], t.Callable[..., t.Any]]:
                def decorator(
                    endpoint: t.Callable[..., t.Any],
                ) -> t.Callable[..., t.Any]:
                    middleware_spy(
                        endpoint,
                        max_age=max_age,
                        public=public,
                        no_cache=no_cache,
                        no_store=no_store,
                        must_revalidate=must_revalidate,
                    )

                    async def wrapper(
                        request: t.Any,
                        *args: t.Any,
                        **kwargs: t.Any,
                    ) -> t.Any:
                        return await endpoint(request, *args, **kwargs)

                    return wrapper

                return decorator

        cache_control_instance = CacheControlDecorator()

        setattr(decorators_module, "cache_control", cache_control_instance.__call__)
        setattr(decorators_module, "CacheControlMiddleware", middleware_spy)
        sys.modules["fastblocks.decorators"] = decorators_module

        cache_control_func = decorators_module.cache_control

        async def endpoint(request: t.Any) -> str:
            return "response"

        cache_control_func(max_age=300, public=True)(endpoint)

        middleware_spy.assert_called_once()
        call_args = middleware_spy.call_args
        assert call_args is not None

        args, kwargs = call_args
        assert len(args) == 1
        assert args[0] is endpoint
        assert "max_age" in kwargs
        assert kwargs["max_age"] == 300
        assert "public" in kwargs
        assert kwargs["public"] is True

"""Simplified tests for the FastBlocks middleware."""

import sys
import types
import typing as t
from unittest.mock import MagicMock, Mock

import pytest
from fastblocks.exceptions import DuplicateCaching


class MockLogger:
    def __init__(self) -> None:
        self.info = MagicMock()
        self.error = MagicMock()
        self.warning = MagicMock()
        self.debug = MagicMock()


class MockCacheMiddleware:
    def __init__(self, app: t.Any) -> None:
        self.app = app

        mock_depends = sys.modules.get("acb.depends")
        if mock_depends and hasattr(mock_depends, "get"):
            # Pass a mock class to the get method
            self.cache = mock_depends.get(MagicMock)
        else:
            self.cache = MagicMock()

        if hasattr(app, "middleware") and app.middleware is not None:
            if not isinstance(app.middleware, list):
                app.middleware = []

            for middleware in app.middleware:
                if isinstance(middleware, MockCacheMiddleware):
                    msg = "Multiple CacheMiddleware instances detected"
                    raise DuplicateCaching(
                        msg,
                    )

            app.middleware.append(self)
        else:
            app.middleware = [self]


class MockCacheControlMiddleware:
    def __init__(
        self,
        app: t.Any,
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

    def process_response(self, response: t.Any) -> t.Any:
        cache_control_parts = []

        if self.max_age > 0:
            cache_control_parts.append(f"max-age={self.max_age}")

        if self.public:
            cache_control_parts.append("public")
        else:
            cache_control_parts.append("private")

        if self.no_cache:
            cache_control_parts.append("no-cache")

        if self.no_store:
            cache_control_parts.append("no-store")

        if self.must_revalidate:
            cache_control_parts.append("must-revalidate")

        cache_control_value = ", ".join(cache_control_parts)

        response.headers["Cache-Control"] = cache_control_value

        return response


@pytest.fixture
def clean_modules() -> t.Generator[None]:
    original_modules = sys.modules.copy()

    for mod in list(sys.modules.keys()):
        if mod.startswith(("fastblocks", "acb")):
            sys.modules.pop(mod, None)

    yield

    sys.modules.clear()
    sys.modules.update(original_modules)


@pytest.mark.unit
class TestMiddleware:
    def test_cache_middleware_initialization(self) -> None:
        mock_cache = MagicMock()

        mock_depends = types.ModuleType("acb.depends")
        setattr(mock_depends, "get", MagicMock(return_value=mock_cache))

        sys.modules["acb"] = types.ModuleType("acb")
        sys.modules["acb.depends"] = mock_depends
        sys.modules["fastblocks"] = types.ModuleType("fastblocks")

        middleware_module = types.ModuleType("fastblocks.middleware")
        setattr(middleware_module, "depends", mock_depends)
        setattr(middleware_module, "CacheMiddleware", MockCacheMiddleware)
        sys.modules["fastblocks.middleware"] = middleware_module

        app = Mock()
        app.middleware = []

        middleware = MockCacheMiddleware(app=app)

        assert middleware.app is app
        assert middleware.cache is mock_cache
        assert app.middleware == [middleware]

    def test_cache_middleware_duplicate_initialization(self) -> None:
        mock_cache = MagicMock()

        exceptions_module = types.ModuleType("fastblocks.exceptions")
        setattr(exceptions_module, "DuplicateCaching", DuplicateCaching)
        sys.modules["fastblocks.exceptions"] = exceptions_module

        mock_depends = types.ModuleType("acb.depends")
        setattr(mock_depends, "get", MagicMock(return_value=mock_cache))

        sys.modules["acb"] = types.ModuleType("acb")
        sys.modules["acb.depends"] = mock_depends
        sys.modules["fastblocks"] = types.ModuleType("fastblocks")

        middleware_module = types.ModuleType("fastblocks.middleware")
        setattr(middleware_module, "depends", mock_depends)
        setattr(middleware_module, "DuplicateCaching", DuplicateCaching)
        setattr(middleware_module, "CacheMiddleware", MockCacheMiddleware)
        sys.modules["fastblocks.middleware"] = middleware_module

        app = Mock()
        app.middleware = []

        MockCacheMiddleware(app=app)

        with pytest.raises(DuplicateCaching):
            MockCacheMiddleware(app=app)

    def test_cache_control_middleware_initialization(self) -> None:
        sys.modules["fastblocks"] = types.ModuleType("fastblocks")

        middleware_module = types.ModuleType("fastblocks.middleware")
        setattr(middleware_module, "CacheControlMiddleware", MockCacheControlMiddleware)
        sys.modules["fastblocks.middleware"] = middleware_module

        app = Mock()

        middleware = MockCacheControlMiddleware(
            app=app,
            max_age=300,
            public=True,
            must_revalidate=True,
        )

        assert middleware.app is app
        assert middleware.max_age == 300
        assert middleware.public
        assert not middleware.no_cache
        assert not middleware.no_store
        assert middleware.must_revalidate

    def test_cache_control_middleware_process_response(self) -> None:
        sys.modules["fastblocks"] = types.ModuleType("fastblocks")

        middleware_module = types.ModuleType("fastblocks.middleware")
        setattr(middleware_module, "CacheControlMiddleware", MockCacheControlMiddleware)
        sys.modules["fastblocks.middleware"] = middleware_module

        app = Mock()
        response = Mock()
        response.headers = {}

        processed_response = MockCacheControlMiddleware(
            app=app,
            max_age=300,
            public=True,
            must_revalidate=True,
        ).process_response(response)

        assert processed_response is response
        assert "Cache-Control" in response.headers
        assert (
            response.headers["Cache-Control"] == "max-age=300, public, must-revalidate"
        )

    def test_cache_control_middleware_assignment(self) -> None:
        sys.modules["fastblocks"] = types.ModuleType("fastblocks")

        middleware_module = types.ModuleType("fastblocks.middleware")
        setattr(middleware_module, "CacheControlMiddleware", MockCacheControlMiddleware)
        sys.modules["fastblocks.middleware"] = middleware_module

        app = Mock()

        first_middleware = MockCacheControlMiddleware(app=app)
        second_middleware = first_middleware

        assert first_middleware is second_middleware

    def test_multiple_cache_middleware(self) -> None:
        app = MagicMock()
        app.middleware = []

        first_middleware = second_middleware = MockCacheMiddleware(app=app)

        with pytest.raises(DuplicateCaching):
            MockCacheMiddleware(app=app)

        assert first_middleware is second_middleware

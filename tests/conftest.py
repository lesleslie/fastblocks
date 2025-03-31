import sys
import typing as t
from unittest.mock import AsyncMock, MagicMock, Mock

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette.types import ASGIApp, Receive, Scope, Send


class MockConfig:  # type: ignore
    class Debug:
        fastblocks = False
        production = True

    debug = Debug()
    deployed = True

    class App:
        name = "test_app"
        secret_key = MagicMock()
        secret_key.get_secret_value.return_value = "test_secret"

    class Auth:
        token_id = None

    app = App()
    auth = Auth()


sys.modules["msgspec"] = MagicMock()  # type: ignore
sys.modules["msgspec.yaml"] = MagicMock()  # type: ignore
sys.modules["msgspec.yaml"].decode = MagicMock(return_value={})  # type: ignore

mock_acb = MagicMock()  # type: ignore
mock_acb.register_pkg = MagicMock()  # type: ignore
sys.modules["acb"] = mock_acb  # type: ignore
sys.modules["acb.config"] = MagicMock()  # type: ignore
sys.modules["acb.config"].Config = MockConfig  # type: ignore

mock_adapters = MagicMock()  # type: ignore


def mock_import_adapter(name: str | None = None) -> t.Any:
    if name is None:
        logger = MagicMock()  # type: ignore
        logger.debug = MagicMock()  # type: ignore
        logger.info = MagicMock()  # type: ignore
        logger.warning = MagicMock()  # type: ignore
        logger.error = MagicMock()  # type: ignore
        logger.critical = MagicMock()  # type: ignore

        cache = AsyncMock()  # type: ignore
        cache.get = AsyncMock(return_value=None)  # type: ignore
        cache.set = AsyncMock()  # type: ignore
        cache.delete = AsyncMock()  # type: ignore
        cache.delete_from_cache = AsyncMock()  # type: ignore
        cache.invalidate_cache_for = AsyncMock()  # type: ignore

        return logger, cache
    elif name == "cache":
        cache = AsyncMock()  # type: ignore
        cache.get = AsyncMock(return_value=None)  # type: ignore
        cache.set = AsyncMock()  # type: ignore
        cache.delete = AsyncMock()  # type: ignore
        cache.delete_from_cache = AsyncMock()  # type: ignore
        cache.invalidate_cache_for = AsyncMock()  # type: ignore
        return cache
    elif name == "logger":  # type: ignore
        logger = MagicMock()  # type: ignore
        logger.debug = MagicMock()  # type: ignore
        logger.info = MagicMock()  # type: ignore
        logger.warning = MagicMock()  # type: ignore
        logger.error = MagicMock()  # type: ignore
        logger.critical = MagicMock()  # type: ignore
        return logger
    return MagicMock()  # type: ignore


mock_adapters.import_adapter = mock_import_adapter  # type: ignore
mock_adapters.get_installed_adapter = MagicMock(return_value=False)  # type: ignore
sys.modules["acb.adapters"] = mock_adapters  # type: ignore

sys.modules["acb.adapters.logger"] = MagicMock()  # type: ignore
sys.modules["acb.adapters.logger.loguru"] = MagicMock()  # type: ignore
sys.modules["acb.adapters.logger.loguru"].InterceptHandler = MagicMock()  # type: ignore

mock_depends = MagicMock()  # type: ignore
mock_depends.depends = MagicMock()  # type: ignore
mock_depends.depends.inject = lambda f: f  # type: ignore

mock_templates = MagicMock()  # type: ignore
mock_templates.app = MagicMock()  # type: ignore
mock_templates.app.render_template = AsyncMock()  # type: ignore


def mock_get(cls: t.Any = None) -> t.Any:  # type: ignore
    if cls is None:
        return mock_templates
    return MagicMock()  # type: ignore


mock_depends.depends.get = mock_get  # type: ignore
sys.modules["acb.depends"] = mock_depends  # type: ignore

mock_actions = MagicMock()  # type: ignore
mock_actions.hash = MagicMock()  # type: ignore


def mock_hash(*args: t.Any, **kwargs: t.Any) -> str:
    return "mocked_hash_value"


def mock_md5(*args: t.Any, **kwargs: t.Any) -> str:
    return "mocked_md5_hash"


mock_actions.hash.hash = mock_hash  # type: ignore
mock_actions.hash.md5 = mock_md5  # type: ignore
sys.modules["acb.actions"] = mock_actions  # type: ignore
sys.modules["acb.actions.hash"] = mock_actions.hash  # type: ignore

sys.modules["starception"] = MagicMock()  # type: ignore

mock_htmx = MagicMock()  # type: ignore
mock_htmx.HtmxMiddleware = MagicMock()  # type: ignore
mock_htmx.HtmxRequest = MagicMock()  # type: ignore
sys.modules["asgi_htmx"] = mock_htmx  # type: ignore

mock_logfire = MagicMock()  # type: ignore
mock_logfire.instrument_starlette = MagicMock()  # type: ignore
sys.modules["logfire"] = mock_logfire  # type: ignore

mock_secure = MagicMock()  # type: ignore
mock_secure.Secure = MagicMock()  # type: ignore
sys.modules["secure"] = mock_secure  # type: ignore

mock_brotli = MagicMock()  # type: ignore
mock_brotli.BrotliMiddleware = MagicMock()  # type: ignore
sys.modules["brotli_asgi"] = mock_brotli  # type: ignore

mock_csrf = MagicMock()  # type: ignore
mock_csrf.middleware = MagicMock()  # type: ignore
mock_csrf.middleware.CSRFMiddleware = MagicMock()  # type: ignore
sys.modules["starlette_csrf"] = mock_csrf  # type: ignore
sys.modules["starlette_csrf.middleware"] = mock_csrf.middleware  # type: ignore


@pytest.fixture
def mock_config() -> MockConfig:  # type: ignore
    return MockConfig()


@pytest.fixture
def mock_logger() -> Mock:
    return MagicMock()


@pytest.fixture
def test_middleware() -> Middleware:
    class TestMiddleware:
        __name__ = "TestMiddleware"

        def __init__(self, app: ASGIApp, param: str = "default") -> None:
            self.app = app
            self.param = param

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:  # type: ignore
            await self.app(scope, receive, send)

    return Middleware(TestMiddleware, param="test")


@pytest.fixture
def exception_handler() -> t.Callable[[Request, Exception], t.Awaitable[Response]]:
    async def custom_handler(request: Request, exc: Exception) -> Response:
        return PlainTextResponse(f"Custom handler: {exc}", status_code=500)

    return custom_handler


@pytest.fixture
def test_lifespan() -> t.Callable[[t.Any], t.AsyncGenerator[None, None]]:  # type: ignore
    async def lifespan(app: t.Any) -> t.AsyncGenerator[None, None]:  # type: ignore
        yield

    return lifespan


@pytest.fixture
def mock_cache() -> AsyncMock:  # type: ignore
    cache = AsyncMock()  # type: ignore
    cache.get = AsyncMock(return_value=None)  # type: ignore
    cache.set = AsyncMock()  # type: ignore
    cache.delete = AsyncMock()  # type: ignore
    cache.delete_from_cache = AsyncMock()  # type: ignore
    cache.invalidate_cache_for = AsyncMock()  # type: ignore
    return cache


@pytest.fixture
def basic_app() -> Starlette:  # type: ignore
    async def homepage(request: Request) -> PlainTextResponse:
        return PlainTextResponse("Hello, world!")

    async def json_endpoint(request: Request) -> JSONResponse:
        return JSONResponse({"message": "Hello, world!"})

    async def error_endpoint(request: Request) -> t.NoReturn:
        raise ValueError("Test error")

    routes: list[Route] = [
        Route("/", homepage),
        Route("/json", json_endpoint),
        Route("/error", error_endpoint),
    ]

    app = Starlette(routes=routes)
    return app


@pytest.fixture
def test_client(basic_app: Starlette) -> TestClient:  # type: ignore
    client = TestClient(basic_app)
    return client

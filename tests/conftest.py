import typing as t
from collections.abc import Awaitable, Callable
from unittest.mock import MagicMock

import pytest
from acb.config import Config
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response
from starlette.types import ASGIApp, Receive, Scope, Send


@pytest.fixture
def mock_config() -> MagicMock:
    config = MagicMock(spec=Config)
    config.debug.fastblocks = False
    config.deployed = True
    config.debug.production = True
    return config


@pytest.fixture
def mock_logger() -> MagicMock:
    return MagicMock()


@pytest.fixture
def test_middleware() -> Middleware:
    class TestMiddleware:
        def __init__(self, app: ASGIApp, param: str = "default") -> None:
            self.app = app
            self.param = param

        async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
            await self.app(scope, receive, send)

    return Middleware(TestMiddleware, param="test")


@pytest.fixture
def exception_handler() -> Callable[[Request, Exception], Awaitable[Response]]:
    async def custom_handler(request: Request, exc: Exception) -> Response:
        return PlainTextResponse(f"Custom handler: {exc}", status_code=500)

    return custom_handler


@pytest.fixture
def test_lifespan() -> Callable[[t.Any], t.AsyncGenerator[None, None]]:
    async def lifespan(app: t.Any) -> t.AsyncGenerator[None, None]:
        yield

    return lifespan

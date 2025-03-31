import typing as t
from unittest.mock import MagicMock, patch

from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp, Receive, Scope, Send
from fastblocks.applications import FastBlocks
from fastblocks.exceptions import handle_exception


class TestFastBlocks:
    @patch("fastblocks.applications.install_error_handler")
    @patch("fastblocks.applications.set_editor")
    @patch("fastblocks.applications.depends.get")
    def test_initialize_fastblocks_with_defaults(
        self,
        mock_depends_get: MagicMock,
        mock_set_editor: MagicMock,
        mock_install_error_handler: MagicMock,
        mock_config: MagicMock,
    ) -> None:
        mock_depends_get.return_value = {}

        app = FastBlocks(config=mock_config)

        assert app.debug is mock_config.debug.fastblocks
        assert app.exception_handlers == {404: handle_exception, 500: handle_exception}
        assert app.user_middleware == []
        assert app.models == {}
        assert app.templates is None
        mock_set_editor.assert_called_once_with("pycharm")
        mock_install_error_handler.assert_not_called()

    @patch("fastblocks.applications.install_error_handler")
    @patch("fastblocks.applications.set_editor")
    @patch("fastblocks.applications.depends.get")
    def test_initialize_with_custom_middleware(
        self,
        mock_depends_get: MagicMock,
        mock_set_editor: MagicMock,
        mock_install_error_handler: MagicMock,
        mock_config: MagicMock,
        test_middleware: Middleware,
    ) -> None:
        mock_depends_get.return_value = {}

        app = FastBlocks(middleware=[test_middleware], config=mock_config)

        assert app.user_middleware == [test_middleware]
        assert len(app.user_middleware) == 1
        assert app.user_middleware[0].cls.__name__ == "TestMiddleware"  # type: ignore
        assert app.user_middleware[0].kwargs == {"param": "test"}

    @patch("fastblocks.applications.install_error_handler")
    @patch("fastblocks.applications.set_editor")
    @patch("fastblocks.applications.depends.get")
    def test_initialize_with_custom_exception_handlers(
        self,
        mock_depends_get: MagicMock,
        mock_set_editor: MagicMock,
        mock_install_error_handler: MagicMock,
        mock_config: MagicMock,
        exception_handler: t.Callable[[Request, Exception], t.Awaitable[Response]],
    ) -> None:
        mock_depends_get.return_value = {}
        custom_handlers = {404: exception_handler, 500: exception_handler}

        app = FastBlocks(exception_handlers=custom_handlers, config=mock_config)

        assert app.exception_handlers == custom_handlers
        assert app.exception_handlers[404] == exception_handler
        assert app.exception_handlers[500] == exception_handler

    @patch("fastblocks.applications.install_error_handler")
    @patch("fastblocks.applications.set_editor")
    @patch("fastblocks.applications.depends.get")
    def test_initialize_with_custom_lifespan(
        self,
        mock_depends_get: MagicMock,
        mock_set_editor: MagicMock,
        mock_install_error_handler: MagicMock,
        mock_config: MagicMock,
        test_lifespan: t.Callable[[t.Any], t.AsyncGenerator[None, None]],
    ) -> None:
        mock_depends_get.return_value = {}

        app = FastBlocks(lifespan=test_lifespan, config=mock_config)

        assert app is not None

    @patch("fastblocks.applications.middlewares")
    @patch("fastblocks.applications.ServerErrorMiddleware")
    @patch("fastblocks.applications.ExceptionMiddleware")
    def test_build_middleware_stack_correctly(
        self,
        mock_exception_middleware: MagicMock,
        mock_server_error_middleware: MagicMock,
        mock_middlewares: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        app = MagicMock(spec=FastBlocks)
        app.debug = False
        app.exception_handlers = {404: handle_exception, 500: handle_exception}
        app.user_middleware = []
        app.router = MagicMock()

        class Middleware1:
            def __init__(self, app: ASGIApp, **kwargs: t.Any) -> None:
                self.app: ASGIApp = app
                self.kwargs = kwargs

            async def __call__(
                self, scope: Scope, receive: Receive, send: Send
            ) -> None:  # type: ignore
                await self.app(scope, receive, send)

        Middleware1.__name__ = "Middleware1"

        class Middleware2:
            def __init__(self, app: ASGIApp, **kwargs: t.Any) -> None:
                self.app: ASGIApp = app
                self.kwargs = kwargs

            async def __call__(
                self, scope: Scope, receive: Receive, send: Send
            ) -> None:  # type: ignore
                await self.app(scope, receive, send)

        Middleware2.__name__ = "Middleware2"

        middleware1: Middleware = Middleware(Middleware1, param1="value1")
        middleware2: Middleware = Middleware(Middleware2, param2="value2")
        mock_middlewares.return_value = [middleware1, middleware2]

        mock_server_error_middleware_instance: MagicMock = MagicMock()
        mock_server_error_middleware_instance.__name__ = "ServerErrorMiddleware"
        mock_server_error_middleware.return_value = (
            mock_server_error_middleware_instance
        )

        mock_exception_middleware_instance: MagicMock = MagicMock()
        mock_exception_middleware_instance.__name__ = "ExceptionMiddleware"
        mock_exception_middleware.return_value = mock_exception_middleware_instance

        mock_server_error_middleware.__name__ = "ServerErrorMiddleware"
        mock_exception_middleware.__name__ = "ExceptionMiddleware"

        result = FastBlocks.build_middleware_stack(app, logger=mock_logger)

        assert result is not None

        mock_logger.info.assert_called_once_with("Middleware stack built")

    @patch("fastblocks.applications.middlewares")
    @patch("fastblocks.applications.ServerErrorMiddleware")
    @patch("fastblocks.applications.ExceptionMiddleware")
    def test_handle_error_handler_assignment(
        self,
        mock_exception_middleware: MagicMock,
        mock_server_error_middleware: MagicMock,
        mock_middlewares: MagicMock,
        mock_logger: MagicMock,
    ) -> None:
        app = MagicMock(spec=FastBlocks)
        app.debug = False

        custom_error_handler = MagicMock()

        app.exception_handlers = {
            404: handle_exception,
            500: custom_error_handler,
            Exception: MagicMock(),
        }

        app.user_middleware = []
        app.router = MagicMock()

        mock_middlewares.return_value = []

        mock_server_error_middleware.__name__ = "ServerErrorMiddleware"
        mock_exception_middleware.__name__ = "ExceptionMiddleware"

        mock_server_error_middleware_instance = MagicMock()
        mock_server_error_middleware_instance.__name__ = "ServerErrorMiddleware"
        mock_server_error_middleware.return_value = (
            mock_server_error_middleware_instance
        )

        mock_exception_middleware_instance = MagicMock()
        mock_exception_middleware_instance.__name__ = "ExceptionMiddleware"
        mock_exception_middleware.return_value = mock_exception_middleware_instance

        FastBlocks.build_middleware_stack(app, logger=mock_logger)

        mock_logger.info.assert_called_once_with("Middleware stack built")

    @patch("fastblocks.applications.install_error_handler")
    @patch("fastblocks.applications.set_editor")
    @patch("fastblocks.applications.depends.get")
    def test_initialize_with_none_parameters(
        self,
        mock_depends_get: MagicMock,
        mock_set_editor: MagicMock,
        mock_install_error_handler: MagicMock,
        mock_config: MagicMock,
    ) -> None:
        mock_depends_get.return_value = {}

        app = FastBlocks(config=mock_config)

        assert app.user_middleware == []
        assert app.exception_handlers == {404: handle_exception, 500: handle_exception}

    @patch("fastblocks.applications.get_installed_adapter")
    @patch("fastblocks.applications.install_error_handler")
    @patch("fastblocks.applications.set_editor")
    @patch("fastblocks.applications.depends.get")
    def test_logfire_integration(
        self,
        mock_depends_get: MagicMock,
        mock_set_editor: MagicMock,
        mock_install_error_handler: MagicMock,
        mock_get_installed_adapter: MagicMock,
        mock_config: MagicMock,
    ) -> None:
        mock_depends_get.return_value = {}
        mock_get_installed_adapter.return_value = True

        mock_logfire = MagicMock()
        mock_logfire.instrument_starlette = MagicMock()

        with patch.dict("sys.modules", {"logfire": mock_logfire}):
            FastBlocks(config=mock_config)

            mock_get_installed_adapter.assert_called_with("logfire")

            mock_logfire.instrument_starlette.assert_called_once()

import typing as t
from collections.abc import Awaitable, Callable
from unittest.mock import MagicMock, patch

from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import Response
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
        exception_handler: Callable[[Request, Exception], Awaitable[Response]],
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
        test_lifespan: Callable[[t.Any], t.AsyncGenerator[None, None]],
    ) -> None:
        mock_depends_get.return_value = {}

        app = FastBlocks(lifespan=test_lifespan, config=mock_config)

        assert app is not None

    @patch("fastblocks.applications.middlewares")
    def test_build_middleware_stack_correctly(
        self, mock_middlewares: MagicMock, mock_logger: MagicMock
    ) -> None:
        app = MagicMock(spec=FastBlocks)
        app.debug = False
        app.exception_handlers = {404: handle_exception, 500: handle_exception}
        app.user_middleware = []
        app.router = MagicMock()

        middleware1 = Middleware(MagicMock(), param1="value1")  # type: ignore
        middleware2 = Middleware(MagicMock(), param2="value2")  # type: ignore
        mock_middlewares.return_value = [middleware1, middleware2]

        result = FastBlocks.build_middleware_stack(app, logger=mock_logger)

        assert isinstance(result, MagicMock)
        mock_logger.debug.assert_called()
        mock_logger.info.assert_called_once_with("Middleware stack built")

    @patch("fastblocks.applications.middlewares")
    def test_handle_error_handler_assignment(
        self, mock_middlewares: MagicMock, mock_logger: MagicMock
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

        FastBlocks.build_middleware_stack(app, logger=mock_logger)

        mock_logger.debug.assert_called()
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

        with patch.dict("sys.modules", {"logfire": MagicMock()}):
            from sys import modules

            mock_logfire = modules["logfire"]
            mock_instrument_starlette = MagicMock()
            mock_logfire.instrument_starlette = MagicMock()  # type: ignore

            app = FastBlocks(config=mock_config)

            mock_get_installed_adapter.assert_called_with("logfire")
            mock_instrument_starlette.assert_called_once_with(app)

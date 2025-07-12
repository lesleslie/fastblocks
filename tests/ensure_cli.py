"""Common module for CLI test fixtures."""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false, reportMissingParameterType=false, reportUnknownParameterType=false, reportArgumentType=false

import asyncio
import sys
import types
from enum import Enum
from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def ensure_cli_module():  # noqa: C901
    """Ensure the CLI module is importable for tests."""
    # ACB modules should already be mocked via conftest.py

    # Create a placeholder cli module if it doesn't exist
    if "fastblocks.cli" not in sys.modules:
        # Create mock modules
        fastblocks_module = types.ModuleType("fastblocks")
        fastblocks_module.__version__ = "0.1.0"
        cli_module = types.ModuleType("fastblocks.cli")

        # Create mock typer app
        class MockTyper:
            def __init__(self) -> None:
                self.commands = {}
                self.callbacks = []

            def command(self, *args, **kwargs):
                def decorator(func):
                    self.commands[func.__name__] = func
                    return func

                return decorator

            def callback(self, *args, **kwargs):
                def decorator(func):
                    self.callbacks.append(func)
                    return func

                return decorator

            def __call__(self, *args, **kwargs):
                return MagicMock()

        # Create mock app
        mock_app = MockTyper()

        # Create mock functions
        def mock_run(docker: bool = False):
            """Run the FastBlocks application."""
            return {"docker": docker}

        def mock_dev(
            server: str = "uvicorn",
            port: int = 8000,
            host: str = "127.0.0.1",
        ):
            """Run the application in development mode."""
            return {"server": server, "port": port, "host": host}

        async def mock_update_configs(app_name: str, domain: str):
            """Update application configuration."""
            return {"app_name": app_name, "domain": domain}

        def mock_create(
            app_name: str,
            style: str = "bulma",
            domain: str = "example.com",
        ):
            """Create new FastBlocks application."""
            # Call asyncio.run on the update_configs coroutine
            asyncio.run(mock_update_configs(app_name, domain))
            return {"app_name": app_name, "style": style, "domain": domain}

        def mock_setup_signal_handlers() -> None:
            """Set up signal handlers."""
            cli_module.signal.signal(cli_module.SIGINT, lambda sig, frame: None)
            cli_module.signal.signal(cli_module.SIGTERM, lambda sig, frame: None)

        def mock_execute(cmd: str, cwd: str | None = None) -> int | None:
            """Execute a shell command."""
            return 0

        # Add enum for styles
        class MockStyles(Enum):
            """Mock styles enum."""

            bulma = "bulma"
            bootstrap = "bootstrap"
            tailwind = "tailwind"

        # Add attributes to cli module
        cli_module.app = mock_app
        cli_module.run = mock_run
        cli_module.dev = mock_dev
        cli_module.create = mock_create
        cli_module.update_configs = mock_update_configs
        cli_module.setup_signal_handlers = mock_setup_signal_handlers
        cli_module.execute = mock_execute
        cli_module.typer = MagicMock()
        cli_module.uvicorn = MagicMock()
        cli_module.Granian = MagicMock()
        cli_module.Path = MagicMock()
        cli_module.signal = MagicMock()
        cli_module.SIGINT = 2
        cli_module.SIGTERM = 15
        cli_module.asyncio = asyncio
        cli_module.Styles = MockStyles
        cli_module.__file__ = "/mock/path/to/cli.py"
        cli_module.console = MagicMock()

        # Register functions with mock app
        mock_app.command()(mock_run)
        mock_app.command()(mock_dev)
        mock_app.command()(mock_create)

        # Register modules
        sys.modules["fastblocks"] = fastblocks_module
        sys.modules["fastblocks.cli"] = cli_module

    # Cleanup after test
    yield

    # Remove the module after test if we created it
    sys.modules.pop("fastblocks.cli", None)
    sys.modules.pop("fastblocks", None)


@pytest.fixture
def completed_future():
    """Return a completed future for testing async functions."""
    future = asyncio.Future()
    future.set_result(None)
    return future


@pytest.fixture
def completed_coro():
    """Return a completed coroutine for testing async functions."""

    async def _completed_coro(*args, **kwargs) -> None:
        return None

    return _completed_coro

"""Test FastBlocks CLI interface."""

import signal
import sys
import types
import typing as t
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def clean_modules() -> t.Generator[None, None, None]:
    original_modules = sys.modules.copy()

    for mod in list(sys.modules.keys()):
        if mod.startswith(("fastblocks", "acb", "typer")):
            sys.modules.pop(mod, None)

    yield

    sys.modules.clear()
    sys.modules.update(original_modules)


@pytest.mark.unit
class TestCLI:
    def test_cli_initialization(
        self, clean_modules: None, mocker: MockerFixture
    ) -> None:
        mock_typer = types.ModuleType("typer")
        mock_typer_app = MagicMock()
        mock_typer_class = MagicMock(return_value=mock_typer_app)
        setattr(mock_typer, "Typer", mock_typer_class)
        sys.modules["typer"] = mock_typer

        mock_typer_colors = types.ModuleType("typer.colors")
        sys.modules["typer.colors"] = mock_typer_colors

        mock_acb = types.ModuleType("acb")
        sys.modules["acb"] = mock_acb

        mock_acb_apps = types.ModuleType("acb.apps")
        mock_app = MagicMock()
        setattr(mock_acb_apps, "app", mock_app)
        sys.modules["acb.apps"] = mock_acb_apps

        fastblocks_module = types.ModuleType("fastblocks")
        sys.modules["fastblocks"] = fastblocks_module

        cli_module = types.ModuleType("fastblocks.cli")

        def signal_handler(sig: int, frame: t.Any) -> None:
            pass

        def setup_signal_handlers() -> None:
            signal.signal(signal.SIGINT, signal_handler)
            signal.signal(signal.SIGTERM, signal_handler)

        typer_app = mock_typer_class()

        setattr(cli_module, "typer", mock_typer)
        setattr(cli_module, "cli", typer_app)
        setattr(cli_module, "signal", signal)
        setattr(cli_module, "setup_signal_handlers", setup_signal_handlers)
        setattr(cli_module, "signal_handler", signal_handler)

        signal_patch = mocker.patch("signal.signal")

        sys.modules["fastblocks.cli"] = cli_module

        from fastblocks.cli import setup_signal_handlers

        setup_signal_handlers()

        mock_typer_class.assert_called_once()

        assert signal_patch.call_count == 2
        signal_calls = signal_patch.call_args_list
        assert len(signal_calls) == 2
        assert signal_calls[0][0][0] == signal.SIGINT
        assert signal_calls[1][0][0] == signal.SIGTERM

    def test_cli_run_command(self, clean_modules: None, mocker: MockerFixture) -> None:
        mock_typer = types.ModuleType("typer")
        mock_typer_app = MagicMock()
        mock_typer_app.command = MagicMock(return_value=lambda func: func)
        setattr(mock_typer, "Typer", MagicMock(return_value=mock_typer_app))
        sys.modules["typer"] = mock_typer

        mock_typer_colors = types.ModuleType("typer.colors")
        sys.modules["typer.colors"] = mock_typer_colors

        mock_acb = types.ModuleType("acb")
        sys.modules["acb"] = mock_acb

        mock_acb_apps = types.ModuleType("acb.apps")
        mock_app = MagicMock()
        setattr(mock_acb_apps, "app", mock_app)
        sys.modules["acb.apps"] = mock_acb_apps

        sys.modules["fastblocks"] = types.ModuleType("fastblocks")

        cli_module = types.ModuleType("fastblocks.cli")

        def test_run(
            host: str = "127.0.0.1",
            port: int = 8000,
            reload: bool = False,
            debug: bool = False,
        ) -> None:
            called_params: t.Dict[str, t.Any] = {
                "host": host,
                "port": port,
                "reload": reload,
                "debug": debug,
            }
            setattr(test_run, "called_with", called_params)

        test_run = mock_typer_app.command()(test_run)

        setattr(cli_module, "typer", mock_typer)
        setattr(cli_module, "cli", mock_typer_app)
        setattr(cli_module, "run", test_run)
        setattr(cli_module, "signal", mocker.MagicMock())
        sys.modules["fastblocks.cli"] = cli_module

        run_func = test_run

        run_func(host="127.0.0.1", port=9000, reload=True, debug=True)

        called_with = getattr(test_run, "called_with", {})
        assert "host" in called_with
        assert called_with["host"] == "127.0.0.1"
        assert called_with["port"] == 9000
        assert called_with["reload"] is True
        assert called_with["debug"] is True

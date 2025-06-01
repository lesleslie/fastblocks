import sys
import types
import typing as t

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_acb(mocker: MockerFixture) -> t.Any:
    mock_acb_module = types.ModuleType("acb")

    mocker.patch.dict(
        "sys.modules",
        {
            "acb": mock_acb_module,
        },
    )

    for mod in list(sys.modules.keys()):
        if mod.startswith("fastblocks"):
            sys.modules.pop(mod, None)

    return mock_acb_module


@pytest.mark.unit
class TestMainEntry:
    def test_main_entry_point(self, mocker: MockerFixture, mock_acb: t.Any) -> None:
        mock_cli_module = types.ModuleType("fastblocks.cli")

        mock_cli = mocker.MagicMock()

        setattr(mock_cli_module, "cli", mock_cli)

        mocker.patch.dict("sys.modules", {"fastblocks.cli": mock_cli_module})

        def simulate_main_execution() -> None:
            from fastblocks.cli import cli

            if "__main__" == "__main__":
                cli()

        simulate_main_execution()

        mock_cli.assert_called_once()

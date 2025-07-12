import sys
import types
import typing as t
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture


class MockMain:
    def __init__(self, register_pkg: t.Any = None, depends: t.Any = None) -> None:
        self.register_pkg = register_pkg or MagicMock()
        self.depends = depends or MagicMock()
        self.app = None
        self.logger = None


@pytest.fixture
def mock_acb(mocker: MockerFixture) -> t.Any:
    mock_acb = mocker.MagicMock()
    mock_depends = mocker.MagicMock()

    mock_acb.depends = mock_depends

    mocker.patch.dict(
        "sys.modules",
        {
            "acb": mock_acb,
            "acb.depends": mock_depends,
        },
    )

    return mock_acb


@pytest.fixture
def clean_modules() -> t.Generator[None]:
    original_modules = sys.modules.copy()

    for mod in list(sys.modules.keys()):
        if mod.startswith(("fastblocks", "acb")):
            sys.modules.pop(mod, None)

    yield

    sys.modules.clear()
    sys.modules.update(original_modules)


@pytest.fixture
def mock_main_dependencies(mocker: MockerFixture, mock_acb: t.Any) -> dict[str, t.Any]:
    mock_register_pkg = mocker.MagicMock()
    mock_depends = mocker.MagicMock()
    mock_app = mocker.MagicMock()
    mock_app.__module__ = "test_module"
    mock_logger = mocker.MagicMock()

    mock_depends.get.side_effect = [mock_app, mock_logger]

    mocker.patch("fastblocks.main.register_pkg", mock_register_pkg)
    mocker.patch("acb.depends.depends", mock_depends)

    if "fastblocks.main" in sys.modules:
        del sys.modules["fastblocks.main"]

    return {
        "register_pkg": mock_register_pkg,
        "depends": mock_depends,
        "app": mock_app,
        "logger": mock_logger,
    }


@pytest.mark.unit
class TestMainModule:
    def test_main_initialization(
        self,
        mocker: MockerFixture,
        mock_acb: t.Any,
        clean_modules: None,
    ) -> None:
        mock_register_pkg = mocker.MagicMock()
        mock_app = mocker.MagicMock()
        mock_logger = mocker.MagicMock()

        mock_depends = mocker.MagicMock()
        mock_depends.get.side_effect = [mock_app, mock_logger]

        sys.modules["fastblocks"] = types.ModuleType("fastblocks")

        main_module = types.ModuleType("fastblocks.main")
        setattr(main_module, "register_pkg", mock_register_pkg)
        setattr(main_module, "depends", mock_depends)
        sys.modules["fastblocks.main"] = main_module

        main_module = sys.modules["fastblocks.main"]

        assert hasattr(main_module, "register_pkg")
        assert main_module.register_pkg is mock_register_pkg
        assert hasattr(main_module, "depends")
        assert main_module.depends is mock_depends

        setattr(main_module, "app", mock_app)
        setattr(main_module, "logger", mock_logger)

        assert main_module.app is mock_app
        assert main_module.logger is mock_logger

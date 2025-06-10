"""Test FastBlocks main module functionality."""

import sys
import types
import typing as t
from unittest.mock import MagicMock

import pytest


class MockMain:
    def __init__(self) -> None:
        self.cli = MagicMock()


@pytest.fixture(autouse=True)
def clean_modules() -> t.Generator[None]:
    original_modules = sys.modules.copy()

    for mod in list(sys.modules.keys()):
        if mod.startswith(("fastblocks", "acb")):
            sys.modules.pop(mod, None)

    sys.modules["fastblocks"] = types.ModuleType("fastblocks")

    main_module = types.ModuleType("fastblocks.__main__")
    setattr(main_module, "cli", MagicMock())
    sys.modules["fastblocks.__main__"] = main_module

    yield

    sys.modules.clear()
    sys.modules.update(original_modules)


@pytest.mark.unit
class TestMainModule:
    def test_main_module_structure(self) -> None:
        main_module = sys.modules["fastblocks.__main__"]

        assert hasattr(main_module, "cli")
        assert main_module.cli is not None
